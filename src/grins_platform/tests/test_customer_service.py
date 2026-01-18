"""
Tests for CustomerService.

This module contains unit tests for the CustomerService class,
testing all CRUD operations, lookups, flag management, and bulk operations.

Validates: Requirement 1.1-1.6, 3.1-3.6, 4.1-4.7, 6.6, 8.1-8.4, 11.1-11.6, 12.1-12.5
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.exceptions import (
    BulkOperationError,
    CustomerNotFoundError,
    DuplicateCustomerError,
)
from grins_platform.models.customer import Customer
from grins_platform.models.enums import CustomerStatus, LeadSource
from grins_platform.schemas.customer import (
    CustomerCreate,
    CustomerFlagsUpdate,
    CustomerListParams,
    CustomerUpdate,
    ServiceHistorySummary,
)
from grins_platform.services.customer_service import MAX_BULK_RECORDS, CustomerService


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock CustomerRepository."""
    return AsyncMock()


@pytest.fixture
def customer_service(mock_repository: AsyncMock) -> CustomerService:
    """Create a CustomerService with mocked repository."""
    return CustomerService(repository=mock_repository)


@pytest.fixture
def sample_customer() -> MagicMock:
    """Create a sample customer mock object."""
    customer = MagicMock(spec=Customer)
    customer.id = uuid.uuid4()
    customer.first_name = "John"
    customer.last_name = "Doe"
    customer.phone = "6125551234"
    customer.email = "john.doe@example.com"
    customer.status = CustomerStatus.ACTIVE.value
    customer.is_priority = False
    customer.is_red_flag = False
    customer.is_slow_payer = False
    customer.is_new_customer = True
    customer.sms_opt_in = False
    customer.email_opt_in = False
    customer.lead_source = LeadSource.WEBSITE.value
    customer.created_at = datetime.now()
    customer.updated_at = datetime.now()
    customer.properties = []
    customer.is_deleted = False
    return customer


@pytest.fixture
def sample_customer_create() -> CustomerCreate:
    """Create a sample CustomerCreate schema."""
    return CustomerCreate(
        first_name="John",
        last_name="Doe",
        phone="612-555-1234",
        email="john.doe@example.com",
        lead_source=LeadSource.WEBSITE,
        sms_opt_in=False,
        email_opt_in=False,
    )


class TestCustomerServiceCreate:
    """Tests for CustomerService.create_customer method."""

    @pytest.mark.asyncio
    async def test_create_customer_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
        sample_customer_create: CustomerCreate,
    ) -> None:
        """Test successful customer creation."""
        # Arrange
        mock_repository.find_by_phone.return_value = None
        mock_repository.create.return_value = sample_customer

        # Act
        result = await customer_service.create_customer(sample_customer_create)

        # Assert
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        mock_repository.find_by_phone.assert_called_once_with("6125551234")
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_customer_duplicate_phone_raises_error(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
        sample_customer_create: CustomerCreate,
    ) -> None:
        """Test that duplicate phone raises DuplicateCustomerError."""
        # Arrange
        mock_repository.find_by_phone.return_value = sample_customer

        # Act & Assert
        with pytest.raises(DuplicateCustomerError) as exc_info:
            await customer_service.create_customer(sample_customer_create)

        assert exc_info.value.existing_id == sample_customer.id
        mock_repository.create.assert_not_called()


