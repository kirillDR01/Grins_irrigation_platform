"""
Tests for Appointment Service Layer.

This module tests the AppointmentService class for Admin Dashboard Phase 3,
including appointment creation, status transitions, and schedule queries.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    StaffNotFoundError,
)
from grins_platform.models.enums import AppointmentStatus
from grins_platform.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
)
from grins_platform.services.appointment_service import AppointmentService

# =============================================================================
# AppointmentService Unit Tests
# =============================================================================


@pytest.mark.unit
class TestAppointmentServiceCreate:
    """Unit tests for AppointmentService.create_appointment method."""

    @pytest.fixture
    def mock_appointment_repository(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repository(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repository: AsyncMock,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> AppointmentService:
        """Create service with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repository,
            job_repository=mock_job_repository,
            staff_repository=mock_staff_repository,
        )

    @pytest.mark.asyncio
    async def test_create_appointment_success(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> None:
        """Test successful appointment creation."""
        # Arrange
        job_id = uuid4()
        staff_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job_repository.get_by_id.return_value = mock_job

        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_staff_repository.get_by_id.return_value = mock_staff

        mock_appointment = MagicMock()
        mock_appointment.id = uuid4()
        mock_appointment_repository.create.return_value = mock_appointment

        data = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=date.today() + timedelta(days=1),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
            notes="Test appointment",
        )

        # Act
        result = await service.create_appointment(data)

        # Assert
        mock_job_repository.get_by_id.assert_called_once_with(job_id)
        mock_staff_repository.get_by_id.assert_called_once_with(staff_id)
        mock_appointment_repository.create.assert_called_once()
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_create_appointment_job_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test creating appointment with non-existent job raises error."""
        # Arrange
        job_id = uuid4()
        staff_id = uuid4()
        mock_job_repository.get_by_id.return_value = None

        data = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=date.today() + timedelta(days=1),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        # Act & Assert
        with pytest.raises(JobNotFoundError):
            await service.create_appointment(data)

    @pytest.mark.asyncio
    async def test_create_appointment_staff_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> None:
        """Test creating appointment with non-existent staff raises error."""
        # Arrange
        job_id = uuid4()
        staff_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job_repository.get_by_id.return_value = mock_job
        mock_staff_repository.get_by_id.return_value = None

        data = AppointmentCreate(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=date.today() + timedelta(days=1),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        # Act & Assert
        with pytest.raises(StaffNotFoundError):
            await service.create_appointment(data)


@pytest.mark.unit
class TestAppointmentServiceGet:
    """Unit tests for AppointmentService.get_appointment method."""

    @pytest.fixture
    def mock_appointment_repository(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repository(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repository: AsyncMock,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> AppointmentService:
        """Create service with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repository,
            job_repository=mock_job_repository,
            staff_repository=mock_staff_repository,
        )

    @pytest.mark.asyncio
    async def test_get_appointment_found(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test getting an appointment when found."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment_repository.get_by_id.return_value = mock_appointment

        # Act
        result = await service.get_appointment(appointment_id)

        # Assert
        mock_appointment_repository.get_by_id.assert_called_once_with(
            appointment_id,
            include_relationships=False,
        )
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_get_appointment_with_relationships(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test getting an appointment with relationships loaded."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment_repository.get_by_id.return_value = mock_appointment

        # Act
        result = await service.get_appointment(
            appointment_id,
            include_relationships=True,
        )

        # Assert
        mock_appointment_repository.get_by_id.assert_called_once_with(
            appointment_id,
            include_relationships=True,
        )
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_get_appointment_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test getting an appointment when not found raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(AppointmentNotFoundError):
            await service.get_appointment(appointment_id)


@pytest.mark.unit
class TestAppointmentServiceUpdate:
    """Unit tests for AppointmentService.update_appointment method."""

    @pytest.fixture
    def mock_appointment_repository(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repository(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repository: AsyncMock,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> AppointmentService:
        """Create service with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repository,
            job_repository=mock_job_repository,
            staff_repository=mock_staff_repository,
        )

    @pytest.mark.asyncio
    async def test_update_appointment_success(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test successful appointment update."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.SCHEDULED.value
        mock_appointment.can_transition_to.return_value = True
        mock_appointment_repository.get_by_id.return_value = mock_appointment
        mock_appointment_repository.update.return_value = mock_appointment

        data = AppointmentUpdate(notes="Updated notes")

        # Act
        result = await service.update_appointment(appointment_id, data)

        # Assert
        mock_appointment_repository.update.assert_called_once()
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_update_appointment_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test updating appointment when not found raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment_repository.get_by_id.return_value = None

        data = AppointmentUpdate(notes="Updated notes")

        # Act & Assert
        with pytest.raises(AppointmentNotFoundError):
            await service.update_appointment(appointment_id, data)

    @pytest.mark.asyncio
    async def test_update_appointment_with_valid_status_transition(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test updating appointment with valid status transition."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.SCHEDULED.value
        mock_appointment.can_transition_to.return_value = True
        mock_appointment_repository.get_by_id.return_value = mock_appointment
        mock_appointment_repository.update.return_value = mock_appointment

        data = AppointmentUpdate(status=AppointmentStatus.CONFIRMED)

        # Act
        result = await service.update_appointment(appointment_id, data)

        # Assert
        mock_appointment.can_transition_to.assert_called_once()
        mock_appointment_repository.update.assert_called_once()
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_update_appointment_with_invalid_status_transition_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test updating appointment with invalid status transition raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.COMPLETED.value
        mock_appointment.can_transition_to.return_value = False
        mock_appointment_repository.get_by_id.return_value = mock_appointment

        data = AppointmentUpdate(status=AppointmentStatus.SCHEDULED)

        # Act & Assert
        with pytest.raises(InvalidStatusTransitionError):
            await service.update_appointment(appointment_id, data)


@pytest.mark.unit
class TestAppointmentServiceCancel:
    """Unit tests for AppointmentService.cancel_appointment method."""

    @pytest.fixture
    def mock_appointment_repository(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repository(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repository: AsyncMock,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> AppointmentService:
        """Create service with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repository,
            job_repository=mock_job_repository,
            staff_repository=mock_staff_repository,
        )

    @pytest.mark.asyncio
    async def test_cancel_appointment_success(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test successful appointment cancellation."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.SCHEDULED.value
        mock_appointment.can_transition_to.return_value = True
        mock_appointment_repository.get_by_id.return_value = mock_appointment
        mock_appointment_repository.update_status.return_value = mock_appointment

        # Act
        result = await service.cancel_appointment(appointment_id)

        # Assert
        mock_appointment_repository.update_status.assert_called_once_with(
            appointment_id,
            AppointmentStatus.CANCELLED,
        )
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_cancel_appointment_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test cancelling appointment when not found raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(AppointmentNotFoundError):
            await service.cancel_appointment(appointment_id)

    @pytest.mark.asyncio
    async def test_cancel_completed_appointment_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test cancelling completed appointment raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.COMPLETED.value
        mock_appointment.can_transition_to.return_value = False
        mock_appointment_repository.get_by_id.return_value = mock_appointment

        # Act & Assert
        with pytest.raises(InvalidStatusTransitionError):
            await service.cancel_appointment(appointment_id)


@pytest.mark.unit
class TestAppointmentServiceList:
    """Unit tests for AppointmentService.list_appointments method."""

    @pytest.fixture
    def mock_appointment_repository(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repository(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repository: AsyncMock,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> AppointmentService:
        """Create service with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repository,
            job_repository=mock_job_repository,
            staff_repository=mock_staff_repository,
        )

    @pytest.mark.asyncio
    async def test_list_appointments_default_params(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test listing appointments with default parameters."""
        # Arrange
        mock_appointments = [MagicMock(), MagicMock()]
        mock_appointment_repository.list_with_filters.return_value = (
            mock_appointments,
            2,
        )

        # Act
        appointments, total = await service.list_appointments()

        # Assert
        mock_appointment_repository.list_with_filters.assert_called_once_with(
            page=1,
            page_size=20,
            status=None,
            staff_id=None,
            job_id=None,
            date_from=None,
            date_to=None,
            sort_by="scheduled_date",
            sort_order="asc",
            include_relationships=True,
        )
        assert appointments == mock_appointments
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_appointments_with_filters(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test listing appointments with filters."""
        # Arrange
        staff_id = uuid4()
        mock_appointments = [MagicMock()]
        mock_appointment_repository.list_with_filters.return_value = (
            mock_appointments,
            1,
        )

        # Act
        appointments, total = await service.list_appointments(
            page=2,
            page_size=10,
            status=AppointmentStatus.SCHEDULED,
            staff_id=staff_id,
            date_from=date.today(),
            sort_by="time_window_start",
            sort_order="desc",
        )

        # Assert
        mock_appointment_repository.list_with_filters.assert_called_once_with(
            page=2,
            page_size=10,
            status=AppointmentStatus.SCHEDULED,
            staff_id=staff_id,
            job_id=None,
            date_from=date.today(),
            date_to=None,
            sort_by="time_window_start",
            sort_order="desc",
            include_relationships=True,
        )
        assert appointments == mock_appointments
        assert total == 1


@pytest.mark.unit
class TestAppointmentServiceScheduleQueries:
    """Unit tests for AppointmentService schedule query methods."""

    @pytest.fixture
    def mock_appointment_repository(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repository(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repository: AsyncMock,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> AppointmentService:
        """Create service with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repository,
            job_repository=mock_job_repository,
            staff_repository=mock_staff_repository,
        )

    @pytest.mark.asyncio
    async def test_get_daily_schedule(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test getting daily schedule."""
        # Arrange
        schedule_date = date.today()
        mock_appointments = [MagicMock(), MagicMock(), MagicMock()]
        mock_appointment_repository.get_daily_schedule.return_value = mock_appointments

        # Act
        appointments, total = await service.get_daily_schedule(schedule_date)

        # Assert
        mock_appointment_repository.get_daily_schedule.assert_called_once_with(
            schedule_date,
            include_relationships=False,
        )
        assert appointments == mock_appointments
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_daily_schedule_with_relationships(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test getting daily schedule with relationships loaded."""
        # Arrange
        schedule_date = date.today()
        mock_appointments = [MagicMock()]
        mock_appointment_repository.get_daily_schedule.return_value = mock_appointments

        # Act
        appointments, total = await service.get_daily_schedule(
            schedule_date,
            include_relationships=True,
        )

        # Assert
        mock_appointment_repository.get_daily_schedule.assert_called_once_with(
            schedule_date,
            include_relationships=True,
        )
        assert appointments == mock_appointments
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_staff_daily_schedule(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> None:
        """Test getting staff daily schedule."""
        # Arrange
        staff_id = uuid4()
        schedule_date = date.today()
        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_staff_repository.get_by_id.return_value = mock_staff

        # Create mock appointments with duration
        mock_apt1 = MagicMock()
        mock_apt1.get_duration_minutes.return_value = 60
        mock_apt2 = MagicMock()
        mock_apt2.get_duration_minutes.return_value = 90
        mock_appointments = [mock_apt1, mock_apt2]
        mock_appointment_repository.get_staff_daily_schedule.return_value = (
            mock_appointments
        )

        # Act
        appointments, total, total_minutes = await service.get_staff_daily_schedule(
            staff_id,
            schedule_date,
        )

        # Assert
        mock_staff_repository.get_by_id.assert_called_once_with(staff_id)
        mock_appointment_repository.get_staff_daily_schedule.assert_called_once_with(
            staff_id,
            schedule_date,
            include_relationships=False,
        )
        assert appointments == mock_appointments
        assert total == 2
        assert total_minutes == 150

    @pytest.mark.asyncio
    async def test_get_staff_daily_schedule_staff_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_staff_repository: AsyncMock,
    ) -> None:
        """Test getting staff daily schedule when staff not found raises error."""
        # Arrange
        staff_id = uuid4()
        schedule_date = date.today()
        mock_staff_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(StaffNotFoundError):
            await service.get_staff_daily_schedule(staff_id, schedule_date)

    @pytest.mark.asyncio
    async def test_get_weekly_schedule(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test getting weekly schedule."""
        # Arrange
        start_date = date.today()
        mock_schedule = {
            start_date: [MagicMock(), MagicMock()],
            start_date + timedelta(days=1): [MagicMock()],
            start_date + timedelta(days=2): [],
            start_date + timedelta(days=3): [MagicMock()],
            start_date + timedelta(days=4): [],
            start_date + timedelta(days=5): [],
            start_date + timedelta(days=6): [],
        }
        mock_appointment_repository.get_weekly_schedule.return_value = mock_schedule

        # Act
        schedule, total = await service.get_weekly_schedule(start_date)

        # Assert
        mock_appointment_repository.get_weekly_schedule.assert_called_once_with(
            start_date,
            include_relationships=False,
        )
        assert schedule == mock_schedule
        assert total == 4  # 2 + 1 + 0 + 1 + 0 + 0 + 0


@pytest.mark.unit
class TestAppointmentServiceStatusTransitions:
    """Unit tests for AppointmentService status transition methods."""

    @pytest.fixture
    def mock_appointment_repository(self) -> AsyncMock:
        """Create mock appointment repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repository(self) -> AsyncMock:
        """Create mock staff repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_appointment_repository: AsyncMock,
        mock_job_repository: AsyncMock,
        mock_staff_repository: AsyncMock,
    ) -> AppointmentService:
        """Create service with mock repositories."""
        return AppointmentService(
            appointment_repository=mock_appointment_repository,
            job_repository=mock_job_repository,
            staff_repository=mock_staff_repository,
        )

    @pytest.mark.asyncio
    async def test_mark_arrived_success(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test marking appointment as arrived (in progress)."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.CONFIRMED.value
        mock_appointment.can_transition_to.return_value = True
        mock_appointment_repository.get_by_id.return_value = mock_appointment
        mock_appointment_repository.update_status.return_value = mock_appointment

        # Act
        result = await service.mark_arrived(appointment_id)

        # Assert
        mock_appointment.can_transition_to.assert_called_once_with(
            AppointmentStatus.IN_PROGRESS.value,
        )
        mock_appointment_repository.update_status.assert_called_once()
        call_args = mock_appointment_repository.update_status.call_args
        assert call_args[0][0] == appointment_id
        assert call_args[0][1] == AppointmentStatus.IN_PROGRESS
        assert call_args[1]["arrived_at"] is not None
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_mark_arrived_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test marking arrived when appointment not found raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(AppointmentNotFoundError):
            await service.mark_arrived(appointment_id)

    @pytest.mark.asyncio
    async def test_mark_arrived_invalid_transition_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test marking arrived with invalid transition raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.COMPLETED.value
        mock_appointment.can_transition_to.return_value = False
        mock_appointment_repository.get_by_id.return_value = mock_appointment

        # Act & Assert
        with pytest.raises(InvalidStatusTransitionError):
            await service.mark_arrived(appointment_id)

    @pytest.mark.asyncio
    async def test_mark_completed_success(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test marking appointment as completed."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.IN_PROGRESS.value
        mock_appointment.can_transition_to.return_value = True
        mock_appointment_repository.get_by_id.return_value = mock_appointment
        mock_appointment_repository.update_status.return_value = mock_appointment

        # Act
        result = await service.mark_completed(appointment_id)

        # Assert
        mock_appointment.can_transition_to.assert_called_once_with(
            AppointmentStatus.COMPLETED.value,
        )
        mock_appointment_repository.update_status.assert_called_once()
        call_args = mock_appointment_repository.update_status.call_args
        assert call_args[0][0] == appointment_id
        assert call_args[0][1] == AppointmentStatus.COMPLETED
        assert call_args[1]["completed_at"] is not None
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_mark_completed_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test marking completed when appointment not found raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(AppointmentNotFoundError):
            await service.mark_completed(appointment_id)

    @pytest.mark.asyncio
    async def test_mark_completed_invalid_transition_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test marking completed with invalid transition raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.SCHEDULED.value
        mock_appointment.can_transition_to.return_value = False
        mock_appointment_repository.get_by_id.return_value = mock_appointment

        # Act & Assert
        with pytest.raises(InvalidStatusTransitionError):
            await service.mark_completed(appointment_id)

    @pytest.mark.asyncio
    async def test_confirm_appointment_success(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test confirming an appointment."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.SCHEDULED.value
        mock_appointment.can_transition_to.return_value = True
        mock_appointment_repository.get_by_id.return_value = mock_appointment
        mock_appointment_repository.update_status.return_value = mock_appointment

        # Act
        result = await service.confirm_appointment(appointment_id)

        # Assert
        mock_appointment.can_transition_to.assert_called_once_with(
            AppointmentStatus.CONFIRMED.value,
        )
        mock_appointment_repository.update_status.assert_called_once_with(
            appointment_id,
            AppointmentStatus.CONFIRMED,
        )
        assert result == mock_appointment

    @pytest.mark.asyncio
    async def test_confirm_appointment_not_found_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test confirming appointment when not found raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(AppointmentNotFoundError):
            await service.confirm_appointment(appointment_id)

    @pytest.mark.asyncio
    async def test_confirm_appointment_invalid_transition_raises_error(
        self,
        service: AppointmentService,
        mock_appointment_repository: AsyncMock,
    ) -> None:
        """Test confirming appointment with invalid transition raises error."""
        # Arrange
        appointment_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = AppointmentStatus.COMPLETED.value
        mock_appointment.can_transition_to.return_value = False
        mock_appointment_repository.get_by_id.return_value = mock_appointment

        # Act & Assert
        with pytest.raises(InvalidStatusTransitionError):
            await service.confirm_appointment(appointment_id)
