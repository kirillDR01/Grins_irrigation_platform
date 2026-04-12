"""Property-based tests for schedule clear operations.

Property 3: Clear Schedule Audit Completeness
- Audit contains all deleted appointments
- Audit contains all reset job IDs

Property 4: Job Status Reset Correctness
- Only 'in_progress' jobs are reset
- 'completed' jobs unchanged

Validates: Requirements 3.1-3.7, 5.1-5.6
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import JobStatus
from grins_platform.services.schedule_clear_service import ScheduleClearService


def create_mock_appointment(
    job_id: Any | None = None,
    scheduled_date: date | None = None,
) -> MagicMock:
    """Create a mock appointment object."""
    appointment = MagicMock()
    appointment.id = uuid4()
    appointment.job_id = job_id if job_id is not None else uuid4()
    appointment.staff_id = uuid4()
    appointment.scheduled_date = scheduled_date or date(2025, 1, 28)
    appointment.time_window_start = "09:00"
    appointment.time_window_end = "11:00"
    appointment.status = "scheduled"
    appointment.notes = "Test appointment"
    appointment.route_order = 1
    appointment.estimated_arrival = None
    return appointment


def create_mock_job(
    job_id: Any | None = None,
    status: str = JobStatus.IN_PROGRESS.value,
) -> MagicMock:
    """Create a mock job object."""
    job = MagicMock()
    job.id = job_id if job_id is not None else uuid4()
    job.status = status
    return job


def create_service_with_mocks() -> tuple[
    ScheduleClearService,
    AsyncMock,
    AsyncMock,
    AsyncMock,
]:
    """Create service with fresh mock repositories."""
    mock_appointment_repo = AsyncMock()
    mock_job_repo = AsyncMock()
    mock_audit_repo = AsyncMock()

    service = ScheduleClearService(
        appointment_repository=mock_appointment_repo,
        job_repository=mock_job_repo,
        audit_repository=mock_audit_repo,
    )

    return service, mock_appointment_repo, mock_job_repo, mock_audit_repo


@pytest.mark.unit
class TestScheduleClearAuditCompletenessProperty:
    """Property-based tests for schedule clear audit completeness.

    Property 3: Clear Schedule Audit Completeness
    - For any set of appointments, the audit must contain all of them
    - For any set of scheduled jobs, the audit must contain all their IDs

    Validates: Requirements 5.1-5.6
    """

    @given(num_appointments=st.integers(min_value=0, max_value=20))
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.asyncio
    async def test_audit_contains_all_appointments(
        self,
        num_appointments: int,
    ) -> None:
        """Property: Audit contains exactly all deleted appointments.

        For any number of appointments N, after clearing:
        - audit.appointment_count == N
        - audit.appointments_data has exactly N entries
        - Each appointment ID appears exactly once in audit
        """
        service, mock_appointment_repo, mock_job_repo, mock_audit_repo = (
            create_service_with_mocks()
        )

        # Create N appointments
        appointments = [create_mock_appointment() for _ in range(num_appointments)]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        # All jobs are scheduled
        for appt in appointments:
            job = create_mock_job(job_id=appt.job_id)
            mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(schedule_date=date(2025, 1, 28))

        # Verify audit was created with correct data
        call_kwargs = mock_audit_repo.create.call_args.kwargs

        # Property: appointment_count equals number of appointments
        assert call_kwargs["appointment_count"] == num_appointments

        # Property: appointments_data has exactly N entries
        assert len(call_kwargs["appointments_data"]) == num_appointments

        # Property: Each appointment ID appears exactly once
        audit_appt_ids = {a["id"] for a in call_kwargs["appointments_data"]}
        original_appt_ids = {str(a.id) for a in appointments}
        assert audit_appt_ids == original_appt_ids

    @given(num_scheduled_jobs=st.integers(min_value=0, max_value=15))
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.asyncio
    async def test_audit_contains_all_reset_job_ids(
        self,
        num_scheduled_jobs: int,
    ) -> None:
        """Property: Audit contains all job IDs that were reset.

        For any number of scheduled jobs N:
        - audit.jobs_reset has exactly N entries
        - Each scheduled job ID appears in jobs_reset
        """
        service, mock_appointment_repo, mock_job_repo, mock_audit_repo = (
            create_service_with_mocks()
        )

        # Create appointments with scheduled jobs
        appointments = [create_mock_appointment() for _ in range(num_scheduled_jobs)]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        # Track expected job IDs
        expected_job_ids: set[Any] = set()
        for appt in appointments:
            job = create_mock_job(
                job_id=appt.job_id, status=JobStatus.IN_PROGRESS.value
            )
            expected_job_ids.add(job.id)
            mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(schedule_date=date(2025, 1, 28))

        call_kwargs = mock_audit_repo.create.call_args.kwargs

        # Property: jobs_reset has exactly N entries
        assert len(call_kwargs["jobs_reset"]) == num_scheduled_jobs

    @given(
        num_appointments=st.integers(min_value=1, max_value=10),
        notes=st.text(min_size=0, max_size=100),
    )
    @settings(max_examples=20, deadline=10000)
    @pytest.mark.asyncio
    async def test_audit_preserves_notes(
        self,
        num_appointments: int,
        notes: str,
    ) -> None:
        """Property: Audit preserves the notes provided during clear."""
        service, mock_appointment_repo, mock_job_repo, mock_audit_repo = (
            create_service_with_mocks()
        )

        appointments = [create_mock_appointment() for _ in range(num_appointments)]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        for appt in appointments:
            job = create_mock_job(job_id=appt.job_id)
            mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(
            schedule_date=date(2025, 1, 28),
            notes=notes,
        )

        call_kwargs = mock_audit_repo.create.call_args.kwargs
        assert call_kwargs["notes"] == notes


@pytest.mark.unit
class TestJobStatusResetCorrectnessProperty:
    """Property-based tests for job status reset correctness.

    Property 4: Job Status Reset Correctness
    - Only jobs with status 'in_progress' are reset to 'to_be_scheduled'
    - Jobs with status 'completed' are unchanged

    Validates: Requirements 3.3-3.4
    """

    @given(
        num_in_progress=st.integers(min_value=0, max_value=10),
        num_to_be_scheduled=st.integers(min_value=0, max_value=5),
        num_completed=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.asyncio
    async def test_only_in_progress_jobs_are_reset(
        self,
        num_in_progress: int,
        num_to_be_scheduled: int,
        num_completed: int,
    ) -> None:
        """Property: Only 'in_progress' jobs are reset, others unchanged.

        Given appointments with jobs in various statuses:
        - Jobs with status 'in_progress' are reset to 'to_be_scheduled'
        - Jobs with status 'to_be_scheduled' are NOT reset
        - Jobs with status 'completed' are NOT reset
        """
        service, mock_appointment_repo, mock_job_repo, mock_audit_repo = (
            create_service_with_mocks()
        )

        # Create appointments with different job statuses
        appointments: list[MagicMock] = []
        job_statuses: dict[Any, str] = {}

        # In-progress jobs (should be reset)
        for _ in range(num_in_progress):
            appt = create_mock_appointment()
            appointments.append(appt)
            job_statuses[appt.job_id] = JobStatus.IN_PROGRESS.value

        # To-be-scheduled jobs (should NOT be reset)
        for _ in range(num_to_be_scheduled):
            appt = create_mock_appointment()
            appointments.append(appt)
            job_statuses[appt.job_id] = JobStatus.TO_BE_SCHEDULED.value

        # Completed jobs (should NOT be reset)
        for _ in range(num_completed):
            appt = create_mock_appointment()
            appointments.append(appt)
            job_statuses[appt.job_id] = JobStatus.COMPLETED.value

        mock_appointment_repo.get_daily_schedule.return_value = appointments

        # Configure job repo to return correct status for each job
        def get_job_by_id(job_id: Any) -> MagicMock:
            status = job_statuses.get(job_id, JobStatus.IN_PROGRESS.value)
            return create_mock_job(job_id=job_id, status=status)

        mock_job_repo.get_by_id.side_effect = get_job_by_id

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(schedule_date=date(2025, 1, 28))

        # Count how many times update was called (only for in_progress jobs)
        update_calls = mock_job_repo.update.call_args_list

        # Property: Number of updates equals number of in_progress jobs
        assert len(update_calls) == num_in_progress

        # Property: All updates set status to 'to_be_scheduled'
        for call in update_calls:
            assert call.kwargs["data"]["status"] == JobStatus.TO_BE_SCHEDULED.value

    @given(num_appointments=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20, deadline=10000)
    @pytest.mark.asyncio
    async def test_to_be_scheduled_jobs_never_reset(
        self,
        num_appointments: int,
    ) -> None:
        """Property: Jobs with status 'to_be_scheduled' are never reset."""
        service, mock_appointment_repo, mock_job_repo, mock_audit_repo = (
            create_service_with_mocks()
        )

        # All appointments have to_be_scheduled jobs
        appointments = [create_mock_appointment() for _ in range(num_appointments)]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        for appt in appointments:
            job = create_mock_job(
                job_id=appt.job_id,
                status=JobStatus.TO_BE_SCHEDULED.value,
            )
            mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(schedule_date=date(2025, 1, 28))

        # Property: No job updates should occur
        mock_job_repo.update.assert_not_called()

        # Property: jobs_reset should be empty
        call_kwargs = mock_audit_repo.create.call_args.kwargs
        assert len(call_kwargs["jobs_reset"]) == 0

    @given(num_appointments=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20, deadline=10000)
    @pytest.mark.asyncio
    async def test_completed_jobs_never_reset(
        self,
        num_appointments: int,
    ) -> None:
        """Property: Jobs with status 'completed' are never reset."""
        service, mock_appointment_repo, mock_job_repo, mock_audit_repo = (
            create_service_with_mocks()
        )

        # All appointments have completed jobs
        appointments = [create_mock_appointment() for _ in range(num_appointments)]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        for appt in appointments:
            job = create_mock_job(job_id=appt.job_id, status=JobStatus.COMPLETED.value)
            mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(schedule_date=date(2025, 1, 28))

        # Property: No job updates should occur
        mock_job_repo.update.assert_not_called()

        # Property: jobs_reset should be empty
        call_kwargs = mock_audit_repo.create.call_args.kwargs
        assert len(call_kwargs["jobs_reset"]) == 0

    @given(
        status=st.sampled_from(
            [
                JobStatus.TO_BE_SCHEDULED.value,
                JobStatus.COMPLETED.value,
                JobStatus.CANCELLED.value,
            ],
        ),
    )
    @settings(max_examples=20, deadline=10000)
    @pytest.mark.asyncio
    async def test_non_in_progress_statuses_never_reset(
        self,
        status: str,
    ) -> None:
        """Property: Jobs with any non-in_progress status are never reset."""
        service, mock_appointment_repo, mock_job_repo, mock_audit_repo = (
            create_service_with_mocks()
        )

        # Create appointment with non-scheduled job
        appointment = create_mock_appointment()
        mock_appointment_repo.get_daily_schedule.return_value = [appointment]

        job = create_mock_job(job_id=appointment.job_id, status=status)
        mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(schedule_date=date(2025, 1, 28))

        # Property: No job updates should occur for non-in_progress status
        mock_job_repo.update.assert_not_called()

        # Property: jobs_reset should be empty
        call_kwargs = mock_audit_repo.create.call_args.kwargs
        assert len(call_kwargs["jobs_reset"]) == 0
