"""Background scheduled jobs for agreement lifecycle and campaign sending.

Implements daily/weekly jobs for payment escalation, renewal checks,
annual notices, orphaned consent cleanup, and campaign recipient processing.

Validates: Requirements 10.1-10.7, 15.1-15.4, 16.1-16.4, 21.1-21.5, 28, 32, 37.2, 37.3
"""

from __future__ import annotations

import os
import time as _time_mod
from datetime import datetime, time, timedelta, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import stripe
from apscheduler.triggers.cron import (  # type: ignore[import-untyped]
    CronTrigger,
)
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from grins_platform.database import get_database_manager
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.alert import Alert
from grins_platform.models.appointment import Appointment
from grins_platform.models.campaign import Campaign, CampaignRecipient
from grins_platform.models.customer import Customer
from grins_platform.models.enums import (
    AgreementStatus,
    AlertSeverity,
    AlertType,
    AppointmentStatus,
    CampaignStatus,
    DisclosureType,
    JobStatus,
)
from grins_platform.models.job import Job
from grins_platform.models.lead import Lead
from grins_platform.models.sent_message import SentMessage
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.repositories.alert_repository import AlertRepository
from grins_platform.schemas.ai import MessageType
from grins_platform.services.campaign_utils import (
    render_poll_block as _render_poll_block,
)
from grins_platform.services.compliance_service import ComplianceService
from grins_platform.services.duplicate_detection_service import (
    DuplicateDetectionService,
)
from grins_platform.services.email_service import EmailService
from grins_platform.services.onboarding_reminder_job import OnboardingReminderJob
from grins_platform.services.sms.consent import check_sms_consent  # noqa: F401
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms.state_machine import (
    RecipientState,
    orphan_recovery_query,
    transition,
)
from grins_platform.services.stripe_config import StripeSettings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.scheduler import BackgroundScheduler

logger = get_logger(__name__)


class FailedPaymentEscalator(LoggerMixin):
    """Escalates failed payments: Day 7 → PAUSED, Day 21 → CANCELLED.

    Validates: Requirements 15.1, 15.2, 15.3, 15.4
    """

    DOMAIN = "scheduler"

    PAUSE_THRESHOLD_DAYS = 7
    CANCEL_THRESHOLD_DAYS = 14  # 14 days after pause (21 total)

    async def run(self) -> None:
        """Execute the failed payment escalation job."""
        self.log_started("escalate_failed_payments")
        db_manager = get_database_manager()
        stripe_settings = StripeSettings()
        now = datetime.now(timezone.utc)

        async for session in db_manager.get_session():
            # Step 1: PAUSED ≥ 14 days → CANCELLED
            paused_cutoff = now - timedelta(days=self.CANCEL_THRESHOLD_DAYS)
            paused_stmt = (
                select(ServiceAgreement)
                .options(
                    selectinload(ServiceAgreement.customer),
                    selectinload(ServiceAgreement.tier),
                    selectinload(ServiceAgreement.jobs),
                )
                .where(
                    ServiceAgreement.status == AgreementStatus.PAUSED.value,
                    ServiceAgreement.updated_at <= paused_cutoff,
                )
            )
            paused_result = await session.execute(paused_stmt)
            paused_agreements = list(paused_result.scalars().all())

            for agreement in paused_agreements:
                self._cancel_agreement(agreement, stripe_settings, now)

            # Step 2: PAST_DUE ≥ 7 days → PAUSED
            past_due_cutoff = now - timedelta(days=self.PAUSE_THRESHOLD_DAYS)
            past_due_stmt = select(ServiceAgreement).where(
                ServiceAgreement.status == AgreementStatus.PAST_DUE.value,
                ServiceAgreement.updated_at <= past_due_cutoff,
            )
            past_due_result = await session.execute(past_due_stmt)
            past_due_agreements = list(past_due_result.scalars().all())

            for agreement in past_due_agreements:
                self._pause_agreement(agreement, stripe_settings)

        self.log_completed("escalate_failed_payments")

    def _cancel_agreement(
        self,
        agreement: ServiceAgreement,
        stripe_settings: StripeSettings,
        now: datetime,
    ) -> None:
        try:
            if agreement.stripe_subscription_id and stripe_settings.is_configured:
                stripe.api_key = stripe_settings.stripe_secret_key
                stripe.Subscription.cancel(
                    agreement.stripe_subscription_id,
                )

            agreement.status = AgreementStatus.CANCELLED.value  # type: ignore[assignment]
            agreement.cancelled_at = now  # type: ignore[assignment]

            for job in agreement.jobs:
                if job.status == JobStatus.TO_BE_SCHEDULED.value:
                    job.status = JobStatus.CANCELLED.value

            logger.info(
                "scheduler.escalate_failed_payments.cancelled",
                agreement_id=str(agreement.id),
                step="day_21_cancel",
            )
        except Exception:
            logger.exception(
                "scheduler.escalate_failed_payments.cancel_failed",
                agreement_id=str(agreement.id),
            )

    def _pause_agreement(
        self,
        agreement: ServiceAgreement,
        stripe_settings: StripeSettings,
    ) -> None:
        try:
            if agreement.stripe_subscription_id and stripe_settings.is_configured:
                stripe.api_key = stripe_settings.stripe_secret_key
                stripe.Subscription.modify(
                    agreement.stripe_subscription_id,
                    pause_collection={"behavior": "void"},
                )

            agreement.status = AgreementStatus.PAUSED.value  # type: ignore[assignment]
            agreement.pause_reason = (  # type: ignore[assignment]
                "Payment failed — auto-paused after 7 days"
            )

            logger.info(
                "scheduler.escalate_failed_payments.paused",
                agreement_id=str(agreement.id),
                step="day_7_pause",
            )
        except Exception:
            logger.exception(
                "scheduler.escalate_failed_payments.pause_failed",
                agreement_id=str(agreement.id),
            )


