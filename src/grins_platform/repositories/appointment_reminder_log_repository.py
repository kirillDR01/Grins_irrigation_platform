"""Repository for :class:`AppointmentReminderLog` rows.

The Day-2 No-Reply Reminder job (gap-10 Phase 1) writes one row per
reminder SMS actually sent so subsequent hourly ticks can dedup against
``(appointment_id, stage)``. This repository exposes the create + read
helpers the job needs.

Validates: scheduling gaps gap-10 Phase 1 (Day-2 No-Reply Reminder)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import desc, func, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment_reminder_log import AppointmentReminderLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AppointmentReminderLogRepository(LoggerMixin):
    """Repository for :class:`AppointmentReminderLog` database operations.

    Mirrors :class:`AlertRepository` — takes an :class:`AsyncSession`,
    exposes structured-logging wrappers via :class:`LoggerMixin`, and
    performs all I/O through the injected session.

    Validates: scheduling gaps gap-10 Phase 1
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations.
        """
        super().__init__()
        self.session = session

    async def create(self, log: AppointmentReminderLog) -> AppointmentReminderLog:
        """Persist a new :class:`AppointmentReminderLog` row.

        Args:
            log: Fully-populated instance to persist.

        Returns:
            The refreshed row (server defaults applied).
        """
        self.log_started(
            "create",
            appointment_id=str(log.appointment_id),
            stage=log.stage,
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        self.log_completed("create", reminder_log_id=str(log.id))
        return log

    async def get_latest_for(
        self,
        appointment_id: UUID,
        stage: str,
    ) -> AppointmentReminderLog | None:
        """Return the most recent log row for ``(appointment_id, stage)``.

        Used by :class:`Day2ReminderJob` as the dedup probe — the
        eligibility query already excludes appointments with a row,
        but the per-row send path also re-checks defensively.

        Args:
            appointment_id: Target appointment UUID.
            stage: Reminder cadence (``day_2``, ``day_before``, ...).

        Returns:
            Most recent :class:`AppointmentReminderLog`, or ``None``.
        """
        self.log_started(
            "get_latest_for",
            appointment_id=str(appointment_id),
            stage=stage,
        )
        stmt = (
            select(AppointmentReminderLog)
            .where(
                AppointmentReminderLog.appointment_id == appointment_id,
                AppointmentReminderLog.stage == stage,
            )
            .order_by(desc(AppointmentReminderLog.sent_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row: AppointmentReminderLog | None = result.scalar_one_or_none()
        self.log_completed("get_latest_for", found=row is not None)
        return row

    async def count_for_appointment(self, appointment_id: UUID) -> int:
        """Return total reminder rows logged for an appointment.

        Args:
            appointment_id: Target appointment UUID.

        Returns:
            Row count across all stages.
        """
        self.log_started(
            "count_for_appointment",
            appointment_id=str(appointment_id),
        )
        stmt = select(func.count(AppointmentReminderLog.id)).where(
            AppointmentReminderLog.appointment_id == appointment_id,
        )
        result = await self.session.execute(stmt)
        count = int(result.scalar() or 0)
        self.log_completed("count_for_appointment", count=count)
        return count
