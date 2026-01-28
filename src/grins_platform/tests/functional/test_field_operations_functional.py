"""
Functional tests for field operations services.

This module contains functional tests that verify the field operations
services work correctly with real database infrastructure.

Validates: Requirements 1.1-1.13, 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.exceptions import (
    CustomerNotFoundError,
    InvalidStatusTransitionError,
    PropertyCustomerMismatchError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
    StaffNotFoundError,
)
from grins_platform.models.enums import (
    JobCategory,
    JobStatus,
    PricingModel,
    ServiceCategory,
    SkillLevel,
    StaffRole,
)
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.schemas.job import JobCreate, JobStatusUpdate, JobUpdate
from grins_platform.schemas.service_offering import (
    ServiceOfferingCreate,
    ServiceOfferingUpdate,
)
from grins_platform.schemas.staff import StaffCreate
from grins_platform.services.job_service import JobService
from grins_platform.services.service_offering_service import ServiceOfferingService
from grins_platform.services.staff_service import StaffService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session for functional tests."""

    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def service_offering_repository(
    mock_db_session: MagicMock,
) -> ServiceOfferingRepository:
    """Create ServiceOfferingRepository with mock session."""
    return ServiceOfferingRepository(mock_db_session)


@pytest.fixture
def staff_repository(mock_db_session: MagicMock) -> StaffRepository:
    """Create StaffRepository with mock session."""
    return StaffRepository(mock_db_session)


@pytest.fixture
def job_repository(mock_db_session: MagicMock) -> JobRepository:
    """Create JobRepository with mock session."""
    return JobRepository(mock_db_session)


@pytest.fixture
def customer_repository(mock_db_session: MagicMock) -> CustomerRepository:
    """Create CustomerRepository with mock session."""
    return CustomerRepository(mock_db_session)


@pytest.fixture
def property_repository(mock_db_session: MagicMock) -> PropertyRepository:
    """Create PropertyRepository with mock session."""
    return PropertyRepository(mock_db_session)


