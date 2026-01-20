"""
Integration tests for field operations.

This module contains integration tests that verify the field operations
components work correctly together with the existing customer/property system.

Validates: Requirements 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7, 6.1-6.9, 7.1-7.4
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.exceptions import (
    CustomerNotFoundError,
    InvalidStatusTransitionError,
    PropertyCustomerMismatchError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
)
from grins_platform.models.enums import (
    JobCategory,
    JobSource,
    JobStatus,
    PricingModel,
    ServiceCategory,
    StaffRole,
)
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.schemas.job import JobCreate, JobStatusUpdate
from grins_platform.services.job_service import JobService

# =============================================================================
# Test Fixtures
# =============================================================================


def create_mock_customer(
    customer_id: uuid.UUID | None = None,
    first_name: str = "John",
    last_name: str = "Doe",
    phone: str = "6125551234",
) -> MagicMock:
    """Create a mock customer object."""
    customer = MagicMock()
    customer.id = customer_id or uuid.uuid4()
    customer.first_name = first_name
    customer.last_name = last_name
    customer.phone = phone
    customer.is_deleted = False
    return customer


def create_mock_property(
    property_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    address: str = "123 Main St",
    zone_count: int = 6,
) -> MagicMock:
    """Create a mock property object."""
    prop = MagicMock()
    prop.id = property_id or uuid.uuid4()
    prop.customer_id = customer_id or uuid.uuid4()
    prop.address = address
    prop.zone_count = zone_count
    return prop


def create_mock_service_offering(
    service_id: uuid.UUID | None = None,
    name: str = "Spring Startup",
    category: str = ServiceCategory.SEASONAL.value,
    pricing_model: str = PricingModel.ZONE_BASED.value,
    base_price: float = 50.0,
    price_per_zone: float = 5.0,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock service offering object."""
    service = MagicMock()
    service.id = service_id or uuid.uuid4()
    service.name = name
    service.category = category
    service.pricing_model = pricing_model
    service.base_price = base_price
    service.price_per_zone = price_per_zone
    service.is_active = is_active
    return service


def create_mock_job(
    job_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    property_id: uuid.UUID | None = None,
    service_offering_id: uuid.UUID | None = None,
    job_type: str = "spring_startup",
    category: str = JobCategory.READY_TO_SCHEDULE.value,
    status: str = JobStatus.REQUESTED.value,
) -> MagicMock:
    """Create a mock job object."""
    job = MagicMock()
    job.id = job_id or uuid.uuid4()
    job.customer_id = customer_id or uuid.uuid4()
    job.property_id = property_id
    job.service_offering_id = service_offering_id
    job.job_type = job_type
    job.category = category
    job.status = status
    job.created_at = datetime.now()
    job.is_deleted = False
    return job


