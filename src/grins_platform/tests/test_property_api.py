"""
Tests for Property API endpoints.

This module contains unit tests for the property CRUD API endpoints,
testing all HTTP methods, validation, error handling, and primary flag behavior.

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
    """Create a mock PropertyService."""
    return AsyncMock(spec=PropertyService)


@pytest.fixture
def app(mock_service: AsyncMock) -> FastAPI:
    """Create FastAPI app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Override dependency
    app.dependency_overrides[get_property_service] = lambda: mock_service

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_customer_id() -> uuid.UUID:
    """Create a sample customer UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_property_response(sample_customer_id: uuid.UUID) -> PropertyResponse:
    """Create a sample PropertyResponse."""
    return PropertyResponse(
        id=uuid.uuid4(),
        customer_id=sample_customer_id,
        address="123 Main St",
        city="Eden Prairie",
        state="MN",
        zip_code="55344",
        zone_count=6,
        system_type=SystemType.STANDARD,
        property_type=PropertyType.RESIDENTIAL,
        is_primary=True,
        access_instructions="Use side gate",
        gate_code="1234",
        has_dogs=False,
        special_notes="Nice lawn",
        latitude=None,
        longitude=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# =============================================================================
# Task 9.1 Tests: POST /api/v1/customers/{customer_id}/properties
# =============================================================================


class TestAddProperty:
    """Tests for POST /api/v1/customers/{customer_id}/properties endpoint."""

    def test_add_property_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test successful property creation returns 201."""
        mock_service.add_property.return_value = sample_property_response

        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "123 Main St",
                "city": "Eden Prairie",
                "state": "MN",
                "zip_code": "55344",
                "zone_count": 6,
                "system_type": "standard",
                "property_type": "residential",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["address"] == "123 Main St"
        assert data["city"] == "Eden Prairie"
        mock_service.add_property.assert_called_once()

    def test_add_property_with_primary_flag(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test adding property with is_primary flag."""
        mock_service.add_property.return_value = sample_property_response

        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "123 Main St",
                "city": "Eden Prairie",
                "is_primary": True,
            },
        )

        assert response.status_code == 201
        mock_service.add_property.assert_called_once()

    def test_add_property_missing_required_fields_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test missing required fields returns 422."""
        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "123 Main St",
                # Missing city
            },
        )

        assert response.status_code == 422

    def test_add_property_invalid_zone_count_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test invalid zone count returns 422."""
        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "123 Main St",
                "city": "Eden Prairie",
                "zone_count": 100,  # Max is 50
            },
        )

        assert response.status_code == 422

    def test_add_property_with_special_instructions(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test adding property with special instructions."""
        mock_service.add_property.return_value = sample_property_response

        response = client.post(
            f"/api/v1/customers/{sample_customer_id}/properties",
            json={
                "address": "123 Main St",
                "city": "Eden Prairie",
                "special_instructions": "Gate code: 1234, dog in backyard",
            },
        )

        assert response.status_code == 201


# =============================================================================
# Task 9.2 Tests: GET /api/v1/customers/{customer_id}/properties
# =============================================================================


