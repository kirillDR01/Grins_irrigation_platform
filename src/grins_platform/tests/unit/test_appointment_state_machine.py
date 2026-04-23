"""Unit tests for the Appointment status state machine.

Validates: gap-04.A (state machine not enforced), gap-04.B (missing
CONFIRMED -> SCHEDULED edge for reschedule_for_request).
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.exceptions import InvalidStatusTransitionError
from grins_platform.models.appointment import (
    VALID_APPOINTMENT_TRANSITIONS,
    Appointment,
)
from grins_platform.models.enums import AppointmentStatus
from grins_platform.repositories.appointment_repository import AppointmentRepository


def _make_real_appointment(status: str | None = "scheduled") -> Appointment:
    """Construct a real Appointment instance (not a Mock) so @validates fires."""
    kwargs: dict[str, object] = {
        "job_id": uuid4(),
        "staff_id": uuid4(),
        "scheduled_date": date.today(),
        "time_window_start": time(9, 0),
        "time_window_end": time(10, 0),
    }
    if status is not None:
        kwargs["status"] = status
    return Appointment(**kwargs)  # type: ignore[arg-type]


# ===========================================================================
# 1. @validates("status") hook
# ===========================================================================


@pytest.mark.unit
class TestValidatesHook:
    """Behaviour of Appointment._validate_status_transition."""

    def test_initial_insert_skips_validator(self) -> None:
        """First set on a freshly-constructed (status=None) row is allowed."""
        appt = _make_real_appointment(status=None)
        appt.status = AppointmentStatus.SCHEDULED.value
        assert appt.status == AppointmentStatus.SCHEDULED.value

    def test_same_status_set_is_noop_on_terminal_completed(self) -> None:
        """Idempotent set on COMPLETED (a terminal status) must not raise."""
        appt = _make_real_appointment(status=AppointmentStatus.COMPLETED.value)
        appt.status = AppointmentStatus.COMPLETED.value
        assert appt.status == AppointmentStatus.COMPLETED.value

    def test_scheduled_to_confirmed_succeeds(self) -> None:
        """SCHEDULED -> CONFIRMED is the canonical happy-path edge."""
        appt = _make_real_appointment(status=AppointmentStatus.SCHEDULED.value)
        appt.status = AppointmentStatus.CONFIRMED.value
        assert appt.status == AppointmentStatus.CONFIRMED.value

    def test_completed_to_scheduled_raises_invalid_transition(self) -> None:
        """COMPLETED is terminal; any non-idempotent set must raise."""
        appt = _make_real_appointment(status=AppointmentStatus.COMPLETED.value)
        with pytest.raises(InvalidStatusTransitionError) as exc:
            appt.status = AppointmentStatus.SCHEDULED.value
        assert exc.value.current_status == AppointmentStatus.COMPLETED
        assert exc.value.requested_status == AppointmentStatus.SCHEDULED


# ===========================================================================
# 2. Dict edges added in this plan (gap-04.B + skip-to-complete)
# ===========================================================================


@pytest.mark.unit
class TestDictContents4B:
    """Edges added to VALID_APPOINTMENT_TRANSITIONS by this plan."""

    def test_confirmed_can_transition_to_scheduled(self) -> None:
        """gap-04.B: reschedule_for_request needs CONFIRMED -> SCHEDULED."""
        assert (
            AppointmentStatus.SCHEDULED.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.CONFIRMED.value]
        )

    def test_scheduled_can_transition_to_completed(self) -> None:
        """Skip-to-complete: /jobs/{id}/complete from SCHEDULED."""
        assert (
            AppointmentStatus.COMPLETED.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.SCHEDULED.value]
        )

    def test_confirmed_can_transition_to_completed(self) -> None:
        """Skip-to-complete: /jobs/{id}/complete from CONFIRMED."""
        assert (
            AppointmentStatus.COMPLETED.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.CONFIRMED.value]
        )


# ===========================================================================
# 3. Repository SQL-update guard
# ===========================================================================


def _build_repo_with_current_status(
    current_status: str | None,
) -> AppointmentRepository:
    """Build an AppointmentRepository with session.execute returning a row
    whose first scalar column is ``current_status``.
    """
    session = AsyncMock()
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = current_status
    session.execute = AsyncMock(return_value=select_result)
    session.flush = AsyncMock()
    return AppointmentRepository(session)


@pytest.mark.unit
@pytest.mark.asyncio
class TestRepositoryGuard:
    """AppointmentRepository._validate_status_transition_or_raise + callers."""

    async def test_update_with_invalid_status_raises(self) -> None:
        """update() must reject COMPLETED -> SCHEDULED."""
        repo = _build_repo_with_current_status(AppointmentStatus.COMPLETED.value)
        with pytest.raises(InvalidStatusTransitionError):
            await repo.update(uuid4(), {"status": AppointmentStatus.SCHEDULED.value})
        assert repo.session.execute.call_count == 1

    async def test_update_with_valid_status_passes_guard(self) -> None:
        """update() must let SCHEDULED -> CONFIRMED through to the SQL UPDATE."""
        repo = _build_repo_with_current_status(AppointmentStatus.SCHEDULED.value)

        update_result = MagicMock()
        update_result.scalar_one_or_none.return_value = MagicMock(
            spec=Appointment,
        )
        guard_result = MagicMock()
        guard_result.scalar_one_or_none.return_value = AppointmentStatus.SCHEDULED.value
        repo.session.execute = AsyncMock(side_effect=[guard_result, update_result])

        result = await repo.update(
            uuid4(),
            {"status": AppointmentStatus.CONFIRMED.value},
        )
        assert result is not None
        assert repo.session.execute.call_count == 2

    async def test_update_status_with_invalid_transition_raises(self) -> None:
        """update_status() also routes through the guard."""
        repo = _build_repo_with_current_status(AppointmentStatus.COMPLETED.value)
        with pytest.raises(InvalidStatusTransitionError):
            await repo.update_status(uuid4(), AppointmentStatus.SCHEDULED)

    async def test_guard_silent_on_missing_row(self) -> None:
        """A missing row must NOT raise; the caller's not-found path handles it."""
        repo = _build_repo_with_current_status(None)
        # Should not raise — repo will produce a None update result later.
        await repo._validate_status_transition_or_raise(
            uuid4(),
            AppointmentStatus.CONFIRMED.value,
        )

    async def test_guard_silent_on_same_status(self) -> None:
        """Idempotent update (same status) must not raise."""
        repo = _build_repo_with_current_status(AppointmentStatus.COMPLETED.value)
        await repo._validate_status_transition_or_raise(
            uuid4(),
            AppointmentStatus.COMPLETED.value,
        )


