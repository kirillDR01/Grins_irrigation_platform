"""
Tests for Appointment Service Layer.

This module tests the AppointmentService class for Admin Dashboard Phase 3,
including appointment creation, status transitions, and schedule queries.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    StaffNotFoundError,
)
from grins_platform.models.enums import (
    AgreementStatus,
    AppointmentStatus,
    DisclosureType,
    JobCategory,
    JobStatus,
)
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


# =============================================================================
# Checkout Webhook Full Flow Tests
# =============================================================================

# Lazy imports for webhook/job-generator tests — avoids import overhead for
# the appointment-only test runs and keeps the module importable even if
# webhook infrastructure changes.
_WEBHOOK_MODULE = "grins_platform.api.v1.webhooks"


def _import_webhook_handler():
    from grins_platform.api.v1.webhooks import StripeWebhookHandler

    return StripeWebhookHandler


def _import_job_generator():
    from grins_platform.services.job_generator import JobGenerator

    return JobGenerator


def _build_stripe_checkout_event(
    consent_token: str,
    *,
    tier_slug: str = "professional-residential",
    package_type: str = "residential",
    zone_count: str = "6",
    has_lake_pump: str = "false",
    has_rpz_backflow: str = "false",
    email_marketing_consent: str = "true",
    customer_name: str = "Jane Smith",
    customer_email: str = "jane.smith@example.com",
    customer_phone: str = "+16125559876",
) -> dict:
    """Build a realistic Stripe ``checkout.session.completed`` event dict."""
    return {
        "id": "evt_test_checkout_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_stripe_abc123",
                "subscription": "sub_stripe_xyz789",
                "customer_details": {
                    "email": customer_email,
                    "name": customer_name,
                    "phone": customer_phone,
                },
                "customer_email": customer_email,
                "metadata": {
                    "consent_token": consent_token,
                    "package_tier": tier_slug,
                    "package_type": package_type,
                    "zone_count": zone_count,
                    "has_lake_pump": has_lake_pump,
                    "has_rpz_backflow": has_rpz_backflow,
                    "email_marketing_consent": email_marketing_consent,
                },
            },
        },
    }


def _make_mock_customer(customer_id=None):
    """Create a mock Customer model with sensible defaults."""
    customer = MagicMock()
    customer.id = customer_id or uuid4()
    customer.first_name = "Jane"
    customer.last_name = "Smith"
    customer.phone = "6125559876"
    customer.email = "jane.smith@example.com"
    customer.stripe_customer_id = None
    customer.email_opt_in = False
    customer.email_opt_in_at = None
    customer.email_opt_in_source = None
    customer.sms_opt_in = False
    customer.sms_opt_in_at = None
    customer.sms_opt_in_source = None
    return customer


def _make_mock_tier(tier_id=None, name="Professional", slug="professional-residential"):
    """Create a mock ServiceAgreementTier."""
    tier = MagicMock()
    tier.id = tier_id or uuid4()
    tier.name = name
    tier.slug = slug
    tier.package_type = "residential"
    tier.annual_price = Decimal("349.00")
    tier.is_active = True
    return tier


def _make_mock_agreement(agreement_id=None, customer_id=None, tier_id=None):
    """Create a mock ServiceAgreement."""
    agreement = MagicMock()
    agreement.id = agreement_id or uuid4()
    agreement.agreement_number = "AGR-2026-001"
    agreement.customer_id = customer_id or uuid4()
    agreement.tier_id = tier_id or uuid4()
    agreement.status = "pending"
    agreement.annual_price = Decimal("349.00")
    agreement.payment_status = "current"
    agreement.property_id = None
    agreement.jobs = []
    return agreement


def _make_mock_session():
    """Create a mock AsyncSession that handles the SMS-consent query."""
    session = AsyncMock()
    mock_sms_result = MagicMock()
    mock_sms_result.scalar_one_or_none.return_value = MagicMock(consent_given=True)
    session.execute = AsyncMock(return_value=mock_sms_result)
    return session


@pytest.mark.unit
class TestCheckoutWebhookFullFlow:
    """End-to-end tests for ``checkout.session.completed`` webhook processing.

    Simulates a customer purchasing a service package from the landing page
    and verifies the entire backend flow: customer creation, agreement
    lifecycle, surcharges, job generation, compliance, and email notifications.
    """

    @pytest.fixture
    def webhook_deps(self):
        """Patch all webhook handler dependencies and yield a dict of mocks."""
        with (
            patch(f"{_WEBHOOK_MODULE}.StripeWebhookEventRepository"),
            patch(f"{_WEBHOOK_MODULE}.CustomerRepository") as p_cr,
            patch(f"{_WEBHOOK_MODULE}.CustomerService") as p_cs,
            patch(f"{_WEBHOOK_MODULE}.AgreementRepository") as p_ar,
            patch(f"{_WEBHOOK_MODULE}.AgreementTierRepository") as p_tr,
            patch(f"{_WEBHOOK_MODULE}.AgreementService") as p_as,
            patch(f"{_WEBHOOK_MODULE}.SurchargeCalculator") as p_sc,
            patch(f"{_WEBHOOK_MODULE}.ComplianceService") as p_co,
            patch(f"{_WEBHOOK_MODULE}.JobGenerator") as p_jg,
            patch(f"{_WEBHOOK_MODULE}.EmailService") as p_es,
        ):
            yield {
                "CustomerRepository": p_cr,
                "CustomerService": p_cs,
                "AgreementRepository": p_ar,
                "AgreementTierRepository": p_tr,
                "AgreementService": p_as,
                "SurchargeCalculator": p_sc,
                "ComplianceService": p_co,
                "JobGenerator": p_jg,
                "EmailService": p_es,
            }

    def _configure_happy_path(self, deps, mock_customer, mock_tier, mock_agreement):
        """Wire up all mock returns for the standard new-customer happy path."""
        # Customer lookup: not found by email or phone → create new
        cust_repo = deps["CustomerRepository"].return_value
        cust_repo.find_by_email = AsyncMock(return_value=[])
        cust_repo.find_by_phone = AsyncMock(return_value=None)
        mock_resp = MagicMock(id=mock_customer.id)
        deps["CustomerService"].return_value.create_customer = AsyncMock(
            return_value=mock_resp,
        )
        cust_repo.get_by_id = AsyncMock(return_value=mock_customer)

        # Tier resolution
        deps["AgreementTierRepository"].return_value.get_by_slug_and_type = AsyncMock(
            return_value=mock_tier,
        )

        # Agreement creation + activation
        agr_svc = deps["AgreementService"].return_value
        agr_svc.create_agreement = AsyncMock(return_value=mock_agreement)
        agr_svc.transition_status = AsyncMock(return_value=mock_agreement)

        # Surcharges
        breakdown = MagicMock(total=Decimal("349.00"))
        deps["SurchargeCalculator"].calculate.return_value = breakdown

        # Agreement update
        deps["AgreementRepository"].return_value.update = AsyncMock(
            return_value=mock_agreement,
        )

        # Job generation (Professional → 3 jobs)
        deps["JobGenerator"].return_value.generate_jobs = AsyncMock(
            return_value=[MagicMock() for _ in range(3)],
        )

        # Compliance
        comp = deps["ComplianceService"].return_value
        comp.link_orphaned_records = AsyncMock(
            return_value={"disclosures_linked": 1, "consents_linked": 1},
        )
        comp.create_disclosure = AsyncMock(return_value=MagicMock())

        # Email
        email = deps["EmailService"].return_value
        email.send_confirmation_email.return_value = {
            "sent": True,
            "content": "Order confirmed",
            "sent_via": "email",
            "recipient_email": "jane.smith@example.com",
        }
        email.send_welcome_email.return_value = {"sent": True}

    # -----------------------------------------------------------------
    # Test: new customer buys Professional Residential
    # -----------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_new_customer_professional_residential_full_flow(
        self,
        webhook_deps,
    ) -> None:
        """Simulate a brand-new customer purchasing Professional Residential.

        Verifies the complete chain:
        1. Customer looked up by email → not found →
           looked up by phone → not found → created
        2. Tier resolved by slug + package_type
        3. Agreement created (PENDING) then activated (ACTIVE)
        4. Surcharges calculated and applied
        5. Seasonal jobs generated
        6. Orphaned consent records linked
        7. Two compliance disclosures created (PRE_SALE + CONFIRMATION)
        8. Welcome + confirmation emails sent
        """
        consent_token = str(uuid4())
        event = _build_stripe_checkout_event(consent_token)
        mock_customer = _make_mock_customer()
        mock_tier = _make_mock_tier()
        mock_agreement = _make_mock_agreement(
            customer_id=mock_customer.id,
            tier_id=mock_tier.id,
        )
        mock_session = _make_mock_session()
        self._configure_happy_path(
            webhook_deps,
            mock_customer,
            mock_tier,
            mock_agreement,
        )

        # ---- Execute ----
        StripeWebhookHandler = _import_webhook_handler()
        handler = StripeWebhookHandler(mock_session)
        await handler._handle_checkout_completed(event)

        # ---- 1. Customer resolution ----
        cust_repo = webhook_deps["CustomerRepository"].return_value
        cust_repo.find_by_email.assert_called_once_with("jane.smith@example.com")
        cust_repo.find_by_phone.assert_called_once_with("6125559876")

        cust_svc = webhook_deps["CustomerService"].return_value
        cust_svc.create_customer.assert_called_once()
        create_data = cust_svc.create_customer.call_args[0][0]
        assert create_data.first_name == "Jane"
        assert create_data.last_name == "Smith"

        cust_repo.get_by_id.assert_called_once_with(mock_customer.id)

        # Stripe customer ID written to customer record
        assert mock_customer.stripe_customer_id == "cus_stripe_abc123"

        # ---- 2. Tier resolution ----
        tier_repo = webhook_deps["AgreementTierRepository"].return_value
        tier_repo.get_by_slug_and_type.assert_called_once_with(
            "professional-residential",
            "residential",
        )

        # ---- 3. Agreement creation and activation ----
        agr_svc = webhook_deps["AgreementService"].return_value
        agr_svc.create_agreement.assert_called_once_with(
            customer_id=mock_customer.id,
            tier_id=mock_tier.id,
            stripe_data={
                "stripe_subscription_id": "sub_stripe_xyz789",
                "stripe_customer_id": "cus_stripe_abc123",
            },
        )
        agr_svc.transition_status.assert_called_once_with(
            mock_agreement.id,
            AgreementStatus.ACTIVE,
            reason="Payment confirmed via Stripe checkout",
        )

        # ---- 4. Surcharges ----
        webhook_deps["SurchargeCalculator"].calculate.assert_called_once_with(
            tier_slug="professional-residential",
            package_type="residential",
            zone_count=6,
            has_lake_pump=False,
            base_price=mock_tier.annual_price,
            has_rpz_backflow=False,
        )
        update_call = webhook_deps["AgreementRepository"].return_value.update.call_args
        update_data = update_call[0][1]
        assert update_data["zone_count"] == 6
        assert update_data["has_lake_pump"] is False
        assert update_data["has_rpz_backflow"] is False
        assert update_data["base_price"] == mock_tier.annual_price
        assert update_data["annual_price"] == Decimal("349.00")

        # ---- 5. Email marketing consent ----
        assert mock_customer.email_opt_in is True

        # ---- 6. Job generation ----
        webhook_deps["JobGenerator"].return_value.generate_jobs.assert_called_once_with(
            mock_agreement,
        )

        # ---- 7. Orphaned consent records linked ----
        comp = webhook_deps["ComplianceService"].return_value
        comp.link_orphaned_records.assert_called_once_with(
            consent_token=UUID(consent_token),
            customer_id=mock_customer.id,
            agreement_id=mock_agreement.id,
        )

        # ---- 8. SMS consent transferred ----
        assert mock_customer.sms_opt_in is True

        # ---- 9. Compliance disclosures (PRE_SALE + CONFIRMATION) ----
        assert comp.create_disclosure.call_count == 2
        disclosure_calls = comp.create_disclosure.call_args_list

        pre_sale = disclosure_calls[0]
        assert pre_sale.kwargs["disclosure_type"] == DisclosureType.PRE_SALE
        assert pre_sale.kwargs["agreement_id"] == mock_agreement.id
        assert pre_sale.kwargs["customer_id"] == mock_customer.id
        assert pre_sale.kwargs["sent_via"] == "stripe_checkout"

        confirmation = disclosure_calls[1]
        assert confirmation.kwargs["disclosure_type"] == DisclosureType.CONFIRMATION
        assert confirmation.kwargs["agreement_id"] == mock_agreement.id
        assert confirmation.kwargs["customer_id"] == mock_customer.id

        # ---- 10. Emails sent ----
        email = webhook_deps["EmailService"].return_value
        email.send_confirmation_email.assert_called_once_with(
            mock_customer,
            mock_agreement,
            mock_tier,
        )
        email.send_welcome_email.assert_called_once_with(
            mock_customer,
            mock_agreement,
            mock_tier,
        )

        # ---- 11. Session flushed at least twice ----
        assert mock_session.flush.call_count >= 2

    # -----------------------------------------------------------------
    # Test: existing customer found by email — no creation
    # -----------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_existing_customer_found_by_email_skips_creation(
        self,
        webhook_deps,
    ) -> None:
        """When a customer with the same email already exists, skip creation.

        The rest of the flow (agreement, jobs, compliance, emails) must still
        execute normally.
        """
        consent_token = str(uuid4())
        event = _build_stripe_checkout_event(consent_token)
        mock_customer = _make_mock_customer()
        mock_tier = _make_mock_tier()
        mock_agreement = _make_mock_agreement(
            customer_id=mock_customer.id,
            tier_id=mock_tier.id,
        )
        mock_session = _make_mock_session()
        self._configure_happy_path(
            webhook_deps,
            mock_customer,
            mock_tier,
            mock_agreement,
        )

        # Override: customer IS found by email
        cust_repo = webhook_deps["CustomerRepository"].return_value
        cust_repo.find_by_email = AsyncMock(return_value=[mock_customer])

        # Execute
        StripeWebhookHandler = _import_webhook_handler()
        handler = StripeWebhookHandler(mock_session)
        await handler._handle_checkout_completed(event)

        # Customer creation must NOT happen
        cust_svc = webhook_deps["CustomerService"].return_value
        cust_svc.create_customer.assert_not_called()
        cust_repo.find_by_phone.assert_not_called()
        cust_repo.get_by_id.assert_not_called()

        # But everything else still runs
        agr_svc = webhook_deps["AgreementService"].return_value
        agr_svc.create_agreement.assert_called_once()
        agr_svc.transition_status.assert_called_once()
        webhook_deps["JobGenerator"].return_value.generate_jobs.assert_called_once()
        comp = webhook_deps["ComplianceService"].return_value
        assert comp.create_disclosure.call_count == 2
        email = webhook_deps["EmailService"].return_value
        email.send_confirmation_email.assert_called_once()
        email.send_welcome_email.assert_called_once()

    # -----------------------------------------------------------------
    # Test: surcharges applied for lake pump + extra zones
    # -----------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_surcharges_applied_with_lake_pump_and_extra_zones(
        self,
        webhook_deps,
    ) -> None:
        """Verify surcharge calculator receives correct flags when lake pump
        and 12 zones are specified in checkout metadata."""
        consent_token = str(uuid4())
        event = _build_stripe_checkout_event(
            consent_token,
            zone_count="12",
            has_lake_pump="true",
            has_rpz_backflow="true",
        )
        mock_customer = _make_mock_customer()
        mock_tier = _make_mock_tier()
        mock_agreement = _make_mock_agreement(
            customer_id=mock_customer.id,
            tier_id=mock_tier.id,
        )
        mock_session = _make_mock_session()
        self._configure_happy_path(
            webhook_deps,
            mock_customer,
            mock_tier,
            mock_agreement,
        )

        # Surcharge returns higher total
        surcharge_total = Decimal("571.50")
        webhook_deps["SurchargeCalculator"].calculate.return_value = MagicMock(
            total=surcharge_total,
        )

        StripeWebhookHandler = _import_webhook_handler()
        handler = StripeWebhookHandler(mock_session)
        await handler._handle_checkout_completed(event)

        # Verify surcharge calculator got the right inputs
        webhook_deps["SurchargeCalculator"].calculate.assert_called_once_with(
            tier_slug="professional-residential",
            package_type="residential",
            zone_count=12,
            has_lake_pump=True,
            base_price=mock_tier.annual_price,
            has_rpz_backflow=True,
        )

        # Verify agreement updated with surcharge data
        update_data = webhook_deps["AgreementRepository"].return_value.update.call_args[
            0
        ][1]
        assert update_data["zone_count"] == 12
        assert update_data["has_lake_pump"] is True
        assert update_data["has_rpz_backflow"] is True
        assert update_data["annual_price"] == surcharge_total


# =============================================================================
# Job Generator — direct unit tests per tier
# =============================================================================


@pytest.mark.unit
class TestJobGeneratorByTier:
    """Verify that JobGenerator creates the correct number and type of jobs
    for each service tier (Essential, Professional, Premium)."""

    @staticmethod
    def _make_agreement_for_tier(name: str, slug: str) -> MagicMock:
        agreement = MagicMock()
        agreement.id = uuid4()
        agreement.customer_id = uuid4()
        agreement.property_id = None
        agreement.tier.name = name
        agreement.tier.slug = slug
        return agreement

    @pytest.mark.asyncio
    async def test_professional_generates_three_jobs(self) -> None:
        """Professional tier: startup, inspection, winterization."""
        JobGenerator = _import_job_generator()
        session = AsyncMock()
        gen = JobGenerator(session)
        agreement = self._make_agreement_for_tier(
            "Professional", "professional-residential"
        )

        jobs = await gen.generate_jobs(agreement)

        assert len(jobs) == 3
        types = [j.job_type for j in jobs]
        assert types == [
            "spring_startup",
            "mid_season_inspection",
            "fall_winterization",
        ]
        for job in jobs:
            assert job.status == JobStatus.TO_BE_SCHEDULED.value
            assert job.category == JobCategory.READY_TO_SCHEDULE.value
            assert job.customer_id == agreement.customer_id
            assert job.service_agreement_id == agreement.id

        # Verify seasonal windows
        assert jobs[0].target_start_date.month == 4  # April
        assert jobs[1].target_start_date.month == 7  # July
        assert jobs[2].target_start_date.month == 10  # October

    @pytest.mark.asyncio
    async def test_essential_generates_two_jobs(self) -> None:
        """Essential tier: spring_startup + fall_winterization only."""
        JobGenerator = _import_job_generator()
        session = AsyncMock()
        gen = JobGenerator(session)
        agreement = self._make_agreement_for_tier("Essential", "essential-residential")

        jobs = await gen.generate_jobs(agreement)

        assert len(jobs) == 2
        types = [j.job_type for j in jobs]
        assert types == ["spring_startup", "fall_winterization"]
        assert jobs[0].target_start_date.month == 4
        assert jobs[1].target_start_date.month == 10

    @pytest.mark.asyncio
    async def test_premium_generates_seven_jobs(self) -> None:
        """Premium tier: spring + 5 monthly visits (May-Sep) + fall winterization."""
        JobGenerator = _import_job_generator()
        session = AsyncMock()
        gen = JobGenerator(session)
        agreement = self._make_agreement_for_tier("Premium", "premium-residential")

        jobs = await gen.generate_jobs(agreement)

        assert len(jobs) == 7
        types = [j.job_type for j in jobs]
        assert types[0] == "spring_startup"
        assert types[1:6] == ["monthly_visit"] * 5
        assert types[6] == "fall_winterization"

        # Monthly visits span May through September
        monthly_months = [j.target_start_date.month for j in jobs[1:6]]
        assert monthly_months == [5, 6, 7, 8, 9]

    @pytest.mark.asyncio
    async def test_all_jobs_linked_to_agreement_and_customer(self) -> None:
        """Every generated job must carry the agreement and customer IDs."""
        JobGenerator = _import_job_generator()
        session = AsyncMock()
        gen = JobGenerator(session)
        agreement = self._make_agreement_for_tier(
            "Professional", "professional-residential"
        )

        jobs = await gen.generate_jobs(agreement)

        for job in jobs:
            assert job.customer_id == agreement.customer_id
            assert job.service_agreement_id == agreement.id
            assert job.property_id == agreement.property_id
            assert job.requested_at is not None