class TestListCustomerProperties:
    """Tests for GET /api/v1/customers/{customer_id}/properties endpoint."""

    def test_list_properties_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test successful property listing returns 200."""
        mock_service.get_customer_properties.return_value = [sample_property_response]

        response = client.get(f"/api/v1/customers/{sample_customer_id}/properties")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["address"] == "123 Main St"

    def test_list_properties_empty(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Test listing properties for customer with no properties."""
        mock_service.get_customer_properties.return_value = []

        response = client.get(f"/api/v1/customers/{sample_customer_id}/properties")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_properties_multiple(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test listing multiple properties."""
        property2 = PropertyResponse(
            id=uuid.uuid4(),
            customer_id=sample_customer_id,
            address="456 Oak Ave",
            city="Plymouth",
            state="MN",
            zip_code="55441",
            zone_count=4,
            system_type=SystemType.STANDARD,
            property_type=PropertyType.RESIDENTIAL,
            is_primary=False,
            access_instructions=None,
            gate_code=None,
            has_dogs=True,
            special_notes=None,
            latitude=None,
            longitude=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_service.get_customer_properties.return_value = [
            sample_property_response,
            property2,
        ]

        response = client.get(f"/api/v1/customers/{sample_customer_id}/properties")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Primary should be first
        assert data[0]["is_primary"] is True


# =============================================================================
# Task 9.3 Tests: GET /api/v1/properties/{id}
# =============================================================================


class TestGetProperty:
    """Tests for GET /api/v1/properties/{id} endpoint."""

    def test_get_property_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test successful property retrieval returns 200."""
        mock_service.get_property.return_value = sample_property_response

        response = client.get(f"/api/v1/properties/{sample_property_response.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["address"] == "123 Main St"
        assert data["city"] == "Eden Prairie"

    def test_get_property_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test non-existent property returns 404."""
        property_id = uuid.uuid4()
        mock_service.get_property.side_effect = PropertyNotFoundError(property_id)

        response = client.get(f"/api/v1/properties/{property_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_property_invalid_uuid_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid UUID format returns 422."""
        response = client.get("/api/v1/properties/not-a-uuid")

        assert response.status_code == 422


# =============================================================================
# Task 9.4 Tests: PUT /api/v1/properties/{id}
# =============================================================================


class TestUpdateProperty:
    """Tests for PUT /api/v1/properties/{id} endpoint."""

    def test_update_property_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test successful property update returns 200."""
        updated_response = PropertyResponse(
            id=sample_property_response.id,
            customer_id=sample_property_response.customer_id,
            address="456 Updated St",  # Updated
            city=sample_property_response.city,
            state=sample_property_response.state,
            zip_code=sample_property_response.zip_code,
            zone_count=sample_property_response.zone_count,
            system_type=sample_property_response.system_type,
            property_type=sample_property_response.property_type,
            is_primary=sample_property_response.is_primary,
            access_instructions=sample_property_response.access_instructions,
            gate_code=sample_property_response.gate_code,
            has_dogs=sample_property_response.has_dogs,
            special_notes=sample_property_response.special_notes,
            latitude=sample_property_response.latitude,
            longitude=sample_property_response.longitude,
            created_at=sample_property_response.created_at,
            updated_at=datetime.now(),
        )
        mock_service.update_property.return_value = updated_response

        response = client.put(
            f"/api/v1/properties/{sample_property_response.id}",
            json={"address": "456 Updated St"},
        )

        assert response.status_code == 200
        assert response.json()["address"] == "456 Updated St"

    def test_update_property_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test updating non-existent property returns 404."""
        property_id = uuid.uuid4()
        mock_service.update_property.side_effect = PropertyNotFoundError(property_id)

        response = client.put(
            f"/api/v1/properties/{property_id}",
            json={"address": "456 Updated St"},
        )

        assert response.status_code == 404

    def test_update_property_zone_count(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test updating zone count."""
        updated_response = PropertyResponse(
            id=sample_property_response.id,
            customer_id=sample_property_response.customer_id,
            address=sample_property_response.address,
            city=sample_property_response.city,
            state=sample_property_response.state,
            zip_code=sample_property_response.zip_code,
            zone_count=10,  # Updated
            system_type=sample_property_response.system_type,
            property_type=sample_property_response.property_type,
            is_primary=sample_property_response.is_primary,
            access_instructions=sample_property_response.access_instructions,
            gate_code=sample_property_response.gate_code,
            has_dogs=sample_property_response.has_dogs,
            special_notes=sample_property_response.special_notes,
            latitude=sample_property_response.latitude,
            longitude=sample_property_response.longitude,
            created_at=sample_property_response.created_at,
            updated_at=datetime.now(),
        )
        mock_service.update_property.return_value = updated_response

        response = client.put(
            f"/api/v1/properties/{sample_property_response.id}",
            json={"zone_count": 10},
        )

        assert response.status_code == 200
        assert response.json()["zone_count"] == 10

    def test_update_property_invalid_zone_count_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test invalid zone count update returns 422."""
        response = client.put(
            f"/api/v1/properties/{sample_property_response.id}",
            json={"zone_count": 100},  # Max is 50
        )

        assert response.status_code == 422

    def test_update_property_system_type(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test updating system type."""
        updated_response = PropertyResponse(
            id=sample_property_response.id,
            customer_id=sample_property_response.customer_id,
            address=sample_property_response.address,
            city=sample_property_response.city,
            state=sample_property_response.state,
            zip_code=sample_property_response.zip_code,
            zone_count=sample_property_response.zone_count,
            system_type=SystemType.LAKE_PUMP,  # Updated
            property_type=sample_property_response.property_type,
            is_primary=sample_property_response.is_primary,
            access_instructions=sample_property_response.access_instructions,
            gate_code=sample_property_response.gate_code,
            has_dogs=sample_property_response.has_dogs,
            special_notes=sample_property_response.special_notes,
            latitude=sample_property_response.latitude,
            longitude=sample_property_response.longitude,
            created_at=sample_property_response.created_at,
            updated_at=datetime.now(),
        )
        mock_service.update_property.return_value = updated_response

        response = client.put(
            f"/api/v1/properties/{sample_property_response.id}",
            json={"system_type": "lake_pump"},
        )

        assert response.status_code == 200
        assert response.json()["system_type"] == "lake_pump"


# =============================================================================
# Task 9.5 Tests: DELETE /api/v1/properties/{id}
# =============================================================================


class TestDeleteProperty:
    """Tests for DELETE /api/v1/properties/{id} endpoint."""

    def test_delete_property_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test successful property deletion returns 204."""
        mock_service.delete_property.return_value = None

        response = client.delete(f"/api/v1/properties/{sample_property_response.id}")

        assert response.status_code == 204
        assert response.content == b""  # No content

    def test_delete_property_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test deleting non-existent property returns 404."""
        property_id = uuid.uuid4()
        mock_service.delete_property.side_effect = PropertyNotFoundError(property_id)

        response = client.delete(f"/api/v1/properties/{property_id}")

        assert response.status_code == 404


# =============================================================================
# Task 9.6 Tests: PUT /api/v1/properties/{id}/primary
# =============================================================================


class TestSetPrimaryProperty:
    """Tests for PUT /api/v1/properties/{id}/primary endpoint."""

    def test_set_primary_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test successful set primary returns 200."""
        mock_service.set_primary.return_value = sample_property_response

        response = client.put(
            f"/api/v1/properties/{sample_property_response.id}/primary",
        )

        assert response.status_code == 200
        assert response.json()["is_primary"] is True

    def test_set_primary_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test setting primary on non-existent property returns 404."""
        property_id = uuid.uuid4()
        mock_service.set_primary.side_effect = PropertyNotFoundError(property_id)

        response = client.put(f"/api/v1/properties/{property_id}/primary")

        assert response.status_code == 404

    def test_set_primary_clears_other_primary(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_property_response: PropertyResponse,
    ) -> None:
        """Test that setting primary clears other primary flags."""
        # This is tested at the service level, but we verify the endpoint works
        mock_service.set_primary.return_value = sample_property_response

        response = client.put(
            f"/api/v1/properties/{sample_property_response.id}/primary",
        )

        assert response.status_code == 200
        mock_service.set_primary.assert_called_once_with(sample_property_response.id)
