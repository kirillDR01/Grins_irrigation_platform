"""Background scheduled jobs for agreement lifecycle management.

Implements daily/weekly jobs for payment escalation, renewal checks,
annual notices, and orphaned consent cleanup.

Validates: Requirements 15.1-15.4, 16.1-16.4, 37.2, 37.3
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import stripe
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from grins_platform.database import get_database_manager
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.enums import (
    AgreementStatus,
    DisclosureType,
    JobStatus,
)
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.services.compliance_service import ComplianceService
from grins_platform.services.email_service import EmailService
from grins_platform.services.onboarding_reminder_job import OnboardingReminderJob
from grins_platform.services.stripe_config import StripeSettings

if TYPE_CHECKING:
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
                if job.status == JobStatus.APPROVED.value:
                    job.status = JobStatus.CANCELLED.value
                    job.closed_at = now

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


# Singleton instances for job functions
_escalator = FailedPaymentEscalator()
_renewal_checker = UpcomingRenewalChecker()
_annual_sender = AnnualNoticeSender()
_orphan_cleaner = OrphanedConsentCleaner()
_onboarding_reminder = OnboardingReminderJob()


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

    logger.info(
        "scheduler.jobs.registered",
        jobs=[
            "escalate_failed_payments",
            "check_upcoming_renewals",
            "send_annual_notices",
            "cleanup_orphaned_consent_records",
            "remind_incomplete_onboarding",
        ],
    )
