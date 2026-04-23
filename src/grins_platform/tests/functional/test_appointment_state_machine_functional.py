"""Functional tests for the appointment state machine enforcement.

Exercises the seam between AppointmentService.reschedule_for_request and
AppointmentRepository — validates gap-04.A (repo guard catches an SQL
UPDATE bypass) and gap-04.B (CONFIRMED -> SCHEDULED edge unblocks the
customer-initiated reschedule path).

Validates: gap-04.A, gap-04.B
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import InvalidStatusTransitionError
from grins_platform.models.appointment import Appointment
from grins_platform.models.enums import AppointmentStatus
from grins_platform.repositories.appointment_repository import AppointmentRepository
from grins_platform.services.appointment_service import AppointmentService


def _make_appointment(**overrides: Any) -> MagicMock:
    """Mock Appointment with sensible defaults (matches existing functional pattern)."""
    apt = MagicMock()
    apt.id = overrides.get("id", uuid4())
    apt.job_id = overrides.get("job_id", uuid4())
    apt.staff_id = overrides.get("staff_id", uuid4())
    apt.scheduled_date = overrides.get("scheduled_date", date(2026, 5, 15))
    apt.time_window_start = overrides.get("time_window_start", time(9, 0))
    apt.time_window_end = overrides.get("time_window_end", time(11, 0))
    apt.status = overrides.get("status", AppointmentStatus.SCHEDULED.value)
    apt.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    apt.updated_at = datetime.now(tz=timezone.utc)
    return apt


def _build_appointment_service(
    *,
    appt_repo: AsyncMock | None = None,
) -> tuple[AppointmentService, AsyncMock]:
    """Build an AppointmentService with AsyncMock repositories."""
    appointment_repo = appt_repo or AsyncMock()
    svc = AppointmentService(
        appointment_repository=appointment_repo,
        job_repository=AsyncMock(),
        staff_repository=AsyncMock(),
        invoice_repository=AsyncMock(),
        estimate_service=AsyncMock(),
        google_review_url="https://g.page/grins-irrigation/review",
    )
    return svc, appointment_repo


@pytest.mark.functional
@pytest.mark.asyncio
class TestRescheduleForRequest:
    """gap-04.B end-to-end through the service layer."""

    async def test_reschedule_for_request_from_confirmed_is_now_allowed(
        self,
    ) -> None:
        """CONFIRMED -> SCHEDULED via reschedule_for_request must succeed."""
        svc, appt_repo = _build_appointment_service()

        appt_id = uuid4()
        original = _make_appointment(
            id=appt_id,
            status=AppointmentStatus.CONFIRMED.value,
        )
        appt_repo.get_by_id.return_value = original

        updated = _make_appointment(
            id=appt_id,
            status=AppointmentStatus.SCHEDULED.value,
            scheduled_date=date(2026, 5, 22),
            time_window_start=time(13, 0),
            time_window_end=time(15, 0),
        )
        appt_repo.update.return_value = updated

        # _send_confirmation_sms touches an HTTP client; stub it out so the
        # test doesn't require real SMS infrastructure.
        svc._send_confirmation_sms = AsyncMock(return_value=None)  # type: ignore[method-assign]
        svc._record_reschedule_reconfirmation_audit = AsyncMock(  # type: ignore[method-assign]
            return_value=None,
        )

        new_at = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
        result = await svc.reschedule_for_request(appt_id, new_at)

        assert result is updated
        # Verify the update payload carried the SCHEDULED status assignment.
        appt_repo.update.assert_awaited_once()
        update_payload = appt_repo.update.await_args.args[1]
        assert update_payload["status"] == AppointmentStatus.SCHEDULED.value
        assert update_payload["scheduled_date"] == date(2026, 5, 22)

    async def test_reschedule_for_request_from_completed_raises(self) -> None:
        """COMPLETED is not in the allowed pre-states; service rejects."""
        svc, appt_repo = _build_appointment_service()
        appt_id = uuid4()
        appt_repo.get_by_id.return_value = _make_appointment(
            id=appt_id,
            status=AppointmentStatus.COMPLETED.value,
        )

        new_at = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
        with pytest.raises(InvalidStatusTransitionError) as exc:
            await svc.reschedule_for_request(appt_id, new_at)

        assert exc.value.current_status == AppointmentStatus.COMPLETED
        assert exc.value.requested_status == AppointmentStatus.SCHEDULED
        # Service-level pre-check fired before we ever called update().
        appt_repo.update.assert_not_called()


@pytest.mark.functional
@pytest.mark.asyncio
class TestRepositoryGuardFunctional:
    """Repo SQL-update guard end-to-end (mocked AsyncSession)."""

    async def test_repository_guard_rejects_invalid_update(self) -> None:
        """update({"status": SCHEDULED}) on a COMPLETED row must raise.

        The guard issues a SELECT; we wire its scalar_one_or_none to
        return COMPLETED. The subsequent SQL UPDATE must never run.
        """
        session = AsyncMock()
        guard_result = MagicMock()
        guard_result.scalar_one_or_none.return_value = AppointmentStatus.COMPLETED.value
        session.execute = AsyncMock(return_value=guard_result)
        session.flush = AsyncMock()

        repo = AppointmentRepository(session)

        with pytest.raises(InvalidStatusTransitionError) as exc:
            await repo.update(
                uuid4(),
                {"status": AppointmentStatus.SCHEDULED.value},
            )

        assert exc.value.current_status == AppointmentStatus.COMPLETED
        assert exc.value.requested_status == AppointmentStatus.SCHEDULED
        # Only the guard SELECT should have run; the UPDATE must not have.
        assert session.execute.call_count == 1

    async def test_repository_guard_lets_valid_status_through(self) -> None:
        """SCHEDULED -> CONFIRMED must reach the SQL UPDATE."""
        session = AsyncMock()

        guard_result = MagicMock()
        guard_result.scalar_one_or_none.return_value = AppointmentStatus.SCHEDULED.value

        update_result = MagicMock()
        update_result.scalar_one_or_none.return_value = MagicMock(spec=Appointment)

        session.execute = AsyncMock(side_effect=[guard_result, update_result])
        session.flush = AsyncMock()

        repo = AppointmentRepository(session)

        out = await repo.update(
            uuid4(),
            {"status": AppointmentStatus.CONFIRMED.value},
        )
        assert out is not None
        assert session.execute.call_count == 2
