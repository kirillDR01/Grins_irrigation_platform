"""Appointment → ScheduleAssignment loader.

Pure adapter: queries persisted ``Appointment`` rows for a given date and
groups them by staff into ``ScheduleAssignment`` instances suitable for the
``CriteriaEvaluator``. Used by ``POST /ai-scheduling/evaluate`` (Bug 3) and
``GET /schedule/capacity/{date}`` (Bug 5) so both endpoints actually score
real schedule state instead of an empty solution.

Validates: Requirements 5.1, 23.1, 23.2
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from grins_platform.log_config import get_logger
from grins_platform.models.appointment import Appointment
from grins_platform.services.schedule_domain import ScheduleAssignment
from grins_platform.services.schedule_solver_service import (
    job_to_schedule_job,
    staff_to_schedule_staff,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


_log = get_logger(__name__)


async def load_assignments_for_date(
    session: AsyncSession,
    schedule_date: date,
) -> list[ScheduleAssignment]:
    """Load persisted ``Appointment`` rows for ``schedule_date`` and group them
    by staff into ``ScheduleAssignment`` instances.

    Cancelled appointments are excluded; every other status (scheduled,
    confirmed, in_progress, completed, no_show) counts as "schedule occurred"
    for evaluation purposes.

    The relationship eager-loading (``selectinload(Appointment.job)`` and
    ``selectinload(Appointment.staff)``) keeps this O(1) DB round-trips
    instead of O(N) per appointment.

    Args:
        session: Active async DB session.
        schedule_date: Target date to load.

    Returns:
        One ``ScheduleAssignment`` per distinct staff with appointments on
        the date, each containing the corresponding ``ScheduleJob`` list.
        Empty list when no appointments exist for the date.
    """
    _log.info(
        "scheduling.evaluate.assignments_load_started",
        schedule_date=str(schedule_date),
    )

    stmt = (
        select(Appointment)
        .where(Appointment.scheduled_date == schedule_date)
        .where(Appointment.status != "cancelled")
        .options(
            selectinload(Appointment.job),
            selectinload(Appointment.staff),
        )
    )
    result = await session.execute(stmt)
    appointments = list(result.scalars().all())

    by_staff: dict[UUID, ScheduleAssignment] = {}
    for appt in appointments:
        if appt.staff_id not in by_staff:
            by_staff[appt.staff_id] = ScheduleAssignment(
                id=uuid4(),
                staff=staff_to_schedule_staff(appt.staff, availability=None),
                jobs=[],
            )
        by_staff[appt.staff_id].jobs.append(job_to_schedule_job(appt.job))

    assignments = list(by_staff.values())

    _log.info(
        "scheduling.evaluate.assignments_loaded",
        schedule_date=str(schedule_date),
        count=len(assignments),
        appointment_count=len(appointments),
    )

    return assignments