class UpcomingRenewalChecker(LoggerMixin):
    """Checks for agreements approaching renewal and triggers alerts.

    Validates: Requirement 16.3
    """

    DOMAIN = "scheduler"

    async def run(self) -> None:
        """Check for upcoming renewals and log alerts."""
        self.log_started("check_upcoming_renewals")
        db_manager = get_database_manager()
        today = datetime.now(timezone.utc).date()
        count = 0

        async for session in db_manager.get_session():
            # Find agreements renewing within 30 days
            threshold = today + timedelta(days=30)
            stmt = select(ServiceAgreement).where(
                ServiceAgreement.status == AgreementStatus.ACTIVE.value,
                ServiceAgreement.renewal_date.isnot(None),
                ServiceAgreement.renewal_date <= threshold,
                ServiceAgreement.renewal_date >= today,
            )
            result = await session.execute(stmt)
            agreements = list(result.scalars().all())
            count = len(agreements)

            for agreement in agreements:
                days_until = (
                    (agreement.renewal_date - today).days
                    if agreement.renewal_date
                    else 0
                )
                logger.info(
                    "scheduler.upcoming_renewal.alert",
                    agreement_id=str(agreement.id),
                    days_until_renewal=days_until,
                )

        self.log_completed("check_upcoming_renewals", count=count)


class AnnualNoticeSender(LoggerMixin):
    """Sends annual notices to ACTIVE agreements in January.

    Validates: Requirements 16.3, 37.2, 37.3, 39B.5
    """

    DOMAIN = "scheduler"

    async def run(self) -> None:
        """Send annual notices for eligible agreements."""
        self.log_started("send_annual_notices")
        now = datetime.now(timezone.utc)

        # Only run in January
        if now.month != 1:
            self.log_completed("send_annual_notices", skipped="not_january")
            return

        db_manager = get_database_manager()
        email_service = EmailService()
        sent_count = 0

        async for session in db_manager.get_session():
            compliance = ComplianceService(session)
            agreements = await compliance.get_annual_notice_due()

            for agreement in agreements:
                sent_count += await self._send_notice(
                    agreement,
                    email_service,
                    compliance,
                    now,
                )

        self.log_completed("send_annual_notices", sent_count=sent_count)

    async def _send_notice(
        self,
        agreement: ServiceAgreement,
        email_service: EmailService,
        compliance: ComplianceService,
        now: datetime,
    ) -> int:
        """Send a single annual notice. Returns 1 if sent, 0 otherwise."""
        try:
            result = email_service.send_annual_notice(
                customer=agreement.customer,
                agreement=agreement,
            )
        except Exception:
            logger.exception(
                "scheduler.annual_notice.failed",
                agreement_id=str(agreement.id),
            )
            return 0

        if not (result.get("sent") or result.get("sent_via") == "pending"):
            return 0

        await compliance.create_disclosure(
            disclosure_type=DisclosureType.ANNUAL_NOTICE,
            agreement_id=agreement.id,
            customer_id=agreement.customer_id,
            content=result.get("content", ""),
            sent_via=result.get("sent_via", "email"),
            recipient_email=result.get("recipient_email"),
            delivery_confirmed=result.get("sent", False),
        )
        agreement.last_annual_notice_sent = now  # type: ignore[assignment]
        logger.info(
            "scheduler.annual_notice.sent",
            agreement_id=str(agreement.id),
        )
        return 1


