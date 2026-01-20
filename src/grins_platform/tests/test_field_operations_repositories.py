"""
Tests for field operations repositories.

This module contains unit tests for ServiceOfferingRepository,
JobRepository, and StaffRepository.

Validates: Requirements 1.1-1.11, 2.1-2.12, 6.1-6.9, 7.1-7.4, 8.1-8.6, 9.1-9.5
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    JobCategory,
    JobStatus,
    PricingModel,
    ServiceCategory,
    SkillLevel,
    StaffRole,
)
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository

# ============================================================================
# ServiceOfferingRepository Tests
# ============================================================================


@pytest.mark.unit
class TestServiceOfferingRepository:
    """Unit tests for ServiceOfferingRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> ServiceOfferingRepository:
        """Create repository with mock session."""
        return ServiceOfferingRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_service_offering(
        self,
        repository: ServiceOfferingRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating a service offering."""
        # Arrange
        name = "Spring Startup"
        category = ServiceCategory.SEASONAL
        pricing_model = PricingModel.ZONE_BASED.value

        # Act
        await repository.create(
            name=name,
            category=category,
            pricing_model=pricing_model,
            base_price=50.0,
            price_per_zone=10.0,
        )

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ServiceOfferingRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a service offering by ID when found."""
        # Arrange
        service_id = uuid4()
        mock_service = MagicMock()
        mock_service.id = service_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_service
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(service_id)

        # Assert
        assert result == mock_service
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ServiceOfferingRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a service offering by ID when not found."""
        # Arrange
        service_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(service_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_service_offering(
        self,
        repository: ServiceOfferingRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating a service offering."""
        # Arrange
        service_id = uuid4()
        mock_service = MagicMock()
        mock_service.id = service_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_service
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.update(
            service_id,
            {"name": "Updated Name", "base_price": 75.0},
        )

        # Assert
        assert result == mock_service
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_service_offering(
        self,
        repository: ServiceOfferingRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test deactivating a service offering."""
        # Arrange
        service_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.deactivate(service_id)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_category(
        self,
        repository: ServiceOfferingRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding services by category."""
        # Arrange
        mock_services = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.find_by_category(ServiceCategory.SEASONAL)

        # Assert
        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_with_filters(
        self,
        repository: ServiceOfferingRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing services with filters."""
        # Arrange
        mock_services = [MagicMock()]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        # Act
        services, total = await repository.list_with_filters(
            page=1,
            page_size=20,
            category=ServiceCategory.REPAIR,
        )

        # Assert
        assert len(services) == 1
        assert total == 1


# ============================================================================
# JobRepository Tests
# ============================================================================


@pytest.mark.unit
class TestJobRepository:
    """Unit tests for JobRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> JobRepository:
        """Create repository with mock session."""
        return JobRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_job(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating a job."""
        # Arrange
        customer_id = uuid4()
        job_type = "spring_startup"
        category = JobCategory.READY_TO_SCHEDULE.value

        # Act
        await repository.create(
            customer_id=customer_id,
            job_type=job_type,
            category=category,
        )

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a job by ID when found."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(job_id)

        # Assert
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a job by ID when not found."""
        # Arrange
        job_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(job_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_soft_delete_job(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test soft deleting a job."""
        # Arrange
        job_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.soft_delete(job_id)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_status(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding jobs by status."""
        # Arrange
        mock_jobs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.find_by_status(JobStatus.REQUESTED)

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_find_by_category(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding jobs by category."""
        # Arrange
        mock_jobs = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.find_by_category(JobCategory.READY_TO_SCHEDULE)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_find_by_customer(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding jobs by customer."""
        # Arrange
        customer_id = uuid4()
        mock_jobs = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.find_by_customer(customer_id)

        # Assert
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_add_status_history(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test adding status history entry."""
        # Arrange
        job_id = uuid4()

        # Act
        await repository.add_status_history(
            job_id=job_id,
            new_status=JobStatus.APPROVED,
            previous_status=JobStatus.REQUESTED,
            notes="Approved by admin",
        )

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_status_history(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting status history for a job."""
        # Arrange
        job_id = uuid4()
        mock_history = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_history
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_status_history(job_id)

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_with_filters(
        self,
        repository: JobRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing jobs with filters."""
        # Arrange
        mock_jobs = [MagicMock()]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = mock_jobs
        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        # Act
        jobs, total = await repository.list_with_filters(
            page=1,
            page_size=20,
            status=JobStatus.REQUESTED,
            category=JobCategory.READY_TO_SCHEDULE,
        )

        # Assert
        assert len(jobs) == 1
        assert total == 5


# ============================================================================
# StaffRepository Tests
# ============================================================================


@pytest.mark.unit
class TestStaffRepository:
    """Unit tests for StaffRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> StaffRepository:
        """Create repository with mock session."""
        return StaffRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_staff(
        self,
        repository: StaffRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating a staff member."""
        # Arrange
        name = "John Doe"
        phone = "6125551234"
        role = StaffRole.TECH

        # Act
        await repository.create(
            name=name,
            phone=phone,
            role=role,
            skill_level=SkillLevel.SENIOR,
        )

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: StaffRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a staff member by ID when found."""
        # Arrange
        staff_id = uuid4()
        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_staff
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(staff_id)

        # Assert
        assert result == mock_staff

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: StaffRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a staff member by ID when not found."""
        # Arrange
        staff_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(staff_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_staff(
        self,
        repository: StaffRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test deactivating a staff member."""
        # Arrange
        staff_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.deactivate(staff_id)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_available(
        self,
        repository: StaffRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding available staff."""
        # Arrange
        mock_staff = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_staff
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.find_available()

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_find_by_role(
        self,
        repository: StaffRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding staff by role."""
        # Arrange
        mock_staff = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_staff
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.find_by_role(StaffRole.TECH)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_update_availability(
        self,
        repository: StaffRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating staff availability."""
        # Arrange
        staff_id = uuid4()
        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_staff
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.update_availability(
            staff_id=staff_id,
            is_available=False,
            availability_notes="On vacation",
        )

        # Assert
        assert result == mock_staff
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_with_filters(
        self,
        repository: StaffRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing staff with filters."""
        # Arrange
        mock_staff = [MagicMock(), MagicMock()]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 10
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = mock_staff
        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        # Act
        staff, total = await repository.list_with_filters(
            page=1,
            page_size=20,
            role=StaffRole.TECH,
            is_available=True,
        )

        # Assert
        assert len(staff) == 2
        assert total == 10
