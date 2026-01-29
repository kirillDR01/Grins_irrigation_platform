"""Schedule Clear Audit Repository for tracking schedule clear operations.

Requirements: 5.1-5.6, 6.1-6.5
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.models.schedule_clear_audit import ScheduleClearAudit


class ScheduleClearAuditRepository(LoggerMixin):
    """Repository for schedule clear audit operations."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(
        self,
        schedule_date: date,
        appointments_data: list[dict[str, Any]],
        jobs_reset: list[UUID],
        appointment_count: int,
        cleared_by: UUID | None = None,
        notes: str | None = None,
    ) -> ScheduleClearAudit:
        """Create a new schedule clear audit record.

        Args:
            schedule_date: The date that was cleared
            appointments_data: Serialized appointment data for recovery
            jobs_reset: List of job IDs that were reset to approved
            appointment_count: Number of appointments deleted
            cleared_by: Staff ID who performed the clear
            notes: Optional notes about the clear operation

        Returns:
            The created audit record
        """
        self.log_started(
            "create_audit",
            schedule_date=str(schedule_date),
            appointment_count=appointment_count,
        )

        audit = ScheduleClearAudit(
            schedule_date=schedule_date,
            appointments_data=appointments_data,
            jobs_reset=jobs_reset,
            appointment_count=appointment_count,
            cleared_by=cleared_by,
            notes=notes,
        )

        self.session.add(audit)
        await self.session.flush()
        await self.session.refresh(audit)

        self.log_completed("create_audit", audit_id=str(audit.id))
        return audit

    async def get_by_id(self, audit_id: UUID) -> ScheduleClearAudit | None:
        """Get an audit record by ID.

        Args:
            audit_id: The audit record ID

        Returns:
            The audit record or None if not found
        """
        self.log_started("get_audit", audit_id=str(audit_id))

        result = await self.session.execute(
            select(ScheduleClearAudit).where(ScheduleClearAudit.id == audit_id),
        )
        audit: ScheduleClearAudit | None = result.scalar_one_or_none()

        if audit:
            self.log_completed("get_audit", found=True)
        else:
            self.log_completed("get_audit", found=False)

        return audit

    async def find_since(
        self,
        hours: int = 24,
    ) -> list[ScheduleClearAudit]:
        """Find audit records from the last N hours.

        Args:
            hours: Number of hours to look back (default 24)

        Returns:
            List of audit records within the time window
        """
        self.log_started("find_since", hours=hours)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = await self.session.execute(
            select(ScheduleClearAudit)
            .where(ScheduleClearAudit.cleared_at >= cutoff)
            .order_by(ScheduleClearAudit.cleared_at.desc()),
        )
        audits = list(result.scalars().all())

        self.log_completed("find_since", count=len(audits))
        return audits
