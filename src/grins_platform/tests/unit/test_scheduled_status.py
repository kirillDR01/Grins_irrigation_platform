"""
Unit tests for the Scheduled job status (Req 5).

Tests:
- Create appointment → job transitions from TO_BE_SCHEDULED to SCHEDULED
- Cancel only appointment → job reverts to TO_BE_SCHEDULED
- Cancel one of two appointments → job stays SCHEDULED
- SCHEDULED job can transition to IN_PROGRESS and CANCELLED

Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import JobStatus
from grins_platform.models.job import VALID_STATUS_TRANSITIONS

# =============================================================================
# Task 8.1: VALID_STATUS_TRANSITIONS tests
# =============================================================================


class TestScheduledStatusTransitions:
    """Tests for SCHEDULED status in VALID_STATUS_TRANSITIONS.

    Validates: Requirement 5.2
    """

    @pytest.mark.unit
    def test_to_be_scheduled_can_reach_scheduled(self) -> None:
        """TO_BE_SCHEDULED → SCHEDULED is a valid transition."""
        transitions = VALID_STATUS_TRANSITIONS[JobStatus.TO_BE_SCHEDULED.value]
        assert JobStatus.SCHEDULED.value in transitions

    @pytest.mark.unit
    def test_to_be_scheduled_can_reach_in_progress(self) -> None:
        """TO_BE_SCHEDULED → IN_PROGRESS remains valid."""
        transitions = VALID_STATUS_TRANSITIONS[JobStatus.TO_BE_SCHEDULED.value]
        assert JobStatus.IN_PROGRESS.value in transitions

    @pytest.mark.unit
    def test_to_be_scheduled_can_reach_cancelled(self) -> None:
        """TO_BE_SCHEDULED → CANCELLED remains valid."""
        transitions = VALID_STATUS_TRANSITIONS[JobStatus.TO_BE_SCHEDULED.value]
        assert JobStatus.CANCELLED.value in transitions

    @pytest.mark.unit
    def test_scheduled_can_reach_in_progress(self) -> None:
        """SCHEDULED → IN_PROGRESS is valid (Job Started)."""
        transitions = VALID_STATUS_TRANSITIONS[JobStatus.SCHEDULED.value]
        assert JobStatus.IN_PROGRESS.value in transitions

    @pytest.mark.unit
    def test_scheduled_can_revert_to_be_scheduled(self) -> None:
        """SCHEDULED → TO_BE_SCHEDULED is valid (last appointment cancelled)."""
        transitions = VALID_STATUS_TRANSITIONS[JobStatus.SCHEDULED.value]
        assert JobStatus.TO_BE_SCHEDULED.value in transitions

    @pytest.mark.unit
    def test_scheduled_can_reach_cancelled(self) -> None:
        """SCHEDULED → CANCELLED is valid."""
        transitions = VALID_STATUS_TRANSITIONS[JobStatus.SCHEDULED.value]
        assert JobStatus.CANCELLED.value in transitions

    @pytest.mark.unit
    def test_in_progress_cannot_reach_to_be_scheduled(self) -> None:
        """IN_PROGRESS → TO_BE_SCHEDULED is no longer valid."""
        transitions = VALID_STATUS_TRANSITIONS[JobStatus.IN_PROGRESS.value]
        assert JobStatus.TO_BE_SCHEDULED.value not in transitions

    @pytest.mark.unit
    def test_in_progress_can_reach_completed_and_cancelled(self) -> None:
        """IN_PROGRESS → COMPLETED and CANCELLED remain valid."""
        transitions = VALID_STATUS_TRANSITIONS[JobStatus.IN_PROGRESS.value]
        assert JobStatus.COMPLETED.value in transitions
        assert JobStatus.CANCELLED.value in transitions


# =============================================================================
# Task 8.2: Auto-transition job to SCHEDULED on appointment creation
# =============================================================================


class TestAutoTransitionToScheduled:
    """Tests for auto-transitioning job to SCHEDULED on appointment creation.

    Validates: Requirement 5.3
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_appointment_transitions_job_to_scheduled(self) -> None:
        """Creating an appointment for a TO_BE_SCHEDULED job transitions it to SCHEDULED."""
        from grins_platform.services.appointment_service import AppointmentService

        job_id = uuid4()
        staff_id = uuid4()

        # Mock job in TO_BE_SCHEDULED status
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.TO_BE_SCHEDULED.value

        # Mock staff
        mock_staff = MagicMock()
        mock_staff.id = staff_id

        # Mock appointment
        mock_appointment = MagicMock()
        mock_appointment.id = uuid4()
        mock_appointment.job_id = job_id

        # Mock repositories
        mock_appt_repo = AsyncMock()
        mock_appt_repo.create.return_value = mock_appointment
        mock_appt_repo.session = AsyncMock()

        mock_job_repo = AsyncMock()
        mock_job_repo.get_by_id.return_value = mock_job

        mock_staff_repo = AsyncMock()
        mock_staff_repo.get_by_id.return_value = mock_staff

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=mock_job_repo,
            staff_repository=mock_staff_repo,
        )

        # Create appointment data
        data = MagicMock()
        data.job_id = job_id
        data.staff_id = staff_id
        data.scheduled_date = date(2025, 4, 15)
        data.time_window_start = time(9, 0)
        data.time_window_end = time(11, 0)
        data.notes = None

        await service.create_appointment(data)

        # Verify job was transitioned to SCHEDULED
        assert mock_job.status == JobStatus.SCHEDULED.value
        mock_appt_repo.session.flush.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_appointment_does_not_change_non_tbs_job(self) -> None:
        """Creating an appointment for an IN_PROGRESS job does not change its status."""
        from grins_platform.services.appointment_service import AppointmentService

        job_id = uuid4()
        staff_id = uuid4()

        # Mock job already IN_PROGRESS
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.IN_PROGRESS.value

        mock_staff = MagicMock()
        mock_staff.id = staff_id

        mock_appointment = MagicMock()
        mock_appointment.id = uuid4()
        mock_appointment.job_id = job_id

        mock_appt_repo = AsyncMock()
        mock_appt_repo.create.return_value = mock_appointment
        mock_appt_repo.session = AsyncMock()

        mock_job_repo = AsyncMock()
        mock_job_repo.get_by_id.return_value = mock_job

        mock_staff_repo = AsyncMock()
        mock_staff_repo.get_by_id.return_value = mock_staff

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=mock_job_repo,
            staff_repository=mock_staff_repo,
        )

        data = MagicMock()
        data.job_id = job_id
        data.staff_id = staff_id
        data.scheduled_date = date(2025, 4, 15)
        data.time_window_start = time(9, 0)
        data.time_window_end = time(11, 0)
        data.notes = None

        await service.create_appointment(data)

        # Job status should remain IN_PROGRESS
        assert mock_job.status == JobStatus.IN_PROGRESS.value


