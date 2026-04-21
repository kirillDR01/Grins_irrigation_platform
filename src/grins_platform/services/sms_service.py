"""SMS Service for customer communications.

Refactored to accept a pluggable BaseSMSProvider, Recipient-based sends,
type-scoped consent, campaign-scoped dedupe, rate-limit integration,
and merge-field templating.

Validates: Requirements 1.5, 1.6, 4.5, 4.6, 8.1-8.6, 9.1-9.5, 11.2, 11.3,
           24, 26, 38, 39
"""

from __future__ import annotations

import os
import re
import time as _time_mod
from datetime import datetime, time, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import (
    select,
    update as sa_update,
)

from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.sent_message import SentMessage
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.schemas.ai import DeliveryStatus, MessageType
from grins_platform.services.sms.audit import log_consent_hard_stop
from grins_platform.services.sms.consent import ConsentType, check_sms_consent
from grins_platform.services.sms.templating import render_template

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.services.sms.base import (
        BaseSMSProvider,
        ProviderSendResult,
    )
    from grins_platform.services.sms.rate_limit_tracker import SMSRateLimitTracker
    from grins_platform.services.sms.recipient import Recipient

logger = get_logger(__name__)

# Exact opt-out keywords (Req 8.1)
EXACT_OPT_OUT_KEYWORDS: frozenset[str] = frozenset(
    {"stop", "quit", "cancel", "unsubscribe", "end", "revoke"},
)

# Informal opt-out phrases (Req 8.5)
INFORMAL_OPT_OUT_PHRASES: tuple[str, ...] = (
    "stop texting me",
    "take me off the list",
    "no more texts",
    "opt out",
    "don't text me",
)

# Central timezone for time window enforcement
CT_TZ = ZoneInfo("America/Chicago")

# Opt-out confirmation message
OPT_OUT_CONFIRMATION_MSG = (
    "You've been unsubscribed from Grins Irrigation texts. Reply START to re-subscribe."
)

# Poll reply auto-confirmation messages
POLL_REPLY_CONFIRMED_MSG = (
    "Thanks! We received your response: {option_label}. "
    "We'll be in touch to confirm your appointment."
)

# Gap 03.B — message types whose earlier rows for the same appointment are
# tombstoned (``superseded_at = NOW()``) when a new one is sent. Cancellation
# is included because a reactivation SMS (reschedule) must supersede it.
_SUPERSEDABLE_MESSAGE_TYPES: frozenset[str] = frozenset(
    {
        MessageType.APPOINTMENT_CONFIRMATION.value,
        MessageType.APPOINTMENT_RESCHEDULE.value,
        MessageType.APPOINTMENT_CANCELLATION.value,
        MessageType.APPOINTMENT_REMINDER.value,
    }
)

POLL_REPLY_UNCLEAR_MSG = (
    "Thanks for your reply! We received your message and will follow up shortly."
)

# Sender prefix and STOP footer
_DEFAULT_PREFIX = "Grins Irrigation: "
_DEFAULT_FOOTER = " Reply STOP to opt out."

# Legacy ``message_type`` string → enum mapping for ``send_automated_message``
# callers. Falls back to ``AUTOMATED_NOTIFICATION`` for unknown strings so
# dedup and audit still function (bughunt CR-8).
_AUTOMATED_STR_TO_MESSAGE_TYPE: dict[str, MessageType] = {
    "lead_confirmation": MessageType.LEAD_CONFIRMATION,
    "estimate_sent": MessageType.ESTIMATE_SENT,
    "contract_sent": MessageType.CONTRACT_SENT,
    "campaign": MessageType.CAMPAIGN,
    "automated": MessageType.AUTOMATED_NOTIFICATION,
    "automated_notification": MessageType.AUTOMATED_NOTIFICATION,
    "appointment_reminder": MessageType.APPOINTMENT_REMINDER,
    "review_request": MessageType.REVIEW_REQUEST,
}


def _mask_phone(phone: str) -> str:
    """Mask phone for logging: +1XXX***XXXX."""
    if len(phone) >= 10:
        return phone[:4] + "***" + phone[-4:]
    return "***"


class SMSError(Exception):
    """Base exception for SMS errors."""


class SMSOptInError(SMSError):
    """Raised when customer has not opted in to SMS."""


class SMSConsentDeniedError(SMSError):
    """Raised when consent check fails."""


class SMSRateLimitDeniedError(SMSError):
    """Raised when rate limit check denies the send."""


