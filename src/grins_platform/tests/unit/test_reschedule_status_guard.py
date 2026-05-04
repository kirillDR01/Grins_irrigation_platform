"""Regression tests for B-4 (2026-05-04 sign-off).

``AppointmentService.reschedule`` previously had no status-machine guard,
so an EN_ROUTE / IN_PROGRESS / COMPLETED / CANCELLED / NO_SHOW appointment
could be silently rescheduled. The guard now restricts reschedules to
``{PENDING, DRAFT, SCHEDULED, CONFIRMED}`` and raises
``InvalidStatusTransitionError`` (surfaced by the route as HTTP 422).
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import InvalidStatusTransitionError
from grins_platform.models.enums import AppointmentStatus
from grins_platform.services.appointment_service import AppointmentService


def _make_appointment(status: str) -> MagicMock:
    appt = MagicMock()
    appt.id = uuid4()
    appt.staff_id = uuid4()
    appt.status = status
    appt.scheduled_date = date(2026, 5, 4)
    appt.time_window_start = time(9, 0)
    appt.time_window_end = time(11, 0)
    return appt


def _build_service(appointment: MagicMock) -> AppointmentService:
    appt_repo = AsyncMock()
    appt_repo.get_by_id = AsyncMock(return_value=appointment)
    appt_repo.update = AsyncMock(return_value=appointment)
    return AppointmentService(
        appointment_repository=appt_repo,
        job_repository=AsyncMock(),
        staff_repository=AsyncMock(),
    )


_DISALLOWED = [
    AppointmentStatus.EN_ROUTE.value,
    AppointmentStatus.IN_PROGRESS.value,
    AppointmentStatus.COMPLETED.value,
    AppointmentStatus.CANCELLED.value,
    AppointmentStatus.NO_SHOW.value,
]

_ALLOWED = [
    AppointmentStatus.PENDING.value,
    AppointmentStatus.DRAFT.value,
    AppointmentStatus.SCHEDULED.value,
    AppointmentStatus.CONFIRMED.value,
]


@pytest.mark.unit
class TestRescheduleStatusGuard:
    """B-4 — reschedule guard rejects non-allowed statuses with 422."""

    @pytest.mark.parametrize("status", _DISALLOWED)
    @pytest.mark.asyncio
    async def test_disallowed_statuses_raise_invalid_status_transition(
        self,
        status: str,
    ) -> None:
        appointment = _make_appointment(status=status)
        service = _build_service(appointment)
        # Skip _check_staff_conflict so any test progress past the guard
        # would silently succeed — we want to ensure the guard fires first.
        service._check_staff_conflict = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await service.reschedule(
                appointment.id,
                date(2026, 5, 5),
                time(14, 0),
                time(15, 0),
            )
        assert exc_info.value.current_status.value == status
        assert exc_info.value.requested_status == AppointmentStatus.SCHEDULED

    @pytest.mark.parametrize("status", _ALLOWED)
    @pytest.mark.asyncio
    async def test_allowed_statuses_pass_guard(self, status: str) -> None:
        appointment = _make_appointment(status=status)
        service = _build_service(appointment)
        service._check_staff_conflict = AsyncMock(return_value=None)  # type: ignore[method-assign]
        # Stub out the post-send reschedule SMS hop, which only fires for
        # SCHEDULED/CONFIRMED and would otherwise hit a real SMS path.
        service._send_reschedule_sms = AsyncMock(return_value=None)  # type: ignore[method-assign]

        # Must not raise.
        result = await service.reschedule(
            appointment.id,
            date(2026, 5, 5),
            time(14, 0),
            time(15, 0),
        )
        assert result is appointment