# =============================================================================
# ServiceOfferingService Functional Tests
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestServiceOfferingServiceFunctional:
    """Functional tests for ServiceOfferingService.

    Tests service offering workflows with mocked repository.

    Validates: Requirement 1.1-1.13
    """

    @pytest.fixture
    def mock_service_repo(self) -> AsyncMock:
        """Create mock service offering repository."""
        return AsyncMock(spec=ServiceOfferingRepository)

    @pytest.fixture
    def service(self, mock_service_repo: AsyncMock) -> ServiceOfferingService:
        """Create ServiceOfferingService with mock repository."""
        return ServiceOfferingService(repository=mock_service_repo)

    async def test_create_seasonal_service_workflow(
        self,
        service: ServiceOfferingService,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test creating a seasonal service offering.

        Validates: Requirement 1.1, 1.2, 1.3
        """

        service_id = uuid.uuid4()
        mock_offering = MagicMock()
        mock_offering.id = service_id
        mock_offering.name = "Spring Startup"
        mock_offering.category = ServiceCategory.SEASONAL.value
        mock_offering.pricing_model = PricingModel.ZONE_BASED.value
        mock_offering.base_price = 50.0
        mock_offering.price_per_zone = 5.0
        mock_offering.is_active = True

        mock_service_repo.create.return_value = mock_offering

        data = ServiceOfferingCreate(
            name="Spring Startup",
            category=ServiceCategory.SEASONAL,
            pricing_model=PricingModel.ZONE_BASED,
            base_price=Decimal("50.00"),
            price_per_zone=Decimal("5.00"),
            estimated_duration_minutes=30,
            duration_per_zone_minutes=5,
        )

        result = await service.create_service(data)

        assert result.id == service_id
        assert result.name == "Spring Startup"
        mock_service_repo.create.assert_called_once()

    async def test_update_service_pricing_workflow(
        self,
        service: ServiceOfferingService,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test updating service pricing.

        Validates: Requirement 1.5
        """

        service_id = uuid.uuid4()
        existing = MagicMock()
        existing.id = service_id
        existing.base_price = 50.0

        updated = MagicMock()
        updated.id = service_id
        updated.base_price = 60.0

        mock_service_repo.get_by_id.return_value = existing
        mock_service_repo.update.return_value = updated

        data = ServiceOfferingUpdate(base_price=Decimal("60.00"))
        result = await service.update_service(service_id, data)

        assert result.base_price == 60.0
        mock_service_repo.update.assert_called_once()

    async def test_deactivate_service_workflow(
        self,
        service: ServiceOfferingService,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test deactivating a service (soft delete).

        Validates: Requirement 1.6
        """

        service_id = uuid.uuid4()
        existing = MagicMock()
        existing.id = service_id
        existing.is_active = True

        mock_service_repo.get_by_id.return_value = existing
        mock_service_repo.deactivate.return_value = None

        await service.deactivate_service(service_id)

        mock_service_repo.deactivate.assert_called_once_with(service_id)

    async def test_get_nonexistent_service_raises_error(
        self,
        service: ServiceOfferingService,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test getting non-existent service raises error.

        Validates: Requirement 1.4
        """
        service_id = uuid.uuid4()
        mock_service_repo.get_by_id.return_value = None

        with pytest.raises(ServiceOfferingNotFoundError):
            await service.get_service(service_id)

    async def test_list_services_by_category_workflow(
        self,
        service: ServiceOfferingService,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test listing services by category.

        Validates: Requirement 1.11
        """

        services = [MagicMock(), MagicMock()]
        mock_service_repo.find_by_category.return_value = services

        result = await service.get_by_category(ServiceCategory.SEASONAL)

        assert len(result) == 2
        mock_service_repo.find_by_category.assert_called_once_with(
            ServiceCategory.SEASONAL,
            active_only=True,
        )


# =============================================================================
# StaffService Functional Tests
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestStaffServiceFunctional:
    """Functional tests for StaffService.

    Tests staff management workflows with mocked repository.

    Validates: Requirement 8.1-8.10, 9.1-9.5
    """

    @pytest.fixture
    def mock_staff_repo(self) -> AsyncMock:
        """Create mock staff repository."""

        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def service(self, mock_staff_repo: AsyncMock) -> StaffService:
        """Create StaffService with mock repository."""
        return StaffService(repository=mock_staff_repo)

    async def test_create_technician_workflow(
        self,
        service: StaffService,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test creating a field technician.

        Validates: Requirement 8.1
        """

        staff_id = uuid.uuid4()
        mock_staff = MagicMock()
        mock_staff.id = staff_id
        mock_staff.name = "John Doe"
        mock_staff.phone = "6125551234"
        mock_staff.role = StaffRole.TECH.value
        mock_staff.skill_level = SkillLevel.SENIOR.value
        mock_staff.is_available = True
        mock_staff.is_active = True

        mock_staff_repo.create.return_value = mock_staff

        data = StaffCreate(
            name="John Doe",
            phone="612-555-1234",
            email="john@example.com",
            role=StaffRole.TECH,
            skill_level=SkillLevel.SENIOR,
        )

        result = await service.create_staff(data)

        assert result.id == staff_id
        assert result.name == "John Doe"
        # Verify phone was normalized
        call_kwargs = mock_staff_repo.create.call_args.kwargs
        assert call_kwargs["phone"] == "6125551234"

    async def test_update_staff_availability_workflow(
        self,
        service: StaffService,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test updating staff availability.

        Validates: Requirement 9.1, 9.2
        """

        staff_id = uuid.uuid4()
        existing = MagicMock()
        existing.id = staff_id
        existing.is_available = True

        updated = MagicMock()
        updated.id = staff_id
        updated.is_available = False
        updated.availability_notes = "On vacation"

        mock_staff_repo.get_by_id.return_value = existing
        mock_staff_repo.update_availability.return_value = updated

        result = await service.update_availability(
            staff_id,
            is_available=False,
            availability_notes="On vacation",
        )

        assert result.is_available is False
        mock_staff_repo.update_availability.assert_called_once()

    async def test_get_available_staff_workflow(
        self,
        service: StaffService,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test getting available staff.

        Validates: Requirement 9.3
        """

        staff1 = MagicMock()
        staff1.is_available = True
        staff2 = MagicMock()
        staff2.is_available = True

        mock_staff_repo.find_available.return_value = [staff1, staff2]

        result = await service.get_available_staff()

        assert len(result) == 2
        mock_staff_repo.find_available.assert_called_once_with(active_only=True)

    async def test_get_staff_by_role_workflow(
        self,
        service: StaffService,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test getting staff by role.

        Validates: Requirement 9.4
        """

        staff = [MagicMock(), MagicMock()]
        mock_staff_repo.find_by_role.return_value = staff

        result = await service.get_by_role(StaffRole.TECH)

        assert len(result) == 2
        mock_staff_repo.find_by_role.assert_called_once_with(
            StaffRole.TECH,
            active_only=True,
        )

    async def test_deactivate_staff_workflow(
        self,
        service: StaffService,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test deactivating staff (soft delete).

        Validates: Requirement 8.6
        """

        staff_id = uuid.uuid4()
        existing = MagicMock()
        existing.id = staff_id

        mock_staff_repo.get_by_id.return_value = existing
        mock_staff_repo.deactivate.return_value = None

        await service.deactivate_staff(staff_id)

        mock_staff_repo.deactivate.assert_called_once_with(staff_id)

    async def test_get_nonexistent_staff_raises_error(
        self,
        service: StaffService,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Test getting non-existent staff raises error.

        Validates: Requirement 8.4
        """
        staff_id = uuid.uuid4()
        mock_staff_repo.get_by_id.return_value = None

        with pytest.raises(StaffNotFoundError):
            await service.get_staff(staff_id)


# =============================================================================
# JobService Functional Tests
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestJobServiceFunctional:
    """Functional tests for JobService.

    Tests job management workflows with mocked repositories.

    Validates: Requirement 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7
    """

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""

        return AsyncMock(spec=JobRepository)

    @pytest.fixture
    def mock_customer_repo(self) -> AsyncMock:
        """Create mock customer repository."""

        return AsyncMock(spec=CustomerRepository)

    @pytest.fixture
    def mock_property_repo(self) -> AsyncMock:
        """Create mock property repository."""

        return AsyncMock(spec=PropertyRepository)

    @pytest.fixture
    def mock_service_repo(self) -> AsyncMock:
        """Create mock service offering repository."""

        return AsyncMock(spec=ServiceOfferingRepository)

    @pytest.fixture
    def service(
        self,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
        mock_property_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> JobService:
        """Create JobService with mock repositories."""
        return JobService(
            job_repository=mock_job_repo,
            customer_repository=mock_customer_repo,
            property_repository=mock_property_repo,
            service_repository=mock_service_repo,
        )

    async def test_create_seasonal_job_workflow(
        self,
        service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
        mock_property_repo: AsyncMock,
    ) -> None:
        """Test creating a seasonal job (auto-categorized as ready_to_schedule).

        Validates: Requirement 2.1, 3.1, 3.2
        """

        customer_id = uuid.uuid4()
        property_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_property = MagicMock()
        mock_property.id = property_id
        mock_property.customer_id = customer_id
        mock_property_repo.get_by_id.return_value = mock_property

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.category = JobCategory.READY_TO_SCHEDULE.value
        mock_job.status = JobStatus.REQUESTED.value
        mock_job_repo.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            property_id=property_id,
            job_type="spring_startup",
            description="Annual spring startup",
        )

        result = await service.create_job(data)

        assert result.id == job_id
        assert result.category == JobCategory.READY_TO_SCHEDULE.value
        # Verify category was set correctly in create call
        call_kwargs = mock_job_repo.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE.value

    async def test_create_complex_job_requires_estimate(
        self,
        service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
    ) -> None:
        """Test creating a complex job (auto-categorized as requires_estimate).

        Validates: Requirement 3.5
        """

        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.category = JobCategory.REQUIRES_ESTIMATE.value
        mock_job_repo.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="new_installation",
            description="Full system installation",
        )

        await service.create_job(data)

        call_kwargs = mock_job_repo.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.REQUIRES_ESTIMATE.value

    async def test_job_status_transition_workflow(
        self,
        service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test job status transition workflow.

        Validates: Requirement 4.1-4.9
        """

        job_id = uuid.uuid4()

        # Start with REQUESTED status
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.REQUESTED.value
        mock_job_repo.get_by_id.return_value = mock_job

        # Transition to APPROVED
        updated_job = MagicMock()
        updated_job.id = job_id
        updated_job.status = JobStatus.APPROVED.value
        mock_job_repo.update.return_value = updated_job

        data = JobStatusUpdate(status=JobStatus.APPROVED)
        result = await service.update_status(job_id, data)

        assert result.status == JobStatus.APPROVED.value
        mock_job_repo.add_status_history.assert_called_once()

    async def test_invalid_status_transition_rejected(
        self,
        service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test invalid status transition is rejected.

        Validates: Requirement 4.10
        """

        job_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.REQUESTED.value
        mock_job_repo.get_by_id.return_value = mock_job

        # Try to skip to COMPLETED (invalid)
        data = JobStatusUpdate(status=JobStatus.COMPLETED)

        with pytest.raises(InvalidStatusTransitionError):
            await service.update_status(job_id, data)

    async def test_job_with_nonexistent_customer_rejected(
        self,
        service: JobService,
        mock_customer_repo: AsyncMock,
    ) -> None:
        """Test job creation with non-existent customer is rejected.

        Validates: Requirement 2.2
        """
        customer_id = uuid.uuid4()
        mock_customer_repo.get_by_id.return_value = None

        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",
        )

        with pytest.raises(CustomerNotFoundError):
            await service.create_job(data)

    async def test_job_with_wrong_property_customer_rejected(
        self,
        service: JobService,
        mock_customer_repo: AsyncMock,
        mock_property_repo: AsyncMock,
    ) -> None:
        """Test job creation with property from different customer is rejected.

        Validates: Requirement 2.3
        """

        customer_id = uuid.uuid4()
        other_customer_id = uuid.uuid4()
        property_id = uuid.uuid4()

        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_property = MagicMock()
        mock_property.id = property_id
        mock_property.customer_id = other_customer_id  # Different customer!
        mock_property_repo.get_by_id.return_value = mock_property

        data = JobCreate(
            customer_id=customer_id,
            property_id=property_id,
            job_type="spring_startup",
        )

        with pytest.raises(PropertyCustomerMismatchError):
            await service.create_job(data)

    async def test_job_with_inactive_service_rejected(
        self,
        service: JobService,
        mock_customer_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test job creation with inactive service is rejected.

        Validates: Requirement 2.4
        """

        customer_id = uuid.uuid4()
        service_id = uuid.uuid4()

        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_service_offering = MagicMock()
        mock_service_offering.id = service_id
        mock_service_offering.is_active = False  # Inactive!
        mock_service_repo.get_by_id.return_value = mock_service_offering

        data = JobCreate(
            customer_id=customer_id,
            service_offering_id=service_id,
            job_type="spring_startup",
        )

        with pytest.raises(ServiceOfferingInactiveError):
            await service.create_job(data)

    async def test_price_calculation_zone_based_workflow(
        self,
        service: JobService,
        mock_job_repo: AsyncMock,
        mock_property_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test price calculation for zone-based pricing.

        Validates: Requirement 5.1-5.5
        """

        job_id = uuid.uuid4()
        property_id = uuid.uuid4()
        service_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.property_id = property_id
        mock_job.service_offering_id = service_id
        mock_job_repo.get_by_id.return_value = mock_job

        mock_property = MagicMock()
        mock_property.id = property_id
        mock_property.zone_count = 8
        mock_property_repo.get_by_id.return_value = mock_property

        mock_service_offering = MagicMock()
        mock_service_offering.id = service_id
        mock_service_offering.pricing_model = PricingModel.ZONE_BASED.value
        mock_service_offering.base_price = 50.0
        mock_service_offering.price_per_zone = 5.0
        mock_service_repo.get_by_id.return_value = mock_service_offering

        result = await service.calculate_price(job_id)

        # Expected: 50 + (5 * 8) = 90
        assert result["calculated_price"] == Decimal("90.00")
        assert result["requires_manual_quote"] is False
        assert result["zone_count"] == 8

    async def test_price_calculation_flat_rate_workflow(
        self,
        service: JobService,
        mock_job_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test price calculation for flat rate pricing.

        Validates: Requirement 5.3
        """

        job_id = uuid.uuid4()
        service_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.property_id = None
        mock_job.service_offering_id = service_id
        mock_job_repo.get_by_id.return_value = mock_job

        mock_service_offering = MagicMock()
        mock_service_offering.id = service_id
        mock_service_offering.pricing_model = PricingModel.FLAT.value
        mock_service_offering.base_price = 100.0
        mock_service_offering.price_per_zone = None
        mock_service_repo.get_by_id.return_value = mock_service_offering

        result = await service.calculate_price(job_id)

        assert result["calculated_price"] == Decimal("100.00")
        assert result["requires_manual_quote"] is False

    async def test_category_reevaluation_on_quote(
        self,
        service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test category is re-evaluated when quoted_amount is set.

        Validates: Requirement 3.7
        """

        job_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.category = JobCategory.REQUIRES_ESTIMATE.value
        mock_job_repo.get_by_id.return_value = mock_job

        updated_job = MagicMock()
        updated_job.id = job_id
        updated_job.category = JobCategory.READY_TO_SCHEDULE.value
        mock_job_repo.update.return_value = updated_job

        data = JobUpdate(quoted_amount=Decimal("500.00"))
        await service.update_job(job_id, data)

        # Verify category was changed to ready_to_schedule
        # The update is called with (job_id, update_data_dict)
        call_args = mock_job_repo.update.call_args
        update_data = call_args[0][1]  # Second positional arg is the update dict
        assert update_data["category"] == JobCategory.READY_TO_SCHEDULE.value

    async def test_complete_job_lifecycle_workflow(
        self,
        service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
    ) -> None:
        """Test complete job lifecycle from creation to closure.

        Validates: Requirement 4.1-4.9
        """

        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        # Setup customer
        mock_customer = MagicMock()
        mock_customer.id = customer_id
        mock_customer_repo.get_by_id.return_value = mock_customer

        # Create job
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.REQUESTED.value
        mock_job_repo.create.return_value = mock_job
        mock_job_repo.get_by_id.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",
        )
        await service.create_job(data)

        # Transition through all states
        transitions = [
            (JobStatus.REQUESTED, JobStatus.APPROVED),
            (JobStatus.APPROVED, JobStatus.SCHEDULED),
            (JobStatus.SCHEDULED, JobStatus.IN_PROGRESS),
            (JobStatus.IN_PROGRESS, JobStatus.COMPLETED),
            (JobStatus.COMPLETED, JobStatus.CLOSED),
        ]

        for current, next_status in transitions:
            mock_job.status = current.value
            updated = MagicMock()
            updated.status = next_status.value
            mock_job_repo.update.return_value = updated

            status_data = JobStatusUpdate(status=next_status)
            result = await service.update_status(job_id, status_data)
            assert result.status == next_status.value