class SMSService(LoggerMixin):
    """Service for sending SMS messages via a pluggable provider."""

    DOMAIN = "business"

    def __init__(
        self,
        session: AsyncSession,
        provider: BaseSMSProvider | None = None,
        rate_limit_tracker: SMSRateLimitTracker | None = None,
    ) -> None:
        """Initialize SMS service.

        Args:
            session: Database session.
            provider: SMS provider. When ``None``, the env-driven factory is
                used — ``SMS_PROVIDER=null`` keeps tests silent, while dev/prod
                default to ``callrail``. Callers that need a silent stub should
                pass ``NullProvider()`` explicitly.
            rate_limit_tracker: Optional rate limit tracker.
        """
        super().__init__()
        self.session = session
        self.message_repo = SentMessageRepository(session)
        if provider is not None:
            self.provider = provider
        else:
            from grins_platform.services.sms.factory import (  # noqa: PLC0415
                get_sms_provider,
            )

            self.provider = get_sms_provider()
        self.rate_limit_tracker = rate_limit_tracker
        self._prefix = os.environ.get("SMS_SENDER_PREFIX", _DEFAULT_PREFIX)
        self._footer = _DEFAULT_FOOTER

    async def send_message(
        self,
        recipient: Recipient,
        message: str,
        message_type: MessageType,
        consent_type: ConsentType = "transactional",
        campaign_id: UUID | None = None,
        job_id: UUID | None = None,
        appointment_id: UUID | None = None,
        *,
        skip_formatting: bool = False,
    ) -> dict[str, Any]:
        """Send an SMS message via the configured provider.

        Args:
            recipient: Unified Recipient (customer, lead, or ad-hoc).
            message: Message body (may contain merge fields).
            message_type: Type of message.
            consent_type: Consent scope (marketing/transactional/operational).
            campaign_id: Optional campaign ID for B4 dedupe scoping.
            job_id: Optional job ID.
            appointment_id: Optional appointment ID.
            skip_formatting: If True, skip prefix/footer/template rendering.

        Returns:
            Result dict with success, message_id, status.

        Raises:
            SMSConsentDeniedError: If consent check fails.
            SMSRateLimitDeniedError: If rate limit denies the send.
            SMSError: If sending fails.
        """
        masked = _mask_phone(recipient.phone)
        _send_t0 = _time_mod.monotonic()

        logger.info(
            "sms.send.requested",
            phone=masked,
            message_type=message_type.value,
            consent_type=consent_type,
            source_type=recipient.source_type,
            provider=self.provider.provider_name,
        )
        self.log_started(
            "send_message",
            phone=masked,
            message_type=message_type.value,
            consent_type=consent_type,
            source_type=recipient.source_type,
        )

        # S11: Type-scoped consent check
        has_consent = await check_sms_consent(
            self.session,
            recipient.phone,
            consent_type,
        )
        if not has_consent:
            logger.info(
                "sms.consent.denied",
                phone=masked,
                consent_type=consent_type,
            )
            self.log_rejected("send_message", reason="consent_denied")
            msg = f"Consent denied for {masked} (type={consent_type})"
            raise SMSConsentDeniedError(msg)

        # B4: Campaign-scoped dedupe (24h window)
        if campaign_id is not None:
            dupes = await self._check_campaign_dedupe(
                recipient,
                campaign_id,
                message_type,
            )
            if dupes:
                self.log_rejected(
                    "send_message",
                    reason="campaign_dedupe",
                    campaign_id=str(campaign_id),
                )
                return {
                    "success": False,
                    "reason": "Duplicate: same recipient+campaign within 24h",
                    "recent_message_id": str(dupes[0].id),
                    "recent_message_sent_at": dupes[0].created_at.isoformat(),
                }
        elif recipient.customer_id is not None:
            # Bug #4 fix: scope appointment_confirmation dedupe per appointment_id
            dedupe_appointment_id = (
                appointment_id
                if message_type == MessageType.APPOINTMENT_CONFIRMATION
                and appointment_id is not None
                else None
            )
            legacy_dupes = await self.message_repo.get_by_customer_and_type(
                customer_id=recipient.customer_id,
                message_type=message_type,
                hours_back=24,
                appointment_id=dedupe_appointment_id,
            )
            if legacy_dupes:
                self.log_rejected(
                    "send_message",
                    reason="duplicate_message_within_24_hours",
                )
                sent_at = legacy_dupes[0].created_at.isoformat()
                return {
                    "success": False,
                    "reason": "Duplicate message prevented",
                    "recent_message_id": str(legacy_dupes[0].id),
                    "recent_message_sent_at": sent_at,
                }

        # Rate limit check
        if self.rate_limit_tracker is not None:
            rl_result = await self.rate_limit_tracker.check()
            if not rl_result.allowed:
                logger.info(
                    "sms.rate_limit.denied",
                    phone=masked,
                    retry_after=rl_result.retry_after_seconds,
                )
                # Create a scheduled message instead of failing
                scheduled_for = datetime.now(tz=timezone.utc) + timedelta(
                    seconds=rl_result.retry_after_seconds,
                )
                sent_message = SentMessage(
                    customer_id=recipient.customer_id,
                    lead_id=recipient.lead_id,
                    job_id=job_id,
                    appointment_id=appointment_id,
                    campaign_id=campaign_id,
                    message_type=message_type.value,
                    message_content=message,
                    recipient_phone=recipient.phone,
                    delivery_status=DeliveryStatus.SCHEDULED.value,
                    scheduled_for=scheduled_for,
                )
                self.session.add(sent_message)
                await self.session.flush()
                return {
                    "success": True,
                    "deferred": True,
                    "message_id": str(sent_message.id),
                    "status": "scheduled",
                    "scheduled_for": scheduled_for.isoformat(),
                }

        # Render merge fields + format message
        if not skip_formatting:
            context = {
                "first_name": recipient.first_name or "",
                "last_name": recipient.last_name or "",
            }
            rendered = render_template(message, context)
            formatted = f"{self._prefix}{rendered}{self._footer}"
        else:
            formatted = message

        # Normalize phone
        formatted_phone = self._format_phone(recipient.phone)

        # Create message record
        sent_message = SentMessage(
            customer_id=recipient.customer_id,
            lead_id=recipient.lead_id,
            job_id=job_id,
            appointment_id=appointment_id,
            campaign_id=campaign_id,
            message_type=message_type.value,
            message_content=formatted,
            recipient_phone=formatted_phone,
            delivery_status=DeliveryStatus.PENDING.value,
        )
        self.session.add(sent_message)
        await self.session.flush()
        await self.session.refresh(sent_message)

        # Send via provider
        try:
            result = await self.provider.send_text(formatted_phone, formatted)

            # Update rate limit tracker from provider response headers
            rl_hourly_remaining: int | None = None
            rl_daily_remaining: int | None = None
            if self.rate_limit_tracker is not None and result.raw_response is not None:
                raw_resp = result.raw_response
                if "_response_headers" in raw_resp:
                    await self.rate_limit_tracker.update_from_headers(
                        raw_resp["_response_headers"],
                    )
                rl_state = await self.rate_limit_tracker.check()
                rl_hourly_remaining = rl_state.state.hourly_remaining
                rl_daily_remaining = rl_state.state.daily_remaining

            sent_message.delivery_status = DeliveryStatus.SENT.value
            sent_message.provider_message_id = result.provider_message_id
            sent_message.provider_conversation_id = result.provider_conversation_id
            sent_message.provider_thread_id = result.provider_thread_id
            sent_message.sent_at = datetime.now(tz=timezone.utc)
            await self.session.flush()

            latency_ms = int((_time_mod.monotonic() - _send_t0) * 1000)
            logger.info(
                "sms.send.succeeded",
                phone=masked,
                provider=self.provider.provider_name,
                provider_conversation_id=result.provider_conversation_id,
                provider_thread_id=result.provider_thread_id,
                latency_ms=latency_ms,
                hourly_remaining=rl_hourly_remaining,
                daily_remaining=rl_daily_remaining,
                x_request_id=result.request_id,
            )
            self.log_completed("send_message", message_id=str(sent_message.id))

            # Gap 03.B — mark prior confirmation-like SMSes for the same
            # appointment as superseded so ``find_confirmation_message``
            # no longer routes stale-thread replies to the moved
            # appointment. Failure is log-and-swallowed: the outbound SMS
            # has already been delivered, so telemetry should not fail it.
            if (
                sent_message.appointment_id is not None
                and sent_message.message_type in _SUPERSEDABLE_MESSAGE_TYPES
            ):
                try:
                    await self.session.execute(
                        sa_update(SentMessage)
                        .where(
                            SentMessage.appointment_id == sent_message.appointment_id,
                            SentMessage.id != sent_message.id,
                            SentMessage.message_type.in_(_SUPERSEDABLE_MESSAGE_TYPES),
                            SentMessage.superseded_at.is_(None),
                        )
                        .values(superseded_at=datetime.now(tz=timezone.utc)),
                    )
                    await self.session.flush()
                except Exception as supersede_exc:
                    logger.exception(
                        "sms.supersede.failed",
                        appointment_id=str(sent_message.appointment_id),
                        new_message_id=str(sent_message.id),
                        error=str(supersede_exc),
                    )

            # CRM2 Req 11.3: auto-update lead last_contacted_at on outbound
            await self._touch_lead_last_contacted(lead_id=recipient.lead_id)

            return {
                "success": True,
                "message_id": str(sent_message.id),
                "provider_message_id": result.provider_message_id,
                "status": "sent",
            }

        except Exception as e:
            sent_message.delivery_status = DeliveryStatus.FAILED.value
            sent_message.error_message = str(e)
            await self.session.flush()

            latency_ms = int((_time_mod.monotonic() - _send_t0) * 1000)
            logger.exception(
                "sms.send.failed",
                phone=masked,
                provider=self.provider.provider_name,
                latency_ms=latency_ms,
                error=str(e),
            )
            self.log_failed("send_message", error=e)
            msg = f"Failed to send SMS: {e}"
            raise SMSError(msg) from e

    async def _check_campaign_dedupe(
        self,
        recipient: Recipient,
        campaign_id: UUID,
        message_type: MessageType,  # noqa: ARG002
    ) -> list[SentMessage]:
        """Check for duplicate sends within a campaign (B4 fix)."""
        from sqlalchemy import and_  # noqa: PLC0415

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
        conditions = [
            SentMessage.campaign_id == campaign_id,
            SentMessage.recipient_phone == self._format_phone(recipient.phone),
            SentMessage.created_at >= cutoff,
        ]
        stmt = (
            select(SentMessage)
            .where(and_(*conditions))
            .order_by(SentMessage.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def send_automated_message(
        self,
        phone: str,
        message: str,
        message_type: str = "automated",
    ) -> dict[str, Any]:
        """Send an automated SMS via the canonical ``send_message`` path.

        Backwards-compat shim preserved for callers that only have a
        phone string and no Lead/Customer reference. Routes the send
        through ``send_message`` so it picks up SentMessage audit rows,
        per-type dedup, consent check, and phone-based lead-touch —
        instead of bypassing all of them (bughunt CR-8).

        Args:
            phone: Phone number
            message: Message content
            message_type: Legacy string type; mapped to ``MessageType``
                with fallback to ``AUTOMATED_NOTIFICATION``.

        Returns:
            Result dict with ``success``, ``reason`` or ``deferred`` keys.

        Validates: Requirements 8.6, 9.4, 9.5; bughunt 2026-04-14 CR-8.
        """
        from grins_platform.services.sms.recipient import (  # noqa: PLC0415
            Recipient,
        )

        self.log_started("send_automated_message", phone=_mask_phone(phone))

        # Enforce 8AM-9PM CT time window for automated sends (Req 9.4, 9.5).
        # Must run *before* send_message because send_message does not
        # carry the time-window policy.
        scheduled_time = self.enforce_time_window(phone, message, message_type)
        if scheduled_time is not None:
            self.log_completed(
                "send_automated_message",
                phone=_mask_phone(phone),
                deferred=True,
            )
            return {
                "success": True,
                "deferred": True,
                "scheduled_for": scheduled_time.isoformat(),
            }

        resolved_type = _AUTOMATED_STR_TO_MESSAGE_TYPE.get(
            message_type,
            MessageType.AUTOMATED_NOTIFICATION,
        )
        recipient = Recipient.from_adhoc(phone=phone)

        try:
            result = await self.send_message(
                recipient=recipient,
                message=message,
                message_type=resolved_type,
                consent_type="transactional",
                skip_formatting=True,
            )
        except SMSConsentDeniedError:
            self.log_rejected(
                "send_automated_message",
                reason="opted_out",
                phone=_mask_phone(phone),
            )
            return {"success": False, "reason": "opted_out"}
        except SMSError as exc:
            self.log_failed("send_automated_message", error=exc)
            return {"success": False, "reason": str(exc)}

        # Ad-hoc recipients have no lead_id, so send_message's built-in
        # lead-touch was a no-op. Try the phone-based lookup here so
        # Last Contacted still updates for legacy phone-only callers.
        await self._touch_lead_last_contacted(phone=phone)

        self.log_completed("send_automated_message", phone=_mask_phone(phone))
        return result

    async def _send_via_provider(
        self,
        phone: str,
        message: str,
    ) -> ProviderSendResult:
        """Send message via the configured provider.

        Args:
            phone: Formatted phone number.
            message: Message content.

        Returns:
            ProviderSendResult from the provider.
        """
        return await self.provider.send_text(phone, message)

    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format.

        Args:
            phone: Raw phone number

        Returns:
            E.164 formatted phone number
        """
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            digits = "1" + digits
        return f"+{digits}"

    async def _touch_lead_last_contacted(
        self,
        *,
        lead_id: UUID | None = None,
        phone: str | None = None,
    ) -> None:
        """Update lead.last_contacted_at on outbound/inbound SMS.

        Looks up by lead_id (outbound) or phone (inbound). Silently
        returns if no matching active lead is found.

        Validates: Requirement 11.3
        """
        from grins_platform.models.lead import Lead  # noqa: PLC0415

        if lead_id is None and phone is None:
            return

        try:
            if lead_id is not None:
                stmt = select(Lead).where(Lead.id == lead_id).limit(1)
            else:
                # Normalize phone to 10-digit for lead lookup
                assert phone is not None
                digits = re.sub(r"\D", "", phone)
                if len(digits) == 11 and digits.startswith("1"):
                    digits = digits[1:]
                if len(digits) != 10:
                    return
                stmt = (
                    select(Lead)
                    .where(Lead.phone == digits, Lead.moved_to.is_(None))
                    .order_by(Lead.created_at.desc())
                    .limit(1)
                )

            result = await self.session.execute(stmt)
            lead: Lead | None = result.scalar_one_or_none()
            if lead is not None:
                lead.last_contacted_at = datetime.now(tz=timezone.utc)
                await self.session.flush()
        except Exception:
            logger.warning(
                "sms.lead_contact_update.failed",
                lead_id=str(lead_id) if lead_id else None,
                phone=_mask_phone(phone) if phone else None,
                exc_info=True,
            )

    async def handle_inbound(
        self,
        from_phone: str,
        body: str,
        provider_sid: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle incoming SMS with STOP keyword, opt-out, and poll reply processing.

        Args:
            from_phone: Sender phone number
            body: Message body
            provider_sid: Provider message SID
            thread_id: Provider thread/conversation ID for campaign correlation

        Returns:
            Processing result

        Validates: Requirements 6.1-6.4, 7.1-7.4, 8.1-8.5
        """
        self.log_started("handle_inbound", from_phone=_mask_phone(from_phone))

        body_stripped = body.strip()
        body_lower = body_stripped.lower()

        # CRM2 Req 11.3: auto-update lead last_contacted_at on inbound SMS.
        # ``from_phone`` is the masked CallRail sender (``***3312``) for
        # provider-routed inbound, so this first-pass touch is a no-op in
        # that case. Each correlation branch below does a second pass with
        # the resolved real E.164 (bughunt L-7 / L-11).
        await self._touch_lead_last_contacted(phone=from_phone)

        # 10.1: Exact opt-out keyword match (Req 8.1, 8.2, 8.3, 8.4)
        if body_lower in EXACT_OPT_OUT_KEYWORDS:
            result = await self._process_exact_opt_out(
                from_phone, body_lower, thread_id=thread_id
            )
            # Bookkeeping: record STOP as campaign response (Req 6.1-6.4)
            # Independent — failure must not block consent revocation
            if thread_id:
                await self._record_opt_out_bookkeeping(
                    from_phone,
                    body,
                    provider_sid,
                    thread_id,
                )
            return result

        # 10.2: Informal opt-out phrase detection (Req 8.5)
        if self._matches_informal_opt_out(body_lower):
            return await self._flag_informal_opt_out(from_phone, body_stripped)

        # Poll reply branch: attempt correlation when thread_id present (Req 7.1-7.4)
        if thread_id:
            poll_result = await self._try_poll_reply(
                from_phone,
                body,
                provider_sid,
                thread_id,
            )
            if poll_result is not None:
                return poll_result

        # Y/R/C confirmation reply branch (CRM2 Req 24.1-24.8)
        if thread_id:
            confirmation_result = await self._try_confirmation_reply(
                from_phone,
                body_stripped,
                provider_sid,
                thread_id,
            )
            if confirmation_result is not None:
                return confirmation_result

        # Delegate to existing webhook handler for other messages
        return await self.handle_webhook(from_phone, body, provider_sid)

    async def _record_opt_out_bookkeeping(
        self,
        from_phone: str,
        body: str,
        provider_sid: str,
        thread_id: str,
    ) -> None:
        """Record STOP reply as campaign_responses row (independent bookkeeping).

        Failure here does not block consent revocation.

        Validates: Req 6.2, 6.4
        """
        try:
            from grins_platform.services.campaign_response_service import (  # noqa: PLC0415
                CampaignResponseService,
            )
            from grins_platform.services.sms.base import InboundSMS  # noqa: PLC0415

            svc = CampaignResponseService(self.session)
            await svc.record_opt_out_as_response(
                InboundSMS(
                    from_phone=from_phone,
                    body=body,
                    provider_sid=provider_sid,
                    thread_id=thread_id,
                ),
            )
        except Exception:
            logger.warning(
                "campaign.response.opt_out_bookkeeping_failed",
                phone_masked=_mask_phone(from_phone),
                exc_info=True,
            )

    async def _try_poll_reply(
        self,
        from_phone: str,
        body: str,
        provider_sid: str,
        thread_id: str,
    ) -> dict[str, Any] | None:
        """Attempt to route inbound as a poll reply.

        Returns a result dict if the reply was parsed or needs_review
        (suppressing communications table write). Returns None for orphans
        so they fall through to the existing handle_webhook handler.

        Validates: Req 7.1, 7.2, 7.3, 7.4
        """
        from grins_platform.services.campaign_response_service import (  # noqa: PLC0415
            CampaignResponseService,
        )
        from grins_platform.services.sms.base import InboundSMS  # noqa: PLC0415

        svc = CampaignResponseService(self.session)
        inbound = InboundSMS(
            from_phone=from_phone,
            body=body,
            provider_sid=provider_sid,
            thread_id=thread_id,
        )
        row = await svc.record_poll_reply(inbound)

        # parsed/needs_review → send auto-reply confirmation, then return
        # without writing to communications (Req 7.2, 7.3)
        if row.status in ("parsed", "needs_review"):
            # Send auto-reply confirmation to the real E.164 phone
            # (row.phone is resolved from the outbound sent_message, not the
            # masked inbound from_phone).
            try:
                if row.status == "parsed":
                    confirmation_msg = POLL_REPLY_CONFIRMED_MSG.format(
                        option_label=row.selected_option_label
                        or row.selected_option_key,
                    )
                else:
                    confirmation_msg = POLL_REPLY_UNCLEAR_MSG

                await self.provider.send_text(row.phone, confirmation_msg)
                logger.info(
                    "sms.poll_reply.auto_reply_sent",
                    status=row.status,
                    phone=_mask_phone(row.phone),
                )
            except Exception:
                logger.warning(
                    "sms.poll_reply.auto_reply_failed",
                    status=row.status,
                    phone=_mask_phone(row.phone),
                    exc_info=True,
                )

            # Update lead Last Contacted using the correlated real phone
            # (bughunt L-7 / L-11).
            await self._touch_lead_last_contacted(phone=row.phone)

            self.log_completed(
                "handle_inbound",
                webhook_action="poll_reply",
                status=row.status,
                phone=_mask_phone(from_phone),
            )
            return {
                "action": "poll_reply",
                "phone": from_phone,
                "status": row.status,
                "option_key": row.selected_option_key,
            }

        # orphan → fall through to handle_webhook (Req 7.4)
        return None

    async def _try_confirmation_reply(
        self,
        from_phone: str,
        body: str,
        provider_sid: str,
        thread_id: str,
    ) -> dict[str, Any] | None:
        """Route inbound SMS to JobConfirmationService if thread matches a confirmation.

        Returns result dict if matched, None to fall through.

        Validates: CRM Changes Update 2 Req 24.1-24.4
        """
        from grins_platform.services.job_confirmation_service import (  # noqa: PLC0415
            JobConfirmationService,
            parse_confirmation_reply,
        )

        svc = JobConfirmationService(self.session)
        # Check if thread_id correlates to an APPOINTMENT_CONFIRMATION message
        # (bughunt L-14: use the public name now that one exists).
        original = await svc.find_confirmation_message(thread_id)
        keyword = parse_confirmation_reply(body)
        use_post_cancel_handler = False
        if original is None:
            # Gap 1.C — a free-text reply on the reschedule-follow-up
            # thread should still land on the open RescheduleRequest.
            # Keyword replies (Y/R/C) stay gated off the followup so
            # e.g. "2" inside a free-text date can't be misparsed as
            # RESCHEDULE on an unrelated follow-up thread.
            if keyword is None:
                original = await svc.find_reschedule_thread(thread_id)
            if original is None:
                # Gap 03.A — reply on a cancellation thread. Route to
                # the post-cancellation handler (Y → reconsider alert,
                # R → new reschedule request, else → needs_review).
                cancellation_original = await svc.find_cancellation_thread(
                    thread_id,
                )
                if cancellation_original is None:
                    return None
                original = cancellation_original
                use_post_cancel_handler = True
        if use_post_cancel_handler:
            result = await svc.handle_post_cancellation_reply(
                thread_id=thread_id,
                keyword=keyword,
                raw_body=body,
                from_phone=from_phone,
                provider_sid=provider_sid,
            )
        else:
            result = await svc.handle_confirmation(
                thread_id=thread_id,
                keyword=keyword,
                raw_body=body,
                from_phone=from_phone,
                provider_sid=provider_sid,
            )

        # Prefer the real E.164 phone from the original SentMessage. CallRail
        # masks the inbound sender (``***3312``), so falling through to
        # ``self._format_phone(from_phone)`` there would produce ``+3312``.
        reply_phone = result.get("recipient_phone") or self._format_phone(from_phone)

        # bughunt M-9 (E2E-8 survivor): the auto-reply and the reschedule
        # follow-up previously called ``provider.send_text`` directly, so
        # neither produced a ``SentMessage`` row — the audit trail missed
        # an entire class of outbound messages. Route them through
        # ``send_message`` with their own message_type so per-type dedup
        # and compliance reporting both stay accurate.
        from grins_platform.services.sms.recipient import (  # noqa: PLC0415
            Recipient,
        )

        reply_recipient = Recipient(
            phone=reply_phone,
            source_type="customer",
            customer_id=original.customer_id,
        )
        appointment_id = original.appointment_id
        job_id = original.job_id

        auto_reply = result.get("auto_reply")
        if auto_reply:
            try:
                _ = await self.send_message(
                    recipient=reply_recipient,
                    message=auto_reply,
                    message_type=MessageType.APPOINTMENT_CONFIRMATION_REPLY,
                    consent_type="transactional",
                    job_id=job_id,
                    appointment_id=appointment_id,
                )
            except Exception:
                logger.warning(
                    "sms.confirmation.auto_reply_failed",
                    phone=_mask_phone(reply_phone),
                    exc_info=True,
                )

        # Reschedule follow-up SMS (Req 14.1)
        follow_up_sms = result.get("follow_up_sms")
        if follow_up_sms:
            try:
                _ = await self.send_message(
                    recipient=reply_recipient,
                    message=follow_up_sms,
                    message_type=MessageType.RESCHEDULE_FOLLOWUP,
                    consent_type="transactional",
                    job_id=job_id,
                    appointment_id=appointment_id,
                )
            except Exception:
                logger.warning(
                    "sms.confirmation.follow_up_failed",
                    phone=_mask_phone(reply_phone),
                    exc_info=True,
                )

        # Update lead Last Contacted using the correlated real phone
        # (bughunt L-7 / L-11).
        await self._touch_lead_last_contacted(phone=reply_phone)

        self.log_completed(
            "handle_inbound",
            webhook_action="confirmation_reply",
            keyword=keyword.value if keyword else None,
            phone=_mask_phone(from_phone),
        )
        return {
            "action": "confirmation_reply",
            "phone": from_phone,
            "keyword": keyword.value if keyword else None,
            **result,
        }

    async def _process_exact_opt_out(
        self,
        phone: str,
        keyword: str,
        *,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Process exact opt-out keyword: create consent record and send confirmation.

        Args:
            phone: Sender phone number
            keyword: The matched keyword
            thread_id: Provider thread/conversation ID for resolving masked phones

        Returns:
            Processing result

        Validates: Requirements 8.1, 8.2, 8.3, 8.4
        """
        now = datetime.now(timezone.utc)

        # Resolve real phone from thread_id when provider masks the sender
        # (e.g. CallRail sends "***3312" instead of the full number).
        real_phone = phone
        if thread_id:
            try:
                from grins_platform.services.campaign_response_service import (  # noqa: PLC0415
                    CampaignResponseService,
                )

                svc = CampaignResponseService(self.session)
                corr = await svc.correlate_reply(thread_id)
                if corr.sent_message and corr.sent_message.recipient_phone:
                    real_phone = corr.sent_message.recipient_phone
            except Exception:
                logger.warning(
                    "sms.opt_out.phone_resolution_failed",
                    phone_masked=_mask_phone(phone),
                    thread_id=thread_id,
                    exc_info=True,
                )

        from grins_platform.services.sms.phone_normalizer import (  # noqa: PLC0415
            PhoneNormalizationError,
            normalize_to_e164,
        )

        try:
            formatted_phone = normalize_to_e164(real_phone)
        except PhoneNormalizationError:
            formatted_phone = self._format_phone(real_phone)

        record = SmsConsentRecord(
            phone_number=formatted_phone,
            consent_type="marketing",
            consent_given=False,
            consent_timestamp=now,
            consent_method="text_stop",
            consent_language_shown=f"Keyword: {keyword}",
            opt_out_timestamp=now,
            opt_out_method="text_stop",
            opt_out_processed_at=now,
            opt_out_confirmation_sent=True,
        )
        self.session.add(record)
        await self.session.flush()

        # Audit: hard STOP received (Requirement 41)
        await log_consent_hard_stop(
            self.session,
            phone_masked=_mask_phone(formatted_phone),
        )

        # Send confirmation SMS (Req 8.3)
        _ = await self.provider.send_text(formatted_phone, OPT_OUT_CONFIRMATION_MSG)

        # Update lead Last Contacted using the resolved real E.164 now that
        # correlation has run (bughunt L-7 / L-11).
        await self._touch_lead_last_contacted(phone=formatted_phone)

        self.log_completed(
            "handle_inbound",
            webhook_action="exact_opt_out",
            keyword=keyword,
            phone=_mask_phone(phone),
        )
        return {
            "action": "opt_out",
            "phone": phone,
            "keyword": keyword,
            "message": OPT_OUT_CONFIRMATION_MSG,
        }

    @staticmethod
    def _matches_informal_opt_out(body_lower: str) -> bool:
        """Check if message body contains an informal opt-out phrase.

        Args:
            body_lower: Lowercased message body

        Returns:
            True if informal opt-out phrase detected
        """
        return any(phrase in body_lower for phrase in INFORMAL_OPT_OUT_PHRASES)

    async def _flag_informal_opt_out(
        self,
        phone: str,
        body: str,
    ) -> dict[str, Any]:
        """Flag informal opt-out for admin review without auto-processing.

        Args:
            phone: Sender phone number
            body: Original message body

        Returns:
            Processing result

        Validates: Requirements 8.5
        """
        self.log_started(
            "flag_informal_opt_out",
            phone=_mask_phone(phone),
        )
        logger.warning(
            "sms.informal_opt_out.flagged",
            phone=_mask_phone(phone),
            action="admin_review_required",
        )
        self.log_completed(
            "handle_inbound",
            webhook_action="informal_opt_out_flagged",
            phone=_mask_phone(phone),
        )
        return {
            "action": "informal_opt_out_flagged",
            "phone": phone,
            "body": body,
            "message": "Informal opt-out detected. Flagged for admin review.",
        }

    async def check_sms_consent_legacy(self, phone: str) -> bool:
        """Check most recent consent record for a phone number.

        Thin wrapper around the consent module for backward compatibility.

        Args:
            phone: Phone number (any format)

        Returns:
            True if consent allows transactional sends.
        """
        return await check_sms_consent(self.session, phone)

    # Alias for backward compatibility with callers using the old name
    async def check_sms_consent(self, phone: str) -> bool:
        """Alias for check_sms_consent_legacy."""
        return await self.check_sms_consent_legacy(phone)

    def enforce_time_window(
        self,
        phone: str,
        message: str,  # noqa: ARG002
        message_type: str = "automated",
    ) -> datetime | None:
        """Enforce 8AM-9PM CT time window for automated SMS.

        Args:
            phone: Recipient phone number (for logging)
            message: Message content (for logging)
            message_type: "automated" or "manual"

        Returns:
            None if send immediately, or scheduled datetime if deferred.

        Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
        """
        # Manual messages bypass time window (Req 9.5)
        if message_type == "manual":
            return None

        now_ct = datetime.now(CT_TZ)
        window_start = time(8, 0)
        window_end = time(21, 0)

        if window_start <= now_ct.time() < window_end:
            return None

        # Compute next 8:00 AM CT
        if now_ct.time() >= window_end:
            next_day = now_ct.date() + timedelta(days=1)
        else:
            next_day = now_ct.date()

        scheduled = datetime.combine(next_day, window_start, tzinfo=CT_TZ)

        self.log_started(
            "enforce_time_window",
            original_time=now_ct.isoformat(),
            scheduled_time=scheduled.isoformat(),
            phone=_mask_phone(phone),
        )
        logger.info(
            "sms.time_window.deferred",
            original_time=now_ct.isoformat(),
            scheduled_time=scheduled.isoformat(),
            phone=_mask_phone(phone),
        )
        return scheduled

    async def handle_webhook(
        self,
        from_phone: str,
        body: str,
        provider_sid: str,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Handle incoming SMS webhook.

        Args:
            from_phone: Sender phone number
            body: Message body
            provider_sid: Provider message SID

        Returns:
            Processing result
        """
        self.log_started("handle_webhook", from_phone=_mask_phone(from_phone))

        body_lower = body.strip().lower()

        # Handle opt-out keywords (bughunt H-10: route through the canonical
        # _process_exact_opt_out so an SmsConsentRecord is actually written;
        # the previous fallback returned opt_out without persisting consent).
        if body_lower in EXACT_OPT_OUT_KEYWORDS:
            return await self._process_exact_opt_out(from_phone, body_lower)

        # Handle confirmation keywords
        if body_lower in ["yes", "confirm", "y"]:
            self.log_completed("handle_webhook", webhook_action="confirm")
            return {
                "action": "confirm",
                "phone": from_phone,
                "message": "Thank you for confirming!",
            }

        # Handle help keywords
        if body_lower in ["help", "info"]:
            self.log_completed("handle_webhook", webhook_action="help")
            return {
                "action": "help",
                "phone": from_phone,
                "message": "Reply STOP to unsubscribe. Call (612) 555-0100 for help.",
            }

        # Default - forward to admin
        self.log_completed("handle_webhook", webhook_action="forward")
        return {
            "action": "forward",
            "phone": from_phone,
            "body": body,
            "message": "Message received and forwarded to admin.",
        }

    async def check_opt_in(self, customer_id: UUID) -> bool:  # noqa: ARG002
        """Check if customer has opted in to SMS.

        Args:
            customer_id: Customer ID

        Returns:
            True if opted in, False otherwise
        """
        # Placeholder - would query customer record
        return False