class OrphanedConsentCleaner(LoggerMixin):
    """Marks consent records > 30 days with no linked customer as abandoned.

    Validates: Requirement 16.3
    """

    DOMAIN = "scheduler"

    ORPHAN_THRESHOLD_DAYS = 30

    async def run(self) -> None:
        """Clean up orphaned consent records."""
        self.log_started("cleanup_orphaned_consent_records")
        db_manager = get_database_manager()
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self.ORPHAN_THRESHOLD_DAYS,
        )
        cleaned = 0

        async for session in db_manager.get_session():
            stmt = select(SmsConsentRecord).where(
                SmsConsentRecord.customer_id.is_(None),
                SmsConsentRecord.consent_timestamp < cutoff,
            )
            result = await session.execute(stmt)
            records = list(result.scalars().all())

            for record in records:
                # Mark as abandoned by setting consent_type
                record.consent_type = "abandoned"  # type: ignore[assignment]
                cleaned += 1

            logger.info(
                "scheduler.cleanup_orphaned.processed",
                cleaned_count=cleaned,
            )

        self.log_completed("cleanup_orphaned_consent_records", cleaned=cleaned)


# -- Central timezone for time-window enforcement --
_CT_TZ = ZoneInfo("America/Chicago")
_WINDOW_START = time(8, 0)
_WINDOW_END = time(21, 0)

# Max recipients per tick (~2 to stay under 140/hr with 60s interval)
_BATCH_SIZE = 2

# Redis key for worker health
_REDIS_WORKER_KEY = "sms:worker:last_tick"

# Sender prefix / footer defaults
_DEFAULT_PREFIX = "Grins Irrigation: "
_DEFAULT_FOOTER = " Reply STOP to opt out."


def _mask_phone(phone: str) -> str:
    """Mask phone for logging: +1XXX***XXXX."""
    if len(phone) >= 10:
        return phone[:4] + "***" + phone[-4:]
    return "***"


def _is_within_time_window() -> bool:
    """Return True if current CT time is within 8 AM - 9 PM."""
    now_ct = datetime.now(_CT_TZ)
    return _WINDOW_START <= now_ct.time() < _WINDOW_END


