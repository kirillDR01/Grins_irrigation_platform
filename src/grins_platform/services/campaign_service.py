"""Campaign management service for marketing campaigns.

Handles campaign creation, sending with consent gating, delivery stats,
and automation rule evaluation.

Validates: CRM Gap Closure Req 45.3, 45.4, 45.5, 45.6, 45.7, 45.8, 45.9, 45.10
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.business_setting import BusinessSetting
from grins_platform.models.campaign import Campaign
from grins_platform.models.customer import Customer
from grins_platform.models.enums import (
    CampaignStatus,
    CampaignType,
    EmailType,
    NotificationType,
)
from grins_platform.models.lead import Lead
from grins_platform.models.property import Property
from grins_platform.schemas.ai import MessageType
from grins_platform.schemas.campaign import (
    CampaignCreate,
    CampaignSendResult,
    CampaignStats,
    CampaignUpdate,
    TargetAudience,
)
from grins_platform.services.sms.phone_normalizer import normalize_to_e164
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms_service import SMSConsentDeniedError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.repositories.campaign_repository import (
        CampaignRepository,
    )
    from grins_platform.services.email_service import EmailService
    from grins_platform.services.sms_service import SMSService


# Default CAN-SPAM unsubscribe text appended to every campaign message
_UNSUBSCRIBE_TEXT = "\n\nTo unsubscribe, reply STOP or contact us at the address above."

# Default physical address fallback when business setting is missing
_DEFAULT_ADDRESS = "Grin's Irrigations"


class CampaignAlreadySentError(Exception):
    """Raised when attempting to send an already-sent campaign."""

    def __init__(self, campaign_id: UUID) -> None:
        self.campaign_id = campaign_id
        super().__init__(
            f"Campaign {campaign_id} has already been sent or is sending.",
        )


class CampaignNotFoundError(Exception):
    """Raised when a campaign is not found."""

    def __init__(self, campaign_id: UUID) -> None:
        self.campaign_id = campaign_id
        super().__init__(f"Campaign {campaign_id} not found.")


class NoRecipientsError(Exception):
    """Raised when target audience filter matches zero customers."""

    def __init__(self, campaign_id: UUID) -> None:
        self.campaign_id = campaign_id
        super().__init__(
            f"Campaign {campaign_id}: target audience matched zero recipients.",
        )


class CampaignNotDraftError(Exception):
    """Raised when attempting to update a campaign that is not in DRAFT status."""

    def __init__(self, campaign_id: UUID, status: str) -> None:
        self.campaign_id = campaign_id
        self.status = status
        super().__init__(
            f"Campaign {campaign_id} is in '{status}' status; only DRAFT campaigns can be edited.",
        )


class EmptyCampaignBodyError(Exception):
    """Raised when attempting to send a campaign with an empty message body."""

    def __init__(self, campaign_id: UUID) -> None:
        self.campaign_id = campaign_id
        super().__init__(
            f"Campaign {campaign_id}: message body is empty. Compose a message before sending.",
        )


def _audience_to_dict(
    value: TargetAudience | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Normalize ``target_audience`` inputs into a plain JSONB-ready dict.

    Pydantic's Union[TargetAudience, dict] resolution is input-dependent —
    some payloads resolve to ``TargetAudience`` and some to ``dict``. JSONB
    columns can't serialize Pydantic models, so always coerce here.
    """
    if value is None:
        return None
    if isinstance(value, TargetAudience):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return value
    return None