# ===========================================================================
# 4. async transition_to() helper
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestTransitionTo:
    """Appointment.transition_to: status change + audit write + log."""

    async def test_transition_to_happy_path_writes_audit_log(self) -> None:
        appt = _make_real_appointment(status=AppointmentStatus.SCHEDULED.value)
        appt.id = uuid4()
        session = AsyncMock()
        session.flush = AsyncMock()
        actor_id = uuid4()

        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository",
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit

            await appt.transition_to(
                session,
                AppointmentStatus.CONFIRMED.value,
                actor_id=actor_id,
                reason="customer_confirmed",
            )

        assert appt.status == AppointmentStatus.CONFIRMED.value
        session.flush.assert_awaited_once()
        mock_audit.create.assert_awaited_once()
        call_kwargs = mock_audit.create.await_args.kwargs
        assert call_kwargs["action"] == "appointment.status.transition"
        assert call_kwargs["resource_type"] == "appointment"
        assert call_kwargs["resource_id"] == appt.id
        assert call_kwargs["actor_id"] == actor_id
        assert call_kwargs["details"] == {
            "from_status": AppointmentStatus.SCHEDULED.value,
            "to_status": AppointmentStatus.CONFIRMED.value,
            "reason": "customer_confirmed",
        }

    async def test_transition_to_audit_failure_does_not_block_transition(
        self,
    ) -> None:
        appt = _make_real_appointment(status=AppointmentStatus.SCHEDULED.value)
        appt.id = uuid4()
        session = AsyncMock()
        session.flush = AsyncMock()

        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository",
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit.create = AsyncMock(side_effect=RuntimeError("db down"))
            mock_audit_cls.return_value = mock_audit

            await appt.transition_to(session, AppointmentStatus.CONFIRMED.value)

        assert appt.status == AppointmentStatus.CONFIRMED.value
        session.flush.assert_awaited_once()

    async def test_transition_to_invalid_edge_raises_before_audit(self) -> None:
        appt = _make_real_appointment(status=AppointmentStatus.COMPLETED.value)
        appt.id = uuid4()
        session = AsyncMock()
        session.flush = AsyncMock()

        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository",
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit

            with pytest.raises(InvalidStatusTransitionError):
                await appt.transition_to(session, AppointmentStatus.SCHEDULED.value)

        # @validates raised; flush + audit must NOT have been called.
        session.flush.assert_not_called()
        mock_audit.create.assert_not_called()


# ===========================================================================
# 5. Hypothesis property: dict ⇔ can_transition_to consistency
# ===========================================================================


all_appointment_statuses = st.sampled_from(list(AppointmentStatus))


@pytest.mark.unit
class TestPropertyTransitionDictIsConsistent:
    """can_transition_to(next) must agree with VALID_APPOINTMENT_TRANSITIONS."""

    @given(current=all_appointment_statuses, next_=all_appointment_statuses)
    @settings(max_examples=100)
    def test_can_transition_to_matches_dict(
        self,
        current: AppointmentStatus,
        next_: AppointmentStatus,
    ) -> None:
        appt = _make_real_appointment(status=current.value)
        expected = next_.value in VALID_APPOINTMENT_TRANSITIONS[current.value]
        assert appt.can_transition_to(next_.value) is expected