class TestCustomerServiceGet:
    """Tests for CustomerService.get_customer method."""

    @pytest.mark.asyncio
    async def test_get_customer_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test successful customer retrieval."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_customer
        mock_repository.get_service_summary.return_value = ServiceHistorySummary(
            total_jobs=5,
            last_service_date=datetime.now(),
            total_revenue=1500.0,
        )

        # Act
        result = await customer_service.get_customer(sample_customer.id)

        # Assert
        assert result.id == sample_customer.id
        assert result.first_name == "John"
        assert result.service_history_summary is not None
        assert result.service_history_summary.total_jobs == 5

    @pytest.mark.asyncio
    async def test_get_customer_not_found_raises_error(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that non-existent customer raises CustomerNotFoundError."""
        # Arrange
        customer_id = uuid.uuid4()
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(CustomerNotFoundError) as exc_info:
            await customer_service.get_customer(customer_id)

        assert exc_info.value.customer_id == customer_id

    @pytest.mark.asyncio
    async def test_get_customer_without_service_history(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test customer retrieval without service history."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_customer

        # Act
        result = await customer_service.get_customer(
            sample_customer.id,
            include_service_history=False,
        )

        # Assert
        assert result.id == sample_customer.id
        assert result.service_history_summary is None
        mock_repository.get_service_summary.assert_not_called()


class TestCustomerServiceUpdate:
    """Tests for CustomerService.update_customer method."""

    @pytest.mark.asyncio
    async def test_update_customer_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test successful customer update."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_customer
        updated_customer = MagicMock(spec=Customer)
        updated_customer.id = sample_customer.id
        updated_customer.first_name = "Jane"
        updated_customer.last_name = "Doe"
        updated_customer.phone = sample_customer.phone
        updated_customer.email = sample_customer.email
        updated_customer.status = CustomerStatus.ACTIVE.value
        updated_customer.is_priority = False
        updated_customer.is_red_flag = False
        updated_customer.is_slow_payer = False
        updated_customer.is_new_customer = True
        updated_customer.sms_opt_in = False
        updated_customer.email_opt_in = False
        updated_customer.lead_source = LeadSource.WEBSITE.value
        updated_customer.created_at = datetime.now()
        updated_customer.updated_at = datetime.now()
        mock_repository.update.return_value = updated_customer

        update_data = CustomerUpdate(first_name="Jane")

        # Act
        result = await customer_service.update_customer(sample_customer.id, update_data)

        # Assert
        assert result.first_name == "Jane"
        mock_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_customer_not_found_raises_error(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that updating non-existent customer raises error."""
        # Arrange
        customer_id = uuid.uuid4()
        mock_repository.get_by_id.return_value = None
        update_data = CustomerUpdate(first_name="Jane")

        # Act & Assert
        with pytest.raises(CustomerNotFoundError):
            await customer_service.update_customer(customer_id, update_data)

    @pytest.mark.asyncio
    async def test_update_customer_duplicate_phone_raises_error(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test that changing to existing phone raises error."""
        # Arrange
        other_customer = MagicMock(spec=Customer)
        other_customer.id = uuid.uuid4()
        other_customer.phone = "6125559999"

        mock_repository.get_by_id.return_value = sample_customer
        mock_repository.find_by_phone.return_value = other_customer

        update_data = CustomerUpdate(phone="612-555-9999")

        # Act & Assert
        with pytest.raises(DuplicateCustomerError) as exc_info:
            await customer_service.update_customer(sample_customer.id, update_data)

        assert exc_info.value.existing_id == other_customer.id


class TestCustomerServiceDelete:
    """Tests for CustomerService.delete_customer method."""

    @pytest.mark.asyncio
    async def test_delete_customer_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test successful customer deletion."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_customer
        mock_repository.soft_delete.return_value = True

        # Act
        result = await customer_service.delete_customer(sample_customer.id)

        # Assert
        assert result is True
        mock_repository.soft_delete.assert_called_once_with(sample_customer.id)

    @pytest.mark.asyncio
    async def test_delete_customer_not_found_raises_error(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that deleting non-existent customer raises error."""
        # Arrange
        customer_id = uuid.uuid4()
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(CustomerNotFoundError):
            await customer_service.delete_customer(customer_id)


class TestCustomerServiceList:
    """Tests for CustomerService.list_customers method."""

    @pytest.mark.asyncio
    async def test_list_customers_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test successful customer listing."""
        # Arrange
        mock_repository.list_with_filters.return_value = ([sample_customer], 1)
        params = CustomerListParams(page=1, page_size=20)

        # Act
        result = await customer_service.list_customers(params)

        # Assert
        assert result.total == 1
        assert result.page == 1
        assert result.page_size == 20
        assert result.total_pages == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_list_customers_pagination(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test customer listing with pagination."""
        # Arrange
        mock_repository.list_with_filters.return_value = ([sample_customer], 50)
        params = CustomerListParams(page=2, page_size=10)

        # Act
        result = await customer_service.list_customers(params)

        # Assert
        assert result.total == 50
        assert result.page == 2
        assert result.page_size == 10
        assert result.total_pages == 5

    @pytest.mark.asyncio
    async def test_list_customers_empty_result(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test customer listing with no results."""
        # Arrange
        mock_repository.list_with_filters.return_value = ([], 0)
        params = CustomerListParams(page=1, page_size=20)

        # Act
        result = await customer_service.list_customers(params)

        # Assert
        assert result.total == 0
        assert result.total_pages == 0
        assert len(result.items) == 0


class TestCustomerServiceLookup:
    """Tests for CustomerService lookup methods."""

    @pytest.mark.asyncio
    async def test_lookup_by_phone_exact_match(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test phone lookup with exact match."""
        # Arrange
        mock_repository.find_by_phone.return_value = sample_customer

        # Act
        result = await customer_service.lookup_by_phone("612-555-1234")

        # Assert
        assert len(result) == 1
        assert result[0].phone == "6125551234"
        mock_repository.find_by_phone.assert_called_once_with("6125551234")

    @pytest.mark.asyncio
    async def test_lookup_by_phone_partial_match(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test phone lookup with partial match."""
        # Arrange
        mock_repository.find_by_phone_partial.return_value = [sample_customer]

        # Act
        result = await customer_service.lookup_by_phone("1234", partial_match=True)

        # Assert
        assert len(result) == 1
        mock_repository.find_by_phone_partial.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_by_phone_not_found(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test phone lookup with no match returns empty list."""
        # Arrange
        mock_repository.find_by_phone.return_value = None

        # Act
        result = await customer_service.lookup_by_phone("612-555-0000")

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_lookup_by_email_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test email lookup success."""
        # Arrange
        mock_repository.find_by_email.return_value = [sample_customer]

        # Act
        result = await customer_service.lookup_by_email("john.doe@example.com")

        # Assert
        assert len(result) == 1
        mock_repository.find_by_email.assert_called_once_with("john.doe@example.com")

    @pytest.mark.asyncio
    async def test_lookup_by_email_not_found(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test email lookup with no match returns empty list."""
        # Arrange
        mock_repository.find_by_email.return_value = []

        # Act
        result = await customer_service.lookup_by_email("unknown@example.com")

        # Assert
        assert len(result) == 0


class TestCustomerServiceFlags:
    """Tests for CustomerService.update_flags method."""

    @pytest.mark.asyncio
    async def test_update_flags_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test successful flag update."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_customer
        updated_customer = MagicMock(spec=Customer)
        updated_customer.id = sample_customer.id
        updated_customer.first_name = sample_customer.first_name
        updated_customer.last_name = sample_customer.last_name
        updated_customer.phone = sample_customer.phone
        updated_customer.email = sample_customer.email
        updated_customer.status = CustomerStatus.ACTIVE.value
        updated_customer.is_priority = True
        updated_customer.is_red_flag = False
        updated_customer.is_slow_payer = False
        updated_customer.is_new_customer = True
        updated_customer.sms_opt_in = False
        updated_customer.email_opt_in = False
        updated_customer.lead_source = LeadSource.WEBSITE.value
        updated_customer.created_at = datetime.now()
        updated_customer.updated_at = datetime.now()
        mock_repository.update_flags.return_value = updated_customer

        flags = CustomerFlagsUpdate(is_priority=True)

        # Act
        result = await customer_service.update_flags(sample_customer.id, flags)

        # Assert
        assert result.is_priority is True
        mock_repository.update_flags.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_flags_not_found_raises_error(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that updating flags for non-existent customer raises error."""
        # Arrange
        customer_id = uuid.uuid4()
        mock_repository.get_by_id.return_value = None
        flags = CustomerFlagsUpdate(is_priority=True)

        # Act & Assert
        with pytest.raises(CustomerNotFoundError):
            await customer_service.update_flags(customer_id, flags)


class TestCustomerServiceBulkOperations:
    """Tests for CustomerService bulk operations."""

    @pytest.mark.asyncio
    async def test_bulk_update_preferences_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test successful bulk preference update."""
        # Arrange
        customer_ids = [uuid.uuid4() for _ in range(5)]
        mock_repository.bulk_update_preferences.return_value = (5, [])

        # Act
        result = await customer_service.bulk_update_preferences(
            customer_ids=customer_ids,
            sms_opt_in=True,
        )

        # Assert
        assert result["updated_count"] == 5
        assert result["failed_count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_bulk_update_preferences_exceeds_limit(
        self,
        customer_service: CustomerService,
    ) -> None:
        """Test that exceeding limit raises error."""
        # Arrange
        customer_ids = [uuid.uuid4() for _ in range(MAX_BULK_RECORDS + 1)]

        # Act & Assert
        with pytest.raises(BulkOperationError) as exc_info:
            await customer_service.bulk_update_preferences(
                customer_ids=customer_ids,
                sms_opt_in=True,
            )

        assert exc_info.value.max_allowed == MAX_BULK_RECORDS

    @pytest.mark.asyncio
    async def test_bulk_update_preferences_no_changes(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test bulk update with no changes requested."""
        # Arrange
        customer_ids = [uuid.uuid4() for _ in range(5)]

        # Act
        result = await customer_service.bulk_update_preferences(
            customer_ids=customer_ids,
            sms_opt_in=None,
            email_opt_in=None,
        )

        # Assert
        assert result["updated_count"] == 0
        mock_repository.bulk_update_preferences.assert_not_called()

    @pytest.mark.asyncio
    async def test_export_customers_csv_success(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test successful CSV export."""
        # Arrange - return customers on first call, empty on second to stop pagination
        mock_repository.list_with_filters.side_effect = [
            ([sample_customer], 1),
            ([], 0),
        ]

        # Act
        result = await customer_service.export_customers_csv()

        # Assert
        assert "id,first_name,last_name,phone,email" in result
        assert "John" in result
        assert "Doe" in result

    @pytest.mark.asyncio
    async def test_export_customers_csv_with_city_filter(
        self,
        customer_service: CustomerService,
        mock_repository: AsyncMock,
        sample_customer: MagicMock,
    ) -> None:
        """Test CSV export with city filter."""
        # Arrange - return customers on first call, empty on second to stop pagination
        mock_repository.list_with_filters.side_effect = [
            ([sample_customer], 1),
            ([], 0),
        ]

        # Act
        result = await customer_service.export_customers_csv(city="Eden Prairie")

        # Assert
        assert "John" in result
        # Verify the filter was passed
        call_args = mock_repository.list_with_filters.call_args_list[0]
        assert call_args[0][0].city == "Eden Prairie"

    @pytest.mark.asyncio
    async def test_export_customers_csv_exceeds_limit(
        self,
        customer_service: CustomerService,
    ) -> None:
        """Test that exceeding export limit raises error."""
        # Act & Assert
        with pytest.raises(BulkOperationError) as exc_info:
            await customer_service.export_customers_csv(limit=MAX_BULK_RECORDS + 1)

        assert exc_info.value.max_allowed == MAX_BULK_RECORDS
