"""
Integration tests for appointment management.

This module contains integration tests that verify the appointment system
works correctly with the existing job and staff systems from Phase 1/2.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    StaffNotFoundError,
)
from grins_platform.models.enums import (
    AppointmentStatus,
    JobStatus,
    StaffRole,
)
from grins_platform.repositories.appointment_repository import AppointmentRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.schemas.appointment import AppointmentCreate, AppointmentUpdate
from grins_platform.services.appointment_service import AppointmentService

# =============================================================================
# Test Fixtures
# =============================================================================


def create_mock_job(
    job_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    status: str = JobStatus.APPROVED.value,
) -> MagicMock:
    """Create a mock job object."""
    job = MagicMock()
    job.id = job_id or uuid.uuid4()
    job.customer_id = customer_id or uuid.uuid4()
    job.status = status
    job.job_type = "spring_startup"
    job.is_deleted = False
    return job


def create_mock_staff(
    staff_id: uuid.UUID | None = None,
    name: str = "John Tech",
    role: str = StaffRole.TECH.value,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock staff object."""
    staff = MagicMock()
    staff.id = staff_id or uuid.uuid4()
    staff.name = name
    staff.role = role
    staff.is_active = is_active
    return staff


def create_mock_appointment(
    appointment_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    staff_id: uuid.UUID | None = None,
    scheduled_date: date | None = None,
    time_window_start: time | None = None,
    time_window_end: time | None = None,
    status: str = AppointmentStatus.SCHEDULED.value,
) -> MagicMock:
    """Create a mock appointment object."""
    apt = MagicMock()
    apt.id = appointment_id or uuid.uuid4()
    apt.job_id = job_id or uuid.uuid4()
    apt.staff_id = staff_id or uuid.uuid4()
    apt.scheduled_date = scheduled_date or date.today()
    apt.time_window_start = time_window_start or time(9, 0)
    apt.time_window_end = time_window_end or time(11, 0)
    apt.status = status
    apt.notes = None
    apt.route_order = None
    apt.estimated_arrival = None
    apt.arrived_at = None
    apt.completed_at = None
    apt.created_at = datetime.now()
    apt.updated_at = datetime.now()

    # Configure can_transition_to method
    def can_transition_to(new_status: str) -> bool:
        valid_transitions = {
            AppointmentStatus.SCHEDULED.value: [
                AppointmentStatus.CONFIRMED.value,
                AppointmentStatus.CANCELLED.value,
            ],
            AppointmentStatus.CONFIRMED.value: [
                AppointmentStatus.IN_PROGRESS.value,
                AppointmentStatus.CANCELLED.value,
            ],
            AppointmentStatus.IN_PROGRESS.value: [
                AppointmentStatus.COMPLETED.value,
                AppointmentStatus.CANCELLED.value,
            ],
            AppointmentStatus.COMPLETED.value: [],
            AppointmentStatus.CANCELLED.value: [],
        }
        return new_status in valid_transitions.get(apt.status, [])

    apt.can_transition_to = can_transition_to
    apt.get_duration_minutes = MagicMock(return_value=120)
    return apt


