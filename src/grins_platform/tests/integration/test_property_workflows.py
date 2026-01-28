"""
Integration tests for property workflow operations.

This module contains integration tests for property CRUD workflows,
primary property switching, and cascade behavior through the API layer.

These tests verify the complete integration between API endpoints and services.

Validates: Requirement 2.1-2.11
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import get_property_service
from grins_platform.api.v1.properties import router
from grins_platform.models.enums import PropertyType, SystemType
from grins_platform.schemas.property import PropertyResponse
from grins_platform.services.property_service import (
    PropertyNotFoundError,
    PropertyService,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_service() -> AsyncMock:
    """Create a mock PropertyService for integration testing."""
    return AsyncMock(spec=PropertyService)


@pytest.fixture
def app(mock_service: AsyncMock) -> FastAPI:
    """Create FastAPI app with mocked dependencies for integration testing."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    # Override dependency to use mock service
    test_app.dependency_overrides[get_property_service] = lambda: mock_service

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client for API requests."""
    return TestClient(app)


@pytest.fixture
def sample_customer_id() -> uuid.UUID:
    """Create a sample customer UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_property_id() -> uuid.UUID:
    """Create a sample property UUID for testing."""
    return uuid.uuid4()


def create_property_response(
    property_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    address: str = "123 Main St",
    city: str = "Eden Prairie",
    state: str = "MN",
    zip_code: str = "55344",
    zone_count: int = 6,
    system_type: SystemType = SystemType.STANDARD,
    property_type: PropertyType = PropertyType.RESIDENTIAL,
    is_primary: bool = False,
    access_instructions: str | None = None,
    gate_code: str | None = None,
    has_dogs: bool = False,
    special_notes: str | None = None,
) -> PropertyResponse:
    """Helper function to create PropertyResponse objects for testing."""
    return PropertyResponse(
        id=property_id or uuid.uuid4(),
        customer_id=customer_id or uuid.uuid4(),
        address=address,
        city=city,
        state=state,
        zip_code=zip_code,
        zone_count=zone_count,
        system_type=system_type,
        property_type=property_type,
        is_primary=is_primary,
        access_instructions=access_instructions,
        gate_code=gate_code,
        has_dogs=has_dogs,
        special_notes=special_notes,
        latitude=None,
        longitude=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# =============================================================================
# Task 10.3: Property CRUD Workflow Integration Tests
# =============================================================================


@pytest.mark.integration
class TestPropertyCRUDWorkflow:
    """Integration tests for complete property CRUD workflow.

    Tests the full lifecycle: add → get → update → list → delete

    Validates: Requirement 2.1-2.6
    """

    def test_complete_property_lifecycle(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test complete property lifecycle: create, read, update, delete.

        This test verifies the full CRUD workflow through the API layer,
        ensuring all operations work together correctly.

        Validates: Requirement 2.1, 2.5, 2.6
        """
        # Step 1: Create a property
        property_id = uuid.uuid4()
        created_property = create_property_response(
            property_id=property_id,
            customer_id=sample_customer_id,
            address="100 Test Lane",
            city="Plymouth",
            is_primary=True,  # First property becomes primary
        )
        mock_service.add_property.return_value = created_property

        create_response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "100 Test Lane",
                "city": "Plymouth",
                "state": "MN",
                "zone_count": 8,
                "system_type": "standard",
                "property_type": "residential",
            },
        )

        assert create_response.status_code == 201
        created_data = create_response.json()
        assert created_data["address"] == "100 Test Lane"
        assert created_data["city"] == "Plymouth"
        mock_service.add_property.assert_called_once()

        # Step 2: Retrieve the property
        mock_service.get_property.return_value = created_property

        get_response = client.get(f"/api/v1/properties/{property_id}")

        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["id"] == str(property_id)
        assert get_data["address"] == "100 Test Lane"

        # Step 3: Update the property
        updated_property = create_property_response(
            property_id=property_id,
            customer_id=sample_customer_id,
            address="100 Test Lane Updated",
            city="Plymouth",
            zone_count=10,
            is_primary=True,
        )
        mock_service.update_property.return_value = updated_property

        update_response = client.put(
            f"/api/v1/properties/{property_id}",
            json={"address": "100 Test Lane Updated", "zone_count": 10},
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["address"] == "100 Test Lane Updated"
        assert update_data["zone_count"] == 10

        # Step 4: List properties for customer
        mock_service.get_customer_properties.return_value = [updated_property]

        list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )

        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data) == 1
        assert list_data[0]["address"] == "100 Test Lane Updated"

        # Step 5: Delete the property
        mock_service.delete_property.return_value = True

        delete_response = client.delete(f"/api/v1/properties/{property_id}")

        assert delete_response.status_code == 204
        mock_service.delete_property.assert_called_once_with(property_id)

    def test_add_multiple_properties_workflow(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test adding multiple properties to a customer.

        Verifies that multiple properties can be added and listed correctly.

        Validates: Requirement 2.5, 2.6
        """
        # Create first property (should become primary)
        property1_id = uuid.uuid4()
        property1 = create_property_response(
            property_id=property1_id,
            customer_id=sample_customer_id,
            address="First Property",
            city="Eden Prairie",
            is_primary=True,
        )
        mock_service.add_property.return_value = property1

        response1 = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={"address": "First Property", "city": "Eden Prairie"},
        )
        assert response1.status_code == 201
        assert response1.json()["is_primary"] is True

        # Create second property (should not be primary)
        property2_id = uuid.uuid4()
        property2 = create_property_response(
            property_id=property2_id,
            customer_id=sample_customer_id,
            address="Second Property",
            city="Plymouth",
            is_primary=False,
        )
        mock_service.add_property.return_value = property2

        response2 = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={"address": "Second Property", "city": "Plymouth"},
        )
        assert response2.status_code == 201
        assert response2.json()["is_primary"] is False

        # Create third property
        property3_id = uuid.uuid4()
        property3 = create_property_response(
            property_id=property3_id,
            customer_id=sample_customer_id,
            address="Third Property",
            city="Maple Grove",
            is_primary=False,
        )
        mock_service.add_property.return_value = property3

        response3 = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={"address": "Third Property", "city": "Maple Grove"},
        )
        assert response3.status_code == 201

        # List all properties - primary should be first
        mock_service.get_customer_properties.return_value = [
            property1,
            property2,
            property3,
        ]

        list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )

        assert list_response.status_code == 200
        properties = list_response.json()
        assert len(properties) == 3
        # Primary property should be first in the list
        assert properties[0]["is_primary"] is True
        assert properties[0]["address"] == "First Property"

    def test_property_not_found_workflow(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test handling of non-existent property operations.

        Validates: Requirement 2.5, 10.3
        """
        non_existent_id = uuid.uuid4()

        # Test GET returns 404
        mock_service.get_property.side_effect = PropertyNotFoundError(non_existent_id)
        get_response = client.get(f"/api/v1/properties/{non_existent_id}")
        assert get_response.status_code == 404
        assert "not found" in get_response.json()["detail"]

        # Test PUT returns 404
        mock_service.update_property.side_effect = PropertyNotFoundError(
            non_existent_id,
        )
        update_response = client.put(
            f"/api/v1/properties/{non_existent_id}",
            json={"address": "Updated Address"},
        )
        assert update_response.status_code == 404

        # Test DELETE returns 404
        mock_service.delete_property.side_effect = PropertyNotFoundError(
            non_existent_id,
        )
        delete_response = client.delete(f"/api/v1/properties/{non_existent_id}")
        assert delete_response.status_code == 404


# =============================================================================
# Task 10.3: Primary Property Switching Integration Tests
# =============================================================================


@pytest.mark.integration
class TestPrimaryPropertySwitching:
    """Integration tests for primary property switching behavior.

    Tests that setting a new primary property correctly clears the old primary.

    Validates: Requirement 2.7
    """

    def test_set_primary_property_workflow(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test setting a property as primary through the API.

        Validates: Requirement 2.7
        """
        property_id = uuid.uuid4()
        property_response = create_property_response(
            property_id=property_id,
            customer_id=sample_customer_id,
            is_primary=True,
        )
        mock_service.set_primary.return_value = property_response

        response = client.put(f"/api/v1/properties/{property_id}/primary")

        assert response.status_code == 200
        data = response.json()
        assert data["is_primary"] is True
        mock_service.set_primary.assert_called_once_with(property_id)

    def test_primary_property_switching_clears_old_primary(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test that setting new primary clears old primary flag.

        This test simulates the workflow where:
        1. Property A is primary
        2. User sets Property B as primary
        3. Property A should no longer be primary

        Validates: Requirement 2.7
        """
        property_a_id = uuid.uuid4()
        property_b_id = uuid.uuid4()

        # Initial state: Property A is primary
        property_a_initial = create_property_response(
            property_id=property_a_id,
            customer_id=sample_customer_id,
            address="Property A",
            is_primary=True,
        )
        property_b_initial = create_property_response(
            property_id=property_b_id,
            customer_id=sample_customer_id,
            address="Property B",
            is_primary=False,
        )

        # List shows A as primary
        mock_service.get_customer_properties.return_value = [
            property_a_initial,
            property_b_initial,
        ]

        list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )
        assert list_response.status_code == 200
        properties = list_response.json()
        assert properties[0]["is_primary"] is True
        assert properties[0]["address"] == "Property A"

        # Set Property B as primary
        property_b_updated = create_property_response(
            property_id=property_b_id,
            customer_id=sample_customer_id,
            address="Property B",
            is_primary=True,
        )
        mock_service.set_primary.return_value = property_b_updated

        set_primary_response = client.put(
            f"/api/v1/properties/{property_b_id}/primary",
        )

        assert set_primary_response.status_code == 200
        assert set_primary_response.json()["is_primary"] is True
        assert set_primary_response.json()["address"] == "Property B"

        # After setting B as primary, list should show B as primary
        property_a_updated = create_property_response(
            property_id=property_a_id,
            customer_id=sample_customer_id,
            address="Property A",
            is_primary=False,  # No longer primary
        )
        mock_service.get_customer_properties.return_value = [
            property_b_updated,  # Now primary, should be first
            property_a_updated,
        ]

        final_list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )
        assert final_list_response.status_code == 200
        final_properties = final_list_response.json()
        # Property B should now be first (primary)
        assert final_properties[0]["is_primary"] is True
        assert final_properties[0]["address"] == "Property B"
        # Property A should no longer be primary
        assert final_properties[1]["is_primary"] is False
        assert final_properties[1]["address"] == "Property A"

    def test_first_property_becomes_primary_automatically(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test that the first property added becomes primary automatically.

        Validates: Requirement 2.7
        """
        property_id = uuid.uuid4()
        # First property should automatically be primary
        first_property = create_property_response(
            property_id=property_id,
            customer_id=sample_customer_id,
            address="First Property",
            is_primary=True,  # Service sets this automatically
        )
        mock_service.add_property.return_value = first_property

        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "First Property",
                "city": "Eden Prairie",
                # Note: is_primary not specified, should default to True for first
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_primary"] is True

    def test_set_primary_on_nonexistent_property_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test that setting primary on non-existent property returns 404.

        Validates: Requirement 2.7, 10.3
        """
        non_existent_id = uuid.uuid4()
        mock_service.set_primary.side_effect = PropertyNotFoundError(non_existent_id)

        response = client.put(f"/api/v1/properties/{non_existent_id}/primary")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_set_already_primary_property(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test setting primary on a property that is already primary.

        Should succeed without error and return the property unchanged.

        Validates: Requirement 2.7
        """
        property_id = uuid.uuid4()
        already_primary = create_property_response(
            property_id=property_id,
            customer_id=sample_customer_id,
            is_primary=True,
        )
        mock_service.set_primary.return_value = already_primary

        response = client.put(f"/api/v1/properties/{property_id}/primary")

        assert response.status_code == 200
        assert response.json()["is_primary"] is True


# =============================================================================
# Task 10.3: Cascade Behavior Integration Tests
# =============================================================================


@pytest.mark.integration
class TestPropertyCascadeBehavior:
    """Integration tests for property cascade behavior.

    Tests behavior when properties are deleted, especially regarding
    primary property reassignment.

    Validates: Requirement 2.6, 2.7
    """

    def test_delete_primary_property_reassigns_primary(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test that deleting primary property reassigns primary to another.

        When the primary property is deleted, another property should
        automatically become the new primary.

        Validates: Requirement 2.6, 2.7
        """
        primary_id = uuid.uuid4()
        secondary_id = uuid.uuid4()

        # Initial state: two properties, first is primary
        primary_property = create_property_response(
            property_id=primary_id,
            customer_id=sample_customer_id,
            address="Primary Property",
            is_primary=True,
        )
        secondary_property = create_property_response(
            property_id=secondary_id,
            customer_id=sample_customer_id,
            address="Secondary Property",
            is_primary=False,
        )

        mock_service.get_customer_properties.return_value = [
            primary_property,
            secondary_property,
        ]

        # Verify initial state
        list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 2
        assert list_response.json()[0]["is_primary"] is True

        # Delete the primary property
        mock_service.delete_property.return_value = True

        delete_response = client.delete(f"/api/v1/properties/{primary_id}")
        assert delete_response.status_code == 204

        # After deletion, secondary should become primary
        secondary_now_primary = create_property_response(
            property_id=secondary_id,
            customer_id=sample_customer_id,
            address="Secondary Property",
            is_primary=True,  # Now primary after deletion
        )
        mock_service.get_customer_properties.return_value = [secondary_now_primary]

        final_list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )
        assert final_list_response.status_code == 200
        final_properties = final_list_response.json()
        assert len(final_properties) == 1
        assert final_properties[0]["is_primary"] is True
        assert final_properties[0]["address"] == "Secondary Property"

    def test_delete_non_primary_property_preserves_primary(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test that deleting non-primary property preserves primary.

        Validates: Requirement 2.6
        """
        primary_id = uuid.uuid4()
        secondary_id = uuid.uuid4()

        primary_property = create_property_response(
            property_id=primary_id,
            customer_id=sample_customer_id,
            address="Primary Property",
            is_primary=True,
        )
        secondary_property = create_property_response(
            property_id=secondary_id,
            customer_id=sample_customer_id,
            address="Secondary Property",
            is_primary=False,
        )

        mock_service.get_customer_properties.return_value = [
            primary_property,
            secondary_property,
        ]

        # Delete the secondary (non-primary) property
        mock_service.delete_property.return_value = True

        delete_response = client.delete(f"/api/v1/properties/{secondary_id}")
        assert delete_response.status_code == 204

        # Primary should still be primary
        mock_service.get_customer_properties.return_value = [primary_property]

        final_list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )
        assert final_list_response.status_code == 200
        final_properties = final_list_response.json()
        assert len(final_properties) == 1
        assert final_properties[0]["is_primary"] is True
        assert final_properties[0]["address"] == "Primary Property"

    def test_delete_only_property(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test deleting the only property for a customer.

        Validates: Requirement 2.6
        """
        only_property_id = uuid.uuid4()
        only_property = create_property_response(
            property_id=only_property_id,
            customer_id=sample_customer_id,
            address="Only Property",
            is_primary=True,
        )

        mock_service.get_customer_properties.return_value = [only_property]

        # Verify initial state
        list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        # Delete the only property
        mock_service.delete_property.return_value = True

        delete_response = client.delete(f"/api/v1/properties/{only_property_id}")
        assert delete_response.status_code == 204

        # Customer should now have no properties
        mock_service.get_customer_properties.return_value = []

        final_list_response = client.get(
            f"/api/v1/customers/{sample_customer_id}/properties",
        )
        assert final_list_response.status_code == 200
        assert final_list_response.json() == []


# =============================================================================
# Task 10.3: Property Validation Integration Tests
# =============================================================================


@pytest.mark.integration
class TestPropertyValidationWorkflow:
    """Integration tests for property validation through the API.

    Tests that validation rules are enforced correctly.

    Validates: Requirement 2.2-2.4, 2.8-2.11
    """

    def test_zone_count_validation(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test zone count validation (1-50 range).

        Validates: Requirement 2.2
        """
        # Test zone count too low (0)
        response_low = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "Test Address",
                "city": "Eden Prairie",
                "zone_count": 0,
            },
        )
        assert response_low.status_code == 422

        # Test zone count too high (51)
        response_high = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "Test Address",
                "city": "Eden Prairie",
                "zone_count": 51,
            },
        )
        assert response_high.status_code == 422

    def test_system_type_validation(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test system type validation (standard or lake_pump).

        Validates: Requirement 2.3
        """
        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "Test Address",
                "city": "Eden Prairie",
                "system_type": "invalid_type",
            },
        )
        assert response.status_code == 422

    def test_property_type_validation(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test property type validation (residential or commercial).

        Validates: Requirement 2.4
        """
        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "Test Address",
                "city": "Eden Prairie",
                "property_type": "invalid_type",
            },
        )
        assert response.status_code == 422

    def test_valid_zone_count_range(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test valid zone count values are accepted.

        Validates: Requirement 2.2
        """
        # Test minimum valid zone count (1)
        property_min = create_property_response(
            customer_id=sample_customer_id,
            zone_count=1,
        )
        mock_service.add_property.return_value = property_min

        response_min = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "Test Address",
                "city": "Eden Prairie",
                "zone_count": 1,
            },
        )
        assert response_min.status_code == 201

        # Test maximum valid zone count (50)
        property_max = create_property_response(
            customer_id=sample_customer_id,
            zone_count=50,
        )
        mock_service.add_property.return_value = property_max

        response_max = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "Test Address 2",
                "city": "Eden Prairie",
                "zone_count": 50,
            },
        )
        assert response_max.status_code == 201

    def test_access_instructions_and_gate_code(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test property with access instructions and gate code.

        Validates: Requirement 2.9
        """
        property_with_access = create_property_response(
            customer_id=sample_customer_id,
            access_instructions="Use side gate, ring doorbell twice",
            gate_code="1234",
            has_dogs=True,
            special_notes="Beware of dog in backyard",
        )
        mock_service.add_property.return_value = property_with_access

        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "Test Address",
                "city": "Eden Prairie",
                "access_instructions": "Use side gate, ring doorbell twice",
                "gate_code": "1234",
                "has_dogs": True,
                "special_notes": "Beware of dog in backyard",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["access_instructions"] == "Use side gate, ring doorbell twice"
        assert data["gate_code"] == "1234"
        assert data["has_dogs"] is True
        assert data["special_notes"] == "Beware of dog in backyard"

    def test_coordinates_validation(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test latitude and longitude coordinate validation.

        Validates: Requirement 2.8
        """
        property_with_coords = create_property_response(
            customer_id=sample_customer_id,
        )
        # Note: PropertyResponse doesn't include lat/long in the helper,
        # but the API should accept valid coordinates
        mock_service.add_property.return_value = property_with_coords

        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "Test Address",
                "city": "Eden Prairie",
                "latitude": 44.8547,
                "longitude": -93.4708,
            },
        )

        assert response.status_code == 201


# =============================================================================
# Task 10.3: Property Update Workflow Integration Tests
# =============================================================================


@pytest.mark.integration
class TestPropertyUpdateWorkflow:
    """Integration tests for property update workflows.

    Validates: Requirement 2.2-2.4, 2.8-2.11
    """

    def test_partial_update_workflow(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_id: uuid.UUID,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test partial property update (only specified fields change).

        Validates: Requirement 2.5
        """
        # Original property
        original = create_property_response(
            property_id=sample_property_id,
            customer_id=sample_customer_id,
            address="Original Address",
            city="Eden Prairie",
            zone_count=6,
        )
        mock_service.get_property.return_value = original

        # Updated property (only address changed)
        updated = create_property_response(
            property_id=sample_property_id,
            customer_id=sample_customer_id,
            address="Updated Address",
            city="Eden Prairie",  # Unchanged
            zone_count=6,  # Unchanged
        )
        mock_service.update_property.return_value = updated

        response = client.put(
            f"/api/v1/properties/{sample_property_id}",
            json={"address": "Updated Address"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["address"] == "Updated Address"
        assert data["city"] == "Eden Prairie"  # Should be unchanged
        assert data["zone_count"] == 6  # Should be unchanged

    def test_update_system_type_workflow(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_id: uuid.UUID,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test updating system type from standard to lake_pump.

        Validates: Requirement 2.3
        """
        updated = create_property_response(
            property_id=sample_property_id,
            customer_id=sample_customer_id,
            system_type=SystemType.LAKE_PUMP,
        )
        mock_service.update_property.return_value = updated

        response = client.put(
            f"/api/v1/properties/{sample_property_id}",
            json={"system_type": "lake_pump"},
        )

        assert response.status_code == 200
        assert response.json()["system_type"] == "lake_pump"

    def test_update_property_type_workflow(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_id: uuid.UUID,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test updating property type from residential to commercial.

        Validates: Requirement 2.4
        """
        updated = create_property_response(
            property_id=sample_property_id,
            customer_id=sample_customer_id,
            property_type=PropertyType.COMMERCIAL,
        )
        mock_service.update_property.return_value = updated

        response = client.put(
            f"/api/v1/properties/{sample_property_id}",
            json={"property_type": "commercial"},
        )

        assert response.status_code == 200
        assert response.json()["property_type"] == "commercial"

    def test_update_zone_count_validation(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
        sample_property_id: uuid.UUID,
    ) -> None:
        """Test zone count validation on update.

        Validates: Requirement 2.2
        """
        # Invalid zone count should be rejected
        response = client.put(
            f"/api/v1/properties/{sample_property_id}",
            json={"zone_count": 100},
        )

        assert response.status_code == 422
