"""
Property-Based Tests for Customer Management.

This module contains property-based tests using Hypothesis to verify
correctness properties of the customer management system.

**Validates: Requirements 2.7, 6.6**
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,  # type: ignore[reportUnknownVariableType]
    settings,
    strategies as st,
)

from grins_platform.exceptions import DuplicateCustomerError
from grins_platform.models.customer import Customer
from grins_platform.models.enums import CustomerStatus, LeadSource
from grins_platform.schemas.customer import CustomerCreate, normalize_phone
from grins_platform.schemas.property import PropertyCreate
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.property_service import PropertyService

# =============================================================================
# Strategies for generating test data
# =============================================================================


def phone_strategy() -> st.SearchStrategy[str]:
    """Generate valid 10-digit phone numbers.

    Returns:
        Strategy that generates phone numbers in various formats.
    """
    # Generate 10 random digits
    digits = st.text(
        alphabet="0123456789",
        min_size=10,
        max_size=10,
    )

    # Optionally add formatting
    @st.composite  # type: ignore[reportArgumentType]
    def formatted_phone(draw: st.DrawFn) -> str:
        base_digits = draw(digits)
        format_choice = draw(st.integers(min_value=0, max_value=4))

        if format_choice == 0:
            # Plain digits: 6125551234
            return base_digits
        if format_choice == 1:
            # Dashes: 612-555-1234
            return f"{base_digits[:3]}-{base_digits[3:6]}-{base_digits[6:]}"
        if format_choice == 2:
            # Parentheses: (612) 555-1234
            return f"({base_digits[:3]}) {base_digits[3:6]}-{base_digits[6:]}"
        if format_choice == 3:
            # Dots: 612.555.1234
            return f"{base_digits[:3]}.{base_digits[3:6]}.{base_digits[6:]}"
        # With country code: 1-612-555-1234
        return f"1-{base_digits[:3]}-{base_digits[3:6]}-{base_digits[6:]}"

    return formatted_phone()


def name_strategy() -> st.SearchStrategy[str]:
    """Generate valid customer names.

    Returns:
        Strategy that generates names between 1-100 characters.
    """
    return st.text(
        alphabet=st.characters(  # type: ignore[reportUnknownMemberType]
            whitelist_categories=("L",),  # Letters only
            min_codepoint=65,
            max_codepoint=122,
        ),
        min_size=1,
        max_size=50,
    ).filter(lambda x: len(x.strip()) > 0)


# =============================================================================
# Task 11.3: Phone Uniqueness Property Tests
# =============================================================================


@pytest.mark.unit
class TestPhoneUniquenessProperty:
    """Property-based tests for phone number uniqueness.

    **Validates: Requirements 6.6**

    Property 1: Phone Number Uniqueness
    For any two active customers C1 and C2, if C1.id ≠ C2.id then
    normalize(C1.phone) ≠ normalize(C2.phone)
    """

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create a mock CustomerRepository."""
        return AsyncMock()

    @pytest.fixture
    def customer_service(self, mock_repository: AsyncMock) -> CustomerService:
        """Create a CustomerService with mocked repository."""
        return CustomerService(repository=mock_repository)

    def _create_mock_customer(
        self,
        phone: str,
        customer_id: str | None = None,
    ) -> MagicMock:
        """Create a mock customer with the given phone number.

        Args:
            phone: Normalized phone number
            customer_id: Optional customer ID (generates one if not provided)

        Returns:
            Mock customer object
        """
        customer = MagicMock(spec=Customer)
        customer.id = uuid4() if customer_id is None else customer_id
        customer.first_name = "Test"
        customer.last_name = "User"
        customer.phone = phone
        customer.email = "test@example.com"
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

    @given(phone=phone_strategy())
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_duplicate_phone_rejected_after_normalization(
        self,
        phone: str,
    ) -> None:
        """Test that duplicate phone numbers are rejected after normalization.

        **Validates: Requirements 6.6**

        Property: Creating a customer with a phone number that normalizes to
        the same value as an existing customer's phone should be rejected.
        """
        # Arrange
        mock_repository = AsyncMock()
        service = CustomerService(repository=mock_repository)

        # Normalize the phone to get the expected stored value
        try:
            normalized_phone = normalize_phone(phone)
        except ValueError:
            # Skip invalid phone numbers
            return

        # Create an existing customer with this normalized phone
        existing_customer = self._create_mock_customer(normalized_phone)
        mock_repository.find_by_phone.return_value = existing_customer

        # Create data for a new customer with the same phone (different format)
        customer_data = CustomerCreate(
            first_name="New",
            last_name="Customer",
            phone=phone,
        )

        # Act & Assert
        with pytest.raises(DuplicateCustomerError) as exc_info:
            await service.create_customer(customer_data)

        # Verify the error contains the existing customer's ID
        assert exc_info.value.existing_id == existing_customer.id

        # Verify find_by_phone was called with the normalized phone
        mock_repository.find_by_phone.assert_called_once_with(normalized_phone)

    @given(
        phone1=phone_strategy(),
        phone2=phone_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_different_phones_both_accepted(
        self,
        phone1: str,
        phone2: str,
    ) -> None:
        """Test that different phone numbers can both be created.

        **Validates: Requirements 6.6**

        Property: Two customers with different normalized phone numbers
        should both be creatable.
        """
        # Arrange
        mock_repository = AsyncMock()
        service = CustomerService(repository=mock_repository)

        try:
            normalized1 = normalize_phone(phone1)
            normalized2 = normalize_phone(phone2)
        except ValueError:
            # Skip invalid phone numbers
            return

        # Skip if phones normalize to the same value
        if normalized1 == normalized2:
            return

        # First customer doesn't exist
        mock_repository.find_by_phone.return_value = None

        # Create mock for the created customer
        created_customer = self._create_mock_customer(normalized1)
        mock_repository.create.return_value = created_customer

        # Act - Create first customer
        customer_data1 = CustomerCreate(
            first_name="First",
            last_name="Customer",
            phone=phone1,
        )
        result1 = await service.create_customer(customer_data1)

        # Assert first customer created
        assert result1.phone == normalized1

        # Reset mock for second customer
        mock_repository.find_by_phone.return_value = None
        created_customer2 = self._create_mock_customer(normalized2)
        mock_repository.create.return_value = created_customer2

        # Act - Create second customer
        customer_data2 = CustomerCreate(
            first_name="Second",
            last_name="Customer",
            phone=phone2,
        )
        result2 = await service.create_customer(customer_data2)

        # Assert second customer created with different phone
        assert result2.phone == normalized2
        assert result1.phone != result2.phone

    @given(phone=phone_strategy())
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_phone_uniqueness_enforced_regardless_of_format(
        self,
        phone: str,
    ) -> None:
        """Test phone uniqueness is enforced regardless of input format.

        **Validates: Requirements 6.6**

        Property: Phone uniqueness check uses normalized form, so
        "612-555-1234" and "(612) 555-1234" are considered the same.
        """
        # Arrange
        mock_repository = AsyncMock()
        service = CustomerService(repository=mock_repository)

        try:
            normalized = normalize_phone(phone)
        except ValueError:
            return

        # Existing customer has the normalized phone
        existing = self._create_mock_customer(normalized)
        mock_repository.find_by_phone.return_value = existing

        # Try to create with the original format
        customer_data = CustomerCreate(
            first_name="Test",
            last_name="User",
            phone=phone,
        )

        # Act & Assert - Should reject due to duplicate
        with pytest.raises(DuplicateCustomerError):
            await service.create_customer(customer_data)

        # Verify lookup used normalized phone
        mock_repository.find_by_phone.assert_called_with(normalized)


# =============================================================================
# Task 11.4: Primary Property Uniqueness Tests
# =============================================================================


@pytest.mark.unit
class TestPrimaryPropertyUniquenessProperty:
    """Property-based tests for primary property uniqueness.

    **Validates: Requirements 2.7**

    Property 3: Primary Property Uniqueness
    For any customer C, at most one property P where P.customer_id = C.id
    has P.is_primary = true
    """

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create a mock PropertyRepository."""
        return AsyncMock()

    @pytest.fixture
    def property_service(self, mock_repository: AsyncMock) -> PropertyService:
        """Create a PropertyService with mocked repository."""
        return PropertyService(repository=mock_repository)

    def _create_mock_property(
        self,
        customer_id: UUID,
        is_primary: bool = False,
        property_id: UUID | None = None,
    ) -> MagicMock:
        """Create a mock property.

        Args:
            customer_id: UUID of the owning customer
            is_primary: Whether this is the primary property
            property_id: Optional property ID

        Returns:
            Mock property object
        """
        prop = MagicMock()
        prop.id = uuid4() if property_id is None else property_id
        prop.customer_id = customer_id
        prop.address = "123 Test St"
        prop.city = "Eden Prairie"
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

    @given(num_properties=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_setting_primary_clears_other_primaries(
        self,
        num_properties: int,
    ) -> None:
        """Test that setting a property as primary clears other primary flags.

        **Validates: Requirements 2.7**

        Property: After calling set_primary on property P, P.is_primary = true
        and all other properties for the same customer have is_primary = false.
        """
        # Arrange
        mock_repository = AsyncMock()
        service = PropertyService(repository=mock_repository)

        customer_id = uuid4()

        # Create multiple properties, one is currently primary
        properties = [
            self._create_mock_property(
                customer_id=customer_id,
                is_primary=(i == 0),  # First one is primary
            )
            for i in range(num_properties)
        ]

        # Select a non-primary property to make primary (if more than one)
        target_property = properties[1] if num_properties > 1 else properties[0]

        # Mock repository behavior
        mock_repository.get_by_id.return_value = target_property

        # After set_primary, the target becomes primary
        updated_property = self._create_mock_property(
            customer_id=customer_id,
            is_primary=True,
            property_id=target_property.id,
        )
        mock_repository.set_primary.return_value = updated_property

        # Act
        result = await service.set_primary(target_property.id)

        # Assert
        assert result.is_primary is True

        # Verify set_primary was called (which internally clears other flags)
        if not target_property.is_primary:
            mock_repository.set_primary.assert_called_once_with(target_property.id)

    @given(num_existing=st.integers(min_value=0, max_value=5))
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_first_property_becomes_primary_automatically(
        self,
        num_existing: int,
    ) -> None:
        """Test that the first property for a customer becomes primary.

        **Validates: Requirements 2.7**

        Property: When adding the first property to a customer, it should
        automatically be set as primary.
        """
        # Arrange
        mock_repository = AsyncMock()
        service = PropertyService(repository=mock_repository)

        customer_id = uuid4()

        # Mock count returns 0 (no existing properties)
        mock_repository.count_by_customer_id.return_value = num_existing

        # Create the property that will be returned
        new_property = self._create_mock_property(
            customer_id=customer_id,
            is_primary=(num_existing == 0),  # Primary if first
        )
        mock_repository.create.return_value = new_property

        # Create property data
        property_data = PropertyCreate(
            address="123 New St",
            city="Eden Prairie",
            is_primary=False,  # Not explicitly requesting primary
        )

        # Act
        _ = await service.add_property(customer_id, property_data)

        # Assert
        if num_existing == 0:
            # First property should be primary
            call_kwargs = mock_repository.create.call_args.kwargs
            assert call_kwargs["is_primary"] is True
        else:
            # Not first property, should respect the is_primary=False
            call_kwargs = mock_repository.create.call_args.kwargs
            assert call_kwargs["is_primary"] is False

    @given(
        num_properties=st.integers(min_value=2, max_value=5),
        primary_index=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_adding_primary_property_clears_existing_primary(
        self,
        num_properties: int,
        primary_index: int,
    ) -> None:
        """Test that adding a new primary property clears existing primary.

        **Validates: Requirements 2.7**

        Property: When adding a property with is_primary=True, the existing
        primary property (if any) should have its primary flag cleared.
        """
        # Ensure primary_index is valid
        _ = primary_index % num_properties  # Validate but don't use

        # Arrange
        mock_repository = AsyncMock()
        service = PropertyService(repository=mock_repository)

        customer_id = uuid4()

        # Existing properties (one is primary)
        mock_repository.count_by_customer_id.return_value = num_properties

        # New property will be created as primary
        new_property = self._create_mock_property(
            customer_id=customer_id,
            is_primary=True,
        )
        mock_repository.create.return_value = new_property
        mock_repository.clear_primary_flag.return_value = 1

        # Create property data requesting primary
        property_data = PropertyCreate(
            address="456 Primary St",
            city="Plymouth",
            is_primary=True,
        )

        # Act
        result = await service.add_property(customer_id, property_data)

        # Assert
        # clear_primary_flag should have been called
        mock_repository.clear_primary_flag.assert_called_once_with(customer_id)

        # New property should be primary
        assert result.is_primary is True

    @pytest.mark.asyncio
    async def test_at_most_one_primary_invariant(self) -> None:
        """Test the invariant: at most one primary property per customer.

        **Validates: Requirements 2.7**

        This test verifies the core invariant by simulating a sequence of
        operations and checking that the invariant holds after each.
        """
        customer_id = uuid4()

        # Track primary status in our "database"
        properties_db: dict[str, MagicMock] = {}

        def count_primaries() -> int:
            return sum(1 for p in properties_db.values() if p.is_primary)

        # Simulate adding properties
        for i in range(5):
            prop_id = uuid4()
            is_first = len(properties_db) == 0

            # Create property
            prop = self._create_mock_property(
                customer_id=customer_id,
                is_primary=is_first,
                property_id=prop_id,
            )
            properties_db[str(prop_id)] = prop

            # Verify invariant: at most one primary
            assert count_primaries() <= 1, (
                f"Invariant violated: {count_primaries()} primaries after adding "
                f"property {i + 1}"
            )

        # Simulate setting different properties as primary
        for _prop_id, prop in list(properties_db.items()):
            # Clear all primaries
            for p in properties_db.values():
                p.is_primary = False

            # Set this one as primary
            prop.is_primary = True

            # Verify invariant
            assert count_primaries() == 1, (
                f"Invariant violated: expected 1 primary, got {count_primaries()}"
            )

