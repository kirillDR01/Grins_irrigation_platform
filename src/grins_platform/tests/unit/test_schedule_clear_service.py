"""Unit tests for ScheduleClearService.

Requirements: 3.1-3.7, 5.1-5.6, 6.1-6.5
Property 3: Clear Schedule Audit Completeness
Property 4: Job Status Reset Correctness
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import ScheduleClearAuditNotFoundError
from grins_platform.models.enums import JobStatus
from grins_platform.schemas.schedule_clear import (
    ScheduleClearAuditDetailResponse,
    ScheduleClearAuditResponse,
    ScheduleClearResponse,
)
from grins_platform.services.schedule_clear_service import ScheduleClearService


@pytest.mark.unit
class TestScheduleClearServiceClearSchedule:
    """Tests for ScheduleClearService.clear_schedule method."""

    @pytest.fixture
    def mock_appointment_repo(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_repo(self) -> AsyncMock:
        """Create mock audit repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> ScheduleClearService:
        """Create service with mock repositories."""
        return ScheduleClearService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            audit_repository=mock_audit_repo,
        )

    def _create_mock_appointment(
        self,
        job_id: str | None = None,
        staff_id: str | None = None,
    ) -> MagicMock:
        """Create a mock appointment object."""
        appointment = MagicMock()
        appointment.id = uuid4()
        appointment.job_id = uuid4() if job_id is None else job_id
        appointment.staff_id = uuid4() if staff_id is None else staff_id
        appointment.scheduled_date = date(2025, 1, 28)
        appointment.time_window_start = "09:00"
        appointment.time_window_end = "11:00"
        appointment.status = "scheduled"
        appointment.notes = "Test appointment"
        appointment.route_order = 1
        appointment.estimated_arrival = None
        return appointment

    def _create_mock_job(
        self,
        job_id: str,
        status: str = JobStatus.SCHEDULED.value,
    ) -> MagicMock:
        """Create a mock job object."""
        job = MagicMock()
        job.id = job_id
        job.status = status
        return job

    @pytest.mark.asyncio
    async def test_clear_schedule_with_appointments(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test clearing schedule with appointments present."""
        schedule_date = date(2025, 1, 28)
        cleared_by = uuid4()

        # Create mock appointments
        appointments = [
            self._create_mock_appointment(),
            self._create_mock_appointment(),
        ]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        # Create mock jobs (scheduled status)
        for appt in appointments:
            mock_job = self._create_mock_job(appt.job_id, JobStatus.SCHEDULED.value)
            mock_job_repo.get_by_id.return_value = mock_job

        # Create mock audit record
        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        # Execute
        result = await service.clear_schedule(
            schedule_date=schedule_date,
            cleared_by=cleared_by,
            notes="Test clear",
        )

        # Verify
        assert isinstance(result, ScheduleClearResponse)
        assert result.audit_id == mock_audit.id
        assert result.schedule_date == schedule_date
        assert result.appointments_deleted == 2
        mock_audit_repo.create.assert_called_once()
        assert mock_appointment_repo.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_schedule_with_no_appointments(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test clearing schedule with no appointments."""
        schedule_date = date(2025, 1, 28)

        # No appointments
        mock_appointment_repo.get_daily_schedule.return_value = []

        # Create mock audit record
        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        # Execute
        result = await service.clear_schedule(schedule_date=schedule_date)

        # Verify
        assert result.appointments_deleted == 0
        assert result.jobs_reset == 0
        mock_audit_repo.create.assert_called_once()
        mock_appointment_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_schedule_creates_audit_log(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test that clear_schedule creates audit log before deletion."""
        schedule_date = date(2025, 1, 28)
        cleared_by = uuid4()
        notes = "Clearing for reschedule"

        appointments = [self._create_mock_appointment()]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        mock_job = self._create_mock_job(appointments[0].job_id)
        mock_job_repo.get_by_id.return_value = mock_job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(
            schedule_date=schedule_date,
            cleared_by=cleared_by,
            notes=notes,
        )

        # Verify audit was created with correct data
        mock_audit_repo.create.assert_called_once()
        call_kwargs = mock_audit_repo.create.call_args.kwargs
        assert call_kwargs["schedule_date"] == schedule_date
        assert call_kwargs["cleared_by"] == cleared_by
        assert call_kwargs["notes"] == notes
        assert call_kwargs["appointment_count"] == 1
        assert len(call_kwargs["appointments_data"]) == 1

    @pytest.mark.asyncio
    async def test_clear_schedule_resets_scheduled_jobs(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test that only scheduled jobs are reset to approved."""
        schedule_date = date(2025, 1, 28)

        # Create appointments with different job statuses
        appt1 = self._create_mock_appointment()
        appt2 = self._create_mock_appointment()
        appointments = [appt1, appt2]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        # First job is scheduled, second is in_progress
        job1 = self._create_mock_job(appt1.job_id, JobStatus.SCHEDULED.value)
        job2 = self._create_mock_job(appt2.job_id, JobStatus.IN_PROGRESS.value)

        mock_job_repo.get_by_id.side_effect = [job1, job2]

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        result = await service.clear_schedule(schedule_date=schedule_date)

        # Only scheduled job should be reset
        assert result.jobs_reset == 1
        mock_job_repo.update.assert_called_once()
        update_call = mock_job_repo.update.call_args
        assert update_call.kwargs["job_id"] == appt1.job_id
        assert update_call.kwargs["data"]["status"] == JobStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_clear_schedule_does_not_reset_completed_jobs(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test that completed jobs are not reset (Property 4)."""
        schedule_date = date(2025, 1, 28)

        appt = self._create_mock_appointment()
        mock_appointment_repo.get_daily_schedule.return_value = [appt]

        # Job is completed
        job = self._create_mock_job(appt.job_id, JobStatus.COMPLETED.value)
        mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        result = await service.clear_schedule(schedule_date=schedule_date)

        # Completed job should not be reset
        assert result.jobs_reset == 0
        mock_job_repo.update.assert_not_called()


@pytest.mark.unit
class TestScheduleClearServiceGetRecentClears:
    """Tests for ScheduleClearService.get_recent_clears method."""

    @pytest.fixture
    def mock_audit_repo(self) -> AsyncMock:
        """Create mock audit repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_audit_repo: AsyncMock) -> ScheduleClearService:
        """Create service with mock repositories."""
        return ScheduleClearService(
            appointment_repository=AsyncMock(),
            job_repository=AsyncMock(),
            audit_repository=mock_audit_repo,
        )

    def _create_mock_audit(self) -> MagicMock:
        """Create a mock audit record."""
        audit = MagicMock()
        audit.id = uuid4()
        audit.schedule_date = date(2025, 1, 28)
        audit.appointment_count = 5
        audit.cleared_at = datetime.now(timezone.utc)
        audit.cleared_by = uuid4()
        audit.notes = "Test clear"
        return audit

    @pytest.mark.asyncio
    async def test_get_recent_clears_default_hours(
        self,
        service: ScheduleClearService,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test get_recent_clears with default 24 hours."""
        audits = [self._create_mock_audit(), self._create_mock_audit()]
        mock_audit_repo.find_since.return_value = audits

        result = await service.get_recent_clears()

        assert len(result) == 2
        mock_audit_repo.find_since.assert_called_once_with(hours=24)
        assert all(isinstance(r, ScheduleClearAuditResponse) for r in result)

    @pytest.mark.asyncio
    async def test_get_recent_clears_custom_hours(
        self,
        service: ScheduleClearService,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test get_recent_clears with custom hours."""
        mock_audit_repo.find_since.return_value = []

        result = await service.get_recent_clears(hours=48)

        assert len(result) == 0
        mock_audit_repo.find_since.assert_called_once_with(hours=48)

    @pytest.mark.asyncio
    async def test_get_recent_clears_empty_list(
        self,
        service: ScheduleClearService,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test get_recent_clears returns empty list when none found."""
        mock_audit_repo.find_since.return_value = []

        result = await service.get_recent_clears()

        assert result == []


@pytest.mark.unit
class TestScheduleClearServiceGetClearDetails:
    """Tests for ScheduleClearService.get_clear_details method."""

    @pytest.fixture
    def mock_audit_repo(self) -> AsyncMock:
        """Create mock audit repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_audit_repo: AsyncMock) -> ScheduleClearService:
        """Create service with mock repositories."""
        return ScheduleClearService(
            appointment_repository=AsyncMock(),
            job_repository=AsyncMock(),
            audit_repository=mock_audit_repo,
        )

    def _create_mock_audit_detail(self) -> MagicMock:
        """Create a mock audit record with full details."""
        audit = MagicMock()
        audit.id = uuid4()
        audit.schedule_date = date(2025, 1, 28)
        audit.appointment_count = 3
        audit.cleared_at = datetime.now(timezone.utc)
        audit.cleared_by = uuid4()
        audit.notes = "Test clear"
        audit.appointments_data = [
            {"id": str(uuid4()), "job_id": str(uuid4())},
            {"id": str(uuid4()), "job_id": str(uuid4())},
        ]
        audit.jobs_reset = [uuid4(), uuid4()]
        return audit

    @pytest.mark.asyncio
    async def test_get_clear_details_valid_id(
        self,
        service: ScheduleClearService,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test get_clear_details with valid ID."""
        audit = self._create_mock_audit_detail()
        mock_audit_repo.get_by_id.return_value = audit

        result = await service.get_clear_details(audit.id)

        assert isinstance(result, ScheduleClearAuditDetailResponse)
        mock_audit_repo.get_by_id.assert_called_once_with(audit.id)

    @pytest.mark.asyncio
    async def test_get_clear_details_not_found(
        self,
        service: ScheduleClearService,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test get_clear_details raises error when not found."""
        audit_id = uuid4()
        mock_audit_repo.get_by_id.return_value = None

        with pytest.raises(ScheduleClearAuditNotFoundError):
            await service.get_clear_details(audit_id)

    @pytest.mark.asyncio
    async def test_get_clear_details_includes_appointments_data(
        self,
        service: ScheduleClearService,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test get_clear_details includes appointments_data."""
        audit = self._create_mock_audit_detail()
        mock_audit_repo.get_by_id.return_value = audit

        result = await service.get_clear_details(audit.id)

        assert result.appointments_data == audit.appointments_data

    @pytest.mark.asyncio
    async def test_get_clear_details_includes_jobs_reset(
        self,
        service: ScheduleClearService,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Test get_clear_details includes jobs_reset."""
        audit = self._create_mock_audit_detail()
        mock_audit_repo.get_by_id.return_value = audit

        result = await service.get_clear_details(audit.id)

        assert result.jobs_reset == audit.jobs_reset


@pytest.mark.unit
class TestScheduleClearServiceAuditCompleteness:
    """Property 3: Clear Schedule Audit Completeness tests."""

    @pytest.fixture
    def mock_appointment_repo(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_repo(self) -> AsyncMock:
        """Create mock audit repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> ScheduleClearService:
        """Create service with mock repositories."""
        return ScheduleClearService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            audit_repository=mock_audit_repo,
        )

    def _create_mock_appointment(self, job_id: str | None = None) -> MagicMock:
        """Create a mock appointment object."""
        appointment = MagicMock()
        appointment.id = uuid4()
        appointment.job_id = uuid4() if job_id is None else job_id
        appointment.staff_id = uuid4()
        appointment.scheduled_date = date(2025, 1, 28)
        appointment.time_window_start = "09:00"
        appointment.time_window_end = "11:00"
        appointment.status = "scheduled"
        appointment.notes = "Test"
        appointment.route_order = 1
        appointment.estimated_arrival = None
        return appointment

    @pytest.mark.asyncio
    async def test_audit_contains_all_deleted_appointments(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Property 3: Audit contains all deleted appointments."""
        # Create 5 appointments
        appointments = [self._create_mock_appointment() for _ in range(5)]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        # All jobs are scheduled
        for appt in appointments:
            job = MagicMock()
            job.id = appt.job_id
            job.status = JobStatus.SCHEDULED.value
            mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(schedule_date=date(2025, 1, 28))

        # Verify audit contains all 5 appointments
        call_kwargs = mock_audit_repo.create.call_args.kwargs
        assert call_kwargs["appointment_count"] == 5
        assert len(call_kwargs["appointments_data"]) == 5

        # Verify each appointment ID is in the audit
        audit_appt_ids = {a["id"] for a in call_kwargs["appointments_data"]}
        original_appt_ids = {str(a.id) for a in appointments}
        assert audit_appt_ids == original_appt_ids

    @pytest.mark.asyncio
    async def test_audit_contains_all_reset_job_ids(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Property 3: Audit contains all reset job IDs."""
        # Create 3 appointments with scheduled jobs
        appointments = [self._create_mock_appointment() for _ in range(3)]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        scheduled_job_ids = []
        for appt in appointments:
            job = MagicMock()
            job.id = appt.job_id
            job.status = JobStatus.SCHEDULED.value
            scheduled_job_ids.append(job.id)
            mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        await service.clear_schedule(schedule_date=date(2025, 1, 28))

        # Verify audit contains all reset job IDs
        call_kwargs = mock_audit_repo.create.call_args.kwargs
        assert len(call_kwargs["jobs_reset"]) == 3


@pytest.mark.unit
class TestScheduleClearServiceJobStatusReset:
    """Property 4: Job Status Reset Correctness tests."""

    @pytest.fixture
    def mock_appointment_repo(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_repo(self) -> AsyncMock:
        """Create mock audit repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> ScheduleClearService:
        """Create service with mock repositories."""
        return ScheduleClearService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            audit_repository=mock_audit_repo,
        )

    def _create_mock_appointment(self) -> MagicMock:
        """Create a mock appointment object."""
        appointment = MagicMock()
        appointment.id = uuid4()
        appointment.job_id = uuid4()
        appointment.staff_id = uuid4()
        appointment.scheduled_date = date(2025, 1, 28)
        appointment.time_window_start = "09:00"
        appointment.time_window_end = "11:00"
        appointment.status = "scheduled"
        appointment.notes = "Test"
        appointment.route_order = 1
        appointment.estimated_arrival = None
        return appointment

    @pytest.mark.asyncio
    async def test_only_scheduled_jobs_are_reset(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Property 4: Only 'scheduled' jobs are reset."""
        # Create appointments with various job statuses
        appt_scheduled = self._create_mock_appointment()
        appt_in_progress = self._create_mock_appointment()
        appt_completed = self._create_mock_appointment()
        appt_approved = self._create_mock_appointment()

        appointments = [appt_scheduled, appt_in_progress, appt_completed, appt_approved]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        # Set up job statuses
        jobs = {
            appt_scheduled.job_id: JobStatus.SCHEDULED.value,
            appt_in_progress.job_id: JobStatus.IN_PROGRESS.value,
            appt_completed.job_id: JobStatus.COMPLETED.value,
            appt_approved.job_id: JobStatus.APPROVED.value,
        }

        def get_job(job_id: str) -> MagicMock:
            job = MagicMock()
            job.id = job_id
            job.status = jobs[job_id]
            return job

        mock_job_repo.get_by_id.side_effect = get_job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        result = await service.clear_schedule(schedule_date=date(2025, 1, 28))

        # Only the scheduled job should be reset
        assert result.jobs_reset == 1
        mock_job_repo.update.assert_called_once()
        update_call = mock_job_repo.update.call_args
        assert update_call.kwargs["job_id"] == appt_scheduled.job_id

    @pytest.mark.asyncio
    async def test_in_progress_jobs_unchanged(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Property 4: 'in_progress' jobs are unchanged."""
        appt = self._create_mock_appointment()
        mock_appointment_repo.get_daily_schedule.return_value = [appt]

        job = MagicMock()
        job.id = appt.job_id
        job.status = JobStatus.IN_PROGRESS.value
        mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        result = await service.clear_schedule(schedule_date=date(2025, 1, 28))

        assert result.jobs_reset == 0
        mock_job_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_completed_jobs_unchanged(
        self,
        service: ScheduleClearService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Property 4: 'completed' jobs are unchanged."""
        appt = self._create_mock_appointment()
        mock_appointment_repo.get_daily_schedule.return_value = [appt]

        job = MagicMock()
        job.id = appt.job_id
        job.status = JobStatus.COMPLETED.value
        mock_job_repo.get_by_id.return_value = job

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.cleared_at = datetime.now(timezone.utc)
        mock_audit_repo.create.return_value = mock_audit

        result = await service.clear_schedule(schedule_date=date(2025, 1, 28))

        assert result.jobs_reset == 0
        mock_job_repo.update.assert_not_called()
