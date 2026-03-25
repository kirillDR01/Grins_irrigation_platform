"""StaffBreakService for managing staff breaks.

Creates and ends break records, adjusts subsequent appointment ETAs
when a break ends.

Validates: CRM Gap Closure Req 42.2, 42.5
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.enums import AppointmentStatus, BreakType
from grins_platform.models.staff_break import StaffBreak

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BreakNotFoundError(Exception):
    """Raised when a staff break is not found."""

    def __init__(self, break_id: UUID) -> None:
        super().__init__(f"Staff break {break_id} not found")
        self.break_id = break_id


class BreakAlreadyEndedError(Exception):
    """Raised when trying to end an already-ended break."""

    def __init__(self, break_id: UUID) -> None:
        super().__init__(f"Staff break {break_id} already ended")
        self.break_id = break_id


class StaffBreakService(LoggerMixin):
    """Service for staff break management.

    Creates break records, ends breaks, and adjusts subsequent
    appointment ETAs based on break duration.

    Validates: CRM Gap Closure Req 42.2, 42.5
    """

    DOMAIN = "staff"

    async def create_break(
        self,
        db: AsyncSession,
        *,
        staff_id: UUID,
        break_type: str,
        appointment_id: UUID | None = None,
    ) -> StaffBreak:
        """Create a new staff break record.

        Args:
            db: Database session.
            staff_id: Staff UUID.
            break_type: Break type (lunch, gas, personal, other).
            appointment_id: Current appointment UUID (optional).

        Returns:
            Created StaffBreak instance.

        Validates: Req 42.2
        """
        self.log_started(
            "create_break",
            staff_id=str(staff_id),
            break_type=break_type,
        )

        # Validate break type
        try:
            BreakType(break_type)
        except ValueError:
            self.log_rejected(
                "create_break",
                reason=f"invalid_break_type: {break_type}",
            )
            msg = f"Invalid break type: {break_type}"
            raise ValueError(msg) from None

        now = datetime.now(tz=timezone.utc)
        staff_break = StaffBreak(
            staff_id=staff_id,
            appointment_id=appointment_id,
            start_time=now.time(),
            break_type=break_type,
        )
        db.add(staff_break)
        await db.flush()
        await db.refresh(staff_break)

        self.log_completed(
            "create_break",
            break_id=str(staff_break.id),
            staff_id=str(staff_id),
        )
        return staff_break

    async def end_break(
        self,
        db: AsyncSession,
        *,
        break_id: UUID,
    ) -> StaffBreak:
        """End a staff break and adjust subsequent appointment ETAs.

        Args:
            db: Database session.
            break_id: StaffBreak UUID.

        Returns:
            Updated StaffBreak instance.

        Raises:
            BreakNotFoundError: If break not found.
            BreakAlreadyEndedError: If break already ended.

        Validates: Req 42.5
        """
        self.log_started("end_break", break_id=str(break_id))

        stmt = select(StaffBreak).where(StaffBreak.id == break_id)
        result = await db.execute(stmt)
        staff_break = result.scalar_one_or_none()

        if staff_break is None:
            raise BreakNotFoundError(break_id)

        if staff_break.end_time is not None:
            raise BreakAlreadyEndedError(break_id)

        now = datetime.now(tz=timezone.utc)
        staff_break.end_time = now.time()
        await db.flush()

        # Calculate break duration in minutes
        start_dt = datetime.combine(now.date(), staff_break.start_time)
        end_dt = datetime.combine(now.date(), staff_break.end_time)
        break_duration = end_dt - start_dt
        break_minutes = int(break_duration.total_seconds() / 60)

        # Adjust subsequent appointment ETAs
        if break_minutes > 0:
            adjusted = await self._adjust_subsequent_etas(
                db,
                staff_id=staff_break.staff_id,
                delay_minutes=break_minutes,
                after_time=staff_break.end_time,
            )
            self.logger.info(
                "staff.break.etas_adjusted",
                break_id=str(break_id),
                staff_id=str(staff_break.staff_id),
                break_minutes=break_minutes,
                appointments_adjusted=adjusted,
            )

        self.log_completed(
            "end_break",
            break_id=str(break_id),
            break_minutes=break_minutes,
        )
        return staff_break

    async def _adjust_subsequent_etas(
        self,
        db: AsyncSession,
        *,
        staff_id: UUID,
        delay_minutes: int,
        after_time: time,
    ) -> int:
        """Adjust estimated arrival times for subsequent appointments.

        Pushes all remaining appointments for the staff member on the
        same day forward by the break duration.

        Args:
            db: Database session.
            staff_id: Staff UUID.
            delay_minutes: Minutes to push forward.
            after_time: Only adjust appointments after this time.

        Returns:
            Number of appointments adjusted.
        """
        from datetime import date as date_type  # noqa: PLC0415

        today = date_type.today()

        # Find subsequent appointments for this staff member today
        active_statuses = [
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
        ]
        stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.staff_id == staff_id,
                    Appointment.scheduled_date == today,
                    Appointment.status.in_(active_statuses),
                    Appointment.time_window_start > after_time,
                ),
            )
            .order_by(Appointment.time_window_start)
        )
        result = await db.execute(stmt)
        appointments = list(result.scalars().all())

        adjusted_count = 0
        delay = timedelta(minutes=delay_minutes)

        for appt in appointments:
            if appt.estimated_arrival is not None:
                # Shift estimated arrival
                old_arrival = datetime.combine(today, appt.estimated_arrival)
                new_arrival = old_arrival + delay
                appt.estimated_arrival = new_arrival.time()
                adjusted_count += 1

        if adjusted_count > 0:
            await db.flush()

        return adjusted_count

    async def get_active_break(
        self,
        db: AsyncSession,
        staff_id: UUID,
    ) -> StaffBreak | None:
        """Get the currently active (unended) break for a staff member.

        Args:
            db: Database session.
            staff_id: Staff UUID.

        Returns:
            Active StaffBreak or None.
        """
        stmt = (
            select(StaffBreak)
            .where(
                and_(
                    StaffBreak.staff_id == staff_id,
                    StaffBreak.end_time.is_(None),
                ),
            )
            .order_by(StaffBreak.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
