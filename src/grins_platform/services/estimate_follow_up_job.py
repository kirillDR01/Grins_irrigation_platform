"""Background job for estimate follow-up SMS cadence (F7).

Walks ``estimate_follow_up`` rows whose ``scheduled_at`` is now or in the
past and dispatches the Day 3 / 7 / 14 / 21 SMS nudges via
``EstimateService.process_follow_ups``. Mirrors the F6
``sales_pipeline_nudge_job`` shape exactly: LoggerMixin class +
module-level singleton + async wrapper for APScheduler.

Validates: F7 sign-off (run-20260504-184355-portal-cron).
"""

from __future__ import annotations

from grins_platform.database import get_database_manager
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.repositories.estimate_repository import EstimateRepository
from grins_platform.services.email_config import EmailSettings
from grins_platform.services.estimate_service import EstimateService
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms_service import SMSService

logger = get_logger(__name__)


class EstimateFollowUpJob(LoggerMixin):
    """Walks ``estimate_follow_up`` rows and sends due SMS nudges.

    Constructs its own ``SMSService`` instance so it can run outside the
    request lifecycle. Without ``sms_service`` wired,
    ``EstimateService.process_follow_ups`` flips every due row to
    ``SKIPPED`` with ``reason="no_channel_available"`` — appears to work
    but never sends. The unit + functional tests assert ``sent_count > 0``
    to lock that contract in.

    Validates: F7 sign-off (run-20260504-184355-portal-cron).
    """

    DOMAIN = "estimate_follow_up"

    async def run(self) -> None:
        """Execute the estimate follow-up cron once."""
        self.log_started("run")
        db_manager = get_database_manager()
        portal_base_url = EmailSettings().portal_base_url
        sent_count = 0

        async for session in db_manager.get_session():
            estimate_repository = EstimateRepository(session=session)
            sms_service = SMSService(session=session, provider=get_sms_provider())
            estimate_service = EstimateService(
                estimate_repository=estimate_repository,
                portal_base_url=portal_base_url,
                sms_service=sms_service,
            )
            sent_count = await estimate_service.process_follow_ups()
            await session.commit()

        self.log_completed("run", entries_sent=sent_count)


_estimate_follow_up_job = EstimateFollowUpJob()


async def process_estimate_follow_ups_job() -> None:
    """Async wrapper for APScheduler registration."""
    await _estimate_follow_up_job.run()
