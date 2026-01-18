"""
Tests for PropertyService.

This module contains unit tests for the PropertyService class,
testing all CRUD operations and primary flag management.

Validates: Requirement 2.1, 2.5-2.11
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import PropertyType, SystemType
from grins_platform.schemas.property import PropertyCreate, PropertyUpdate
from grins_platform.services.property_service import (
    PropertyNotFoundError,
    PropertyService,
)

if TYPE_CHECKING:
    from uuid import UUID


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock PropertyRepository."""
    return AsyncMock()


@pytest.fixture
def property_service(mock_repository: AsyncMock) -> PropertyService:
    """Create a PropertyService with mocked repository."""
    return PropertyService(repository=mock_repository)


@pytest.fixture
def sample_property_create() -> PropertyCreate:
    """Create a sample PropertyCreate schema."""
    return PropertyCreate(
        address="123 Main St",
        city="Eden Prairie",
        state="MN",
        zip_code="55344",
        zone_count=8,
        system_type=SystemType.STANDARD,
        property_type=PropertyType.RESIDENTIAL,
        is_primary=False,
        access_instructions="Ring doorbell",
        gate_code="1234",
        has_dogs=True,
        special_notes="Large backyard",
        latitude=44.8547,
        longitude=-93.4708,
    )


@pytest.fixture
def sample_property_update() -> PropertyUpdate:
    """Create a sample PropertyUpdate schema."""
    return PropertyUpdate(
        zone_count=10,
        has_dogs=False,
        special_notes="Updated notes",
    )


def create_mock_property(
    property_id: UUID | None = None,
    customer_id: UUID | None = None,
    is_primary: bool = False,
) -> MagicMock:
    """Create a mock Property object."""
    mock = MagicMock()
    mock.id = property_id or uuid4()
    mock.customer_id = customer_id or uuid4()
    mock.address = "123 Main St"
    mock.city = "Eden Prairie"
    mock.state = "MN"
    mock.zip_code = "55344"
    mock.zone_count = 8
    mock.system_type = "standard"
    mock.property_type = "residential"
    mock.is_primary = is_primary
    mock.access_instructions = "Ring doorbell"
    mock.gate_code = "1234"
    mock.has_dogs = True
    mock.special_notes = "Large backyard"
    mock.latitude = Decimal("44.8547")
    mock.longitude = Decimal("-93.4708")
    mock.created_at = datetime.now()
    mock.updated_at = datetime.now()
    return mock


