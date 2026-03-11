"""Background job for onboarding reminder notifications.

Sends SMS reminders to customers with incomplete onboarding (no property linked)
at T+24h, T+72h, and creates admin notification at T+7d.

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from grins_platform.database import get_database_manager
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.services.sms_service import SMSService

logger = get_logger(__name__)

# Thresholds in hours
_24H = 24
_72H = 72
_7D = 168  # 7 * 24


class OnboardingReminderJob(LoggerMixin):
    """Sends onboarding reminders for agreements missing property setup.

    Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
    """

    DOMAIN = "onboarding"

    async def run(self) -> None:
        """Execute the onboarding reminder job."""
        self.log_started("run")
        db_manager = get_database_manager()
        now = datetime.now(timezone.utc)

        async for session in db_manager.get_session():
            # Query agreements with no property, status active or pending
            stmt = (
                select(ServiceAgreement)
                .options(selectinload(ServiceAgreement.customer))
                .where(
                    ServiceAgreement.status.in_(["active", "pending"]),
                    ServiceAgreement.property_id.is_(None),
                )
            )
            result = await session.execute(stmt)
            agreements = list(result.scalars().all())

            sms_service = SMSService(session)

            for agreement in agreements:
                await self._process_agreement(agreement, sms_service, now)

            await session.commit()

        self.log_completed("run")

    async def _process_agreement(
        self,
        agreement: ServiceAgreement,
        sms_service: SMSService,
        now: datetime,
    ) -> None:
        """Process a single agreement for reminder eligibility."""
        hours_since = (now - agreement.created_at).total_seconds() / 3600
        count = agreement.onboarding_reminder_count

        if count == 0 and hours_since >= _24H:
            await self._send_reminder(
                agreement,
                sms_service,
                now,
                "24h_sms",
            )
        elif count == 1 and hours_since >= _72H:
            await self._send_reminder(
                agreement,
                sms_service,
                now,
                "72h_sms",
            )
        elif count == 2 and hours_since >= _7D:
            await self._create_admin_notification(agreement, now)

    async def _send_reminder(
        self,
        agreement: ServiceAgreement,
        sms_service: SMSService,
        now: datetime,
        step: str,
    ) -> None:
        """Send an SMS reminder, gated on consent and time window."""
        phone = agreement.customer.phone
        agreement_id = str(agreement.id)

        # Gate on consent (Req 10.5)
        has_consent = await sms_service.check_sms_consent(phone)
        if not has_consent:
            logger.info(
                "onboarding.reminder.skipped_no_consent",
                agreement_id=agreement_id,
                step=step,
            )
            return

        message = (
            "Hi! Your Grins Irrigation account is almost ready. "
            "Please complete your property setup to get started."
        )

        # Gate on time window (Req 10.5)
        scheduled = sms_service.enforce_time_window(phone, message, "automated")
        if scheduled is not None:
            logger.info(
                "onboarding.reminder.deferred",
                agreement_id=agreement_id,
                step=step,
                scheduled_for=scheduled.isoformat(),
            )
            return

        await sms_service.send_automated_message(phone, message, "automated")

        agreement.onboarding_reminder_count += 1  # type: ignore[assignment]
        agreement.onboarding_reminder_sent_at = now  # type: ignore[assignment]

        logger.info(
            "onboarding.reminder.sent",
            agreement_id=agreement_id,
            step=step,
            reminder_count=agreement.onboarding_reminder_count,
        )

    async def _create_admin_notification(
        self,
        agreement: ServiceAgreement,
        now: datetime,
    ) -> None:
        """Create admin notification at T+7d (no SMS)."""
        agreement_id = str(agreement.id)

        agreement.onboarding_reminder_count += 1  # type: ignore[assignment]
        agreement.onboarding_reminder_sent_at = now  # type: ignore[assignment]

        logger.warning(
            "onboarding.reminder.admin_alert",
            agreement_id=agreement_id,
            step="7d_admin_alert",
            reminder_count=agreement.onboarding_reminder_count,
            customer_phone=agreement.customer.phone,
        )