# =============================================================================
# Appointment-Job Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAppointmentJobIntegration:
    """Integration tests for appointment-job relationships.

    Tests that appointments correctly integrate with the job system.

    Validates: Admin Dashboard Requirement 1.1, 1.3
    """

    @pytest.fixture
    def mock_appointment_repo(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock(spec=JobRepository)

    @pytest.fixture
    def mock_staff_repo(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def appointment_service(
        self,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> AppointmentService:
        """Create AppointmentService with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            staff_repository=mock_staff_repo,
        )

    async def test_appointment_creation_with_existing_job(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test appointment creation with existing job succeeds.

        Validates: Admin Dashboard Requirement 1.1
        """
        job_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        appointment_id = uuid.uuid4()

        mock_job = create_mock_job(job_id=job_id)
        mock_job_repo.get_by_id.return_value = mock_job

        mock_staff = create_mock_staff(staff_id=staff_id)
        mock_staff_repo.get_by_id.return_value = mock_staff

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            job_id=job_id,
            staff_id=staff_id,
        )
        mock_appointment_repo.create.return_value = mock_appointment

        data = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=date.today(),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        result = await appointment_service.create_appointment(data)

        assert result.id == appointment_id
        assert result.job_id == job_id
        mock_job_repo.get_by_id.assert_called_once_with(job_id)


    async def test_appointment_creation_with_nonexistent_job_fails(
        self,
        appointment_service: AppointmentService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test appointment creation with non-existent job fails.

        Validates: Admin Dashboard Requirement 1.1
        """
        job_id = uuid.uuid4()
        staff_id = uuid.uuid4()

        mock_job_repo.get_by_id.return_value = None

        data = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=date.today(),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        with pytest.raises(JobNotFoundError):
            await appointment_service.create_appointment(data)

    async def test_appointment_retrieval_includes_job_reference(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test appointment retrieval includes job reference.

        Validates: Admin Dashboard Requirement 1.3
        """
        job_id = uuid.uuid4()
        appointment_id = uuid.uuid4()

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            job_id=job_id,
        )
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        result = await appointment_service.get_appointment(appointment_id)

        assert result.job_id == job_id

    async def test_multiple_appointments_for_same_job(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test creating multiple appointments for the same job.

        Validates: Admin Dashboard Requirement 1.1
        """
        job_id = uuid.uuid4()
        staff_id_1 = uuid.uuid4()
        staff_id_2 = uuid.uuid4()

        mock_job = create_mock_job(job_id=job_id)
        mock_job_repo.get_by_id.return_value = mock_job

        mock_staff_1 = create_mock_staff(staff_id=staff_id_1)
        mock_staff_2 = create_mock_staff(staff_id=staff_id_2)
        mock_staff_repo.get_by_id.side_effect = [mock_staff_1, mock_staff_2]

        apt_1 = create_mock_appointment(job_id=job_id, staff_id=staff_id_1)
        apt_2 = create_mock_appointment(job_id=job_id, staff_id=staff_id_2)
        mock_appointment_repo.create.side_effect = [apt_1, apt_2]

        # Create first appointment
        data_1 = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id_1,
            scheduled_date=date.today(),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )
        result_1 = await appointment_service.create_appointment(data_1)

        # Create second appointment
        data_2 = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id_2,
            scheduled_date=date.today() + timedelta(days=1),
            time_window_start=time(14, 0),
            time_window_end=time(16, 0),
        )
        result_2 = await appointment_service.create_appointment(data_2)

        assert result_1.job_id == job_id
        assert result_2.job_id == job_id
        assert result_1.staff_id != result_2.staff_id


# =============================================================================
# Appointment-Staff Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAppointmentStaffIntegration:
    """Integration tests for appointment-staff relationships.

    Tests that appointments correctly integrate with the staff system.

    Validates: Admin Dashboard Requirement 1.1, 1.5
    """

    @pytest.fixture
    def mock_appointment_repo(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock(spec=JobRepository)

    @pytest.fixture
    def mock_staff_repo(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def appointment_service(
        self,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> AppointmentService:
        """Create AppointmentService with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            staff_repository=mock_staff_repo,
        )

    async def test_appointment_creation_with_existing_staff(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test appointment creation with existing staff succeeds.

        Validates: Admin Dashboard Requirement 1.1
        """
        job_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        appointment_id = uuid.uuid4()

        mock_job = create_mock_job(job_id=job_id)
        mock_job_repo.get_by_id.return_value = mock_job

        mock_staff = create_mock_staff(staff_id=staff_id)
        mock_staff_repo.get_by_id.return_value = mock_staff

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            job_id=job_id,
            staff_id=staff_id,
        )
        mock_appointment_repo.create.return_value = mock_appointment

        data = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=date.today(),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        result = await appointment_service.create_appointment(data)

        assert result.staff_id == staff_id
        mock_staff_repo.get_by_id.assert_called_once_with(staff_id)

    async def test_appointment_creation_with_nonexistent_staff_fails(
        self,
        appointment_service: AppointmentService,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test appointment creation with non-existent staff fails.

        Validates: Admin Dashboard Requirement 1.1
        """
        job_id = uuid.uuid4()
        staff_id = uuid.uuid4()

        mock_job = create_mock_job(job_id=job_id)
        mock_job_repo.get_by_id.return_value = mock_job

        mock_staff_repo.get_by_id.return_value = None

        data = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=date.today(),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        with pytest.raises(StaffNotFoundError):
            await appointment_service.create_appointment(data)


    async def test_staff_daily_schedule_retrieval(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test retrieving staff daily schedule.

        Validates: Admin Dashboard Requirement 1.5
        """
        staff_id = uuid.uuid4()
        schedule_date = date.today()

        mock_staff = create_mock_staff(staff_id=staff_id)
        mock_staff_repo.get_by_id.return_value = mock_staff

        appointments = [
            create_mock_appointment(
                staff_id=staff_id,
                scheduled_date=schedule_date,
                time_window_start=time(9, 0),
                time_window_end=time(11, 0),
            ),
            create_mock_appointment(
                staff_id=staff_id,
                scheduled_date=schedule_date,
                time_window_start=time(13, 0),
                time_window_end=time(15, 0),
            ),
        ]
        mock_appointment_repo.get_staff_daily_schedule.return_value = appointments

        result, count, total_minutes = (
            await appointment_service.get_staff_daily_schedule(
                staff_id=staff_id,
                schedule_date=schedule_date,
            )
        )

        assert len(result) == 2
        assert count == 2
        assert total_minutes == 240  # 2 appointments * 120 minutes each
        mock_staff_repo.get_by_id.assert_called_once_with(staff_id)

    async def test_staff_daily_schedule_with_nonexistent_staff_fails(
        self,
        appointment_service: AppointmentService,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test staff daily schedule with non-existent staff fails.

        Validates: Admin Dashboard Requirement 1.5
        """
        staff_id = uuid.uuid4()
        mock_staff_repo.get_by_id.return_value = None

        with pytest.raises(StaffNotFoundError):
            await appointment_service.get_staff_daily_schedule(
                staff_id=staff_id,
                schedule_date=date.today(),
            )

    async def test_staff_with_multiple_appointments_same_day(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test staff with multiple appointments on the same day.

        Validates: Admin Dashboard Requirement 1.5
        """
        staff_id = uuid.uuid4()
        schedule_date = date.today()

        mock_staff = create_mock_staff(staff_id=staff_id)
        mock_staff_repo.get_by_id.return_value = mock_staff

        # Create 5 appointments for the same staff on the same day
        appointments = [
            create_mock_appointment(
                staff_id=staff_id,
                scheduled_date=schedule_date,
                time_window_start=time(8 + i * 2, 0),
                time_window_end=time(10 + i * 2, 0),
            )
            for i in range(5)
        ]
        mock_appointment_repo.get_staff_daily_schedule.return_value = appointments

        result, count, total_minutes = (
            await appointment_service.get_staff_daily_schedule(
                staff_id=staff_id,
                schedule_date=schedule_date,
            )
        )

        assert len(result) == 5
        assert count == 5
        assert total_minutes == 600  # 5 appointments * 120 minutes each


# =============================================================================
# Daily and Weekly Schedule Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestScheduleQueryIntegration:
    """Integration tests for schedule query operations.

    Tests daily and weekly schedule queries with existing data.

    Validates: Admin Dashboard Requirement 1.5
    """

    @pytest.fixture
    def mock_appointment_repo(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock(spec=JobRepository)

    @pytest.fixture
    def mock_staff_repo(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def appointment_service(
        self,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> AppointmentService:
        """Create AppointmentService with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            staff_repository=mock_staff_repo,
        )

    async def test_daily_schedule_retrieval(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test retrieving daily schedule for all staff.

        Validates: Admin Dashboard Requirement 1.5
        """
        schedule_date = date.today()

        appointments = [
            create_mock_appointment(
                scheduled_date=schedule_date,
                time_window_start=time(9, 0),
                time_window_end=time(11, 0),
            ),
            create_mock_appointment(
                scheduled_date=schedule_date,
                time_window_start=time(11, 0),
                time_window_end=time(13, 0),
            ),
            create_mock_appointment(
                scheduled_date=schedule_date,
                time_window_start=time(14, 0),
                time_window_end=time(16, 0),
            ),
        ]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        result, count = await appointment_service.get_daily_schedule(schedule_date)

        assert len(result) == 3
        assert count == 3
        mock_appointment_repo.get_daily_schedule.assert_called_once_with(
            schedule_date,
            include_relationships=False,
        )

    async def test_daily_schedule_empty_day(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test retrieving daily schedule for a day with no appointments.

        Validates: Admin Dashboard Requirement 1.5
        """
        schedule_date = date.today()
        mock_appointment_repo.get_daily_schedule.return_value = []

        result, count = await appointment_service.get_daily_schedule(schedule_date)

        assert len(result) == 0
        assert count == 0


    async def test_weekly_schedule_retrieval(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test retrieving weekly schedule.

        Validates: Admin Dashboard Requirement 1.5
        """
        start_date = date.today()

        # Create schedule dict with appointments spread across the week
        schedule: dict[date, list[MagicMock]] = {}
        total_appointments = 0
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            # Add 2 appointments per day
            schedule[current_date] = [
                create_mock_appointment(
                    scheduled_date=current_date,
                    time_window_start=time(9, 0),
                    time_window_end=time(11, 0),
                ),
                create_mock_appointment(
                    scheduled_date=current_date,
                    time_window_start=time(14, 0),
                    time_window_end=time(16, 0),
                ),
            ]
            total_appointments += 2

        mock_appointment_repo.get_weekly_schedule.return_value = schedule

        result, count = await appointment_service.get_weekly_schedule(start_date)

        assert len(result) == 7  # 7 days
        assert count == 14  # 2 appointments per day * 7 days
        mock_appointment_repo.get_weekly_schedule.assert_called_once_with(
            start_date,
            include_relationships=False,
        )

    async def test_weekly_schedule_partial_week(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test weekly schedule with appointments only on some days.

        Validates: Admin Dashboard Requirement 1.5
        """
        start_date = date.today()

        # Create schedule with appointments only on Monday, Wednesday, Friday
        schedule: dict[date, list[MagicMock]] = {}
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            if i in [0, 2, 4]:  # Mon, Wed, Fri
                schedule[current_date] = [
                    create_mock_appointment(scheduled_date=current_date),
                ]
            else:
                schedule[current_date] = []

        mock_appointment_repo.get_weekly_schedule.return_value = schedule

        result, count = await appointment_service.get_weekly_schedule(start_date)

        assert len(result) == 7  # Still 7 days
        assert count == 3  # Only 3 days have appointments

    async def test_daily_schedule_with_relationships(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test daily schedule with related entities loaded.

        Validates: Admin Dashboard Requirement 1.5
        """
        schedule_date = date.today()

        appointments = [
            create_mock_appointment(scheduled_date=schedule_date),
        ]
        mock_appointment_repo.get_daily_schedule.return_value = appointments

        result, _count = await appointment_service.get_daily_schedule(
            schedule_date,
            include_relationships=True,
        )

        assert len(result) == 1
        mock_appointment_repo.get_daily_schedule.assert_called_once_with(
            schedule_date,
            include_relationships=True,
        )


# =============================================================================
# Status Workflow Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAppointmentStatusWorkflowIntegration:
    """Integration tests for appointment status workflow.

    Tests the complete appointment lifecycle and status transitions.

    Validates: Admin Dashboard Requirement 1.2
    """

    @pytest.fixture
    def mock_appointment_repo(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock(spec=JobRepository)

    @pytest.fixture
    def mock_staff_repo(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def appointment_service(
        self,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> AppointmentService:
        """Create AppointmentService with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            staff_repository=mock_staff_repo,
        )

    async def test_complete_appointment_lifecycle(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test complete appointment lifecycle from scheduled to completed.

        Validates: Admin Dashboard Requirement 1.2
        """
        appointment_id = uuid.uuid4()

        # Start with SCHEDULED status
        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        # Confirm appointment
        confirmed_apt = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.CONFIRMED.value,
        )
        mock_appointment_repo.update_status.return_value = confirmed_apt

        result = await appointment_service.confirm_appointment(appointment_id)
        assert result.status == AppointmentStatus.CONFIRMED.value

        # Update mock for next transition
        mock_appointment.status = AppointmentStatus.CONFIRMED.value
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        # Mark arrived (in progress)
        in_progress_apt = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )
        mock_appointment_repo.update_status.return_value = in_progress_apt

        result = await appointment_service.mark_arrived(appointment_id)
        assert result.status == AppointmentStatus.IN_PROGRESS.value

        # Update mock for next transition
        mock_appointment.status = AppointmentStatus.IN_PROGRESS.value
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        # Mark completed
        completed_apt = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.COMPLETED.value,
        )
        mock_appointment_repo.update_status.return_value = completed_apt

        result = await appointment_service.mark_completed(appointment_id)
        assert result.status == AppointmentStatus.COMPLETED.value


    async def test_appointment_cancellation_from_scheduled(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test appointment cancellation from scheduled status.

        Validates: Admin Dashboard Requirement 1.2
        """
        appointment_id = uuid.uuid4()

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        cancelled_apt = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.CANCELLED.value,
        )
        mock_appointment_repo.update_status.return_value = cancelled_apt

        result = await appointment_service.cancel_appointment(appointment_id)

        assert result.status == AppointmentStatus.CANCELLED.value

    async def test_appointment_cancellation_from_confirmed(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test appointment cancellation from confirmed status.

        Validates: Admin Dashboard Requirement 1.2
        """
        appointment_id = uuid.uuid4()

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.CONFIRMED.value,
        )
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        cancelled_apt = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.CANCELLED.value,
        )
        mock_appointment_repo.update_status.return_value = cancelled_apt

        result = await appointment_service.cancel_appointment(appointment_id)

        assert result.status == AppointmentStatus.CANCELLED.value

    async def test_invalid_transition_from_completed(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test that completed appointments cannot be cancelled.

        Validates: Admin Dashboard Requirement 1.2
        """
        appointment_id = uuid.uuid4()

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.COMPLETED.value,
        )
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        with pytest.raises(InvalidStatusTransitionError):
            await appointment_service.cancel_appointment(appointment_id)

    async def test_invalid_transition_from_cancelled(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test that cancelled appointments cannot be confirmed.

        Validates: Admin Dashboard Requirement 1.2
        """
        appointment_id = uuid.uuid4()

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.CANCELLED.value,
        )
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        with pytest.raises(InvalidStatusTransitionError):
            await appointment_service.confirm_appointment(appointment_id)


# =============================================================================
# Cross-Component Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossComponentAppointmentIntegration:
    """Integration tests for cross-component interactions.

    Tests that appointments work correctly with existing Phase 1/2 components.

    Validates: All Admin Dashboard integration requirements
    """

    @pytest.fixture
    def mock_appointment_repo(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock(spec=JobRepository)

    @pytest.fixture
    def mock_staff_repo(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def appointment_service(
        self,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> AppointmentService:
        """Create AppointmentService with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repo,
            job_repository=mock_job_repo,
            staff_repository=mock_staff_repo,
        )

    async def test_create_appointment_with_all_references(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test creating appointment with job and staff references.

        Validates: Admin Dashboard Requirement 1.1
        """
        job_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        appointment_id = uuid.uuid4()

        mock_job = create_mock_job(job_id=job_id)
        mock_job_repo.get_by_id.return_value = mock_job

        mock_staff = create_mock_staff(staff_id=staff_id)
        mock_staff_repo.get_by_id.return_value = mock_staff

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            job_id=job_id,
            staff_id=staff_id,
        )
        mock_appointment_repo.create.return_value = mock_appointment

        data = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=date.today(),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
            notes="Test appointment",
        )

        result = await appointment_service.create_appointment(data)

        assert result.job_id == job_id
        assert result.staff_id == staff_id
        mock_job_repo.get_by_id.assert_called_once_with(job_id)
        mock_staff_repo.get_by_id.assert_called_once_with(staff_id)

    async def test_list_appointments_with_filters(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test listing appointments with various filters.

        Validates: Admin Dashboard Requirement 1.4
        """
        staff_id = uuid.uuid4()
        job_id = uuid.uuid4()

        appointments = [
            create_mock_appointment(staff_id=staff_id, job_id=job_id),
            create_mock_appointment(staff_id=staff_id, job_id=job_id),
        ]
        mock_appointment_repo.list_with_filters.return_value = (appointments, 2)

        result, total = await appointment_service.list_appointments(
            page=1,
            page_size=20,
            status=AppointmentStatus.SCHEDULED,
            staff_id=staff_id,
            job_id=job_id,
            date_from=date.today(),
            date_to=date.today() + timedelta(days=7),
        )

        assert len(result) == 2
        assert total == 2
        mock_appointment_repo.list_with_filters.assert_called_once()


    async def test_update_appointment_with_new_staff(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test updating appointment with new staff assignment.

        Validates: Admin Dashboard Requirement 1.2
        """
        appointment_id = uuid.uuid4()
        new_staff_id = uuid.uuid4()

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        updated_apt = create_mock_appointment(
            appointment_id=appointment_id,
            staff_id=new_staff_id,
        )
        mock_appointment_repo.update.return_value = updated_apt

        data = AppointmentUpdate(staff_id=new_staff_id)
        result = await appointment_service.update_appointment(appointment_id, data)

        assert result.staff_id == new_staff_id

    async def test_update_appointment_reschedule(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test rescheduling an appointment to a new date/time.

        Validates: Admin Dashboard Requirement 1.2
        """
        appointment_id = uuid.uuid4()
        new_date = date.today() + timedelta(days=3)
        new_start = time(14, 0)
        new_end = time(16, 0)

        mock_appointment = create_mock_appointment(
            appointment_id=appointment_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        mock_appointment_repo.get_by_id.return_value = mock_appointment

        updated_apt = create_mock_appointment(
            appointment_id=appointment_id,
            scheduled_date=new_date,
            time_window_start=new_start,
            time_window_end=new_end,
        )
        mock_appointment_repo.update.return_value = updated_apt

        data = AppointmentUpdate(
            scheduled_date=new_date,
            time_window_start=new_start,
            time_window_end=new_end,
        )
        result = await appointment_service.update_appointment(appointment_id, data)

        assert result.scheduled_date == new_date
        assert result.time_window_start == new_start
        assert result.time_window_end == new_end

    async def test_appointment_not_found_error(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test error handling when appointment not found.

        Validates: Admin Dashboard Requirement 1.3
        """
        appointment_id = uuid.uuid4()
        mock_appointment_repo.get_by_id.return_value = None

        with pytest.raises(AppointmentNotFoundError):
            await appointment_service.get_appointment(appointment_id)

    async def test_update_nonexistent_appointment_fails(
        self,
        appointment_service: AppointmentService,
        mock_appointment_repo: AsyncMock,
    ) -> None:
        """Test updating non-existent appointment fails.

        Validates: Admin Dashboard Requirement 1.2
        """
        appointment_id = uuid.uuid4()
        mock_appointment_repo.get_by_id.return_value = None

        data = AppointmentUpdate(notes="Updated notes")

        with pytest.raises(AppointmentNotFoundError):
            await appointment_service.update_appointment(appointment_id, data)
