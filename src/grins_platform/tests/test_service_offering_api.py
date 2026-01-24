"""
Tests for Service Offering API endpoints.

This module contains unit tests for the service offering CRUD API endpoints,
testing all HTTP methods, validation, error handling, and pagination.

Validates: Requirement 1.1-1.13, 12.1-12.7
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import get_service_offering_service
from grins_platform.api.v1.services import router
from grins_platform.exceptions import ServiceOfferingNotFoundError
from grins_platform.models.enums import PricingModel, ServiceCategory
from grins_platform.schemas.service_offering import ServiceOfferingResponse
from grins_platform.services.service_offering_service import ServiceOfferingService

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_service() -> AsyncMock:
    """Create a mock ServiceOfferingService."""
    return AsyncMock(spec=ServiceOfferingService)


@pytest.fixture
def app(mock_service: AsyncMock) -> FastAPI:
    """Create FastAPI app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/services")

    # Override dependency
    app.dependency_overrides[get_service_offering_service] = lambda: mock_service

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_service_response() -> ServiceOfferingResponse:
    """Create a sample ServiceOfferingResponse."""
    return ServiceOfferingResponse(
        id=uuid.uuid4(),
        name="Spring Startup",
        category=ServiceCategory.SEASONAL,
        description="Spring irrigation system startup service",
        base_price=Decimal("75.00"),
        price_per_zone=Decimal("10.00"),
        pricing_model=PricingModel.ZONE_BASED,
        estimated_duration_minutes=45,
        duration_per_zone_minutes=5,
        staffing_required=1,
        equipment_required=["standard_tools"],
        buffer_minutes=10,
        lien_eligible=False,
        requires_prepay=False,
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_service_list(
    sample_service_response: ServiceOfferingResponse,
) -> list[ServiceOfferingResponse]:
    """Create a list of sample ServiceOfferingResponse objects."""
    service2 = ServiceOfferingResponse(
        id=uuid.uuid4(),
        name="Winterization",
        category=ServiceCategory.SEASONAL,
        description="Fall winterization service",
        base_price=Decimal("85.00"),
        price_per_zone=Decimal("12.00"),
        pricing_model=PricingModel.ZONE_BASED,
        estimated_duration_minutes=60,
        duration_per_zone_minutes=7,
        staffing_required=1,
        equipment_required=["compressor"],
        buffer_minutes=10,
        lien_eligible=False,
        requires_prepay=False,
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    return [sample_service_response, service2]


# =============================================================================
# Task 11.5 Tests: POST /api/v1/services - Create Service
# =============================================================================


@pytest.mark.unit
class TestCreateService:
    """Tests for POST /api/v1/services endpoint."""

    def test_create_service_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test successful service creation returns 201."""
        mock_service.create_service.return_value = sample_service_response

        response = client.post(
            "/api/v1/services",
            json={
                "name": "Spring Startup",
                "category": "seasonal",
                "description": "Spring irrigation system startup service",
                "base_price": "75.00",
                "price_per_zone": "10.00",
                "pricing_model": "zone_based",
                "estimated_duration_minutes": 45,
                "duration_per_zone_minutes": 5,
                "staffing_required": 1,
                "equipment_required": ["standard_tools"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Spring Startup"
        assert data["category"] == "seasonal"
        assert data["pricing_model"] == "zone_based"
        mock_service.create_service.assert_called_once()

    def test_create_service_minimal_fields(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test service creation with only required fields."""
        mock_service.create_service.return_value = sample_service_response

        response = client.post(
            "/api/v1/services",
            json={
                "name": "Basic Service",
                "category": "repair",
                "pricing_model": "flat",
            },
        )

        assert response.status_code == 201
        mock_service.create_service.assert_called_once()

    def test_create_service_invalid_category_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid category returns 422."""
        response = client.post(
            "/api/v1/services",
            json={
                "name": "Test Service",
                "category": "invalid_category",
                "pricing_model": "flat",
            },
        )

        assert response.status_code == 422

    def test_create_service_invalid_pricing_model_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid pricing model returns 422."""
        response = client.post(
            "/api/v1/services",
            json={
                "name": "Test Service",
                "category": "seasonal",
                "pricing_model": "invalid_model",
            },
        )

        assert response.status_code == 422

    def test_create_service_missing_required_fields_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test missing required fields returns 422."""
        response = client.post(
            "/api/v1/services",
            json={
                "name": "Test Service",
                # Missing category and pricing_model
            },
        )

        assert response.status_code == 422

    def test_create_service_negative_price_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test negative price returns 422."""
        response = client.post(
            "/api/v1/services",
            json={
                "name": "Test Service",
                "category": "seasonal",
                "pricing_model": "flat",
                "base_price": "-10.00",
            },
        )

        assert response.status_code == 422

    def test_create_service_negative_duration_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test negative duration returns 422."""
        response = client.post(
            "/api/v1/services",
            json={
                "name": "Test Service",
                "category": "seasonal",
                "pricing_model": "flat",
                "estimated_duration_minutes": -30,
            },
        )

        assert response.status_code == 422

    def test_create_service_zero_staffing_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test zero staffing required returns 422."""
        response = client.post(
            "/api/v1/services",
            json={
                "name": "Test Service",
                "category": "seasonal",
                "pricing_model": "flat",
                "staffing_required": 0,
            },
        )

        assert response.status_code == 422


# =============================================================================
# Task 11.3 Tests: GET /api/v1/services/{id} - Get Service by ID
# =============================================================================


@pytest.mark.unit
class TestGetService:
    """Tests for GET /api/v1/services/{id} endpoint."""

    def test_get_service_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test successful service retrieval returns 200."""
        mock_service.get_service.return_value = sample_service_response

        response = client.get(f"/api/v1/services/{sample_service_response.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Spring Startup"
        assert data["category"] == "seasonal"
        assert data["pricing_model"] == "zone_based"
        assert "equipment_required" in data

    def test_get_service_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test non-existent service returns 404."""
        service_id = uuid.uuid4()
        mock_service.get_service.side_effect = ServiceOfferingNotFoundError(service_id)

        response = client.get(f"/api/v1/services/{service_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_service_invalid_uuid_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid UUID format returns 422."""
        response = client.get("/api/v1/services/not-a-uuid")

        assert response.status_code == 422


# =============================================================================
# Task 11.6 Tests: PUT /api/v1/services/{id} - Update Service
# =============================================================================


@pytest.mark.unit
class TestUpdateService:
    """Tests for PUT /api/v1/services/{id} endpoint."""

    def test_update_service_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test successful service update returns 200."""
        updated_response = ServiceOfferingResponse(
            id=sample_service_response.id,
            name="Updated Spring Startup",
            category=sample_service_response.category,
            description=sample_service_response.description,
            base_price=Decimal("85.00"),  # Updated
            price_per_zone=sample_service_response.price_per_zone,
            pricing_model=sample_service_response.pricing_model,
            estimated_duration_minutes=sample_service_response.estimated_duration_minutes,
            duration_per_zone_minutes=sample_service_response.duration_per_zone_minutes,
            staffing_required=sample_service_response.staffing_required,
            equipment_required=sample_service_response.equipment_required,
            buffer_minutes=sample_service_response.buffer_minutes,
            lien_eligible=sample_service_response.lien_eligible,
            requires_prepay=sample_service_response.requires_prepay,
            is_active=sample_service_response.is_active,
            created_at=sample_service_response.created_at,
            updated_at=datetime.now(),
        )
        mock_service.update_service.return_value = updated_response

        response = client.put(
            f"/api/v1/services/{sample_service_response.id}",
            json={"name": "Updated Spring Startup", "base_price": "85.00"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Spring Startup"
        assert data["base_price"] == "85.00"

    def test_update_service_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test updating non-existent service returns 404."""
        service_id = uuid.uuid4()
        mock_service.update_service.side_effect = ServiceOfferingNotFoundError(
            service_id,
        )

        response = client.put(
            f"/api/v1/services/{service_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404

    def test_update_service_partial_update(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test partial service update (only some fields)."""
        mock_service.update_service.return_value = sample_service_response

        response = client.put(
            f"/api/v1/services/{sample_service_response.id}",
            json={"description": "Updated description only"},
        )

        assert response.status_code == 200
        mock_service.update_service.assert_called_once()

    def test_update_service_deactivate(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test deactivating service via update."""
        deactivated_response = ServiceOfferingResponse(
            id=sample_service_response.id,
            name=sample_service_response.name,
            category=sample_service_response.category,
            description=sample_service_response.description,
            base_price=sample_service_response.base_price,
            price_per_zone=sample_service_response.price_per_zone,
            pricing_model=sample_service_response.pricing_model,
            estimated_duration_minutes=sample_service_response.estimated_duration_minutes,
            duration_per_zone_minutes=sample_service_response.duration_per_zone_minutes,
            staffing_required=sample_service_response.staffing_required,
            equipment_required=sample_service_response.equipment_required,
            buffer_minutes=sample_service_response.buffer_minutes,
            lien_eligible=sample_service_response.lien_eligible,
            requires_prepay=sample_service_response.requires_prepay,
            is_active=False,  # Deactivated
            created_at=sample_service_response.created_at,
            updated_at=datetime.now(),
        )
        mock_service.update_service.return_value = deactivated_response

        response = client.put(
            f"/api/v1/services/{sample_service_response.id}",
            json={"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False


# =============================================================================
# Task 11.7 Tests: DELETE /api/v1/services/{id} - Deactivate Service
# =============================================================================


@pytest.mark.unit
class TestDeleteService:
    """Tests for DELETE /api/v1/services/{id} endpoint."""

    def test_delete_service_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test successful service deactivation returns 204."""
        mock_service.deactivate_service.return_value = None

        response = client.delete(f"/api/v1/services/{sample_service_response.id}")

        assert response.status_code == 204
        assert response.content == b""  # No content
        mock_service.deactivate_service.assert_called_once()

    def test_delete_service_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test deleting non-existent service returns 404."""
        service_id = uuid.uuid4()
        mock_service.deactivate_service.side_effect = ServiceOfferingNotFoundError(
            service_id,
        )

        response = client.delete(f"/api/v1/services/{service_id}")

        assert response.status_code == 404


# =============================================================================
# Task 11.2 Tests: GET /api/v1/services - List Services
# =============================================================================


@pytest.mark.unit
class TestListServices:
    """Tests for GET /api/v1/services endpoint."""

    def test_list_services_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test successful service listing returns 200."""
        mock_service.list_services.return_value = ([sample_service_response], 1)

        response = client.get("/api/v1/services")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Spring Startup"

    def test_list_services_with_pagination(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_list: list[ServiceOfferingResponse],
    ) -> None:
        """Test service listing with pagination parameters."""
        mock_service.list_services.return_value = (sample_service_list, 50)

        response = client.get(
            "/api/v1/services",
            params={"page": 2, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total"] == 50
        assert data["total_pages"] == 5

    def test_list_services_with_category_filter(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test service listing with category filter."""
        mock_service.list_services.return_value = ([sample_service_response], 1)

        response = client.get(
            "/api/v1/services",
            params={"category": "seasonal"},
        )

        assert response.status_code == 200
        mock_service.list_services.assert_called_once()
        call_kwargs = mock_service.list_services.call_args.kwargs
        assert call_kwargs["category"] == ServiceCategory.SEASONAL

    def test_list_services_with_is_active_filter(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test service listing with is_active filter."""
        mock_service.list_services.return_value = ([sample_service_response], 1)

        response = client.get(
            "/api/v1/services",
            params={"is_active": True},
        )

        assert response.status_code == 200
        mock_service.list_services.assert_called_once()
        call_kwargs = mock_service.list_services.call_args.kwargs
        assert call_kwargs["is_active"] is True

    def test_list_services_empty_result(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test service listing with no results."""
        mock_service.list_services.return_value = ([], 0)

        response = client.get("/api/v1/services")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
        assert data["total_pages"] == 0

    def test_list_services_invalid_page_size_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid page_size returns 422."""
        response = client.get(
            "/api/v1/services",
            params={"page_size": 200},  # Max is 100
        )

        assert response.status_code == 422

    def test_list_services_with_sorting(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_list: list[ServiceOfferingResponse],
    ) -> None:
        """Test service listing with sorting parameters."""
        mock_service.list_services.return_value = (sample_service_list, 2)

        response = client.get(
            "/api/v1/services",
            params={"sort_by": "base_price", "sort_order": "desc"},
        )

        assert response.status_code == 200
        mock_service.list_services.assert_called_once()
        call_kwargs = mock_service.list_services.call_args.kwargs
        assert call_kwargs["sort_by"] == "base_price"
        assert call_kwargs["sort_order"] == "desc"

    def test_list_services_invalid_sort_order_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid sort_order returns 422."""
        response = client.get(
            "/api/v1/services",
            params={"sort_order": "invalid"},
        )

        assert response.status_code == 422


# =============================================================================
# Task 11.4 Tests: GET /api/v1/services/category/{category} - Get by Category
# =============================================================================


@pytest.mark.unit
class TestGetServicesByCategory:
    """Tests for GET /api/v1/services/category/{category} endpoint."""

    def test_get_services_by_category_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_list: list[ServiceOfferingResponse],
    ) -> None:
        """Test successful category retrieval returns 200."""
        mock_service.get_by_category.return_value = sample_service_list

        response = client.get("/api/v1/services/category/seasonal")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(s["category"] == "seasonal" for s in data)

    def test_get_services_by_category_empty(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test category with no services returns empty array."""
        mock_service.get_by_category.return_value = []

        response = client.get("/api/v1/services/category/landscaping")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_services_by_category_invalid_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid category returns 422."""
        response = client.get("/api/v1/services/category/invalid_category")

        assert response.status_code == 422

    def test_get_services_by_category_all_categories(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test all valid categories are accepted."""
        mock_service.get_by_category.return_value = [sample_service_response]

        valid_categories = [
            "seasonal",
            "repair",
            "installation",
            "diagnostic",
            "landscaping",
        ]

        for category in valid_categories:
            response = client.get(f"/api/v1/services/category/{category}")
            assert response.status_code == 200, f"Failed for category: {category}"


# =============================================================================
# Additional Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestServiceOfferingAPIEdgeCases:
    """Additional edge case tests for service offering API."""

    def test_create_service_with_all_fields(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test creating service with all optional fields."""
        mock_service.create_service.return_value = sample_service_response

        response = client.post(
            "/api/v1/services",
            json={
                "name": "Complete Service",
                "category": "installation",
                "description": "Full installation service",
                "base_price": "500.00",
                "price_per_zone": "75.00",
                "pricing_model": "zone_based",
                "estimated_duration_minutes": 180,
                "duration_per_zone_minutes": 30,
                "staffing_required": 2,
                "equipment_required": ["pipe_puller", "utility_trailer"],
                "lien_eligible": True,
                "requires_prepay": True,
            },
        )

        assert response.status_code == 201

    def test_update_service_empty_body(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test updating service with empty body."""
        mock_service.update_service.return_value = sample_service_response

        response = client.put(
            f"/api/v1/services/{sample_service_response.id}",
            json={},
        )

        assert response.status_code == 200

    def test_list_services_combined_filters(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test listing services with multiple filters combined."""
        mock_service.list_services.return_value = ([sample_service_response], 1)

        response = client.get(
            "/api/v1/services",
            params={
                "category": "seasonal",
                "is_active": True,
                "page": 1,
                "page_size": 10,
                "sort_by": "name",
                "sort_order": "asc",
            },
        )

        assert response.status_code == 200
        mock_service.list_services.assert_called_once()

    def test_create_service_whitespace_name_trimmed(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test that service name whitespace is trimmed."""
        mock_service.create_service.return_value = sample_service_response

        response = client.post(
            "/api/v1/services",
            json={
                "name": "  Spring Startup  ",
                "category": "seasonal",
                "pricing_model": "flat",
            },
        )

        assert response.status_code == 201
        # The schema should trim the name
        call_args = mock_service.create_service.call_args
        assert call_args[0][0].name == "Spring Startup"

    def test_pagination_total_pages_calculation(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test total_pages is calculated correctly."""
        # 25 total items with page_size 10 = 3 pages
        mock_service.list_services.return_value = ([sample_service_response], 25)

        response = client.get(
            "/api/v1/services",
            params={"page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert data["total_pages"] == 3

    def test_pagination_single_item_single_page(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_service_response: ServiceOfferingResponse,
    ) -> None:
        """Test single item results in single page."""
        mock_service.list_services.return_value = ([sample_service_response], 1)

        response = client.get("/api/v1/services")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["total_pages"] == 1
