"""Unit tests for ``services.ai.scheduling.appointment_loader``.

Covers the per-staff bucketing logic and the ``status != 'cancelled'`` filter
without exercising real DB or the full Job/Staff conversion helpers (those
are exercised separately by integration tests).

Validates: Requirements 5.1, 23.1, 23.2
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from grins_platform.services.ai.scheduling.appointment_loader import (
    load_assignments_for_date,
)
from grins_platform.services.schedule_domain import (
    ScheduleJob,
    ScheduleLocation,
    ScheduleStaff,
)


def _stub_schedule_job(job_id: uuid.UUID) -> ScheduleJob:
    return ScheduleJob(
        id=job_id,
        customer_name="Test Customer",
        location=ScheduleLocation(latitude=0, longitude=0),  # type: ignore[arg-type]
        service_type="Irrigation",
        duration_minutes=60,
    )


def _stub_schedule_staff(staff_id: uuid.UUID) -> ScheduleStaff:
    return ScheduleStaff(
        id=staff_id,
        name="Test Tech",
        start_location=ScheduleLocation(latitude=0, longitude=0),  # type: ignore[arg-type]
    )


def _make_appointment(staff_id: uuid.UUID, job_id: uuid.UUID, status: str) -> MagicMock:
    """Build a minimal Appointment-shaped mock."""
    appt = MagicMock()
    appt.id = uuid.uuid4()
    appt.staff_id = staff_id
    appt.job_id = job_id
    appt.status = status
    appt.staff = MagicMock(id=staff_id, name="Test Tech")
    appt.job = MagicMock(id=job_id)
    return appt


def _make_session(appts: list[MagicMock]) -> AsyncMock:
    """Return an AsyncSession mock whose execute() yields ``appts``."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = appts
    session.execute.return_value = result
    return session


@pytest.mark.unit
@pytest.mark.asyncio
@patch(
    "grins_platform.services.ai.scheduling.appointment_loader.staff_to_schedule_staff"
)
@patch("grins_platform.services.ai.scheduling.appointment_loader.job_to_schedule_job")
async def test_load_assignments_groups_by_staff(
    mock_job_to: MagicMock,
    mock_staff_to: MagicMock,
) -> None:
    """Two appointments for one staff produce one assignment with two jobs."""
    staff_id = uuid.uuid4()
    job_a, job_b = uuid.uuid4(), uuid.uuid4()
    mock_staff_to.return_value = _stub_schedule_staff(staff_id)
    mock_job_to.side_effect = lambda j: _stub_schedule_job(j.id)

    appts = [
        _make_appointment(staff_id, job_a, "scheduled"),
        _make_appointment(staff_id, job_b, "in_progress"),
    ]
    session = _make_session(appts)

    assignments = await load_assignments_for_date(session, date(2026, 5, 1))

    assert len(assignments) == 1
    assert assignments[0].staff.id == staff_id
    assert {j.id for j in assignments[0].jobs} == {job_a, job_b}


@pytest.mark.unit
@pytest.mark.asyncio
@patch(
    "grins_platform.services.ai.scheduling.appointment_loader.staff_to_schedule_staff"
)
@patch("grins_platform.services.ai.scheduling.appointment_loader.job_to_schedule_job")
async def test_load_assignments_separate_staff_get_separate_assignments(
    mock_job_to: MagicMock,
    mock_staff_to: MagicMock,
) -> None:
    """Different staff_ids produce distinct ScheduleAssignment rows."""
    staff_a, staff_b = uuid.uuid4(), uuid.uuid4()
    job_a, job_b = uuid.uuid4(), uuid.uuid4()
    mock_staff_to.side_effect = lambda s, availability=None: _stub_schedule_staff(  # noqa: ARG005
        s.id
    )
    mock_job_to.side_effect = lambda j: _stub_schedule_job(j.id)

    appts = [
        _make_appointment(staff_a, job_a, "scheduled"),
        _make_appointment(staff_b, job_b, "confirmed"),
    ]
    session = _make_session(appts)

    assignments = await load_assignments_for_date(session, date(2026, 5, 1))

    assert len(assignments) == 2
    staff_ids = {a.staff.id for a in assignments}
    assert staff_ids == {staff_a, staff_b}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_assignments_empty_for_no_appointments() -> None:
    """No appointments → empty list, not an error."""
    session = _make_session([])
    assignments = await load_assignments_for_date(session, date(2026, 5, 1))
    assert assignments == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_assignments_filters_cancelled() -> None:
    """The query excludes cancelled appointments via the WHERE clause.

    The DB filter is enforced at the SQLAlchemy level, so the mock session
    should never see cancelled rows. We verify that the executed statement
    contains the ``status != "cancelled"`` predicate.
    """
    session = _make_session([])
    await load_assignments_for_date(session, date(2026, 5, 1))

    session.execute.assert_called_once()
    stmt = session.execute.call_args.args[0]
    sql_text = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "cancelled" in sql_text.lower()
