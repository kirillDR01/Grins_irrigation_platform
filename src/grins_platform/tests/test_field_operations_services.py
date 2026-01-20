"""
Tests for Field Operations Service Layer.

This module tests all service classes for Phase 2 Field Operations,
including ServiceOfferingService, JobService, and StaffService.

Validates: Requirements 1.1-1.13, 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7,
6.1-6.9, 7.1-7.4, 8.1-8.10, 9.1-9.5
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    CustomerNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    PropertyCustomerMismatchError,
    PropertyNotFoundError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
    StaffNotFoundError,
)
from grins_platform.models.enums import (
    JobCategory,
    JobSource,
    JobStatus,
    PricingModel,
    ServiceCategory,
    StaffRole,
)
from grins_platform.schemas.job import JobCreate, JobStatusUpdate, JobUpdate
from grins_platform.schemas.service_offering import (
    ServiceOfferingCreate,
    ServiceOfferingUpdate,
)
from grins_platform.schemas.staff import StaffCreate, StaffUpdate
from grins_platform.services.job_service import JobService
from grins_platform.services.service_offering_service import ServiceOfferingService
from grins_platform.services.staff_service import StaffService

# =============================================================================
# ServiceOfferingService Tests
# =============================================================================


@pytest.mark.unit
class TestServiceOfferingService:
    """Unit tests for ServiceOfferingService with mocked repository."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository: AsyncMock) -> ServiceOfferingService:
        """Create service with mock repository."""
        return ServiceOfferingService(mock_repository)

    @pytest.mark.asyncio
    async def test_create_service_calls_repository(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that create_service calls repository.create."""
        # Arrange
        mock_service = MagicMock()
        mock_service.id = uuid4()
        mock_repository.create.return_value = mock_service

        data = ServiceOfferingCreate(
            name="Spring Startup",
            category=ServiceCategory.SEASONAL,
            pricing_model=PricingModel.ZONE_BASED,
            base_price=Decimal("50.00"),
            price_per_zone=Decimal("10.00"),
        )

        # Act
        result = await service.create_service(data)

        # Assert
        mock_repository.create.assert_called_once()
        assert result == mock_service

    @pytest.mark.asyncio
    async def test_get_service_found(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test getting a service when found."""
        # Arrange
        service_id = uuid4()
        mock_service = MagicMock()
        mock_service.id = service_id
        mock_repository.get_by_id.return_value = mock_service

        # Act
        result = await service.get_service(service_id)

        # Assert
        mock_repository.get_by_id.assert_called_once_with(
            service_id, include_inactive=True,
        )
        assert result == mock_service

    @pytest.mark.asyncio
    async def test_get_service_not_found_raises_error(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test getting a service when not found raises error."""
        # Arrange
        service_id = uuid4()
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ServiceOfferingNotFoundError):
            await service.get_service(service_id)

    @pytest.mark.asyncio
    async def test_update_service_found(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test updating a service when found."""
        # Arrange
        service_id = uuid4()
        mock_service = MagicMock()
        mock_service.id = service_id
        mock_repository.get_by_id.return_value = mock_service
        mock_repository.update.return_value = mock_service

        data = ServiceOfferingUpdate(name="Updated Name")

        # Act
        result = await service.update_service(service_id, data)

        # Assert
        mock_repository.update.assert_called_once()
        assert result == mock_service

    @pytest.mark.asyncio
    async def test_update_service_not_found_raises_error(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test updating a service when not found raises error."""
        # Arrange
        service_id = uuid4()
        mock_repository.get_by_id.return_value = None

        data = ServiceOfferingUpdate(name="Updated Name")

        # Act & Assert
        with pytest.raises(ServiceOfferingNotFoundError):
            await service.update_service(service_id, data)

    @pytest.mark.asyncio
    async def test_deactivate_service_found(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test deactivating a service when found."""
        # Arrange
        service_id = uuid4()
        mock_service = MagicMock()
        mock_service.id = service_id
        mock_repository.get_by_id.return_value = mock_service

        # Act
        await service.deactivate_service(service_id)

        # Assert
        mock_repository.deactivate.assert_called_once_with(service_id)

    @pytest.mark.asyncio
    async def test_deactivate_service_not_found_raises_error(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test deactivating a service when not found raises error."""
        # Arrange
        service_id = uuid4()
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ServiceOfferingNotFoundError):
            await service.deactivate_service(service_id)

    @pytest.mark.asyncio
    async def test_list_services(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test listing services with filters."""
        # Arrange
        mock_services = [MagicMock(), MagicMock()]
        mock_repository.list_with_filters.return_value = (mock_services, 2)

        # Act
        services, total = await service.list_services(
            page=1,
            page_size=20,
            category=ServiceCategory.SEASONAL,
        )

        # Assert
        mock_repository.list_with_filters.assert_called_once()
        assert services == mock_services
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_by_category(
        self,
        service: ServiceOfferingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test getting services by category."""
        # Arrange
        mock_services = [MagicMock(), MagicMock()]
        mock_repository.find_by_category.return_value = mock_services

        # Act
        result = await service.get_by_category(ServiceCategory.SEASONAL)

        # Assert
        mock_repository.find_by_category.assert_called_once_with(
            ServiceCategory.SEASONAL, active_only=True,
        )
        assert result == mock_services


# =============================================================================
# StaffService Tests
# =============================================================================


@pytest.mark.unit
class TestStaffService:
    """Unit tests for StaffService with mocked repository."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository: AsyncMock) -> StaffService:
        """Create service with mock repository."""
        return StaffService(mock_repository)

    @pytest.mark.asyncio
    async def test_create_staff_normalizes_phone(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that create_staff normalizes phone number."""
        # Arrange
        mock_staff = MagicMock()
        mock_staff.id = uuid4()
        mock_repository.create.return_value = mock_staff

        data = StaffCreate(
            name="John Doe",
            phone="(612) 555-1234",
            role=StaffRole.TECH,
        )

        # Act
        await service.create_staff(data)

        # Assert
        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["phone"] == "6125551234"

    @pytest.mark.asyncio
    async def test_get_staff_found(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test getting a staff member when found."""
        # Arrange
        staff_id = uuid4()
        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_repository.get_by_id.return_value = mock_staff

        # Act
        result = await service.get_staff(staff_id)

        # Assert
        mock_repository.get_by_id.assert_called_once_with(
            staff_id, include_inactive=True,
        )
        assert result == mock_staff

    @pytest.mark.asyncio
    async def test_get_staff_not_found_raises_error(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test getting a staff member when not found raises error."""
        # Arrange
        staff_id = uuid4()
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(StaffNotFoundError):
            await service.get_staff(staff_id)

    @pytest.mark.asyncio
    async def test_update_staff_found(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test updating a staff member when found."""
        # Arrange
        staff_id = uuid4()
        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_repository.get_by_id.return_value = mock_staff
        mock_repository.update.return_value = mock_staff

        data = StaffUpdate(name="Updated Name")

        # Act
        result = await service.update_staff(staff_id, data)

        # Assert
        mock_repository.update.assert_called_once()
        assert result == mock_staff

    @pytest.mark.asyncio
    async def test_update_staff_not_found_raises_error(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test updating a staff member when not found raises error."""
        # Arrange
        staff_id = uuid4()
        mock_repository.get_by_id.return_value = None

        data = StaffUpdate(name="Updated Name")

        # Act & Assert
        with pytest.raises(StaffNotFoundError):
            await service.update_staff(staff_id, data)

    @pytest.mark.asyncio
    async def test_deactivate_staff_found(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test deactivating a staff member when found."""
        # Arrange
        staff_id = uuid4()
        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_repository.get_by_id.return_value = mock_staff

        # Act
        await service.deactivate_staff(staff_id)

        # Assert
        mock_repository.deactivate.assert_called_once_with(staff_id)

    @pytest.mark.asyncio
    async def test_deactivate_staff_not_found_raises_error(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test deactivating a staff member when not found raises error."""
        # Arrange
        staff_id = uuid4()
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(StaffNotFoundError):
            await service.deactivate_staff(staff_id)

    @pytest.mark.asyncio
    async def test_update_availability(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test updating staff availability."""
        # Arrange
        staff_id = uuid4()
        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_repository.get_by_id.return_value = mock_staff
        mock_repository.update_availability.return_value = mock_staff

        # Act
        result = await service.update_availability(
            staff_id, is_available=False, availability_notes="On vacation",
        )

        # Assert
        mock_repository.update_availability.assert_called_once_with(
            staff_id=staff_id,
            is_available=False,
            availability_notes="On vacation",
        )
        assert result == mock_staff

    @pytest.mark.asyncio
    async def test_list_staff(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test listing staff with filters."""
        # Arrange
        mock_staff_list = [MagicMock(), MagicMock()]
        mock_repository.list_with_filters.return_value = (mock_staff_list, 2)

        # Act
        staff, total = await service.list_staff(
            page=1,
            page_size=20,
            role=StaffRole.TECH,
        )

        # Assert
        mock_repository.list_with_filters.assert_called_once()
        assert staff == mock_staff_list
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_available_staff(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test getting available staff."""
        # Arrange
        mock_staff_list = [MagicMock(), MagicMock()]
        mock_repository.find_available.return_value = mock_staff_list

        # Act
        result = await service.get_available_staff()

        # Assert
        mock_repository.find_available.assert_called_once_with(active_only=True)
        assert result == mock_staff_list

    @pytest.mark.asyncio
    async def test_get_by_role(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test getting staff by role."""
        # Arrange
        mock_staff_list = [MagicMock(), MagicMock()]
        mock_repository.find_by_role.return_value = mock_staff_list

        # Act
        result = await service.get_by_role(StaffRole.TECH)

        # Assert
        mock_repository.find_by_role.assert_called_once_with(
            StaffRole.TECH, active_only=True,
        )
        assert result == mock_staff_list



# =============================================================================
# JobService Tests
# =============================================================================


@pytest.mark.unit
class TestJobService:
    """Unit tests for JobService with mocked repositories."""

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_customer_repository(self) -> AsyncMock:
        """Create mock customer repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_property_repository(self) -> AsyncMock:
        """Create mock property repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_service_repository(self) -> AsyncMock:
        """Create mock service offering repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_job_repository: AsyncMock,
        mock_customer_repository: AsyncMock,
        mock_property_repository: AsyncMock,
        mock_service_repository: AsyncMock,
    ) -> JobService:
        """Create service with mock repositories."""
        return JobService(
            job_repository=mock_job_repository,
            customer_repository=mock_customer_repository,
            property_repository=mock_property_repository,
            service_repository=mock_service_repository,
        )

    # -------------------------------------------------------------------------
    # Job Creation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_job_with_valid_customer(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test creating a job with valid customer."""
        # Arrange
        customer_id = uuid4()
        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer

        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job_repository.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",
        )

        # Act
        result = await service.create_job(data)

        # Assert
        mock_customer_repository.get_by_id.assert_called_once_with(customer_id)
        mock_job_repository.create.assert_called_once()
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_create_job_customer_not_found_raises_error(
        self,
        service: JobService,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test creating a job with non-existent customer raises error."""
        # Arrange
        customer_id = uuid4()
        mock_customer_repository.get_by_id.return_value = None

        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",
        )

        # Act & Assert
        with pytest.raises(CustomerNotFoundError):
            await service.create_job(data)

    @pytest.mark.asyncio
    async def test_create_job_property_not_found_raises_error(
        self,
        service: JobService,
        mock_customer_repository: AsyncMock,
        mock_property_repository: AsyncMock,
    ) -> None:
        """Test creating a job with non-existent property raises error."""
        # Arrange
        customer_id = uuid4()
        property_id = uuid4()
        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer
        mock_property_repository.get_by_id.return_value = None

        data = JobCreate(
            customer_id=customer_id,
            property_id=property_id,
            job_type="spring_startup",
        )

        # Act & Assert
        with pytest.raises(PropertyNotFoundError):
            await service.create_job(data)

    @pytest.mark.asyncio
    async def test_create_job_property_customer_mismatch_raises_error(
        self,
        service: JobService,
        mock_customer_repository: AsyncMock,
        mock_property_repository: AsyncMock,
    ) -> None:
        """Test creating a job with property from different customer raises error."""
        # Arrange
        customer_id = uuid4()
        other_customer_id = uuid4()
        property_id = uuid4()

        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer

        mock_property = MagicMock()
        mock_property.id = property_id
        mock_property.customer_id = other_customer_id  # Different customer
        mock_property_repository.get_by_id.return_value = mock_property

        data = JobCreate(
            customer_id=customer_id,
            property_id=property_id,
            job_type="spring_startup",
        )

        # Act & Assert
        with pytest.raises(PropertyCustomerMismatchError):
            await service.create_job(data)

    @pytest.mark.asyncio
    async def test_create_job_service_not_found_raises_error(
        self,
        service: JobService,
        mock_customer_repository: AsyncMock,
        mock_service_repository: AsyncMock,
    ) -> None:
        """Test creating a job with non-existent service raises error."""
        # Arrange
        customer_id = uuid4()
        service_offering_id = uuid4()

        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer
        mock_service_repository.get_by_id.return_value = None

        data = JobCreate(
            customer_id=customer_id,
            service_offering_id=service_offering_id,
            job_type="spring_startup",
        )

        # Act & Assert
        with pytest.raises(ServiceOfferingNotFoundError):
            await service.create_job(data)

    @pytest.mark.asyncio
    async def test_create_job_inactive_service_raises_error(
        self,
        service: JobService,
        mock_customer_repository: AsyncMock,
        mock_service_repository: AsyncMock,
    ) -> None:
        """Test creating a job with inactive service raises error."""
        # Arrange
        customer_id = uuid4()
        service_offering_id = uuid4()

        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer

        mock_service_offering = MagicMock()
        mock_service_offering.id = service_offering_id
        mock_service_offering.is_active = False
        mock_service_repository.get_by_id.return_value = mock_service_offering

        data = JobCreate(
            customer_id=customer_id,
            service_offering_id=service_offering_id,
            job_type="spring_startup",
        )

        # Act & Assert
        with pytest.raises(ServiceOfferingInactiveError):
            await service.create_job(data)

    # -------------------------------------------------------------------------
    # Auto-Categorization Tests (Property 3)
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_auto_categorize_seasonal_job_ready_to_schedule(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test seasonal jobs are categorized as ready_to_schedule."""
        # Arrange
        customer_id = uuid4()
        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer

        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job_repository.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",  # Seasonal job type
        )

        # Act
        await service.create_job(data)

        # Assert
        call_kwargs = mock_job_repository.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE.value

    @pytest.mark.asyncio
    async def test_auto_categorize_small_repair_ready_to_schedule(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test small repairs are categorized as ready_to_schedule."""
        # Arrange
        customer_id = uuid4()
        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer

        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job_repository.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="small_repair",
        )

        # Act
        await service.create_job(data)

        # Assert
        call_kwargs = mock_job_repository.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE.value

    @pytest.mark.asyncio
    async def test_auto_categorize_quoted_job_ready_to_schedule(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test jobs with quoted_amount are categorized as ready_to_schedule."""
        # Arrange
        customer_id = uuid4()
        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer

        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job_repository.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="custom_installation",  # Not a ready-to-schedule type
            quoted_amount=Decimal("500.00"),  # But has a quote
        )

        # Act
        await service.create_job(data)

        # Assert
        call_kwargs = mock_job_repository.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE.value

    @pytest.mark.asyncio
    async def test_auto_categorize_partner_job_ready_to_schedule(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test partner jobs are categorized as ready_to_schedule."""
        # Arrange
        customer_id = uuid4()
        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer

        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job_repository.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="custom_installation",
            source=JobSource.PARTNER,
        )

        # Act
        await service.create_job(data)

        # Assert
        call_kwargs = mock_job_repository.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE.value

    @pytest.mark.asyncio
    async def test_auto_categorize_other_job_requires_estimate(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test other jobs are categorized as requires_estimate."""
        # Arrange
        customer_id = uuid4()
        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repository.get_by_id.return_value = mock_customer

        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job_repository.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="custom_installation",  # Not a ready-to-schedule type
            # No quoted_amount, not a partner
        )

        # Act
        await service.create_job(data)

        # Assert
        call_kwargs = mock_job_repository.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.REQUIRES_ESTIMATE.value

    # -------------------------------------------------------------------------
    # Status Transition Tests (Property 4)
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_valid_status_transition_requested_to_approved(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test valid transition from requested to approved."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.REQUESTED.value
        mock_job_repository.get_by_id.return_value = mock_job
        mock_job_repository.update.return_value = mock_job

        data = JobStatusUpdate(status=JobStatus.APPROVED)

        # Act
        result = await service.update_status(job_id, data)

        # Assert
        mock_job_repository.update.assert_called_once()
        mock_job_repository.add_status_history.assert_called_once()
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_invalid_status_transition_raises_error(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test invalid status transition raises error."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.REQUESTED.value  # Can't go directly to completed
        mock_job_repository.get_by_id.return_value = mock_job

        data = JobStatusUpdate(status=JobStatus.COMPLETED)

        # Act & Assert
        with pytest.raises(InvalidStatusTransitionError):
            await service.update_status(job_id, data)

    @pytest.mark.asyncio
    async def test_terminal_state_no_transitions(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test terminal states have no valid transitions."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.CLOSED.value  # Terminal state
        mock_job_repository.get_by_id.return_value = mock_job

        data = JobStatusUpdate(status=JobStatus.REQUESTED)

        # Act & Assert
        with pytest.raises(InvalidStatusTransitionError):
            await service.update_status(job_id, data)

    # -------------------------------------------------------------------------
    # Job CRUD Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_job_found(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test getting a job when found."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job_repository.get_by_id.return_value = mock_job

        # Act
        result = await service.get_job(job_id)

        # Assert
        mock_job_repository.get_by_id.assert_called_once_with(
            job_id, include_relationships=False,
        )
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_get_job_not_found_raises_error(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test getting a job when not found raises error."""
        # Arrange
        job_id = uuid4()
        mock_job_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(JobNotFoundError):
            await service.get_job(job_id)

    @pytest.mark.asyncio
    async def test_update_job_found(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test updating a job when found."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.category = JobCategory.REQUIRES_ESTIMATE.value
        mock_job_repository.get_by_id.return_value = mock_job
        mock_job_repository.update.return_value = mock_job

        data = JobUpdate(description="Updated description")

        # Act
        result = await service.update_job(job_id, data)

        # Assert
        mock_job_repository.update.assert_called_once()
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_update_job_with_quote_changes_category(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test updating a job with quoted_amount changes category."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.category = JobCategory.REQUIRES_ESTIMATE.value
        mock_job_repository.get_by_id.return_value = mock_job
        mock_job_repository.update.return_value = mock_job

        data = JobUpdate(quoted_amount=Decimal("500.00"))

        # Act
        await service.update_job(job_id, data)

        # Assert
        call_kwargs = mock_job_repository.update.call_args[0][1]
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE.value

    @pytest.mark.asyncio
    async def test_delete_job_found(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test deleting a job when found."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job_repository.get_by_id.return_value = mock_job

        # Act
        await service.delete_job(job_id)

        # Assert
        mock_job_repository.soft_delete.assert_called_once_with(job_id)

    @pytest.mark.asyncio
    async def test_delete_job_not_found_raises_error(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test deleting a job when not found raises error."""
        # Arrange
        job_id = uuid4()
        mock_job_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(JobNotFoundError):
            await service.delete_job(job_id)

    # -------------------------------------------------------------------------
    # List and Filter Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_jobs(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test listing jobs with filters."""
        # Arrange
        mock_jobs = [MagicMock(), MagicMock()]
        mock_job_repository.list_with_filters.return_value = (mock_jobs, 2)

        # Act
        jobs, total = await service.list_jobs(
            page=1,
            page_size=20,
            status=JobStatus.REQUESTED,
        )

        # Assert
        mock_job_repository.list_with_filters.assert_called_once()
        assert jobs == mock_jobs
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_ready_to_schedule(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test getting jobs ready to schedule."""
        # Arrange
        mock_jobs = [MagicMock(), MagicMock()]
        mock_job_repository.list_with_filters.return_value = (mock_jobs, 2)

        # Act
        jobs, total = await service.get_ready_to_schedule()

        # Assert
        call_kwargs = mock_job_repository.list_with_filters.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE
        assert jobs == mock_jobs
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_needs_estimate(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test getting jobs needing estimates."""
        # Arrange
        mock_jobs = [MagicMock(), MagicMock()]
        mock_job_repository.list_with_filters.return_value = (mock_jobs, 2)

        # Act
        jobs, total = await service.get_needs_estimate()

        # Assert
        call_kwargs = mock_job_repository.list_with_filters.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.REQUIRES_ESTIMATE
        assert jobs == mock_jobs
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_status_history(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test getting status history for a job."""
        # Arrange
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job_repository.get_by_id.return_value = mock_job

        mock_history = [MagicMock(), MagicMock()]
        mock_job_repository.get_status_history.return_value = mock_history

        # Act
        result = await service.get_status_history(job_id)

        # Assert
        mock_job_repository.get_status_history.assert_called_once_with(job_id)
        assert result == mock_history

    # -------------------------------------------------------------------------
    # Price Calculation Tests (Property 5)
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_calculate_price_flat_pricing(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_service_repository: AsyncMock,
    ) -> None:
        """Test price calculation with flat pricing model."""
        # Arrange
        job_id = uuid4()
        service_offering_id = uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.service_offering_id = service_offering_id
        mock_job.property_id = None
        mock_job_repository.get_by_id.return_value = mock_job

        mock_service_offering = MagicMock()
        mock_service_offering.id = service_offering_id
        mock_service_offering.pricing_model = PricingModel.FLAT.value
        mock_service_offering.base_price = 100.00
        mock_service_offering.price_per_zone = None
        mock_service_repository.get_by_id.return_value = mock_service_offering

        # Act
        result = await service.calculate_price(job_id)

        # Assert
        assert result["calculated_price"] == Decimal("100.00")
        assert result["requires_manual_quote"] is False

    @pytest.mark.asyncio
    async def test_calculate_price_zone_based_pricing(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_property_repository: AsyncMock,
        mock_service_repository: AsyncMock,
    ) -> None:
        """Test price calculation with zone-based pricing model."""
        # Arrange
        job_id = uuid4()
        service_offering_id = uuid4()
        property_id = uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.service_offering_id = service_offering_id
        mock_job.property_id = property_id
        mock_job_repository.get_by_id.return_value = mock_job

        mock_property = MagicMock()
        mock_property.id = property_id
        mock_property.zone_count = 5
        mock_property_repository.get_by_id.return_value = mock_property

        mock_service_offering = MagicMock()
        mock_service_offering.id = service_offering_id
        mock_service_offering.pricing_model = PricingModel.ZONE_BASED.value
        mock_service_offering.base_price = 50.00
        mock_service_offering.price_per_zone = 10.00
        mock_service_repository.get_by_id.return_value = mock_service_offering

        # Act
        result = await service.calculate_price(job_id)

        # Assert
        # base_price + (price_per_zone * zone_count) = 50 + (10 * 5) = 100
        assert result["calculated_price"] == Decimal("100.00")
        assert result["requires_manual_quote"] is False
        assert result["zone_count"] == 5

    @pytest.mark.asyncio
    async def test_calculate_price_custom_requires_manual_quote(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
        mock_service_repository: AsyncMock,
    ) -> None:
        """Test price calculation with custom pricing requires manual quote."""
        # Arrange
        job_id = uuid4()
        service_offering_id = uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.service_offering_id = service_offering_id
        mock_job.property_id = None
        mock_job_repository.get_by_id.return_value = mock_job

        mock_service_offering = MagicMock()
        mock_service_offering.id = service_offering_id
        mock_service_offering.pricing_model = PricingModel.CUSTOM.value
        mock_service_offering.base_price = None
        mock_service_offering.price_per_zone = None
        mock_service_repository.get_by_id.return_value = mock_service_offering

        # Act
        result = await service.calculate_price(job_id)

        # Assert
        assert result["calculated_price"] is None
        assert result["requires_manual_quote"] is True

    @pytest.mark.asyncio
    async def test_calculate_price_no_service_requires_manual_quote(
        self,
        service: JobService,
        mock_job_repository: AsyncMock,
    ) -> None:
        """Test price calculation without service requires manual quote."""
        # Arrange
        job_id = uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.service_offering_id = None
        mock_job.property_id = None
        mock_job_repository.get_by_id.return_value = mock_job

        # Act
        result = await service.calculate_price(job_id)

        # Assert
        assert result["requires_manual_quote"] is True
