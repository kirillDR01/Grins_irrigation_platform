"""Integration tests for combined job + appointment status flow (Req 19).

Tests the full lifecycle of job and appointment status transitions,
cancellation revert scenarios, and skip scenarios at the model/service
level to validate the combined status flow logic.

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from grins_platform.exceptions import InvalidStatusTransitionError
from grins_platform.models.appointment import (
    VALID_APPOINTMENT_TRANSITIONS,
    Appointment,
)
from grins_platform.models.enums import AppointmentStatus, JobStatus
from grins_platform.models.job import VALID_STATUS_TRANSITIONS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(
    *,
    job_status: str = JobStatus.TO_BE_SCHEDULED.value,
    on_my_way_at: datetime | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> Mock:
    """Create a mock Job."""
    job = Mock()
    job.id = uuid4()
    job.status = job_status
    job.on_my_way_at = on_my_way_at
    job.started_at = started_at
    job.completed_at = completed_at
    job.payment_collected_on_site = False
    job.service_agreement_id = None
    return job


def _make_appointment(
    *,
    appt_status: str = AppointmentStatus.CONFIRMED.value,
    job_id: object | None = None,
) -> Mock:
    """Create a mock Appointment."""
    appt = Mock()
    appt.id = uuid4()
    appt.job_id = job_id or uuid4()
    appt.status = appt_status
    appt.en_route_at = None
    appt.arrived_at = None
    appt.completed_at = None
    appt.created_at = datetime.now(tz=timezone.utc)
    return appt


def _simulate_on_my_way(job: Mock, appt: Mock) -> None:
    """Simulate the On My Way button logic from the endpoint."""
    job.on_my_way_at = datetime.now(tz=timezone.utc)
    if appt and appt.status in (
        AppointmentStatus.CONFIRMED.value,
        AppointmentStatus.SCHEDULED.value,
    ):
        appt.status = AppointmentStatus.EN_ROUTE.value


def _simulate_started(job: Mock, appt: Mock) -> None:
    """Simulate the Job Started button logic from the endpoint.

    Mirrors ``job_started`` in ``api/v1/jobs.py``: SCHEDULED, CONFIRMED, and
    EN_ROUTE are all valid pre-states per CR-2.
    """
    job.started_at = datetime.now(tz=timezone.utc)
    if job.status in (
        JobStatus.TO_BE_SCHEDULED.value,
        JobStatus.SCHEDULED.value,
    ):
        job.status = JobStatus.IN_PROGRESS.value
    if appt and appt.status in (
        AppointmentStatus.SCHEDULED.value,
        AppointmentStatus.CONFIRMED.value,
        AppointmentStatus.EN_ROUTE.value,
    ):
        appt.status = AppointmentStatus.IN_PROGRESS.value


def _simulate_complete(job: Mock, appt: Mock) -> None:
    """Simulate the Job Complete button logic from the endpoint."""
    job.status = JobStatus.COMPLETED.value
    if appt and appt.status not in (
        AppointmentStatus.COMPLETED.value,
        AppointmentStatus.CANCELLED.value,
        AppointmentStatus.NO_SHOW.value,
    ):
        appt.status = AppointmentStatus.COMPLETED.value


# ---------------------------------------------------------------------------
# Task 25.1: Complete Job + Appointment Lifecycle (Req 18.1, 18.2, 18.3)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCompleteJobAppointmentLifecycle:
    """Test the full combined flow from creation through completion.

    Validates: Requirements 18.1, 18.2, 18.3
    """

    def test_full_lifecycle_draft_to_completed(self) -> None:
        """Full flow: DRAFT → SCHEDULED → CONFIRMED → EN_ROUTE → IN_PROGRESS → COMPLETED.

        Verifies both job and appointment statuses at every step.

        Validates: Requirements 18.1, 18.2, 18.3
        """
        # Step 0: Create appointment (DRAFT) and job transitions to SCHEDULED
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.DRAFT.value,
            job_id=job.id,
        )

        # Verify initial state
        assert job.status == JobStatus.SCHEDULED.value
        assert appt.status == AppointmentStatus.DRAFT.value

        # Step 1: Send confirmation → DRAFT → SCHEDULED
        assert (
            AppointmentStatus.SCHEDULED.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.DRAFT.value]
        )
        appt.status = AppointmentStatus.SCHEDULED.value
        assert appt.status == AppointmentStatus.SCHEDULED.value

        # Step 2: Customer confirms → SCHEDULED → CONFIRMED
        assert (
            AppointmentStatus.CONFIRMED.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.SCHEDULED.value]
        )
        appt.status = AppointmentStatus.CONFIRMED.value
        assert appt.status == AppointmentStatus.CONFIRMED.value

        # Step 3: On My Way → CONFIRMED → EN_ROUTE
        _simulate_on_my_way(job, appt)
        assert job.on_my_way_at is not None
        assert appt.status == AppointmentStatus.EN_ROUTE.value

        # Step 4: Job Started → job IN_PROGRESS, appointment IN_PROGRESS
        _simulate_started(job, appt)
        assert job.status == JobStatus.IN_PROGRESS.value
        assert job.started_at is not None
        assert appt.status == AppointmentStatus.IN_PROGRESS.value

        # Step 5: Job Complete → both COMPLETED
        _simulate_complete(job, appt)
        assert job.status == JobStatus.COMPLETED.value
        assert appt.status == AppointmentStatus.COMPLETED.value

    def test_all_transitions_are_valid_per_transition_tables(self) -> None:
        """Every transition in the lifecycle is valid per the transition tables.

        Validates: Requirements 18.1, 18.2
        """
        # Job transitions
        assert (
            JobStatus.SCHEDULED.value
            in VALID_STATUS_TRANSITIONS[JobStatus.TO_BE_SCHEDULED.value]
        )
        assert (
            JobStatus.IN_PROGRESS.value
            in VALID_STATUS_TRANSITIONS[JobStatus.SCHEDULED.value]
        )
        assert (
            JobStatus.COMPLETED.value
            in VALID_STATUS_TRANSITIONS[JobStatus.IN_PROGRESS.value]
        )

        # Appointment transitions
        assert (
            AppointmentStatus.SCHEDULED.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.DRAFT.value]
        )
        assert (
            AppointmentStatus.CONFIRMED.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.SCHEDULED.value]
        )
        assert (
            AppointmentStatus.EN_ROUTE.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.CONFIRMED.value]
        )
        assert (
            AppointmentStatus.IN_PROGRESS.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.EN_ROUTE.value]
        )
        assert (
            AppointmentStatus.COMPLETED.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.IN_PROGRESS.value]
        )

    def test_on_my_way_from_scheduled_unconfirmed(self) -> None:
        """On My Way from SCHEDULED (unconfirmed) appointment → EN_ROUTE.

        Validates: Requirement 18.2
        """
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.SCHEDULED.value,
            job_id=job.id,
        )

        # Verify transition is valid
        assert (
            AppointmentStatus.EN_ROUTE.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.SCHEDULED.value]
        )

        _simulate_on_my_way(job, appt)
        assert appt.status == AppointmentStatus.EN_ROUTE.value

    def test_both_transition_atomically(self) -> None:
        """Both job and appointment transition in the same operation.

        Validates: Requirement 18.3
        """
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.EN_ROUTE.value,
            job_id=job.id,
        )

        # Started transitions both in one call
        _simulate_started(job, appt)
        assert job.status == JobStatus.IN_PROGRESS.value
        assert appt.status == AppointmentStatus.IN_PROGRESS.value

        # Complete transitions both in one call
        _simulate_complete(job, appt)
        assert job.status == JobStatus.COMPLETED.value
        assert appt.status == AppointmentStatus.COMPLETED.value


# ---------------------------------------------------------------------------
# gap-04: @validates("status") smoke test on a real Appointment instance
# ---------------------------------------------------------------------------


def _make_real_appointment(status: str = "scheduled") -> Appointment:
    return Appointment(
        job_id=uuid4(),
        staff_id=uuid4(),
        scheduled_date=date.today(),
        time_window_start=time(9, 0),
        time_window_end=time(11, 0),
        status=status,
    )


@pytest.mark.integration
class TestStateMachineSmoke:
    """gap-04 smoke: real Appointment + @validates fires on attribute set.

    The wider integration suite uses Mock() appointments which bypass
    @validates entirely. This class instantiates the real model so the
    validator runs. No DB session is needed for attribute-level checks.
    """

    def test_golden_path_scheduled_to_completed(self) -> None:
        """SCHEDULED -> CONFIRMED -> EN_ROUTE -> IN_PROGRESS -> COMPLETED."""
        appt = _make_real_appointment(AppointmentStatus.SCHEDULED.value)
        for next_status in (
            AppointmentStatus.CONFIRMED.value,
            AppointmentStatus.EN_ROUTE.value,
            AppointmentStatus.IN_PROGRESS.value,
            AppointmentStatus.COMPLETED.value,
        ):
            appt.status = next_status
            assert appt.status == next_status

    def test_completed_is_terminal_and_blocks_further_transitions(self) -> None:
        """A COMPLETED appointment cannot be re-set to SCHEDULED."""
        appt = _make_real_appointment(AppointmentStatus.COMPLETED.value)
        with pytest.raises(InvalidStatusTransitionError):
            appt.status = AppointmentStatus.SCHEDULED.value


# ---------------------------------------------------------------------------
# Task 25.2: Cancellation Revert Scenarios (Req 18.4)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCancellationRevertScenarios:
    """Test cancellation scenarios and job status revert logic.

    Validates: Requirement 18.4
    """

    @pytest.mark.asyncio
    async def test_cancel_only_appointment_reverts_job_to_tbs(self) -> None:
        """Cancel the only appointment → job reverts to TO_BE_SCHEDULED.

        Validates: Requirement 18.4
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        now = datetime.now(tz=timezone.utc)
        job = _make_job(
            job_status=JobStatus.SCHEDULED.value,
            on_my_way_at=now,
            started_at=now,
        )
        appt = _make_appointment(
            appt_status=AppointmentStatus.CANCELLED.value,
            job_id=job.id,
        )
        appt.en_route_at = now
        appt.arrived_at = now
        appt.completed_at = now

        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()

        with patch(
            "grins_platform.services.appointment_service.count_active_appointments",
            new_callable=AsyncMock,
            return_value=0,
        ):
            await clear_on_site_data(session, appt, job=job)

        # Appointment timestamps cleared
        assert appt.en_route_at is None
        assert appt.arrived_at is None
        assert appt.completed_at is None

        # Job timestamps cleared (no other active appointments)
        assert job.on_my_way_at is None
        assert job.started_at is None
        assert job.completed_at is None

    @pytest.mark.asyncio
    async def test_cancel_one_of_two_appointments_job_stays_scheduled(
        self,
    ) -> None:
        """Cancel one of two appointments → job stays SCHEDULED.

        Validates: Requirement 18.4
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        now = datetime.now(tz=timezone.utc)
        job = _make_job(
            job_status=JobStatus.SCHEDULED.value,
            on_my_way_at=now,
        )
        appt = _make_appointment(
            appt_status=AppointmentStatus.CANCELLED.value,
            job_id=job.id,
        )
        appt.en_route_at = now
        appt.arrived_at = None
        appt.completed_at = None

        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()

        # Another active appointment exists
        with patch(
            "grins_platform.services.appointment_service.count_active_appointments",
            new_callable=AsyncMock,
            return_value=1,
        ):
            await clear_on_site_data(session, appt, job=job)

        # Appointment timestamps cleared
        assert appt.en_route_at is None

        # Job timestamps preserved (other active appointment exists)
        assert job.on_my_way_at == now
        assert job.status == JobStatus.SCHEDULED.value

    def test_cancellation_revert_transition_is_valid(self) -> None:
        """SCHEDULED → TO_BE_SCHEDULED is a valid transition for revert.

        Validates: Requirement 18.4
        """
        assert (
            JobStatus.TO_BE_SCHEDULED.value
            in VALID_STATUS_TRANSITIONS[JobStatus.SCHEDULED.value]
        )

    def test_cancellation_from_any_non_terminal_appointment_status(self) -> None:
        """CANCELLED is reachable from all non-terminal appointment statuses.

        Validates: Requirement 18.4
        """
        non_terminal = [
            AppointmentStatus.DRAFT.value,
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
            AppointmentStatus.EN_ROUTE.value,
            AppointmentStatus.IN_PROGRESS.value,
        ]
        for s in non_terminal:
            assert (
                AppointmentStatus.CANCELLED.value in VALID_APPOINTMENT_TRANSITIONS[s]
            ), f"CANCELLED should be reachable from {s}"


# ---------------------------------------------------------------------------
# Task 25.3: Skip Scenarios (Req 18.5)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSkipScenarios:
    """Test skip scenarios where steps in the progression are skipped.

    Validates: Requirement 18.5
    """

    def test_complete_directly_skipping_on_my_way_and_started(self) -> None:
        """Job Complete clicked directly → both go to COMPLETED.

        Skips On My Way and Job Started entirely.

        Validates: Requirement 18.5
        """
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.CONFIRMED.value,
            job_id=job.id,
        )

        # Skip directly to complete
        _simulate_complete(job, appt)

        assert job.status == JobStatus.COMPLETED.value
        assert appt.status == AppointmentStatus.COMPLETED.value

    def test_started_directly_skipping_on_my_way(self) -> None:
        """Job Started clicked (skipped On My Way) → both go to IN_PROGRESS.

        Validates: Requirement 18.5
        """
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.CONFIRMED.value,
            job_id=job.id,
        )

        # Skip On My Way, go directly to Started
        _simulate_started(job, appt)

        assert job.status == JobStatus.IN_PROGRESS.value
        assert appt.status == AppointmentStatus.IN_PROGRESS.value

    def test_complete_from_scheduled_appointment_skipping_all(self) -> None:
        """Complete from SCHEDULED appointment (skipped confirm, On My Way, Started).

        Validates: Requirement 18.5
        """
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.SCHEDULED.value,
            job_id=job.id,
        )

        _simulate_complete(job, appt)

        assert job.status == JobStatus.COMPLETED.value
        assert appt.status == AppointmentStatus.COMPLETED.value

    def test_complete_from_draft_appointment(self) -> None:
        """Complete from DRAFT appointment (never sent confirmation).

        Validates: Requirement 18.5
        """
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.DRAFT.value,
            job_id=job.id,
        )

        _simulate_complete(job, appt)

        assert job.status == JobStatus.COMPLETED.value
        assert appt.status == AppointmentStatus.COMPLETED.value

    def test_started_from_confirmed_skipping_on_my_way(self) -> None:
        """Started from CONFIRMED (skipped On My Way) → IN_PROGRESS.

        The _simulate_started logic allows CONFIRMED → IN_PROGRESS.

        Validates: Requirement 18.5
        """
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.CONFIRMED.value,
            job_id=job.id,
        )

        _simulate_started(job, appt)

        assert job.status == JobStatus.IN_PROGRESS.value
        assert appt.status == AppointmentStatus.IN_PROGRESS.value

    def test_end_to_end_skip_confirm_and_on_my_way_flow(self) -> None:
        """End-to-end: customer never replies Y, tech skips On My Way, clicks Started.

        Starting state is SCHEDULED (Send Confirmation fired but no Y/R/C reply).
        Clicking Job Started must promote both the job and the appointment to
        IN_PROGRESS, then Job Complete promotes both to COMPLETED.

        **Validates: CR-2 / 2026-04-14 E2E-6 fix.** Before CR-2, the appointment
        remained SCHEDULED while the job advanced, violating the diagram promise
        that steps can be skipped.
        """
        job = _make_job(job_status=JobStatus.SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.SCHEDULED.value,
            job_id=job.id,
        )

        # SCHEDULED → IN_PROGRESS is allowed per the transitions table
        assert (
            AppointmentStatus.IN_PROGRESS.value
            in VALID_APPOINTMENT_TRANSITIONS[AppointmentStatus.SCHEDULED.value]
        )

        _simulate_started(job, appt)

        assert job.status == JobStatus.IN_PROGRESS.value
        assert appt.status == AppointmentStatus.IN_PROGRESS.value

        _simulate_complete(job, appt)

        assert job.status == JobStatus.COMPLETED.value
        assert appt.status == AppointmentStatus.COMPLETED.value
