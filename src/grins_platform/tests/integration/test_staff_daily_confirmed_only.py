"""Integration test for the ``confirmed_only`` filter on the
``get_staff_daily_schedule`` repository + service path.

Seeds three appointments for one staff member on one date with statuses
SCHEDULED, CONFIRMED, CANCELLED, then asserts that
``AppointmentService.get_staff_daily_schedule(...)`` returns exactly the
single CONFIRMED appointment — the tech-mobile schedule view must never
show un-confirmed or cancelled work.

Validates: cluster-c-job-creation-and-signwell-removal Tasks 6 + 7.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.models.enums import AppointmentStatus, StaffRole
from grins_platform.repositories.appointment_repository import AppointmentRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.services.appointment_service import AppointmentService

# =============================================================================
# Helpers
# =============================================================================


def _make_appointment(
    *,
    staff_id: uuid.UUID,
    scheduled_date: date,
    status: str,
    time_window_start: time,
    time_window_end: time,
) -> MagicMock:
    apt = MagicMock()
    apt.id = uuid.uuid4()
    apt.job_id = uuid.uuid4()
    apt.staff_id = staff_id
    apt.scheduled_date = scheduled_date
    apt.time_window_start = time_window_start
    apt.time_window_end = time_window_end
    apt.status = status
    apt.notes = None
    apt.route_order = None
    apt.estimated_arrival = None
    apt.arrived_at = None
    apt.completed_at = None
    apt.created_at = datetime.now()
    apt.updated_at = datetime.now()
    apt.get_duration_minutes = MagicMock(return_value=120)
    return apt


def _make_staff(staff_id: uuid.UUID) -> MagicMock:
    staff = MagicMock()
    staff.id = staff_id
    staff.name = "Tech One"
    staff.role = StaffRole.TECH.value
    staff.is_active = True
    return staff


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestStaffDailyScheduleConfirmedOnly:
    """The default ``confirmed_only=True`` filter must hide
    SCHEDULED and CANCELLED appointments from the staff daily view."""

    async def test_returns_only_confirmed_appointment(self) -> None:
        staff_id = uuid.uuid4()
        schedule_date = date.today()

        scheduled = _make_appointment(
            staff_id=staff_id,
            scheduled_date=schedule_date,
            status=AppointmentStatus.SCHEDULED.value,
            time_window_start=time(8, 0),
            time_window_end=time(10, 0),
        )
        confirmed = _make_appointment(
            staff_id=staff_id,
            scheduled_date=schedule_date,
            status=AppointmentStatus.CONFIRMED.value,
            time_window_start=time(10, 0),
            time_window_end=time(12, 0),
        )
        cancelled = _make_appointment(
            staff_id=staff_id,
            scheduled_date=schedule_date,
            status=AppointmentStatus.CANCELLED.value,
            time_window_start=time(13, 0),
            time_window_end=time(15, 0),
        )

        # Mock the repository: when called with confirmed_only=True (the
        # default), return only the confirmed row. When called with
        # confirmed_only=False, return all three. The real repository
        # SQL filter is unit-tested elsewhere — this test pins down the
        # service-default contract.
        mock_appointment_repo = AsyncMock(spec=AppointmentRepository)

        async def _staff_daily_side_effect(
            sid: uuid.UUID,
            sdate: date,
            include_relationships: bool = False,
            confirmed_only: bool = True,
        ) -> list[MagicMock]:
            assert sid == staff_id
            assert sdate == schedule_date
            all_three = [scheduled, confirmed, cancelled]
            confirmed_value = AppointmentStatus.CONFIRMED.value
            if confirmed_only:
                return [a for a in all_three if a.status == confirmed_value]
            return all_three

        mock_appointment_repo.get_staff_daily_schedule.side_effect = (
            _staff_daily_side_effect
        )

        mock_staff_repo = AsyncMock(spec=StaffRepository)
        mock_staff_repo.get_by_id.return_value = _make_staff(staff_id)

        mock_job_repo = AsyncMock(spec=JobRepository)

        service = AppointmentService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            staff_repository=mock_staff_repo,
        )

        (
            result,
            count,
            total_minutes,
        ) = await service.get_staff_daily_schedule(
            staff_id=staff_id,
            schedule_date=schedule_date,
        )

        assert count == 1
        assert len(result) == 1
        assert result[0].id == confirmed.id
        assert result[0].status == AppointmentStatus.CONFIRMED.value
        # Default service call must propagate confirmed_only=True down to
        # the repository.
        kwargs = mock_appointment_repo.get_staff_daily_schedule.await_args.kwargs
        assert kwargs.get("confirmed_only") is True
        assert total_minutes == 120
