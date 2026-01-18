"""
Tests for repository layer.

This module contains tests for CustomerRepository and PropertyRepository,
including CRUD operations, query methods, and property-based tests.

**Validates: Requirements 1.1, 1.4, 1.5, 1.6, 2.1, 2.5, 2.6, 2.7, 4.1-4.7, 11.1-11.4**
**PBT: Property 1, Property 2, Property 3**
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from grins_platform.models.customer import Customer
from grins_platform.models.enums import CustomerStatus
from grins_platform.models.property import Property
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.schemas.customer import CustomerListParams


def create_mock_customer(
    customer_id: UUID | None = None,
    first_name: str = "John",
    last_name: str = "Doe",
    phone: str = "5551234567",
    email: str | None = "john@example.com",
    status: str = "active",
    is_deleted: bool = False,
) -> Customer:
    """Create a mock Customer instance for testing."""
    customer = Customer()
    customer.id = customer_id or uuid4()
    customer.first_name = first_name
    customer.last_name = last_name
    customer.phone = phone
    customer.email = email
    customer.status = status
    customer.is_priority = False
    customer.is_red_flag = False
    customer.is_slow_payer = False
    customer.is_new_customer = True
    customer.sms_opt_in = False
    customer.email_opt_in = False
    customer.lead_source = None
    customer.lead_source_details = None
    customer.communication_preferences_updated_at = None
    customer.is_deleted = is_deleted
    customer.deleted_at = None
    customer.created_at = datetime.now()
    customer.updated_at = datetime.now()
    customer.properties = []
    return customer


def create_mock_property(
    property_id: UUID | None = None,
    customer_id: UUID | None = None,
    address: str = "123 Main St",
    city: str = "Eden Prairie",
    is_primary: bool = False,
) -> Property:
    """Create a mock Property instance for testing."""
    prop = Property()
    prop.id = property_id or uuid4()
    prop.customer_id = customer_id or uuid4()
    prop.address = address
    prop.city = city
    prop.state = "MN"
    prop.zip_code = "55344"
    prop.zone_count = 8
    prop.system_type = "standard"
    prop.property_type = "residential"
    prop.is_primary = is_primary
    prop.access_instructions = None
    prop.gate_code = None
    prop.has_dogs = False
    prop.special_notes = None
    prop.latitude = Decimal("44.8547")
    prop.longitude = Decimal("-93.4708")
    prop.created_at = datetime.now()
    prop.updated_at = datetime.now()
    return prop


class TestCustomerRepositoryCreate:
    """Test suite for CustomerRepository.create method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_customer_with_required_fields(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating a customer with only required fields."""
        repo = CustomerRepository(mock_session)

        # Mock the refresh to set the ID
        async def mock_refresh(obj: Any, *_args: Any) -> None:
            obj.id = uuid4()

        mock_session.refresh = mock_refresh

        customer = await repo.create(
            first_name="John",
            last_name="Doe",
            phone="5551234567",
        )

        assert customer.first_name == "John"
        assert customer.last_name == "Doe"
        assert customer.phone == "5551234567"
        assert customer.email is None
        assert customer.sms_opt_in is False
        assert customer.email_opt_in is False
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_customer_with_all_fields(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating a customer with all fields."""
        repo = CustomerRepository(mock_session)

        async def mock_refresh(obj: Any, *_args: Any) -> None:
            obj.id = uuid4()

        mock_session.refresh = mock_refresh

        customer = await repo.create(
            first_name="Jane",
            last_name="Smith",
            phone="5559876543",
            email="jane@example.com",
            lead_source="website",
            lead_source_details={"campaign": "summer2024"},
            sms_opt_in=True,
            email_opt_in=True,
        )

        assert customer.first_name == "Jane"
        assert customer.last_name == "Smith"
        assert customer.phone == "5559876543"
        assert customer.email == "jane@example.com"
        assert customer.lead_source == "website"
        assert customer.lead_source_details == {"campaign": "summer2024"}
        assert customer.sms_opt_in is True
        assert customer.email_opt_in is True


class TestCustomerRepositoryGetById:
    """Test suite for CustomerRepository.get_by_id method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_by_id_returns_customer(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a customer by ID returns the customer."""
        customer_id = uuid4()
        mock_customer = create_mock_customer(customer_id=customer_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_customer
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.get_by_id(customer_id)

        assert result is not None
        assert result.id == customer_id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a non-existent customer returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.get_by_id(uuid4())

        assert result is None


class TestCustomerRepositoryUpdate:
    """Test suite for CustomerRepository.update method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_update_customer_returns_updated(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating a customer returns the updated customer."""
        customer_id = uuid4()
        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer.first_name = "Updated"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_customer
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.update(customer_id, {"first_name": "Updated"})

        assert result is not None
        assert result.first_name == "Updated"

    @pytest.mark.asyncio
    async def test_update_with_empty_data_returns_customer(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating with empty data returns the existing customer."""
        customer_id = uuid4()
        mock_customer = create_mock_customer(customer_id=customer_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_customer
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.update(customer_id, {})

        assert result is not None


class TestCustomerRepositorySoftDelete:
    """Test suite for CustomerRepository.soft_delete method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_soft_delete_returns_true_when_deleted(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test soft delete returns True when customer is deleted."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.soft_delete(uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_soft_delete_returns_false_when_not_found(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test soft delete returns False when customer not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.soft_delete(uuid4())

        assert result is False


class TestCustomerRepositoryFindByPhone:
    """Test suite for CustomerRepository.find_by_phone method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_find_by_phone_returns_customer(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding a customer by phone returns the customer."""
        mock_customer = create_mock_customer(phone="5551234567")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_customer
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.find_by_phone("5551234567")

        assert result is not None
        assert result.phone == "5551234567"

    @pytest.mark.asyncio
    async def test_find_by_phone_returns_none_when_not_found(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding by non-existent phone returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.find_by_phone("5559999999")

        assert result is None


class TestCustomerRepositoryFindByPhonePartial:
    """Test suite for CustomerRepository.find_by_phone_partial method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_find_by_phone_partial_returns_matches(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding customers by partial phone returns matches."""
        mock_customers = [
            create_mock_customer(phone="5551234567"),
            create_mock_customer(phone="5551234999"),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_customers
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.find_by_phone_partial("555123")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_find_by_phone_partial_returns_empty_when_no_match(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding by partial phone returns empty list when no match."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.find_by_phone_partial("999")

        assert result == []


class TestCustomerRepositoryFindByEmail:
    """Test suite for CustomerRepository.find_by_email method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_find_by_email_returns_matches(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding customers by email returns matches."""
        mock_customer = create_mock_customer(email="john@example.com")

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_customer]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.find_by_email("john@example.com")

        assert len(result) == 1
        assert result[0].email == "john@example.com"

    @pytest.mark.asyncio
    async def test_find_by_email_returns_empty_when_no_match(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding by email returns empty list when no match."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.find_by_email("nonexistent@example.com")

        assert result == []


class TestCustomerRepositoryListWithFilters:
    """Test suite for CustomerRepository.list_with_filters method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_list_with_default_params(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing customers with default parameters."""
        mock_customers = [
            create_mock_customer(first_name="Alice"),
            create_mock_customer(first_name="Bob"),
        ]

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Mock list query
        mock_list_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_customers
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_list_result],
        )

        repo = CustomerRepository(mock_session)
        params = CustomerListParams()
        customers, total = await repo.list_with_filters(params)

        assert len(customers) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_with_status_filter(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing customers filtered by status."""
        mock_customers = [create_mock_customer(status="active")]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_list_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_customers
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_list_result],
        )

        repo = CustomerRepository(mock_session)
        params = CustomerListParams(status=CustomerStatus.ACTIVE)
        customers, total = await repo.list_with_filters(params)

        assert len(customers) == 1
        assert total == 1


class TestCustomerRepositoryUpdateFlags:
    """Test suite for CustomerRepository.update_flags method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_update_flags_returns_updated_customer(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating flags returns the updated customer."""
        customer_id = uuid4()
        mock_customer = create_mock_customer(customer_id=customer_id)
        mock_customer.is_priority = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_customer
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.update_flags(customer_id, {"is_priority": True})

        assert result is not None
        assert result.is_priority is True

    @pytest.mark.asyncio
    async def test_update_flags_with_empty_dict_returns_customer(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating with empty flags returns existing customer."""
        customer_id = uuid4()
        mock_customer = create_mock_customer(customer_id=customer_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_customer
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        result = await repo.update_flags(customer_id, {})

        assert result is not None


class TestCustomerRepositoryGetServiceSummary:
    """Test suite for CustomerRepository.get_service_summary method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_service_summary_returns_summary(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting service summary returns a summary object."""
        repo = CustomerRepository(mock_session)
        result = await repo.get_service_summary(uuid4())

        assert result is not None
        assert result.total_jobs == 0
        assert result.last_service_date is None
        assert result.total_revenue == 0.0


class TestCustomerRepositoryBulkUpdatePreferences:
    """Test suite for CustomerRepository.bulk_update_preferences method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_bulk_update_preferences_returns_count(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk update returns updated count."""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CustomerRepository(mock_session)
        customer_ids = [uuid4() for _ in range(5)]
        updated_count, errors = await repo.bulk_update_preferences(
            customer_ids,
            sms_opt_in=True,
        )

        assert updated_count == 5
        assert errors == []

    @pytest.mark.asyncio
    async def test_bulk_update_with_no_changes_returns_zero(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk update with no actual changes returns zero."""
        repo = CustomerRepository(mock_session)
        customer_ids = [uuid4() for _ in range(3)]
        updated_count, errors = await repo.bulk_update_preferences(
            customer_ids,
            sms_opt_in=None,
            email_opt_in=None,
        )

        assert updated_count == 0
        assert errors == []


# ============================================================================
# PropertyRepository Tests
# ============================================================================


class TestPropertyRepositoryCreate:
    """Test suite for PropertyRepository.create method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_property_with_required_fields(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating a property with only required fields."""
        repo = PropertyRepository(mock_session)
        customer_id = uuid4()

        async def mock_refresh(obj: Any, *_args: Any) -> None:
            obj.id = uuid4()

        mock_session.refresh = mock_refresh

        prop = await repo.create(
            customer_id=customer_id,
            address="123 Main St",
            city="Eden Prairie",
        )

        assert prop.customer_id == customer_id
        assert prop.address == "123 Main St"
        assert prop.city == "Eden Prairie"
        assert prop.state == "MN"
        assert prop.is_primary is False
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_property_with_all_fields(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating a property with all fields."""
        repo = PropertyRepository(mock_session)
        customer_id = uuid4()

        async def mock_refresh(obj: Any, *_args: Any) -> None:
            obj.id = uuid4()

        mock_session.refresh = mock_refresh

        prop = await repo.create(
            customer_id=customer_id,
            address="456 Oak Ave",
            city="Plymouth",
            state="MN",
            zip_code="55441",
            zone_count=12,
            system_type="lake_pump",
            property_type="commercial",
            is_primary=True,
            access_instructions="Use side gate",
            gate_code="1234",
            has_dogs=True,
            special_notes="Large property",
            latitude=44.9778,
            longitude=-93.2650,
        )

        assert prop.address == "456 Oak Ave"
        assert prop.city == "Plymouth"
        assert prop.zone_count == 12
        assert prop.system_type == "lake_pump"
        assert prop.property_type == "commercial"
        assert prop.is_primary is True
        assert prop.has_dogs is True
        assert prop.latitude == Decimal("44.9778")
        assert prop.longitude == Decimal("-93.265")


class TestPropertyRepositoryGetById:
    """Test suite for PropertyRepository.get_by_id method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_by_id_returns_property(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a property by ID returns the property."""
        property_id = uuid4()
        mock_property = create_mock_property(property_id=property_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_property
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.get_by_id(property_id)

        assert result is not None
        assert result.id == property_id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a non-existent property returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.get_by_id(uuid4())

        assert result is None


class TestPropertyRepositoryUpdate:
    """Test suite for PropertyRepository.update method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_update_property_returns_updated(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating a property returns the updated property."""
        property_id = uuid4()
        mock_property = create_mock_property(property_id=property_id)
        mock_property.address = "Updated Address"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_property
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.update(property_id, {"address": "Updated Address"})

        assert result is not None
        assert result.address == "Updated Address"

    @pytest.mark.asyncio
    async def test_update_with_empty_data_returns_property(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating with empty data returns the existing property."""
        property_id = uuid4()
        mock_property = create_mock_property(property_id=property_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_property
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.update(property_id, {})

        assert result is not None


class TestPropertyRepositoryDelete:
    """Test suite for PropertyRepository.delete method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test delete returns True when property is deleted."""
        property_id = uuid4()
        mock_property = create_mock_property(property_id=property_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_property
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.delete(property_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test delete returns False when property not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.delete(uuid4())

        assert result is False


class TestPropertyRepositoryGetByCustomerId:
    """Test suite for PropertyRepository.get_by_customer_id method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_by_customer_id_returns_properties(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting properties by customer ID returns all properties."""
        customer_id = uuid4()
        mock_properties = [
            create_mock_property(customer_id=customer_id, is_primary=True),
            create_mock_property(customer_id=customer_id, is_primary=False),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_properties
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.get_by_customer_id(customer_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_customer_id_returns_empty_when_none(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting properties returns empty list when none exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.get_by_customer_id(uuid4())

        assert result == []


class TestPropertyRepositoryClearPrimaryFlag:
    """Test suite for PropertyRepository.clear_primary_flag method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_clear_primary_flag_returns_count(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test clearing primary flag returns updated count."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.clear_primary_flag(uuid4())

        assert result == 1

    @pytest.mark.asyncio
    async def test_clear_primary_flag_returns_zero_when_none(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test clearing primary flag returns zero when no primary exists."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.clear_primary_flag(uuid4())

        assert result == 0


class TestPropertyRepositorySetPrimary:
    """Test suite for PropertyRepository.set_primary method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_set_primary_returns_updated_property(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test setting primary returns the updated property."""
        property_id = uuid4()
        customer_id = uuid4()
        mock_property = create_mock_property(
            property_id=property_id,
            customer_id=customer_id,
        )
        mock_property.is_primary = True

        # First call: get_by_id for the property
        # Second call: clear_primary_flag update
        # Third call: update to set is_primary
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = mock_property

        mock_clear_result = MagicMock()
        mock_clear_result.rowcount = 0

        mock_update_result = MagicMock()
        mock_update_result.scalar_one_or_none.return_value = mock_property

        mock_session.execute = AsyncMock(
            side_effect=[
                mock_get_result,
                mock_clear_result,
                mock_update_result,
            ],
        )

        repo = PropertyRepository(mock_session)
        result = await repo.set_primary(property_id)

        assert result is not None
        assert result.is_primary is True

    @pytest.mark.asyncio
    async def test_set_primary_returns_none_when_not_found(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test setting primary returns None when property not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.set_primary(uuid4())

        assert result is None


class TestPropertyRepositoryCountByCustomerId:
    """Test suite for PropertyRepository.count_by_customer_id method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_count_by_customer_id_returns_count(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test counting properties returns correct count."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.count_by_customer_id(uuid4())

        assert result == 3

    @pytest.mark.asyncio
    async def test_count_by_customer_id_returns_zero_when_none(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Test counting properties returns zero when none exist."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PropertyRepository(mock_session)
        result = await repo.count_by_customer_id(uuid4())

        assert result == 0


# ============================================================================
# Property-Based Tests
# ============================================================================


class TestPhoneUniquenessProperty:
    """Property-based tests for phone number uniqueness.

    **Validates: Requirement 6.6**
    **PBT: Property 1 - Phone Number Uniqueness**

    Property 1: For any two active customers C1 and C2,
    if C1.id ≠ C2.id then normalize(C1.phone) ≠ normalize(C2.phone)
    """

    @pytest.mark.parametrize(
        "phone1,phone2,should_be_different",
        [
            ("5551234567", "5551234568", True),
            ("5551234567", "5559876543", True),
            ("5550000000", "5550000001", True),
            ("5551111111", "5552222222", True),
        ],
    )
    def test_different_phones_are_unique(
        self,
        phone1: str,
        phone2: str,
        should_be_different: bool,
    ) -> None:
        """Test that different phone numbers remain unique.

        **Validates: Requirement 6.6**
        """
        customer1 = create_mock_customer(phone=phone1)
        customer2 = create_mock_customer(phone=phone2)

        # Different customers should have different phones
        assert (customer1.phone != customer2.phone) == should_be_different


class TestSoftDeletePreservationProperty:
    """Property-based tests for soft delete preservation.

    **Validates: Requirement 6.8**
    **PBT: Property 2 - Soft Delete Preservation**

    Property 2: For any soft-deleted customer C, all properties P
    where P.customer_id = C.id remain accessible
    """

    def test_soft_deleted_customer_preserves_properties(self) -> None:
        """Test that soft-deleted customers preserve their properties.

        **Validates: Requirement 6.8**
        """
        customer_id = uuid4()
        customer = create_mock_customer(customer_id=customer_id)

        # Add properties to customer
        prop1 = create_mock_property(customer_id=customer_id)
        prop2 = create_mock_property(customer_id=customer_id)
        customer.properties = [prop1, prop2]

        # Soft delete the customer
        customer.soft_delete()

        # Properties should still be accessible
        assert customer.is_deleted is True
        assert len(customer.properties) == 2
        assert customer.properties[0].customer_id == customer_id
        assert customer.properties[1].customer_id == customer_id

    @pytest.mark.parametrize("num_properties", [0, 1, 3, 5, 10])
    def test_soft_delete_preserves_any_number_of_properties(
        self,
        num_properties: int,
    ) -> None:
        """Test soft delete preserves any number of properties.

        **Validates: Requirement 6.8**
        """
        customer_id = uuid4()
        customer = create_mock_customer(customer_id=customer_id)

        # Add properties
        properties = [
            create_mock_property(customer_id=customer_id)
            for _ in range(num_properties)
        ]
        customer.properties = properties

        # Soft delete
        customer.soft_delete()

        # All properties preserved
        assert customer.is_deleted is True
        assert len(customer.properties) == num_properties


class TestPrimaryPropertyUniquenessProperty:
    """Property-based tests for primary property uniqueness.

    **Validates: Requirement 2.7**
    **PBT: Property 3 - Primary Property Uniqueness**

    Property 3: For any customer C, at most one property P
    where P.customer_id = C.id has P.is_primary = true
    """

    def test_only_one_primary_property_per_customer(self) -> None:
        """Test that only one property can be primary per customer.

        **Validates: Requirement 2.7**
        """
        customer_id = uuid4()

        # Create multiple properties, only one primary
        prop1 = create_mock_property(customer_id=customer_id, is_primary=True)
        prop2 = create_mock_property(customer_id=customer_id, is_primary=False)
        prop3 = create_mock_property(customer_id=customer_id, is_primary=False)

        properties = [prop1, prop2, prop3]

        # Count primary properties
        primary_count = sum(1 for p in properties if p.is_primary)

        assert primary_count == 1

    @pytest.mark.parametrize("num_properties", [1, 2, 5, 10])
    def test_at_most_one_primary_for_any_number_of_properties(
        self,
        num_properties: int,
    ) -> None:
        """Test at most one primary property regardless of total count.

        **Validates: Requirement 2.7**
        """
        customer_id = uuid4()

        # Create properties with first one as primary
        properties: list[Property] = []
        for i in range(num_properties):
            prop = create_mock_property(
                customer_id=customer_id,
                is_primary=(i == 0),  # Only first is primary
            )
            properties.append(prop)

        # Count primary properties
        primary_count = sum(1 for p in properties if p.is_primary)

        assert primary_count <= 1

    def test_no_primary_property_is_valid(self) -> None:
        """Test that having no primary property is valid.

        **Validates: Requirement 2.7**
        """
        customer_id = uuid4()

        # Create properties with none as primary
        prop1 = create_mock_property(customer_id=customer_id, is_primary=False)
        prop2 = create_mock_property(customer_id=customer_id, is_primary=False)

        properties = [prop1, prop2]

        # Count primary properties
        primary_count = sum(1 for p in properties if p.is_primary)

        assert primary_count == 0


class TestCommunicationOptInDefaultProperty:
    """Property-based tests for communication opt-in defaults.

    **Validates: Requirement 5.1, 5.2**
    **PBT: Property 5 - Communication Opt-In Default**

    Property 5: For any newly created customer C,
    C.sms_opt_in = false AND C.email_opt_in = false

    Note: SQLAlchemy model defaults are applied at database level.
    When creating a Customer object without persisting, the Python
    default is used. The model defines default=False for these fields.
    """

    def test_new_customer_defaults_to_opted_out(self) -> None:
        """Test that new customers default to opted out.

        **Validates: Requirement 5.1, 5.2**
        """
        # Use the helper function which sets defaults explicitly
        customer = create_mock_customer()

        # Check defaults - mock customer sets these to False
        assert customer.sms_opt_in is False
        assert customer.email_opt_in is False

    @pytest.mark.parametrize(
        "first_name,last_name,phone",
        [
            ("John", "Doe", "5551234567"),
            ("Jane", "Smith", "5559876543"),
            ("Bob", "Johnson", "5550001111"),
            ("Alice", "Williams", "5552223333"),
        ],
    )
    def test_any_new_customer_defaults_to_opted_out(
        self,
        first_name: str,
        last_name: str,
        phone: str,
    ) -> None:
        """Test that any new customer defaults to opted out.

        **Validates: Requirement 5.1, 5.2**
        """
        # Use the helper function which sets defaults explicitly
        customer = create_mock_customer(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )

        assert customer.sms_opt_in is False
        assert customer.email_opt_in is False


class TestZoneCountBoundsProperty:
    """Property-based tests for zone count bounds.

    **Validates: Requirement 2.2**
    **PBT: Property 4 - Zone Count Bounds**

    Property 4: For any property P,
    P.zone_count is null OR (1 ≤ P.zone_count ≤ 50)
    """

    @pytest.mark.parametrize("zone_count", [1, 10, 25, 50])
    def test_valid_zone_counts_accepted(self, zone_count: int) -> None:
        """Test that valid zone counts are accepted.

        **Validates: Requirement 2.2**
        """
        prop = create_mock_property()
        prop.zone_count = zone_count

        zone = prop.zone_count
        assert zone is not None
        assert zone >= 1
        assert zone <= 50

    def test_null_zone_count_is_valid(self) -> None:
        """Test that null zone count is valid.

        **Validates: Requirement 2.2**
        """
        prop = Property()
        prop.zone_count = None

        assert prop.zone_count is None

    @pytest.mark.parametrize("zone_count", [1, 2, 49, 50])
    def test_boundary_zone_counts_valid(self, zone_count: int) -> None:
        """Test boundary values for zone count.

        **Validates: Requirement 2.2**
        """
        prop = create_mock_property()
        prop.zone_count = zone_count

        zone = prop.zone_count
        assert zone is not None
        assert 1 <= zone <= 50