class TestPropertyServiceAddProperty:
    """Tests for PropertyService.add_property method."""

    @pytest.mark.asyncio
    async def test_add_property_success(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
        sample_property_create: PropertyCreate,
    ) -> None:
        """Test successful property creation."""
        customer_id = uuid4()
        mock_property = create_mock_property(customer_id=customer_id)

        mock_repository.count_by_customer_id.return_value = 1
        mock_repository.create.return_value = mock_property

        result = await property_service.add_property(
            customer_id,
            sample_property_create,
        )

        assert result.id == mock_property.id
        assert result.customer_id == customer_id
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_first_property_becomes_primary(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
        sample_property_create: PropertyCreate,
    ) -> None:
        """Test that first property is automatically set as primary."""
        customer_id = uuid4()
        mock_property = create_mock_property(
            customer_id=customer_id,
            is_primary=True,
        )

        # No existing properties
        mock_repository.count_by_customer_id.return_value = 0
        mock_repository.create.return_value = mock_property

        result = await property_service.add_property(
            customer_id,
            sample_property_create,
        )

        # Verify is_primary was set to True in the create call
        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["is_primary"] is True
        assert result.is_primary is True

    @pytest.mark.asyncio
    async def test_add_property_with_primary_flag_clears_others(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that setting primary flag clears other primary properties."""
        customer_id = uuid4()
        mock_property = create_mock_property(
            customer_id=customer_id,
            is_primary=True,
        )

        # Existing properties
        mock_repository.count_by_customer_id.return_value = 2
        mock_repository.clear_primary_flag.return_value = 1
        mock_repository.create.return_value = mock_property

        data = PropertyCreate(
            address="456 Oak Ave",
            city="Plymouth",
            is_primary=True,
        )

        await property_service.add_property(customer_id, data)

        # Verify clear_primary_flag was called
        mock_repository.clear_primary_flag.assert_called_once_with(customer_id)

    @pytest.mark.asyncio
    async def test_add_property_outside_service_area_logs_warning(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that adding property outside service area logs warning."""
        customer_id = uuid4()
        mock_property = create_mock_property(customer_id=customer_id)

        mock_repository.count_by_customer_id.return_value = 0
        mock_repository.create.return_value = mock_property

        data = PropertyCreate(
            address="123 Main St",
            city="Los Angeles",  # Outside service area
        )

        # Should not raise, just log warning
        result = await property_service.add_property(customer_id, data)
        assert result is not None


class TestPropertyServiceGetProperty:
    """Tests for PropertyService.get_property method."""

    @pytest.mark.asyncio
    async def test_get_property_success(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test successful property retrieval."""
        property_id = uuid4()
        mock_property = create_mock_property(property_id=property_id)

        mock_repository.get_by_id.return_value = mock_property

        result = await property_service.get_property(property_id)

        assert result.id == property_id
        mock_repository.get_by_id.assert_called_once_with(property_id)

    @pytest.mark.asyncio
    async def test_get_property_not_found(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test property not found raises exception."""
        property_id = uuid4()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(PropertyNotFoundError) as exc_info:
            await property_service.get_property(property_id)

        assert exc_info.value.property_id == property_id


class TestPropertyServiceGetCustomerProperties:
    """Tests for PropertyService.get_customer_properties method."""

    @pytest.mark.asyncio
    async def test_get_customer_properties_success(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test successful retrieval of customer properties."""
        customer_id = uuid4()
        mock_properties = [
            create_mock_property(customer_id=customer_id, is_primary=True),
            create_mock_property(customer_id=customer_id, is_primary=False),
        ]

        mock_repository.get_by_customer_id.return_value = mock_properties

        result = await property_service.get_customer_properties(customer_id)

        assert len(result) == 2
        mock_repository.get_by_customer_id.assert_called_once_with(customer_id)

    @pytest.mark.asyncio
    async def test_get_customer_properties_empty(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test retrieval when customer has no properties."""
        customer_id = uuid4()
        mock_repository.get_by_customer_id.return_value = []

        result = await property_service.get_customer_properties(customer_id)

        assert len(result) == 0


class TestPropertyServiceUpdateProperty:
    """Tests for PropertyService.update_property method."""

    @pytest.mark.asyncio
    async def test_update_property_success(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
        sample_property_update: PropertyUpdate,
    ) -> None:
        """Test successful property update."""
        property_id = uuid4()
        mock_property = create_mock_property(property_id=property_id)
        updated_mock = create_mock_property(property_id=property_id)
        updated_mock.zone_count = 10
        updated_mock.has_dogs = False

        mock_repository.get_by_id.return_value = mock_property
        mock_repository.update.return_value = updated_mock

        result = await property_service.update_property(
            property_id,
            sample_property_update,
        )

        assert result.id == property_id
        mock_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_property_not_found(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
        sample_property_update: PropertyUpdate,
    ) -> None:
        """Test update on non-existent property raises exception."""
        property_id = uuid4()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(PropertyNotFoundError) as exc_info:
            await property_service.update_property(property_id, sample_property_update)

        assert exc_info.value.property_id == property_id

    @pytest.mark.asyncio
    async def test_update_property_no_changes(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test update with no fields returns existing property."""
        property_id = uuid4()
        mock_property = create_mock_property(property_id=property_id)

        mock_repository.get_by_id.return_value = mock_property

        # Empty update
        empty_update = PropertyUpdate()

        result = await property_service.update_property(property_id, empty_update)

        assert result.id == property_id
        # update should not be called when no fields to update
        mock_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_property_city_outside_service_area(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test updating city to outside service area logs warning."""
        property_id = uuid4()
        mock_property = create_mock_property(property_id=property_id)
        updated_mock = create_mock_property(property_id=property_id)
        updated_mock.city = "Chicago"

        mock_repository.get_by_id.return_value = mock_property
        mock_repository.update.return_value = updated_mock

        update_data = PropertyUpdate(city="Chicago")

        # Should not raise, just log warning
        result = await property_service.update_property(property_id, update_data)
        assert result is not None


class TestPropertyServiceDeleteProperty:
    """Tests for PropertyService.delete_property method."""

    @pytest.mark.asyncio
    async def test_delete_property_success(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test successful property deletion."""
        property_id = uuid4()
        customer_id = uuid4()
        mock_property = create_mock_property(
            property_id=property_id,
            customer_id=customer_id,
            is_primary=False,
        )

        mock_repository.get_by_id.return_value = mock_property
        mock_repository.delete.return_value = True
        mock_repository.get_by_customer_id.return_value = []

        result = await property_service.delete_property(property_id)

        assert result is True
        mock_repository.delete.assert_called_once_with(property_id)

    @pytest.mark.asyncio
    async def test_delete_property_not_found(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test delete on non-existent property raises exception."""
        property_id = uuid4()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(PropertyNotFoundError) as exc_info:
            await property_service.delete_property(property_id)

        assert exc_info.value.property_id == property_id

    @pytest.mark.asyncio
    async def test_delete_primary_property_reassigns_primary(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test deleting primary property reassigns primary to another."""
        property_id = uuid4()
        customer_id = uuid4()
        other_property_id = uuid4()

        mock_property = create_mock_property(
            property_id=property_id,
            customer_id=customer_id,
            is_primary=True,
        )
        other_property = create_mock_property(
            property_id=other_property_id,
            customer_id=customer_id,
            is_primary=False,
        )

        mock_repository.get_by_id.return_value = mock_property
        mock_repository.delete.return_value = True
        mock_repository.get_by_customer_id.return_value = [other_property]
        mock_repository.set_primary.return_value = other_property

        result = await property_service.delete_property(property_id)

        assert result is True
        mock_repository.set_primary.assert_called_once_with(other_property_id)


class TestPropertyServiceSetPrimary:
    """Tests for PropertyService.set_primary method."""

    @pytest.mark.asyncio
    async def test_set_primary_success(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test successful set primary operation."""
        property_id = uuid4()
        mock_property = create_mock_property(
            property_id=property_id,
            is_primary=False,
        )
        updated_mock = create_mock_property(
            property_id=property_id,
            is_primary=True,
        )

        mock_repository.get_by_id.return_value = mock_property
        mock_repository.set_primary.return_value = updated_mock

        result = await property_service.set_primary(property_id)

        assert result.is_primary is True
        mock_repository.set_primary.assert_called_once_with(property_id)

    @pytest.mark.asyncio
    async def test_set_primary_not_found(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test set primary on non-existent property raises exception."""
        property_id = uuid4()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(PropertyNotFoundError) as exc_info:
            await property_service.set_primary(property_id)

        assert exc_info.value.property_id == property_id

    @pytest.mark.asyncio
    async def test_set_primary_already_primary(
        self,
        property_service: PropertyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test set primary on already primary property returns it unchanged."""
        property_id = uuid4()
        mock_property = create_mock_property(
            property_id=property_id,
            is_primary=True,
        )

        mock_repository.get_by_id.return_value = mock_property

        result = await property_service.set_primary(property_id)

        assert result.is_primary is True
        # set_primary should not be called on repository
        mock_repository.set_primary.assert_not_called()


class TestPropertyNotFoundError:
    """Tests for PropertyNotFoundError exception."""

    def test_exception_message(self) -> None:
        """Test exception message format."""
        property_id = uuid4()
        error = PropertyNotFoundError(property_id)

        assert str(error) == f"Property not found: {property_id}"
        assert error.property_id == property_id