# =============================================================================
# Task 8.3: Revert job to TO_BE_SCHEDULED on last appointment cancellation
# =============================================================================


class TestRevertToBeScheduledOnCancel:
    """Tests for reverting job to TO_BE_SCHEDULED when last appointment is cancelled.

    Validates: Requirements 5.4, 5.5
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_only_appointment_reverts_job_to_tbs(self) -> None:
        """Cancelling the only appointment reverts SCHEDULED job to TO_BE_SCHEDULED."""
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        job_id = uuid4()
        appt_id = uuid4()

        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.job_id = job_id
        mock_appointment.en_route_at = None
        mock_appointment.arrived_at = None
        mock_appointment.completed_at = None

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.SCHEDULED.value
        mock_job.on_my_way_at = None
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.payment_collected_on_site = False

        mock_session = AsyncMock()
        # count_active_appointments returns 0 (no other active appointments)
        mock_session.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=0)
        )

        await clear_on_site_data(mock_session, mock_appointment, job=mock_job)

        # Job should be reverted to TO_BE_SCHEDULED
        assert mock_job.status == JobStatus.TO_BE_SCHEDULED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_one_of_two_appointments_keeps_scheduled(self) -> None:
        """Cancelling one of two appointments keeps job as SCHEDULED."""
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        job_id = uuid4()
        appt_id = uuid4()

        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.job_id = job_id
        mock_appointment.en_route_at = None
        mock_appointment.arrived_at = None
        mock_appointment.completed_at = None

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.SCHEDULED.value
        mock_job.on_my_way_at = None
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.payment_collected_on_site = False

        mock_session = AsyncMock()
        # count_active_appointments returns 1 (one other active appointment)
        mock_session.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=1)
        )

        await clear_on_site_data(mock_session, mock_appointment, job=mock_job)

        # Job should remain SCHEDULED
        assert mock_job.status == JobStatus.SCHEDULED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_appointment_in_progress_job_reverts_to_tbs(self) -> None:
        """Cancelling the last active appointment on an IN_PROGRESS job
        reverts the job to TO_BE_SCHEDULED. Previously IN_PROGRESS was
        stranded without a visible path forward (bughunt L-12).
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        job_id = uuid4()
        appt_id = uuid4()

        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.job_id = job_id
        mock_appointment.en_route_at = None
        mock_appointment.arrived_at = None
        mock_appointment.completed_at = None

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.IN_PROGRESS.value
        mock_job.on_my_way_at = None
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.payment_collected_on_site = False

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=0)
        )

        await clear_on_site_data(mock_session, mock_appointment, job=mock_job)

        # Job is reverted to TO_BE_SCHEDULED under the L-12 fix
        assert mock_job.status == JobStatus.TO_BE_SCHEDULED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_appointment_on_tbs_job_unchanged(self) -> None:
        """Cancelling the last active appointment on a job that is
        already TO_BE_SCHEDULED leaves the job status alone — the
        revert target is the same.
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        job_id = uuid4()
        appt_id = uuid4()

        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.job_id = job_id
        mock_appointment.en_route_at = None
        mock_appointment.arrived_at = None
        mock_appointment.completed_at = None

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.TO_BE_SCHEDULED.value
        mock_job.on_my_way_at = None
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.payment_collected_on_site = False

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=0)
        )

        await clear_on_site_data(mock_session, mock_appointment, job=mock_job)

        # Job stays TO_BE_SCHEDULED (no applicable revert)
        assert mock_job.status == JobStatus.TO_BE_SCHEDULED.value