def create_mock_staff(
    staff_id: uuid.UUID | None = None,
    name: str = "John Tech",
    role: str = StaffRole.TECH.value,
    is_available: bool = True,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock staff object."""
    staff = MagicMock()
    staff.id = staff_id or uuid.uuid4()
    staff.name = name
    staff.role = role
    staff.is_available = is_available
    staff.is_active = is_active
    return staff



# =============================================================================
# Job-Customer Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobCustomerIntegration:
    """Integration tests for job-customer relationships.

    Tests that jobs correctly integrate with the customer system.

    Validates: Requirement 2.2, 10.8, 10.11
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
    def job_service(
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

    async def test_job_creation_with_existing_customer(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
    ) -> None:
        """Test job creation with existing customer succeeds.

        Validates: Requirement 2.2
        """
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_job = create_mock_job(job_id=job_id, customer_id=customer_id)
        mock_job_repo.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",
        )

        result = await job_service.create_job(data)

        assert result.id == job_id
        mock_customer_repo.get_by_id.assert_called_once_with(customer_id)

    async def test_job_creation_with_nonexistent_customer_fails(
        self,
        job_service: JobService,
        mock_customer_repo: AsyncMock,
    ) -> None:
        """Test job creation with non-existent customer fails.

        Validates: Requirement 2.2, Property 9
        """
        customer_id = uuid.uuid4()
        mock_customer_repo.get_by_id.return_value = None

        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",
        )

        with pytest.raises(CustomerNotFoundError):
            await job_service.create_job(data)

    async def test_job_retrieval_includes_customer_reference(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test job retrieval includes customer reference.

        Validates: Requirement 6.1
        """
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_job = create_mock_job(job_id=job_id, customer_id=customer_id)
        mock_job_repo.get_by_id.return_value = mock_job

        result = await job_service.get_job(job_id)

        assert result.customer_id == customer_id



# =============================================================================
# Job-Property Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobPropertyIntegration:
    """Integration tests for job-property relationships.

    Tests that jobs correctly integrate with the property system.

    Validates: Requirement 2.3, 5.2, 5.5, 10.9
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
    def job_service(
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

    async def test_job_creation_with_valid_property(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
        mock_property_repo: AsyncMock,
    ) -> None:
        """Test job creation with valid property succeeds.

        Validates: Requirement 2.3
        """
        customer_id = uuid.uuid4()
        property_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_property = create_mock_property(
            property_id=property_id,
            customer_id=customer_id,
        )
        mock_property_repo.get_by_id.return_value = mock_property

        mock_job = create_mock_job(
            job_id=job_id,
            customer_id=customer_id,
            property_id=property_id,
        )
        mock_job_repo.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            property_id=property_id,
            job_type="spring_startup",
        )

        result = await job_service.create_job(data)

        assert result.property_id == property_id

    async def test_job_creation_with_property_from_different_customer_fails(
        self,
        job_service: JobService,
        mock_customer_repo: AsyncMock,
        mock_property_repo: AsyncMock,
    ) -> None:
        """Test job creation with property from different customer fails.

        Validates: Requirement 2.3, Property 10
        """
        customer_id = uuid.uuid4()
        other_customer_id = uuid.uuid4()
        property_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_property = create_mock_property(
            property_id=property_id,
            customer_id=other_customer_id,  # Different customer!
        )
        mock_property_repo.get_by_id.return_value = mock_property

        data = JobCreate(
            customer_id=customer_id,
            property_id=property_id,
            job_type="spring_startup",
        )

        with pytest.raises(PropertyCustomerMismatchError):
            await job_service.create_job(data)

    async def test_price_calculation_uses_property_zone_count(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_property_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test price calculation uses property zone count.

        Validates: Requirement 5.2, 5.5
        """
        job_id = uuid.uuid4()
        property_id = uuid.uuid4()
        service_id = uuid.uuid4()

        mock_job = create_mock_job(
            job_id=job_id,
            property_id=property_id,
            service_offering_id=service_id,
        )
        mock_job_repo.get_by_id.return_value = mock_job

        mock_property = create_mock_property(
            property_id=property_id,
            zone_count=10,
        )
        mock_property_repo.get_by_id.return_value = mock_property

        mock_service = create_mock_service_offering(
            service_id=service_id,
            pricing_model=PricingModel.ZONE_BASED.value,
            base_price=50.0,
            price_per_zone=5.0,
        )
        mock_service_repo.get_by_id.return_value = mock_service

        result = await job_service.calculate_price(job_id)

        # Expected: 50 + (5 * 10) = 100
        assert result["calculated_price"] == Decimal("100.00")
        assert result["zone_count"] == 10



# =============================================================================
# Job-Service Offering Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobServiceOfferingIntegration:
    """Integration tests for job-service offering relationships.

    Tests that jobs correctly integrate with the service offering system.

    Validates: Requirement 2.4, 5.1-5.4, 10.10
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
    def job_service(
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

    async def test_job_creation_with_active_service(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test job creation with active service succeeds.

        Validates: Requirement 2.4
        """
        customer_id = uuid.uuid4()
        service_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_service = create_mock_service_offering(
            service_id=service_id,
            is_active=True,
        )
        mock_service_repo.get_by_id.return_value = mock_service

        mock_job = create_mock_job(
            job_id=job_id,
            customer_id=customer_id,
            service_offering_id=service_id,
        )
        mock_job_repo.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            service_offering_id=service_id,
            job_type="spring_startup",
        )

        result = await job_service.create_job(data)

        assert result.service_offering_id == service_id

    async def test_job_creation_with_inactive_service_fails(
        self,
        job_service: JobService,
        mock_customer_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test job creation with inactive service fails.

        Validates: Requirement 2.4, Property 11
        """
        customer_id = uuid.uuid4()
        service_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_service = create_mock_service_offering(
            service_id=service_id,
            is_active=False,  # Inactive!
        )
        mock_service_repo.get_by_id.return_value = mock_service

        data = JobCreate(
            customer_id=customer_id,
            service_offering_id=service_id,
            job_type="spring_startup",
        )

        with pytest.raises(ServiceOfferingInactiveError):
            await job_service.create_job(data)

    async def test_job_creation_with_nonexistent_service_fails(
        self,
        job_service: JobService,
        mock_customer_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test job creation with non-existent service fails.

        Validates: Requirement 2.4
        """
        customer_id = uuid.uuid4()
        service_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_service_repo.get_by_id.return_value = None

        data = JobCreate(
            customer_id=customer_id,
            service_offering_id=service_id,
            job_type="spring_startup",
        )

        with pytest.raises(ServiceOfferingNotFoundError):
            await job_service.create_job(data)

    async def test_price_calculation_uses_service_pricing_model(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test price calculation uses service pricing model.

        Validates: Requirement 5.1-5.4
        """
        job_id = uuid.uuid4()
        service_id = uuid.uuid4()

        mock_job = create_mock_job(
            job_id=job_id,
            property_id=None,
            service_offering_id=service_id,
        )
        mock_job_repo.get_by_id.return_value = mock_job

        mock_service = create_mock_service_offering(
            service_id=service_id,
            pricing_model=PricingModel.FLAT.value,
            base_price=150.0,
        )
        mock_service_repo.get_by_id.return_value = mock_service

        result = await job_service.calculate_price(job_id)

        assert result["calculated_price"] == Decimal("150.00")
        assert result["pricing_model"] == PricingModel.FLAT.value



# =============================================================================
# Status Workflow Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestStatusWorkflowIntegration:
    """Integration tests for job status workflow.

    Tests the complete job lifecycle and status history recording.

    Validates: Requirement 4.1-4.9, 7.1-7.4
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
    def job_service(
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

    async def test_complete_job_lifecycle(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
    ) -> None:
        """Test complete job lifecycle from creation to closure.

        Validates: Requirement 4.1-4.9, Property 6
        """
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        # Create job
        mock_job = create_mock_job(
            job_id=job_id,
            customer_id=customer_id,
            status=JobStatus.REQUESTED.value,
        )
        mock_job_repo.create.return_value = mock_job
        mock_job_repo.get_by_id.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",
        )
        await job_service.create_job(data)

        # Verify initial status history was recorded
        mock_job_repo.add_status_history.assert_called()

        # Test all valid transitions
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
            result = await job_service.update_status(job_id, status_data)

            assert result.status == next_status.value

    async def test_status_history_recorded_on_transition(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test status history is recorded on each transition.

        Validates: Requirement 7.1, Property 6
        """
        job_id = uuid.uuid4()

        mock_job = create_mock_job(
            job_id=job_id,
            status=JobStatus.REQUESTED.value,
        )
        mock_job_repo.get_by_id.return_value = mock_job

        updated = MagicMock()
        updated.status = JobStatus.APPROVED.value
        mock_job_repo.update.return_value = updated

        status_data = JobStatusUpdate(
            status=JobStatus.APPROVED,
            notes="Approved by manager",
        )
        await job_service.update_status(job_id, status_data)

        mock_job_repo.add_status_history.assert_called_once_with(
            job_id=job_id,
            new_status=JobStatus.APPROVED,
            previous_status=JobStatus.REQUESTED,
            notes="Approved by manager",
        )

    async def test_invalid_transition_from_requested_to_completed(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test invalid transition from REQUESTED to COMPLETED is rejected.

        Validates: Requirement 4.10
        """
        job_id = uuid.uuid4()

        mock_job = create_mock_job(
            job_id=job_id,
            status=JobStatus.REQUESTED.value,
        )
        mock_job_repo.get_by_id.return_value = mock_job

        status_data = JobStatusUpdate(status=JobStatus.COMPLETED)

        with pytest.raises(InvalidStatusTransitionError):
            await job_service.update_status(job_id, status_data)

    async def test_terminal_state_has_no_valid_transitions(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test terminal states (CLOSED, CANCELLED) have no valid transitions.

        Validates: Requirement 4.8, 4.9
        """
        job_id = uuid.uuid4()

        # Test CLOSED state
        mock_job = create_mock_job(
            job_id=job_id,
            status=JobStatus.CLOSED.value,
        )
        mock_job_repo.get_by_id.return_value = mock_job

        for next_status in JobStatus:
            if next_status != JobStatus.CLOSED:
                status_data = JobStatusUpdate(status=next_status)
                with pytest.raises(InvalidStatusTransitionError):
                    await job_service.update_status(job_id, status_data)

    async def test_cancellation_from_any_non_terminal_state(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test job can be cancelled from any non-terminal state.

        Validates: Requirement 4.7
        """
        job_id = uuid.uuid4()

        cancellable_states = [
            JobStatus.REQUESTED,
            JobStatus.APPROVED,
            JobStatus.SCHEDULED,
            JobStatus.IN_PROGRESS,
        ]

        for state in cancellable_states:
            mock_job = create_mock_job(
                job_id=job_id,
                status=state.value,
            )
            mock_job_repo.get_by_id.return_value = mock_job

            updated = MagicMock()
            updated.status = JobStatus.CANCELLED.value
            mock_job_repo.update.return_value = updated

            status_data = JobStatusUpdate(status=JobStatus.CANCELLED)
            result = await job_service.update_status(job_id, status_data)

            assert result.status == JobStatus.CANCELLED.value



# =============================================================================
# Cross-Component Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossComponentIntegration:
    """Integration tests for cross-component interactions.

    Tests that field operations work correctly with existing Phase 1 components.

    Validates: All integration requirements
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
    def job_service(
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

    async def test_create_job_with_all_references(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
        mock_property_repo: AsyncMock,
        mock_service_repo: AsyncMock,
    ) -> None:
        """Test creating job with customer, property, and service references.

        Validates: Requirement 2.1-2.4
        """
        customer_id = uuid.uuid4()
        property_id = uuid.uuid4()
        service_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_property = create_mock_property(
            property_id=property_id,
            customer_id=customer_id,
            zone_count=8,
        )
        mock_property_repo.get_by_id.return_value = mock_property

        mock_service = create_mock_service_offering(
            service_id=service_id,
            is_active=True,
        )
        mock_service_repo.get_by_id.return_value = mock_service

        mock_job = create_mock_job(
            job_id=job_id,
            customer_id=customer_id,
            property_id=property_id,
            service_offering_id=service_id,
        )
        mock_job_repo.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            property_id=property_id,
            service_offering_id=service_id,
            job_type="spring_startup",
        )

        result = await job_service.create_job(data)

        assert result.customer_id == customer_id
        assert result.property_id == property_id
        assert result.service_offering_id == service_id

    async def test_list_jobs_with_customer_filter(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test listing jobs filtered by customer.

        Validates: Requirement 6.4
        """
        customer_id = uuid.uuid4()

        jobs = [
            create_mock_job(customer_id=customer_id),
            create_mock_job(customer_id=customer_id),
        ]
        mock_job_repo.list_with_filters.return_value = (jobs, 2)

        result, total = await job_service.get_customer_jobs(customer_id)

        assert len(result) == 2
        assert total == 2
        mock_job_repo.list_with_filters.assert_called_once()

    async def test_auto_categorization_with_partner_source(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
    ) -> None:
        """Test auto-categorization for partner source jobs.

        Validates: Requirement 3.4
        """
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_job = create_mock_job(
            job_id=job_id,
            customer_id=customer_id,
            category=JobCategory.READY_TO_SCHEDULE.value,
        )
        mock_job_repo.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="new_installation",  # Would normally require estimate
            source=JobSource.PARTNER,  # But partner source makes it ready
        )

        await job_service.create_job(data)

        call_kwargs = mock_job_repo.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE.value

    async def test_auto_categorization_with_quoted_amount(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
        mock_customer_repo: AsyncMock,
    ) -> None:
        """Test auto-categorization for jobs with quoted amount.

        Validates: Requirement 3.3
        """
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer_repo.get_by_id.return_value = mock_customer

        mock_job = create_mock_job(
            job_id=job_id,
            customer_id=customer_id,
            category=JobCategory.READY_TO_SCHEDULE.value,
        )
        mock_job_repo.create.return_value = mock_job

        data = JobCreate(
            customer_id=customer_id,
            job_type="new_installation",  # Would normally require estimate
            quoted_amount=Decimal("5000.00"),  # But has quote
        )

        await job_service.create_job(data)

        call_kwargs = mock_job_repo.create.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE.value

    async def test_get_ready_to_schedule_jobs(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test getting jobs ready to schedule.

        Validates: Requirement 6.7
        """
        jobs = [
            create_mock_job(category=JobCategory.READY_TO_SCHEDULE.value),
            create_mock_job(category=JobCategory.READY_TO_SCHEDULE.value),
        ]
        mock_job_repo.list_with_filters.return_value = (jobs, 2)

        result, _total = await job_service.get_ready_to_schedule()

        assert len(result) == 2
        mock_job_repo.list_with_filters.assert_called_once()
        call_kwargs = mock_job_repo.list_with_filters.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.READY_TO_SCHEDULE

    async def test_get_needs_estimate_jobs(
        self,
        job_service: JobService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test getting jobs needing estimates.

        Validates: Requirement 6.8
        """
        jobs = [
            create_mock_job(category=JobCategory.REQUIRES_ESTIMATE.value),
        ]
        mock_job_repo.list_with_filters.return_value = (jobs, 1)

        result, _total = await job_service.get_needs_estimate()

        assert len(result) == 1
        call_kwargs = mock_job_repo.list_with_filters.call_args.kwargs
        assert call_kwargs["category"] == JobCategory.REQUIRES_ESTIMATE

