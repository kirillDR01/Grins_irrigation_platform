"""
Tests for Customer API endpoints.

This module contains unit tests for the customer CRUD API endpoints,
testing all HTTP methods, validation, error handling, and pagination.

Validates: Requirement 1.1-1.6, 3.1-3.6, 4.1-4.7, 6.6, 10.1-10.7
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.customers import router
from grins_platform.api.v1.dependencies import get_customer_service
from grins_platform.exceptions import CustomerNotFoundError, DuplicateCustomerError
from grins_platform.models.enums import CustomerStatus, LeadSource
from grins_platform.schemas.customer import (
    CustomerDetailResponse,
    CustomerResponse,
    PaginatedCustomerResponse,
    ServiceHistorySummary,
)
from grins_platform.services.customer_service import CustomerService

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_service() -> AsyncMock:
    """Create a mock CustomerService."""
    return AsyncMock(spec=CustomerService)


@pytest.fixture
def app(mock_service: AsyncMock) -> FastAPI:
    """Create FastAPI app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/customers")

    # Override dependency
    app.dependency_overrides[get_customer_service] = lambda: mock_service

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_customer_response() -> CustomerResponse:
    """Create a sample CustomerResponse."""
    return CustomerResponse(
        id=uuid.uuid4(),
        first_name="John",
        last_name="Doe",
        phone="6125551234",
        email="john.doe@example.com",
        status=CustomerStatus.ACTIVE,
        is_priority=False,
        is_red_flag=False,
        is_slow_payer=False,
        is_new_customer=True,
        sms_opt_in=False,
        email_opt_in=False,
        lead_source=LeadSource.WEBSITE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_detail_response(
    sample_customer_response: CustomerResponse,
) -> CustomerDetailResponse:
    """Create a sample CustomerDetailResponse."""
    return CustomerDetailResponse(
        id=sample_customer_response.id,
        first_name=sample_customer_response.first_name,
        last_name=sample_customer_response.last_name,
        phone=sample_customer_response.phone,
        email=sample_customer_response.email,
        status=sample_customer_response.status,
        is_priority=sample_customer_response.is_priority,
        is_red_flag=sample_customer_response.is_red_flag,
        is_slow_payer=sample_customer_response.is_slow_payer,
        is_new_customer=sample_customer_response.is_new_customer,
        sms_opt_in=sample_customer_response.sms_opt_in,
        email_opt_in=sample_customer_response.email_opt_in,
        lead_source=sample_customer_response.lead_source,
        created_at=sample_customer_response.created_at,
        updated_at=sample_customer_response.updated_at,
        properties=[],
        service_history_summary=ServiceHistorySummary(
            total_jobs=5,
            last_service_date=datetime.now(),
            total_revenue=1500.0,
        ),
    )


# =============================================================================
# Task 7.2 Tests: POST /api/v1/customers
# =============================================================================


class TestCreateCustomer:
    """Tests for POST /api/v1/customers endpoint."""

    def test_create_customer_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test successful customer creation returns 201."""
        mock_service.create_customer.return_value = sample_customer_response

        response = client.post(
            "/api/v1/customers",
            json={
                "first_name": "John",
                "last_name": "Doe",
                "phone": "612-555-1234",
                "email": "john.doe@example.com",
                "lead_source": "website",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        mock_service.create_customer.assert_called_once()

    def test_create_customer_duplicate_phone_returns_400(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test duplicate phone returns 400."""
        existing_id = uuid.uuid4()
        mock_service.create_customer.side_effect = DuplicateCustomerError(
            existing_id,
            "6125551234",
        )

        response = client.post(
            "/api/v1/customers",
            json={
                "first_name": "John",
                "last_name": "Doe",
                "phone": "612-555-1234",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_customer_invalid_phone_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid phone format returns 422."""
        response = client.post(
            "/api/v1/customers",
            json={
                "first_name": "John",
                "last_name": "Doe",
                "phone": "123",  # Too short
            },
        )

        assert response.status_code == 422

    def test_create_customer_missing_required_fields_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test missing required fields returns 422."""
        response = client.post(
            "/api/v1/customers",
            json={
                "first_name": "John",
                # Missing last_name and phone
            },
        )

        assert response.status_code == 422


# =============================================================================
# Task 7.3 Tests: GET /api/v1/customers/{id}
# =============================================================================


class TestGetCustomer:
    """Tests for GET /api/v1/customers/{id} endpoint."""

    def test_get_customer_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_detail_response: CustomerDetailResponse,
    ) -> None:
        """Test successful customer retrieval returns 200."""
        mock_service.get_customer.return_value = sample_detail_response

        response = client.get(f"/api/v1/customers/{sample_detail_response.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert "properties" in data
        assert "service_history_summary" in data

    def test_get_customer_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test non-existent customer returns 404."""
        customer_id = uuid.uuid4()
        mock_service.get_customer.side_effect = CustomerNotFoundError(customer_id)

        response = client.get(f"/api/v1/customers/{customer_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_customer_without_properties(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_detail_response: CustomerDetailResponse,
    ) -> None:
        """Test get customer with include_properties=false."""
        mock_service.get_customer.return_value = sample_detail_response

        response = client.get(
            f"/api/v1/customers/{sample_detail_response.id}",
            params={"include_properties": False},
        )

        assert response.status_code == 200
        mock_service.get_customer.assert_called_once()
        call_kwargs = mock_service.get_customer.call_args.kwargs
        assert call_kwargs["include_properties"] is False

    def test_get_customer_invalid_uuid_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid UUID format returns 422."""
        response = client.get("/api/v1/customers/not-a-uuid")

        assert response.status_code == 422


# =============================================================================
# Task 7.4 Tests: PUT /api/v1/customers/{id}
# =============================================================================


class TestUpdateCustomer:
    """Tests for PUT /api/v1/customers/{id} endpoint."""

    def test_update_customer_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test successful customer update returns 200."""
        updated_response = CustomerResponse(
            id=sample_customer_response.id,
            first_name="Jane",  # Updated
            last_name=sample_customer_response.last_name,
            phone=sample_customer_response.phone,
            email=sample_customer_response.email,
            status=sample_customer_response.status,
            is_priority=sample_customer_response.is_priority,
            is_red_flag=sample_customer_response.is_red_flag,
            is_slow_payer=sample_customer_response.is_slow_payer,
            is_new_customer=sample_customer_response.is_new_customer,
            sms_opt_in=sample_customer_response.sms_opt_in,
            email_opt_in=sample_customer_response.email_opt_in,
            lead_source=sample_customer_response.lead_source,
            created_at=sample_customer_response.created_at,
            updated_at=sample_customer_response.updated_at,
        )
        mock_service.update_customer.return_value = updated_response

        response = client.put(
            f"/api/v1/customers/{sample_customer_response.id}",
            json={"first_name": "Jane"},
        )

        assert response.status_code == 200
        assert response.json()["first_name"] == "Jane"

    def test_update_customer_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test updating non-existent customer returns 404."""
        customer_id = uuid.uuid4()
        mock_service.update_customer.side_effect = CustomerNotFoundError(customer_id)

        response = client.put(
            f"/api/v1/customers/{customer_id}",
            json={"first_name": "Jane"},
        )

        assert response.status_code == 404

    def test_update_customer_duplicate_phone_returns_400(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test updating to duplicate phone returns 400."""
        existing_id = uuid.uuid4()
        mock_service.update_customer.side_effect = DuplicateCustomerError(
            existing_id,
            "6125559999",
        )

        response = client.put(
            f"/api/v1/customers/{sample_customer_response.id}",
            json={"phone": "612-555-9999"},
        )

        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]


# =============================================================================
# Task 7.5 Tests: DELETE /api/v1/customers/{id}
# =============================================================================


class TestDeleteCustomer:
    """Tests for DELETE /api/v1/customers/{id} endpoint."""

    def test_delete_customer_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test successful customer deletion returns 204."""
        mock_service.delete_customer.return_value = True

        response = client.delete(f"/api/v1/customers/{sample_customer_response.id}")

        assert response.status_code == 204
        assert response.content == b""  # No content

    def test_delete_customer_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test deleting non-existent customer returns 404."""
        customer_id = uuid.uuid4()
        mock_service.delete_customer.side_effect = CustomerNotFoundError(customer_id)

        response = client.delete(f"/api/v1/customers/{customer_id}")

        assert response.status_code == 404


# =============================================================================
# Task 7.6 Tests: GET /api/v1/customers
# =============================================================================


class TestListCustomers:
    """Tests for GET /api/v1/customers endpoint."""

    def test_list_customers_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test successful customer listing returns 200."""
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[sample_customer_response],
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1

    def test_list_customers_with_pagination(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test customer listing with pagination parameters."""
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[sample_customer_response],
            total=50,
            page=2,
            page_size=10,
            total_pages=5,
        )

        response = client.get(
            "/api/v1/customers",
            params={"page": 2, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total_pages"] == 5

    def test_list_customers_with_filters(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test customer listing with filter parameters."""
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[sample_customer_response],
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={
                "city": "Eden Prairie",
                "status": "active",
                "is_priority": True,
            },
        )

        assert response.status_code == 200
        mock_service.list_customers.assert_called_once()

    def test_list_customers_empty_result(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test customer listing with no results."""
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_list_customers_invalid_page_size_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test invalid page_size returns 422."""
        response = client.get(
            "/api/v1/customers",
            params={"page_size": 200},  # Max is 100
        )

        assert response.status_code == 422

    def test_list_customers_with_search(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test customer listing with search parameter."""
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[sample_customer_response],
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"search": "John"},
        )

        assert response.status_code == 200


# =============================================================================
# Task 8.1 Tests: PUT /api/v1/customers/{id}/flags
# =============================================================================


class TestUpdateCustomerFlags:
    """Tests for PUT /api/v1/customers/{id}/flags endpoint."""

    def test_update_flags_success(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test successful flag update returns 200."""
        updated_response = CustomerResponse(
            id=sample_customer_response.id,
            first_name=sample_customer_response.first_name,
            last_name=sample_customer_response.last_name,
            phone=sample_customer_response.phone,
            email=sample_customer_response.email,
            status=sample_customer_response.status,
            is_priority=True,  # Updated
            is_red_flag=sample_customer_response.is_red_flag,
            is_slow_payer=sample_customer_response.is_slow_payer,
            is_new_customer=sample_customer_response.is_new_customer,
            sms_opt_in=sample_customer_response.sms_opt_in,
            email_opt_in=sample_customer_response.email_opt_in,
            lead_source=sample_customer_response.lead_source,
            created_at=sample_customer_response.created_at,
            updated_at=sample_customer_response.updated_at,
        )
        mock_service.update_flags.return_value = updated_response

        response = client.put(
            f"/api/v1/customers/{sample_customer_response.id}/flags",
            json={"is_priority": True},
        )

        assert response.status_code == 200
        assert response.json()["is_priority"] is True

    def test_update_flags_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test updating flags for non-existent customer returns 404."""
        customer_id = uuid.uuid4()
        mock_service.update_flags.side_effect = CustomerNotFoundError(customer_id)

        response = client.put(
            f"/api/v1/customers/{customer_id}/flags",
            json={"is_priority": True},
        )

        assert response.status_code == 404

    def test_update_multiple_flags(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        sample_customer_response: CustomerResponse,
    ) -> None:
        """Test updating multiple flags at once."""
        updated_response = CustomerResponse(
            id=sample_customer_response.id,
            first_name=sample_customer_response.first_name,
            last_name=sample_customer_response.last_name,
            phone=sample_customer_response.phone,
            email=sample_customer_response.email,
            status=sample_customer_response.status,
            is_priority=True,
            is_red_flag=True,
            is_slow_payer=True,
            is_new_customer=False,
            sms_opt_in=sample_customer_response.sms_opt_in,
            email_opt_in=sample_customer_response.email_opt_in,
            lead_source=sample_customer_response.lead_source,
            created_at=sample_customer_response.created_at,
            updated_at=sample_customer_response.updated_at,
        )
        mock_service.update_flags.return_value = updated_response

        response = client.put(
            f"/api/v1/customers/{sample_customer_response.id}/flags",
            json={
                "is_priority": True,
                "is_red_flag": True,
                "is_slow_payer": True,
                "is_new_customer": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_priority"] is True
        assert data["is_red_flag"] is True
        assert data["is_slow_payer"] is True
        assert data["is_new_customer"] is False