class CampaignWorker(LoggerMixin):
    """Processes pending campaign recipients on a 60-second interval.

    Performs orphan recovery, claims rows with ``FOR UPDATE SKIP LOCKED``,
    transitions through the state machine, and delegates to SMSService.

    Validates: Requirements 10.1-10.7, 21.1-21.5, 28, 32
    """

    DOMAIN = "campaign"

    async def run(self) -> None:
        """Execute one tick of the campaign worker."""
        tick_start = _time_mod.monotonic()
        self.log_started("worker_tick")
        db_manager = get_database_manager()
        processed = 0
        orphans_recovered = 0

        async for session in db_manager.get_session():
            # 1. Orphan recovery first
            orphans_recovered = await orphan_recovery_query(session)
            if orphans_recovered:
                logger.info(
                    "campaign.worker.orphan_recovered",
                    count=orphans_recovered,
                )

            # 2. Time-window check - skip if outside 8 AM - 9 PM CT
            if not _is_within_time_window():
                logger.info("campaign.worker.outside_time_window")
                await self._record_tick(session, 0, tick_start, orphans_recovered)
                self.log_completed("worker_tick", processed=0, reason="outside_window")
                return

            # 3. Claim pending recipients with FOR UPDATE SKIP LOCKED
            now = datetime.now(timezone.utc)
            claim_stmt = (
                select(CampaignRecipient)
                .join(Campaign, CampaignRecipient.campaign_id == Campaign.id)
                .where(
                    CampaignRecipient.delivery_status == RecipientState.pending.value,
                    CampaignRecipient.channel == "sms",
                    Campaign.status.in_(
                        [
                            CampaignStatus.SENDING.value,
                            CampaignStatus.SENT.value,
                        ]
                    ),
                    (Campaign.scheduled_at.is_(None)) | (Campaign.scheduled_at <= now),
                )
                .order_by(CampaignRecipient.created_at.asc())
                .limit(_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            result = await session.execute(claim_stmt)
            recipients = list(result.scalars().all())

            if not recipients:
                await self._record_tick(session, 0, tick_start, orphans_recovered)
                self.log_completed("worker_tick", processed=0)
                return

            # 4. Process each claimed recipient
            provider = get_sms_provider()

            # L10: Create Redis client once for the whole batch
            redis_url = os.environ.get("REDIS_URL")
            redis_client = None
            if redis_url:
                try:
                    from redis.asyncio import Redis  # noqa: PLC0415

                    redis_client = Redis.from_url(redis_url, decode_responses=True)
                except Exception:
                    logger.debug("campaign.worker.redis_connect_failed")

            try:
                for cr in recipients:
                    await self._process_recipient(session, cr, provider, redis_client)
                    processed += 1
            finally:
                if redis_client:
                    await redis_client.aclose()

            # 5. Update campaign status if all recipients are terminal
            campaign_ids = {cr.campaign_id for cr in recipients}
            for cid in campaign_ids:
                await self._update_campaign_status(session, cid)

            await self._record_tick(session, processed, tick_start, orphans_recovered)

        tick_ms = int((_time_mod.monotonic() - tick_start) * 1000)
        logger.info(
            "campaign.worker.tick",
            recipients_processed=processed,
            tick_duration_ms=tick_ms,
            orphans_recovered=orphans_recovered,
        )
        self.log_completed(
            "worker_tick",
            processed=processed,
            tick_duration_ms=tick_ms,
        )

    async def _process_recipient(
        self,
        session: AsyncSession,
        cr: CampaignRecipient,
        provider: object,
        redis_client: object | None = None,
    ) -> None:
        """Process a single campaign recipient through the state machine."""
        from grins_platform.services.sms.base import BaseSMSProvider  # noqa: PLC0415
        from grins_platform.services.sms.rate_limit_tracker import (  # noqa: PLC0415
            SMSRateLimitTracker,
        )
        from grins_platform.services.sms_service import (  # noqa: PLC0415
            SMSConsentDeniedError,
            SMSError,
            SMSRateLimitDeniedError,
            SMSService,
        )

        assert isinstance(provider, BaseSMSProvider)

        # Resolve the actual person (customer or lead)
        recipient = await self._resolve_recipient(session, cr)
        if recipient is None:
            cr.delivery_status = RecipientState.failed.value
            cr.error_message = "no_customer_or_lead_found"
            return

        # State machine: pending -> sending
        _ = transition(RecipientState(cr.delivery_status), RecipientState.sending)
        cr.delivery_status = RecipientState.sending.value
        cr.sending_started_at = datetime.now(timezone.utc)
        await session.flush()

        # Load campaign body
        campaign = await session.get(Campaign, cr.campaign_id)
        if campaign is None:
            cr.delivery_status = RecipientState.failed.value
            cr.error_message = "campaign_not_found"
            return

        # L11: Consent check handled by SMSService.send_message()

        # Rate limit check (Redis client created once per batch — L10)
        tracker = SMSRateLimitTracker(
            provider=provider.provider_name,
            account_id=os.environ.get("CALLRAIL_ACCOUNT_ID", ""),
            redis_client=redis_client,
        )
        rl_result = await tracker.check()
        if not rl_result.allowed:
            # Revert to pending - will be retried next tick
            _ = transition(RecipientState.sending, RecipientState.pending)
            cr.delivery_status = RecipientState.pending.value
            cr.sending_started_at = None
            logger.info(
                "campaign.worker.rate_limited",
                retry_after=rl_result.retry_after_seconds,
            )
            return

        # Send via provider (SMSService handles merge fields + formatting)
        # For poll campaigns, append the rendered poll block to the body
        # before handing off to SMSService. SMSService still applies the
        # sender prefix + STOP footer.
        composed_body = (campaign.body or "") + _render_poll_block(
            campaign.poll_options,
        )
        try:
            sms_svc = SMSService(
                session=session,
                provider=provider,
                rate_limit_tracker=tracker,
            )
            result = await sms_svc.send_message(
                recipient=recipient,
                message=composed_body,
                message_type=MessageType.CAMPAIGN,
                consent_type="marketing",
                campaign_id=campaign.id,
                skip_formatting=False,
            )
            if result.get("success"):
                _ = transition(RecipientState.sending, RecipientState.sent)
                cr.delivery_status = RecipientState.sent.value
                cr.sent_at = datetime.now(timezone.utc)
            else:
                _ = transition(RecipientState.sending, RecipientState.failed)
                cr.delivery_status = RecipientState.failed.value
                cr.error_message = result.get("reason", "send_returned_false")

        except (SMSConsentDeniedError, SMSRateLimitDeniedError) as e:
            _ = transition(RecipientState.sending, RecipientState.failed)
            cr.delivery_status = RecipientState.failed.value
            cr.error_message = str(e)
        except SMSError as e:
            _ = transition(RecipientState.sending, RecipientState.failed)
            cr.delivery_status = RecipientState.failed.value
            cr.error_message = str(e)
            logger.exception(
                "campaign.worker.send_failed",
                phone=_mask_phone(recipient.phone),
                error=str(e),
            )
        except Exception as e:
            _ = transition(RecipientState.sending, RecipientState.failed)
            cr.delivery_status = RecipientState.failed.value
            cr.error_message = str(e)
            logger.exception(
                "campaign.worker.unexpected_error",
                error=str(e),
            )
        finally:
            # Persist the recipient's terminal state before the tick's
            # aggregate COUNT in _update_campaign_status runs. The session
            # is created with autoflush=False, so without this explicit
            # flush the COUNT would read the stale "sending" row and the
            # campaign would be left stuck in SENDING forever.
            await session.flush()

    async def _resolve_recipient(
        self,
        session: AsyncSession,
        cr: CampaignRecipient,
    ) -> Recipient | None:
        """Build a Recipient from a CampaignRecipient's customer or lead FK."""
        if cr.customer_id:
            customer = await session.get(Customer, cr.customer_id)
            if customer:
                return Recipient.from_customer(customer)
        if cr.lead_id:
            lead = await session.get(Lead, cr.lead_id)
            if lead:
                return Recipient.from_lead(lead)
        return None

    async def _update_campaign_status(
        self,
        session: AsyncSession,
        campaign_id: object,
    ) -> None:
        """Derive campaign status from aggregate recipient states."""
        from uuid import UUID  # noqa: PLC0415

        cid = campaign_id if isinstance(campaign_id, UUID) else UUID(str(campaign_id))

        # Respect explicit user cancellation — never overwrite CANCELLED
        campaign = await session.get(Campaign, cid)
        if campaign is not None and campaign.status == CampaignStatus.CANCELLED.value:
            return

        # Count recipients by status
        count_stmt = (
            select(
                CampaignRecipient.delivery_status,
                func.count().label("cnt"),
            )
            .where(CampaignRecipient.campaign_id == cid)
            .group_by(CampaignRecipient.delivery_status)
        )
        result = await session.execute(count_stmt)
        counts: dict[str, int] = {row[0]: row[1] for row in result.all()}

        pending = counts.get(RecipientState.pending.value, 0)
        sending = counts.get(RecipientState.sending.value, 0)

        # If any are still pending or sending, campaign is still sending
        if pending > 0 or sending > 0:
            return

        # All terminal — determine final status
        sent = counts.get(RecipientState.sent.value, 0)
        failed = counts.get(RecipientState.failed.value, 0)
        cancelled = counts.get(RecipientState.cancelled.value, 0)
        total = sent + failed + cancelled

        if total == 0:
            return

        if campaign is None:
            return

        if sent > 0 and failed == 0:
            campaign.status = CampaignStatus.SENT.value  # type: ignore[assignment]
            campaign.sent_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        elif sent > 0 and failed > 0:
            # Partial — mark as sent (partial failures tracked at recipient level)
            campaign.status = CampaignStatus.SENT.value  # type: ignore[assignment]
            campaign.sent_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        elif failed > 0 and sent == 0:
            # All failed — still a terminal dispatch; the user can inspect
            # per-recipient error messages and invoke the retry-failed endpoint
            # which re-sets the campaign back to SENDING and enqueues new
            # pending rows. Leaving the campaign in SENDING here would make
            # it appear stuck in the UI forever.
            campaign.status = CampaignStatus.SENT.value  # type: ignore[assignment]
            campaign.sent_at = datetime.now(timezone.utc)  # type: ignore[assignment]

    async def _record_tick(
        self,
        session: AsyncSession,  # noqa: ARG002
        processed: int,
        tick_start: float,
        orphans_recovered: int,
    ) -> None:
        """Record worker tick metadata in Redis for health endpoint."""
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            return
        try:
            from redis.asyncio import Redis  # noqa: PLC0415

            redis = Redis.from_url(redis_url, decode_responses=True)
            tick_ms = int((_time_mod.monotonic() - tick_start) * 1000)
            import json  # noqa: PLC0415

            payload = json.dumps(
                {
                    "last_tick_at": datetime.now(timezone.utc).isoformat(),
                    "last_tick_duration_ms": tick_ms,
                    "last_tick_recipients_processed": processed,
                    "orphans_recovered": orphans_recovered,
                },
            )
            await redis.set(_REDIS_WORKER_KEY, payload, ex=300)
            await redis.aclose()
        except Exception:
            logger.debug("campaign.worker.redis_tick_failed")


# ============================================================================
# No-reply confirmation flagger (bughunt H-7)
# ============================================================================


# Default number of days after confirmation SMS with no reply before we
# flag the appointment for admin review. BusinessSettingService can override
# via the ``confirmation_no_reply_days`` key. Once H-12 lands we switch from
# the hardcoded constant to the injected setting.
DEFAULT_NO_REPLY_DAYS = 3


class NoReplyConfirmationFlagger(LoggerMixin):
    """Flag SCHEDULED appointments with no Y/R/C reply for N days.

    The Y/R/C confirmation SMS flow fires once when the admin moves an
    appointment from DRAFT → SCHEDULED. If the customer never replies,
    the appointment sits silently in the schedule and nobody knows. This
    nightly job looks up every SCHEDULED appointment whose most recent
    ``appointment_confirmation`` ``SentMessage`` is older than the
    configured threshold and has received no ``JobConfirmationResponse``
    since, then:

    1. sets ``Appointment.needs_review_reason = "no_confirmation_response"``
    2. creates an ``Alert(type=CONFIRMATION_NO_REPLY, severity=INFO)``

    so the ``/schedule`` admin review queue (H-7 FE) can surface the row.

    Idempotent: the ``needs_review_reason IS NULL`` guard means a second
    run sees the flagged rows as already-triaged and skips them.

    Validates: bughunt 2026-04-16 finding H-7.
    """

    DOMAIN = "scheduler"

    # Reason token written into ``Appointment.needs_review_reason`` so
    # the FE can distinguish different review buckets later if needed.
    REVIEW_REASON_NO_REPLY = "no_confirmation_response"

    async def _resolve_threshold_days(self, session: AsyncSession) -> int:
        """Return the "N days" threshold.

        Attempts to read ``confirmation_no_reply_days`` from
        ``BusinessSetting`` via :class:`SettingsService`. Falls back to
        :data:`DEFAULT_NO_REPLY_DAYS` when the table / row is missing —
        the H-12 migration seeds the row, but this fallback protects
        against an out-of-order migration environment.
        """
        # Import lazily so test doubles can patch the module-level
        # service without needing it resolved at import time.
        try:
            from grins_platform.services.settings_service import (  # noqa: PLC0415
                SettingNotFoundError,
                SettingsService,
            )
        except Exception:
            return DEFAULT_NO_REPLY_DAYS

        service = SettingsService()
        try:
            value = await service.get_setting(
                session,
                "confirmation_no_reply_days",
            )
        except SettingNotFoundError:
            return DEFAULT_NO_REPLY_DAYS
        except Exception:
            # Any other failure — be conservative and use the default
            # rather than silently disabling the job.
            return DEFAULT_NO_REPLY_DAYS

        # BusinessSettingService (H-12) persists as {"value": N}. Older
        # SettingsService calls might store {"days": N}. Accept either.
        if not isinstance(value, dict):
            return DEFAULT_NO_REPLY_DAYS
        days = value.get("value", value.get("days"))
        if not isinstance(days, int) or days <= 0:
            return DEFAULT_NO_REPLY_DAYS
        return days

    async def run(self) -> None:
        """Execute the flag-no-reply-confirmations job."""
        self.log_started("flag_no_reply_confirmations")
        db_manager = get_database_manager()
        flagged = 0

        try:
            async for session in db_manager.get_session():
                flagged = await self._run_once(session)
        except Exception as exc:
            self.log_failed("flag_no_reply_confirmations", error=exc)
            raise

        self.log_completed(
            "flag_no_reply_confirmations",
            flagged_count=flagged,
        )

    async def _run_once(self, session: AsyncSession) -> int:
        """Scan + flag in a single session."""
        from grins_platform.models.job_confirmation import (  # noqa: PLC0415
            JobConfirmationResponse,
        )

        days = await self._resolve_threshold_days(session)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        # Most-recent APPOINTMENT_CONFIRMATION sent_at per appointment,
        # as a correlated subquery. We filter by ``sent_at IS NOT NULL``
        # so in-flight / failed rows don't falsely trigger the flag.
        latest_confirmation_subq = (
            select(func.max(SentMessage.sent_at))
            .where(
                SentMessage.appointment_id == Appointment.id,
                SentMessage.message_type == MessageType.APPOINTMENT_CONFIRMATION.value,
                SentMessage.sent_at.is_not(None),
            )
            .correlate(Appointment)
            .scalar_subquery()
        )

        stmt = select(Appointment).where(
            Appointment.status == AppointmentStatus.SCHEDULED.value,
            Appointment.needs_review_reason.is_(None),
            latest_confirmation_subq.is_not(None),
            latest_confirmation_subq < cutoff,
        )
        result = await session.execute(stmt)
        candidates = list(result.scalars().all())

        alert_repo = AlertRepository(session)
        flagged = 0

        for appt in candidates:
            # Re-read the most-recent confirmation sent_at so we can
            # check for a later customer reply (and embed the age in
            # the alert message).
            sent_at_stmt = select(func.max(SentMessage.sent_at)).where(
                SentMessage.appointment_id == appt.id,
                SentMessage.message_type == MessageType.APPOINTMENT_CONFIRMATION.value,
                SentMessage.sent_at.is_not(None),
            )
            sent_at_result = await session.execute(sent_at_stmt)
            last_confirmation_at: datetime | None = sent_at_result.scalar()
            if last_confirmation_at is None:
                # Defensive — the subquery above already filters this, but
                # keep a guard in case of a race with a second scheduler.
                continue

            # Skip if the customer has already replied after the
            # confirmation was sent.
            reply_stmt = select(func.count()).where(
                JobConfirmationResponse.appointment_id == appt.id,
                JobConfirmationResponse.received_at > last_confirmation_at,
            )
            reply_result = await session.execute(reply_stmt)
            reply_count = int(reply_result.scalar() or 0)
            if reply_count > 0:
                continue

            # Lookup the customer name via Job → Customer.
            customer_name = "the customer"
            job = await session.get(Job, appt.job_id)
            if job is not None:
                customer = await session.get(Customer, job.customer_id)
                if customer is not None:
                    customer_name = customer.full_name or customer_name

            # Flag the appointment.
            appt.needs_review_reason = self.REVIEW_REASON_NO_REPLY

            # Create the alert row via the shared repository.
            try:
                alert = Alert(
                    type=AlertType.CONFIRMATION_NO_REPLY.value,
                    severity=AlertSeverity.INFO.value,
                    entity_type="appointment",
                    entity_id=appt.id,
                    message=(f"No reply from {customer_name} after {days} days"),
                )
                await alert_repo.create(alert)
                flagged += 1
            except Exception as exc:  # pragma: no cover - defensive
                # Never block the loop on a single alert failure; revert
                # the flag so a retry on the next tick picks it back up.
                appt.needs_review_reason = None
                self.log_failed(
                    "flag_no_reply_confirmations.create_alert",
                    appointment_id=str(appt.id),
                    error=exc,
                )

        return flagged


# Singleton instances for job functions
_escalator = FailedPaymentEscalator()
_renewal_checker = UpcomingRenewalChecker()
_annual_sender = AnnualNoticeSender()
_orphan_cleaner = OrphanedConsentCleaner()
_onboarding_reminder = OnboardingReminderJob()
_campaign_worker = CampaignWorker()
_no_reply_flagger = NoReplyConfirmationFlagger()


async def run_duplicate_detection_sweep_job() -> None:
    """Entry point for the nightly duplicate detection sweep.

    Validates: CRM Changes Update 2 Req 5.6
    """
    service = DuplicateDetectionService()
    db_manager = get_database_manager()
    async for session in db_manager.get_session():
        await service.run_nightly_sweep(session)


async def escalate_failed_payments_job() -> None:
    """Entry point for the escalate_failed_payments scheduled job."""
    await _escalator.run()


async def check_upcoming_renewals_job() -> None:
    """Entry point for the check_upcoming_renewals scheduled job."""
    await _renewal_checker.run()


async def send_annual_notices_job() -> None:
    """Entry point for the send_annual_notices scheduled job."""
    await _annual_sender.run()


async def cleanup_orphaned_consent_records_job() -> None:
    """Entry point for the cleanup_orphaned_consent_records scheduled job."""
    await _orphan_cleaner.run()


async def remind_incomplete_onboarding_job() -> None:
    """Entry point for the onboarding reminder scheduled job."""
    await _onboarding_reminder.run()


async def process_pending_campaign_recipients() -> None:
    """Entry point for the campaign worker scheduled job."""
    await _campaign_worker.run()


async def flag_no_reply_confirmations() -> None:
    """Entry point for the nightly flag-no-reply-confirmations job.

    Validates: bughunt 2026-04-16 finding H-7.
    """
    await _no_reply_flagger.run()


async def prune_webhook_processed_logs_job() -> None:
    """Delete ``webhook_processed_logs`` rows older than 30 days.

    Validates: Gap 07 — Webhook Security & Dedup (7.B) retention.
    """
    from grins_platform.repositories.webhook_processed_log_repository import (  # noqa: PLC0415
        WebhookProcessedLogRepository,
    )

    db_manager = get_database_manager()
    async for session in db_manager.get_session():
        repo = WebhookProcessedLogRepository(session)
        deleted = await repo.prune_older_than(days=30)
        await session.commit()
        logger.info(
            "scheduler.webhook_processed_logs.pruned",
            deleted=deleted,
        )


def register_scheduled_jobs(scheduler: BackgroundScheduler) -> None:
    """Register all background jobs with the scheduler.

    Validates: Requirement 16.3
    """
    scheduler.add_job(
        escalate_failed_payments_job,
        "cron",
        hour=2,
        minute=0,
        id="escalate_failed_payments",
        replace_existing=True,
    )

    scheduler.add_job(
        check_upcoming_renewals_job,
        "cron",
        hour=9,
        minute=0,
        id="check_upcoming_renewals",
        replace_existing=True,
    )

    scheduler.add_job(
        send_annual_notices_job,
        "cron",
        hour=10,
        minute=0,
        id="send_annual_notices",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_orphaned_consent_records_job,
        "cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        id="cleanup_orphaned_consent_records",
        replace_existing=True,
    )

    scheduler.add_job(
        remind_incomplete_onboarding_job,
        "cron",
        hour=10,
        minute=0,
        id="remind_incomplete_onboarding",
        replace_existing=True,
    )

    scheduler.add_job(
        process_pending_campaign_recipients,
        "interval",
        seconds=60,
        id="process_pending_campaign_recipients",
        replace_existing=True,
    )

    scheduler.add_job(
        run_duplicate_detection_sweep_job,
        "cron",
        hour=1,
        minute=30,
        id="duplicate_detection_sweep",
        replace_existing=True,
    )

    # bughunt H-7: nightly sweep that flags SCHEDULED appointments whose
    # Y/R/C confirmation SMS has been silent for N days (default 3) so
    # the admin review queue on /schedule can surface them.
    scheduler.add_job(
        flag_no_reply_confirmations,
        CronTrigger(hour=6, minute=0),
        id="flag_no_reply_confirmations",
        replace_existing=True,
    )

    # Gap 07 — daily prune of fallback-dedup rows older than 30 days.
    scheduler.add_job(
        prune_webhook_processed_logs_job,
        "cron",
        hour=3,
        minute=30,
        id="prune_webhook_processed_logs",
        replace_existing=True,
    )

    logger.info(
        "scheduler.jobs.registered",
        jobs=[
            "escalate_failed_payments",
            "check_upcoming_renewals",
            "send_annual_notices",
            "cleanup_orphaned_consent_records",
            "remind_incomplete_onboarding",
            "process_pending_campaign_recipients",
            "duplicate_detection_sweep",
            "flag_no_reply_confirmations",
            "prune_webhook_processed_logs",
        ],
    )