class CampaignService(LoggerMixin):
    """Service for marketing campaign lifecycle management.

    Handles creation, consent-gated sending, delivery statistics,
    and recurring automation rule evaluation.

    Validates: CRM Gap Closure Req 45.3, 45.4, 45.5, 45.6, 45.7, 45.8, 45.9, 45.10
    """

    DOMAIN = "campaign"

    def __init__(
        self,
        campaign_repository: CampaignRepository,
        sms_service: SMSService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        """Initialize CampaignService with dependencies.

        Args:
            campaign_repository: Repository for campaign DB ops.
            sms_service: Optional SMSService for SMS campaigns.
            email_service: Optional EmailService for email campaigns.
        """
        super().__init__()
        self.repo = campaign_repository
        self.sms_service = sms_service
        self.email_service = email_service

    # ================================================================
    # create_campaign — Req 45.3
    # ================================================================

    async def create_campaign(
        self,
        data: CampaignCreate,
        created_by: UUID | None = None,
    ) -> Campaign:
        """Create a new campaign in DRAFT status.

        Args:
            data: Campaign creation payload.
            created_by: Staff UUID who created the campaign.

        Returns:
            The newly created Campaign record.

        Validates: CRM Gap Closure Req 45.3
        """
        self.log_started(
            "create_campaign",
            name=data.name,
            campaign_type=data.campaign_type.value,
        )

        # Serialize poll_options through Pydantic JSON mode so bare
        # ``date`` instances become ISO strings before the JSONB write.
        # SQLAlchemy's JSON encoder cannot serialize raw ``date`` values
        # and would otherwise raise at flush time. Mirrors the same
        # handling in ``update_campaign`` below.
        poll_options_json: list[dict[str, Any]] | None = None
        if data.poll_options is not None:
            poll_options_json = [
                opt.model_dump(mode="json") for opt in data.poll_options
            ]

        campaign = await self.repo.create(
            name=data.name,
            campaign_type=data.campaign_type.value,
            status=CampaignStatus.DRAFT.value,
            target_audience=_audience_to_dict(data.target_audience),
            subject=data.subject,
            body=data.body,
            scheduled_at=data.scheduled_at,
            poll_options=poll_options_json,
            created_by=created_by,
        )

        self.log_completed(
            "create_campaign",
            campaign_id=str(campaign.id),
        )
        return campaign

    # ================================================================
    # update_campaign — draft edits
    # ================================================================

    async def update_campaign(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
    ) -> Campaign:
        """Update a draft campaign.

        Only campaigns in DRAFT status may be edited. Only fields
        explicitly provided (non-None) are applied.

        Args:
            campaign_id: UUID of the campaign to update.
            data: Partial campaign update payload.

        Returns:
            The updated Campaign record.

        Raises:
            CampaignNotFoundError: Campaign does not exist.
            CampaignNotDraftError: Campaign is not in DRAFT status.
        """
        self.log_started("update_campaign", campaign_id=str(campaign_id))

        campaign = await self.repo.get_by_id(campaign_id)
        if campaign is None:
            self.log_failed(
                "update_campaign",
                error=CampaignNotFoundError(campaign_id),
            )
            raise CampaignNotFoundError(campaign_id)

        if campaign.status != CampaignStatus.DRAFT.value:
            self.log_rejected(
                "update_campaign",
                reason="not_draft",
                campaign_id=str(campaign_id),
                status=campaign.status,
            )
            raise CampaignNotDraftError(campaign_id, campaign.status)

        update_fields = data.model_dump(exclude_unset=True, exclude_none=False)
        # Keys that were never set are already excluded above. We deliberately
        # keep keys whose caller-provided value is ``None`` so that a draft
        # edit can CLEAR nullable fields (``poll_options``, ``subject``,
        # ``scheduled_at``, ``target_audience``). The only exception is
        # ``body``, which is NOT NULL on the model — dropping it here
        # preserves the existing body rather than triggering an IntegrityError.
        if "body" in update_fields and update_fields["body"] is None:
            del update_fields["body"]

        # poll_options is a JSONB column and each PollOption contains
        # `start_date` / `end_date` as `datetime.date` objects. SQLAlchemy's
        # JSON encoder can't serialize bare `date` instances, so the default
        # `model_dump()` above produces a payload that fails at flush time
        # with `TypeError: Object of type date is not JSON serializable`.
        # Re-serialize just this field through Pydantic's JSON mode so the
        # dates land as ISO strings. Leave other fields (notably
        # `scheduled_at`, which is a SQLAlchemy DateTime column that
        # expects a real datetime instance) untouched.
        if "poll_options" in update_fields and data.poll_options is not None:
            update_fields["poll_options"] = [
                opt.model_dump(mode="json") for opt in data.poll_options
            ]

        if "target_audience" in update_fields and data.target_audience is not None:
            update_fields["target_audience"] = _audience_to_dict(data.target_audience)

        if not update_fields:
            self.log_completed(
                "update_campaign",
                campaign_id=str(campaign_id),
                changed=0,
            )
            return campaign

        updated = await self.repo.update(campaign_id, **update_fields)
        if updated is None:
            # Defensive: get_by_id succeeded above, so this shouldn't happen
            raise CampaignNotFoundError(campaign_id)

        self.log_completed(
            "update_campaign",
            campaign_id=str(campaign_id),
            changed=len(update_fields),
        )
        return updated

    # ================================================================
    # send_campaign — Req 45.4, 45.6, 45.7, 45.8
    # ================================================================

    async def send_campaign(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> CampaignSendResult:
        """Send a campaign to filtered recipients with consent gating.

        Filters recipients by target_audience criteria, skips customers
        without SMS consent (for SMS) and customers who opted out of
        email (for email). Enforces CAN-SPAM compliance by appending
        physical address and unsubscribe link.

        Designed to be called as a background job (Req 45.7).

        Args:
            db: Async database session (for audience queries).
            campaign_id: UUID of the campaign to send.

        Returns:
            CampaignSendResult with delivery counts.

        Raises:
            CampaignNotFoundError: Campaign does not exist.
            CampaignAlreadySentError: Campaign already sent/sending.
            NoRecipientsError: No recipients match audience filter.

        Validates: CRM Gap Closure Req 45.4, 45.6, 45.7, 45.8
        """
        self.log_started("send_campaign", campaign_id=str(campaign_id))

        campaign = await self.repo.get_by_id(campaign_id)
        if campaign is None:
            self.log_failed(
                "send_campaign",
                error=CampaignNotFoundError(campaign_id),
            )
            raise CampaignNotFoundError(campaign_id)

        if campaign.status in (
            CampaignStatus.SENT.value,
            CampaignStatus.SENDING.value,
        ):
            self.log_rejected(
                "send_campaign",
                reason="already_sent",
                campaign_id=str(campaign_id),
                status=campaign.status,
            )
            raise CampaignAlreadySentError(campaign_id)

        if not (campaign.body and campaign.body.strip()):
            self.log_rejected("send_campaign", reason="empty_body", campaign_id=str(campaign_id))
            raise EmptyCampaignBodyError(campaign_id)

        # Transition to SENDING
        await self.repo.update(
            campaign_id,
            status=CampaignStatus.SENDING.value,
        )

        # Fetch business address for CAN-SPAM (Req 45.8)
        business_address = await self._get_business_address(db)

        # Build recipients from target audience filter
        recipients = await self._filter_recipients(db, campaign)

        if not recipients:
            await self.repo.update(
                campaign_id,
                status=CampaignStatus.DRAFT.value,
            )
            self.log_rejected(
                "send_campaign",
                reason="no_recipients",
                campaign_id=str(campaign_id),
            )
            raise NoRecipientsError(campaign_id)

        sent = 0
        skipped = 0
        failed = 0

        for recipient in recipients:
            # Fetch Customer model for email channel resolution
            customer: Customer | None = None
            if recipient.source_type == "customer" and recipient.customer_id:
                cust_result = await db.execute(
                    select(Customer).where(
                        Customer.id == recipient.customer_id,
                    ),
                )
                customer = cust_result.scalar_one_or_none()

            channels = self._resolve_channels(
                campaign,
                recipient,
                customer,
            )

            if not channels:
                skipped += 1
                self.logger.info(
                    "campaign.campaignservice.send_skipped",
                    campaign_id=str(campaign_id),
                    source_type=recipient.source_type,
                    reason="no_consented_channel",
                )
                await self.repo.add_recipient(
                    campaign_id=campaign_id,
                    customer_id=recipient.customer_id,
                    lead_id=recipient.lead_id,
                    channel=campaign.campaign_type,
                    delivery_status="opted_out",
                )
                continue

            for channel in channels:
                ok = await self._send_to_recipient(
                    campaign=campaign,
                    recipient=recipient,
                    channel=channel,
                    business_address=business_address,
                    customer=customer,
                )
                if ok:
                    sent += 1
                else:
                    failed += 1

        # Transition to SENT
        now = datetime.now(tz=timezone.utc)
        await self.repo.update(
            campaign_id,
            status=CampaignStatus.SENT.value,
            sent_at=now,
        )

        self.log_completed(
            "send_campaign",
            campaign_id=str(campaign_id),
            total_recipients=len(recipients),
            sent=sent,
            skipped=skipped,
            failed=failed,
        )

        return CampaignSendResult(
            campaign_id=campaign_id,
            total_recipients=len(recipients),
            sent=sent,
            skipped=skipped,
            failed=failed,
        )

    # ================================================================
    # enqueue_campaign_send — Req 8.4, 31, 41
    # ================================================================

    async def enqueue_campaign_send(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> tuple[UUID, int]:
        """Enqueue campaign recipients for background delivery.

        Validates campaign, filters recipients, creates CampaignRecipient
        rows with ``delivery_status='pending'``, and sets campaign status
        to SENDING so the background worker picks them up.

        Args:
            db: Async database session (for audience queries).
            campaign_id: UUID of the campaign to enqueue.

        Returns:
            Tuple of (campaign_id, total_recipients_enqueued).

        Raises:
            CampaignNotFoundError: Campaign does not exist.
            CampaignAlreadySentError: Campaign already sent/sending.
            NoRecipientsError: No recipients match audience filter.

        Validates: Requirements 8.4, 31, 41
        """
        self.log_started("enqueue_campaign_send", campaign_id=str(campaign_id))

        # Advisory lock to prevent concurrent /send requests creating duplicate recipients
        from sqlalchemy import text as sa_text  # noqa: PLC0415

        lock_key = f"send:{campaign_id}"
        await self.repo.session.execute(
            sa_text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": lock_key},
        )

        campaign = await self.repo.get_by_id(campaign_id)
        if campaign is None:
            self.log_failed(
                "enqueue_campaign_send",
                error=CampaignNotFoundError(campaign_id),
            )
            raise CampaignNotFoundError(campaign_id)

        if campaign.status in (
            CampaignStatus.SENT.value,
            CampaignStatus.SENDING.value,
        ):
            self.log_rejected(
                "enqueue_campaign_send",
                reason="already_sent",
                campaign_id=str(campaign_id),
                status=campaign.status,
            )
            raise CampaignAlreadySentError(campaign_id)

        # Defensive: reject sending a campaign with an empty body.
        # Draft creation allows empty body so the wizard can persist before
        # composition, but we must never actually send an empty message.
        if not (campaign.body and campaign.body.strip()):
            self.log_rejected(
                "enqueue_campaign_send",
                reason="empty_body",
                campaign_id=str(campaign_id),
            )
            raise EmptyCampaignBodyError(campaign_id)

        recipients = await self._filter_recipients(db, campaign)
        if not recipients:
            self.log_rejected(
                "enqueue_campaign_send",
                reason="no_recipients",
                campaign_id=str(campaign_id),
            )
            raise NoRecipientsError(campaign_id)

        # Create CampaignRecipient rows with pending status (bulk insert)
        from grins_platform.models.campaign import (  # noqa: PLC0415
            CampaignRecipient,
        )

        rows = [
            CampaignRecipient(
                campaign_id=campaign_id,
                customer_id=recipient.customer_id,
                lead_id=recipient.lead_id,
                channel="sms",
                delivery_status="pending",
            )
            for recipient in recipients
        ]
        self.repo.session.add_all(rows)
        await self.repo.session.flush()

        # Transition to SENDING so background worker picks up
        _ = await self.repo.update(
            campaign_id,
            status=CampaignStatus.SENDING.value,
        )

        self.log_completed(
            "enqueue_campaign_send",
            campaign_id=str(campaign_id),
            total_recipients=len(recipients),
        )
        return campaign_id, len(recipients)

    # ================================================================
    # cancel_campaign — Req 28, 37
    # ================================================================

    async def cancel_campaign(self, campaign_id: UUID) -> int:
        """Cancel a campaign by transitioning pending recipients to cancelled.

        ``sending`` rows are left untouched so they finish naturally.
        Campaign status is set to ``cancelled``.

        Args:
            campaign_id: UUID of the campaign.

        Returns:
            Number of recipients cancelled.

        Raises:
            CampaignNotFoundError: If campaign does not exist.
        """
        self.log_started("cancel_campaign", campaign_id=str(campaign_id))

        campaign = await self.repo.get_by_id(campaign_id)
        if campaign is None:
            self.log_failed(
                "cancel_campaign",
                error=CampaignNotFoundError(campaign_id),
            )
            raise CampaignNotFoundError(campaign_id)

        if campaign.status not in (
            CampaignStatus.SENDING.value,
            CampaignStatus.SCHEDULED.value,
        ):
            self.log_rejected(
                "cancel_campaign",
                reason="invalid_status",
                campaign_id=str(campaign_id),
                status=campaign.status,
            )
            raise CampaignNotDraftError(campaign_id, campaign.status)

        cancelled = await self.repo.cancel_pending_recipients(campaign_id)
        await self.repo.update(campaign_id, status=CampaignStatus.CANCELLED.value)

        self.log_completed(
            "cancel_campaign",
            campaign_id=str(campaign_id),
            cancelled=cancelled,
        )
        return cancelled

    # ================================================================
    # get_campaign_stats — Req 45.5
    # ================================================================

    async def get_campaign_stats(
        self,
        campaign_id: UUID,
    ) -> CampaignStats:
        """Get delivery statistics for a campaign.

        Aggregates recipient delivery statuses from campaign_recipients.

        Args:
            campaign_id: UUID of the campaign.

        Returns:
            CampaignStats with delivery metric counts.

        Raises:
            CampaignNotFoundError: If campaign does not exist.

        Validates: CRM Gap Closure Req 45.5
        """
        self.log_started(
            "get_campaign_stats",
            campaign_id=str(campaign_id),
        )

        campaign = await self.repo.get_by_id(campaign_id)
        if campaign is None:
            self.log_failed(
                "get_campaign_stats",
                error=CampaignNotFoundError(campaign_id),
            )
            raise CampaignNotFoundError(campaign_id)

        stats_dict = await self.repo.get_campaign_stats(campaign_id)

        result = CampaignStats(
            campaign_id=campaign_id,
            total=stats_dict.get("total", 0),
            pending=stats_dict.get("pending", 0),
            sending=stats_dict.get("sending", 0),
            sent=stats_dict.get("sent", 0),
            delivered=stats_dict.get("delivered", 0),
            failed=stats_dict.get("failed", 0),
            bounced=stats_dict.get("bounced", 0),
            opted_out=stats_dict.get("opted_out", 0),
        )

        self.log_completed(
            "get_campaign_stats",
            campaign_id=str(campaign_id),
            total=result.total,
        )
        return result

    # ================================================================
    # retry_failed_recipients — Req 37
    # ================================================================

    async def retry_failed_recipients(
        self,
        campaign_id: UUID,
        recipient_ids: list[UUID] | None = None,
    ) -> int:
        """Retry failed recipients by cloning them as new pending rows.

        Original failed rows are kept for audit. If ``recipient_ids`` is
        ``None``, all failed recipients are retried.

        Args:
            campaign_id: Campaign UUID.
            recipient_ids: Specific failed recipient IDs to retry, or None for all.

        Returns:
            Number of new pending rows created.

        Raises:
            CampaignNotFoundError: If campaign does not exist.
        """
        self.log_started("retry_failed_recipients", campaign_id=str(campaign_id))

        # Advisory lock to prevent concurrent retries creating duplicate rows
        from sqlalchemy import text as sa_text  # noqa: PLC0415

        lock_key = f"retry:{campaign_id}"
        await self.repo.session.execute(
            sa_text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": lock_key},
        )

        campaign = await self.repo.get_by_id(campaign_id)
        if campaign is None:
            self.log_failed(
                "retry_failed_recipients",
                error=CampaignNotFoundError(campaign_id),
            )
            raise CampaignNotFoundError(campaign_id)

        if campaign.status == CampaignStatus.CANCELLED.value:
            self.log_rejected(
                "retry_failed_recipients",
                reason="campaign_cancelled",
                campaign_id=str(campaign_id),
            )
            raise CampaignNotDraftError(campaign_id, campaign.status)

        if recipient_ids is None:
            failed = await self.repo.get_failed_recipients(campaign_id)
            recipient_ids = [r.id for r in failed]

        created = await self.repo.clone_recipients_as_pending(
            campaign_id, recipient_ids,
        )

        # Leave campaign status as SENT — the worker claim query accepts
        # SENT status when pending recipients exist (M22)

        self.log_completed(
            "retry_failed_recipients",
            campaign_id=str(campaign_id),
            retried=created,
        )
        return created

    # ================================================================
    # finalize_stale_campaigns — stale SENDING recovery
    # ================================================================

    async def finalize_stale_campaigns(self, stale_minutes: int = 30) -> int:
        """Finalize campaigns stuck in SENDING with no pending recipients.

        Args:
            stale_minutes: Minutes after which a SENDING campaign is considered stale.

        Returns:
            Number of campaigns finalized.
        """
        self.log_started("finalize_stale_campaigns", stale_minutes=stale_minutes)
        stale = await self.repo.get_stale_sending_campaigns(stale_minutes)
        finalized = 0
        for campaign in stale:
            stats = await self.repo.get_campaign_stats(campaign.id)
            pending = stats.get("pending", 0) + stats.get("sending", 0)
            if pending == 0:
                await self.repo.update(campaign.id, status=CampaignStatus.SENT.value)
                self.logger.info(
                    "campaign.finalize_stale",
                    campaign_id=str(campaign.id),
                    stats=stats,
                )
                finalized += 1
        self.log_completed("finalize_stale_campaigns", finalized=finalized)
        return finalized

    # ================================================================
    # evaluate_automation_rules — Req 45.10
    # ================================================================

    async def evaluate_automation_rules(
        self,
        db: AsyncSession,
    ) -> int:
        """Evaluate recurring automation rules and trigger campaigns.

        Runs as a daily background job. Scans all campaigns with
        automation_rule set, evaluates the trigger criteria, and
        creates + sends new campaign instances for matching rules.

        Example automation_rule JSONB::

            {
                "trigger": "no_appointment_in_days",
                "days": 90,
                "frequency": "weekly",
                "last_triggered_at": "2025-01-01T00:00:00Z",
            }

        Args:
            db: Async database session.

        Returns:
            Number of campaigns triggered.

        Validates: CRM Gap Closure Req 45.10
        """
        self.log_started("evaluate_automation_rules")

        campaigns_with_rules = await self._get_campaigns_with_rules(db)
        triggered_count = 0

        for campaign in campaigns_with_rules:
            rule = campaign.automation_rule
            if rule is None:
                continue

            if not self._should_trigger(rule):
                continue

            try:
                now_str = datetime.now(tz=timezone.utc).strftime(
                    "%Y-%m-%d",
                )
                new_campaign = await self.repo.create(
                    name=f"{campaign.name} — Auto {now_str}",
                    campaign_type=campaign.campaign_type,
                    status=CampaignStatus.DRAFT.value,
                    target_audience=campaign.target_audience,
                    subject=campaign.subject,
                    body=campaign.body,
                    poll_options=campaign.poll_options,
                    created_by=campaign.created_by,
                )

                await self.send_campaign(db, new_campaign.id)

                # Update last_triggered_at on the template
                updated_rule: dict[str, Any] = {**rule}
                updated_rule["last_triggered_at"] = datetime.now(
                    tz=timezone.utc,
                ).isoformat()
                await self.repo.update(
                    campaign.id,
                    automation_rule=updated_rule,
                )

                triggered_count += 1

                self.logger.info(
                    "campaign.campaignservice.automation_triggered",
                    template_id=str(campaign.id),
                    new_id=str(new_campaign.id),
                    trigger=rule.get("trigger", "unknown"),
                )

            except (
                NoRecipientsError,
                CampaignAlreadySentError,
            ) as exc:
                self.logger.warning(
                    "campaign.campaignservice.automation_skipped",
                    template_id=str(campaign.id),
                    reason=str(exc),
                )
            except Exception as exc:
                self.log_failed(
                    "evaluate_automation_rules",
                    error=exc,
                )

        self.log_completed(
            "evaluate_automation_rules",
            triggered_count=triggered_count,
        )
        return triggered_count

    # ================================================================
    # Private helpers
    # ================================================================

    async def _get_business_address(
        self,
        db: AsyncSession,
    ) -> str:
        """Fetch physical business address for CAN-SPAM.

        Validates: CRM Gap Closure Req 45.8
        """
        stmt = select(BusinessSetting).where(
            BusinessSetting.setting_key == "company_address",
        )
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()

        if setting and setting.setting_value:
            val = setting.setting_value
            if isinstance(val, str) and val.strip():
                return val.strip()
        return _DEFAULT_ADDRESS

    async def _filter_recipients(
        self,
        db: AsyncSession,
        campaign: Campaign,
        *,
        create_ghost_leads: bool = True,
    ) -> list[Recipient]:
        """Filter recipients from Customer + Lead + ad-hoc sources.

        Returns a deduplicated list of Recipient objects. When the same
        E.164 phone appears in multiple sources, the customer record wins.

        Supports both the new structured ``TargetAudience`` format (keys:
        ``customers``, ``leads``, ``ad_hoc``) and the legacy flat format
        (keys: ``lead_source``, ``is_active``, ``no_appointment_in_days``).

        Args:
            db: Async database session.
            campaign: Campaign (or fake audience wrapper) to filter for.
            create_ghost_leads: When True (send path), create ghost leads
                for ad-hoc CSV rows that don't match any existing
                customer/lead. When False (preview path), ad-hoc rows are
                returned with lead_id=None and no DB writes happen.

        Validates: Requirements 13.1, 13.6, 5.5
        """
        from grins_platform.models.appointment import (  # noqa: PLC0415
            Appointment,
        )
        from grins_platform.models.job import Job  # noqa: PLC0415

        audience = campaign.target_audience or {}
        seen_phones: dict[str, Recipient] = {}

        # ----------------------------------------------------------
        # Detect structured vs legacy format
        # ----------------------------------------------------------
        is_structured = any(k in audience for k in ("customers", "leads", "ad_hoc"))
        cust_filters = audience.get("customers") or {} if is_structured else audience
        lead_filters = audience.get("leads") or {} if is_structured else {}
        adhoc_filters = audience.get("ad_hoc") or {} if is_structured else {}

        # ----------------------------------------------------------
        # 1. Customer source
        # ----------------------------------------------------------
        if cust_filters or not is_structured:
            base_q = select(Customer).where(
                Customer.status == "active",
                Customer.is_deleted.is_(False),
            )

            if cust_filters.get("sms_opt_in") is not None:
                base_q = base_q.where(
                    Customer.sms_opt_in.is_(cust_filters["sms_opt_in"]),
                )

            ids_inc = cust_filters.get("ids_include")
            if ids_inc:
                base_q = base_q.where(Customer.id.in_(ids_inc))

            if cust_filters.get("lead_source"):
                base_q = base_q.where(
                    Customer.lead_source == cust_filters["lead_source"],
                )

            if cust_filters.get("is_active") is not None:
                status_val = "active" if cust_filters["is_active"] else "inactive"
                base_q = base_q.where(Customer.status == status_val)

            # City filter via properties join
            cities = cust_filters.get("cities")
            if cities:
                base_q = base_q.where(
                    Customer.id.in_(
                        select(Property.customer_id).where(
                            Property.city.in_(cities),
                        ),
                    ),
                )

            # Tags filter (Customer has no tags column — skip if present)
            # last_service_between handled via appointments post-filter below

            base_q = base_q.options(selectinload(Customer.properties))
            result = await db.execute(base_q)
            customers: list[Customer] = list(result.scalars().unique().all())

            # Post-filter: no_appointment_in_days (legacy + structured)
            days_threshold = cust_filters.get("no_appointment_in_days")
            if days_threshold is not None and isinstance(days_threshold, int):
                cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_threshold)
                filtered: list[Customer] = []
                for cust in customers:
                    appt_stmt = (
                        select(Appointment.id)
                        .join(Job, Appointment.job_id == Job.id)
                        .where(Job.customer_id == cust.id)
                        .where(Appointment.scheduled_date >= cutoff.date())
                        .limit(1)
                    )
                    appt_result = await db.execute(appt_stmt)
                    if appt_result.scalar_one_or_none() is None:
                        filtered.append(cust)
                customers = filtered

            # Post-filter: last_service_between
            svc_range = cust_filters.get("last_service_between")
            if svc_range and len(svc_range) == 2:
                start_d, end_d = svc_range
                # JSONB stores dates as ISO strings — parse back to date objects
                from datetime import date as _date  # noqa: PLC0415

                if isinstance(start_d, str):
                    start_d = _date.fromisoformat(start_d)
                if isinstance(end_d, str):
                    end_d = _date.fromisoformat(end_d)
                start_dt = datetime(
                    start_d.year,
                    start_d.month,
                    start_d.day,
                    tzinfo=timezone.utc,
                )
                end_dt = datetime(
                    end_d.year,
                    end_d.month,
                    end_d.day,
                    23,
                    59,
                    59,
                    tzinfo=timezone.utc,
                )
                svc_filtered: list[Customer] = []
                for cust in customers:
                    appt_stmt = (
                        select(Appointment.id)
                        .join(Job, Appointment.job_id == Job.id)
                        .where(Job.customer_id == cust.id)
                        .where(Appointment.scheduled_date >= start_dt.date())
                        .where(Appointment.scheduled_date <= end_dt.date())
                        .limit(1)
                    )
                    appt_result = await db.execute(appt_stmt)
                    if appt_result.scalar_one_or_none() is not None:
                        svc_filtered.append(cust)
                customers = svc_filtered

            for cust in customers:
                try:
                    phone = normalize_to_e164(cust.phone)
                except Exception:
                    self.logger.warning(
                        "campaign.filter_recipients.bad_phone",
                        customer_id=str(cust.id),
                    )
                    continue
                seen_phones[phone] = Recipient(
                    phone=phone,
                    source_type="customer",
                    customer_id=cust.id,
                    first_name=cust.first_name,
                    last_name=cust.last_name,
                )

        # ----------------------------------------------------------
        # 2. Lead source
        # ----------------------------------------------------------
        if lead_filters:
            lead_q = select(Lead).where(Lead.status != "converted")

            if lead_filters.get("sms_consent") is not None:
                lead_q = lead_q.where(
                    Lead.sms_consent.is_(lead_filters["sms_consent"]),
                )

            ids_inc = lead_filters.get("ids_include")
            if ids_inc:
                lead_q = lead_q.where(Lead.id.in_(ids_inc))

            statuses = lead_filters.get("statuses")
            if statuses:
                lead_q = lead_q.where(Lead.status.in_(statuses))

            if lead_filters.get("lead_source"):
                lead_q = lead_q.where(
                    Lead.lead_source == lead_filters["lead_source"],
                )

            if lead_filters.get("intake_tag"):
                lead_q = lead_q.where(
                    Lead.intake_tag == lead_filters["intake_tag"],
                )

            cities = lead_filters.get("cities")
            if cities:
                lead_q = lead_q.where(Lead.city.in_(cities))

            created_range = lead_filters.get("created_between")
            if created_range and len(created_range) == 2:
                start_d, end_d = created_range
                # JSONB stores dates as ISO strings — parse back to date objects
                from datetime import date as _date  # noqa: PLC0415

                if isinstance(start_d, str):
                    start_d = _date.fromisoformat(start_d)
                if isinstance(end_d, str):
                    end_d = _date.fromisoformat(end_d)
                start_dt = datetime(
                    start_d.year,
                    start_d.month,
                    start_d.day,
                    tzinfo=timezone.utc,
                )
                end_dt = datetime(
                    end_d.year,
                    end_d.month,
                    end_d.day,
                    23,
                    59,
                    59,
                    tzinfo=timezone.utc,
                )
                lead_q = lead_q.where(Lead.created_at >= start_dt)
                lead_q = lead_q.where(Lead.created_at <= end_dt)

            # action_tags_include (JSONB contains)
            action_tags = lead_filters.get("action_tags_include")
            if action_tags:
                for tag in action_tags:
                    lead_q = lead_q.where(Lead.action_tags.contains([tag]))

            result = await db.execute(lead_q)
            leads: list[Lead] = list(result.scalars().all())

            for lead in leads:
                try:
                    phone = normalize_to_e164(lead.phone)
                except Exception:
                    self.logger.warning(
                        "campaign.filter_recipients.bad_phone",
                        lead_id=str(lead.id),
                    )
                    continue
                # Customer wins on phone collision
                if phone not in seen_phones:
                    parts = lead.name.strip().split(None, 1) if lead.name else []
                    first_name = parts[0] if parts else None
                    last_name = parts[1] if len(parts) > 1 else None
                    seen_phones[phone] = Recipient(
                        phone=phone,
                        source_type="lead",
                        lead_id=lead.id,
                        first_name=first_name,
                        last_name=last_name,
                    )

        # ----------------------------------------------------------
        # 3. Ad-hoc CSV source
        # ----------------------------------------------------------
        # Recipients are embedded inline in ``target_audience.ad_hoc.recipients``
        # by the CSV upload endpoint. Preview reads without creating ghost
        # leads; send creates ghost leads so each recipient can be tracked
        # via campaign_recipients.lead_id.
        adhoc_rows = self._extract_adhoc_rows(adhoc_filters)
        if adhoc_rows:
            from grins_platform.services.sms.ghost_lead import (  # noqa: PLC0415
                create_or_get as create_ghost,
            )

            for row in adhoc_rows:
                phone_raw = row.get("phone")
                if not phone_raw:
                    continue
                try:
                    phone = normalize_to_e164(phone_raw)
                except Exception:
                    self.logger.warning(
                        "campaign.filter_recipients.adhoc_bad_phone",
                        phone_raw=phone_raw,
                    )
                    continue
                first_name = row.get("first_name")
                last_name = row.get("last_name")
                # CSV is the authoritative source for names in ad-hoc
                # campaigns. If this phone already exists from a customer or
                # lead source, replace the names with whatever the CSV says
                # (even if blank — the CSV is the single source of truth).
                if phone in seen_phones:
                    existing = seen_phones[phone]
                    seen_phones[phone] = dataclasses.replace(
                        existing,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    continue
                lead_id: UUID | None = None
                if create_ghost_leads:
                    try:
                        lead = await create_ghost(
                            db,
                            phone=phone,
                            first_name=first_name,
                            last_name=last_name,
                        )
                        lead_id = lead.id
                    except Exception:
                        self.logger.warning(
                            "campaign.filter_recipients.ghost_lead_failed",
                            phone=phone,
                        )
                        continue
                seen_phones[phone] = Recipient.from_adhoc(
                    phone=phone,
                    lead_id=lead_id,
                    first_name=first_name,
                    last_name=last_name,
                )

        return list(seen_phones.values())

    @staticmethod
    def _extract_adhoc_rows(
        adhoc_filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract ad-hoc recipient rows from the audience filter.

        Only supports the inline ``recipients`` payload embedded in
        ``target_audience.ad_hoc.recipients``. Returns an empty list when
        no recipients are present or the payload is malformed.
        """
        if not adhoc_filters:
            return []
        raw = adhoc_filters.get("recipients")
        if not isinstance(raw, list):
            return []
        rows: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                rows.append(item)
        return rows

    async def preview_audience(
        self,
        db: AsyncSession,
        target_audience: dict[str, Any],
    ) -> dict[str, Any]:
        """Preview audience without creating a campaign.

        Returns total count, per-source breakdown, and first 20 matches.

        Validates: Requirement 13.8
        """
        self.log_started("preview_audience")

        # Build a lightweight object with .target_audience for _filter_recipients
        class _FakeAudience:
            def __init__(self, ta: dict[str, Any]) -> None:
                self.target_audience = ta

        fake = _FakeAudience(target_audience)
        recipients = await self._filter_recipients(
            db,
            fake,  # type: ignore[arg-type]
            create_ghost_leads=False,
        )

        customers_count = sum(1 for r in recipients if r.source_type == "customer")
        leads_count = sum(1 for r in recipients if r.source_type == "lead")
        ad_hoc_count = sum(1 for r in recipients if r.source_type == "ad_hoc")

        from grins_platform.services.sms_service import (  # noqa: PLC0415
            _mask_phone,
        )

        matches = [
            {
                "phone_masked": _mask_phone(r.phone),
                "source_type": r.source_type,
                "first_name": r.first_name,
                "last_name": r.last_name,
            }
            for r in recipients[:20]
        ]

        self.log_completed(
            "preview_audience",
            total=len(recipients),
            customers=customers_count,
            leads=leads_count,
            ad_hoc=ad_hoc_count,
        )
        return {
            "total": len(recipients),
            "customers_count": customers_count,
            "leads_count": leads_count,
            "ad_hoc_count": ad_hoc_count,
            "matches": matches,
        }

    @staticmethod
    def _resolve_channels(
        campaign: Campaign,
        recipient: Recipient,  # noqa: ARG004
        customer: Customer | None = None,
    ) -> list[str]:
        """Determine channels for a recipient based on campaign type.

        Consent is checked downstream by SMSService.send_message() via
        check_sms_consent(). Email still checks email_opt_in here since
        EmailService does not have a centralized consent module yet.

        Args:
            campaign: The campaign being sent.
            recipient: Unified Recipient object.
            customer: Optional Customer model for email opt-in check.

        Validates: CRM Gap Closure Req 45.6, CallRail B2 fix, CallRail 4.8
        """
        channels: list[str] = []
        ctype = campaign.campaign_type

        if ctype in (
            CampaignType.SMS.value,
            CampaignType.BOTH.value,
        ):
            # B2 fix: do NOT check customer.sms_opt_in here.
            # Consent is enforced by SMSService via check_sms_consent().
            channels.append("sms")

        if (
            ctype
            in (
                CampaignType.EMAIL.value,
                CampaignType.BOTH.value,
            )
            and customer is not None
            and customer.email_opt_in
            and customer.email
        ):
            channels.append("email")

        return channels

    async def _send_to_recipient(
        self,
        *,
        campaign: Campaign,
        recipient: Recipient,
        channel: str,
        business_address: str,
        customer: Customer | None = None,
    ) -> bool:
        """Send a campaign message to one recipient on one channel.

        Appends CAN-SPAM footer (physical address + unsubscribe).
        Records a CampaignRecipient row for tracking.
        Consent is checked by SMSService.send_message() via check_sms_consent().

        Populates CampaignRecipient.customer_id or lead_id based on
        recipient.source_type.

        Args:
            campaign: The campaign being sent.
            recipient: Unified Recipient object.
            channel: "sms" or "email".
            business_address: Physical address for CAN-SPAM.
            customer: Optional Customer model for email sends.

        Returns True if sent successfully, False otherwise.

        Validates: CRM Gap Closure Req 45.4, 45.8, CallRail B2 fix, CallRail 4.8, 19.1
        """
        from grins_platform.services.campaign_utils import render_poll_block  # noqa: PLC0415

        composed_body = (campaign.body or "") + render_poll_block(campaign.poll_options)
        compliant_body = self._apply_can_spam(
            composed_body,
            business_address,
        )

        success = False
        customer_id = recipient.customer_id
        lead_id = recipient.lead_id

        if channel == "sms" and self.sms_service is not None:
            try:
                sms_result = await self.sms_service.send_message(
                    recipient=recipient,
                    message=compliant_body,
                    message_type=MessageType.CAMPAIGN,
                    consent_type="marketing",
                    campaign_id=campaign.id,
                )
                success = sms_result.get("success", False)
            except SMSConsentDeniedError:
                self.logger.info(
                    "campaign.campaignservice.consent_denied",
                    campaign_id=str(campaign.id),
                    source_type=recipient.source_type,
                )
                await self.repo.add_recipient(
                    campaign_id=campaign.id,
                    customer_id=customer_id,
                    lead_id=lead_id,
                    channel=channel,
                    delivery_status="opted_out",
                )
                return False
            except Exception as exc:
                self.log_failed(
                    "send_to_recipient_sms",
                    error=exc,
                    campaign_id=str(campaign.id),
                    source_type=recipient.source_type,
                )

        elif (
            channel == "email"
            and self.email_service is not None
            and customer is not None
        ):
            try:
                success = self.email_service._send_email(  # noqa: SLF001
                    to_email=customer.email or "",
                    subject=campaign.subject or campaign.name,
                    html_body=compliant_body,
                    email_type=NotificationType.CAMPAIGN.value,
                    classification=EmailType.COMMERCIAL,
                )
            except Exception as exc:
                self.log_failed(
                    "send_to_recipient_email",
                    error=exc,
                    campaign_id=str(campaign.id),
                    source_type=recipient.source_type,
                )

        # Record recipient
        delivery_status = "sent" if success else "failed"
        sent_at = datetime.now(tz=timezone.utc) if success else None

        await self.repo.add_recipient(
            campaign_id=campaign.id,
            customer_id=customer_id,
            lead_id=lead_id,
            channel=channel,
            delivery_status=delivery_status,
            sent_at=sent_at,
            error_message=None if success else "delivery_failed",
        )

        return success

    @staticmethod
    def _apply_can_spam(body: str, business_address: str) -> str:
        """Append CAN-SPAM physical address and unsubscribe link.

        Validates: CRM Gap Closure Req 45.8
        """
        footer = f"\n\n{business_address}{_UNSUBSCRIBE_TEXT}"
        return body + footer

    async def _get_campaigns_with_rules(
        self,
        db: AsyncSession,
    ) -> list[Campaign]:
        """Fetch campaigns that have automation_rule set."""
        stmt = (
            select(Campaign)
            .where(Campaign.automation_rule.isnot(None))
            .where(
                Campaign.status.in_(
                    [
                        CampaignStatus.DRAFT.value,
                        CampaignStatus.SENT.value,
                    ],
                ),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _should_trigger(rule: dict[str, Any]) -> bool:
        """Check if an automation rule is due based on frequency.

        Supported frequencies: daily, weekly, monthly.
        """
        frequency = rule.get("frequency", "weekly")
        last_triggered = rule.get("last_triggered_at")

        if last_triggered is None:
            return True

        try:
            last_dt = datetime.fromisoformat(str(last_triggered))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return True

        now = datetime.now(tz=timezone.utc)
        elapsed = now - last_dt

        frequency_map: dict[str, int] = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
        }
        required_days = frequency_map.get(frequency, 7)

        return elapsed >= timedelta(days=required_days)
