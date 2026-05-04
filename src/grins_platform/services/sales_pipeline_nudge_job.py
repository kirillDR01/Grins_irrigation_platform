"""Background job for sales pipeline auto-nudges (F6).

Walks SalesEntry rows in {SEND_ESTIMATE, PENDING_APPROVAL, SEND_CONTRACT}
whose last_contact_date is older than STALE_DAYS and whose nudges are not
paused. Sends a single nudge email per stale entry per nudge cadence,
bumps last_contact_date, and writes an audit row.

Validates: F6 sign-off (run-20260504-185844-full).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select

from grins_platform.database import get_database_manager
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.enums import SalesEntryStatus
from grins_platform.models.sales import SalesEntry
from grins_platform.services.audit_service import AuditService
from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import EmailService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

STALE_DAYS = 3
NUDGE_TARGET_STATUSES: tuple[str, ...] = (
    SalesEntryStatus.SEND_ESTIMATE.value,
    SalesEntryStatus.PENDING_APPROVAL.value,
    SalesEntryStatus.SEND_CONTRACT.value,
)


class SalesPipelineNudgeJob(LoggerMixin):
    """Walks SalesEntry rows and sends auto-nudge emails for stale entries.

    Validates: F6 sign-off (run-20260504-185844-full).
    """

    DOMAIN = "sales_pipeline_nudge"

    async def run(self) -> None:
        """Execute the sales pipeline nudge job."""
        self.log_started("run")
        db_manager = get_database_manager()
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=STALE_DAYS)
        email_service = EmailService(EmailSettings())
        audit = AuditService()
        sent_count = 0

        async for session in db_manager.get_session():
            # SalesEntry.customer is lazy="selectin" already (models/sales.py)
            # so no explicit selectinload() needed.
            stmt = select(SalesEntry).where(
                SalesEntry.status.in_(NUDGE_TARGET_STATUSES),
                SalesEntry.last_contact_date.is_not(None),
                SalesEntry.last_contact_date <= cutoff,
                (SalesEntry.nudges_paused_until.is_(None))
                | (SalesEntry.nudges_paused_until <= now),
                SalesEntry.dismissed_at.is_(None),
            )
            entries = list((await session.execute(stmt)).scalars().all())

            for entry in entries:
                if await self._process(entry, email_service, audit, session, now):
                    sent_count += 1

            await session.commit()

        self.log_completed("run", entries_nudged=sent_count)

    async def _process(
        self,
        entry: SalesEntry,
        email_service: EmailService,
        audit: AuditService,
        session: AsyncSession,
        now: datetime,
    ) -> bool:
        """Send one nudge email if eligible. Returns True iff sent."""
        customer = entry.customer
        if customer is None or not getattr(customer, "email", None):
            logger.info(
                "sales_pipeline.nudge.skipped_no_email",
                entry_id=str(entry.id),
            )
            return False

        result = email_service.send_sales_pipeline_nudge(
            recipient_email=customer.email,
            customer_first_name=getattr(customer, "first_name", None),
            portal_url=None,
            estimate_total=None,
        )
        if not result.get("sent"):
            logger.warning(
                "sales_pipeline.nudge.send_failed",
                entry_id=str(entry.id),
                sent_via=result.get("sent_via"),
            )
            return False

        entry.last_contact_date = now
        entry.updated_at = now

        _ = await audit.log_action(
            session,
            action="sales_pipeline.nudge.sent",
            resource_type="sales_pipeline_entry",
            resource_id=entry.id,
            details={
                "actor_type": "system",
                "source": "nightly_job",
                "recipient_email": customer.email,
                "status": entry.status,
            },
        )

        logger.info(
            "sales_pipeline.nudge.sent",
            entry_id=str(entry.id),
            status=entry.status,
        )
        return True


_sales_pipeline_nudge_job = SalesPipelineNudgeJob()


async def nudge_stale_sales_entries_job() -> None:
    """Async wrapper for APScheduler registration."""
    await _sales_pipeline_nudge_job.run()
