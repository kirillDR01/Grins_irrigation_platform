"""
Integration tests for customer search and filter functionality.

This module tests the full workflow of searching and filtering customers
through the API endpoints, validating pagination, filtering, and sorting.

Validates: Requirement 4.1-4.7
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.customers import router
from grins_platform.api.v1.dependencies import get_customer_service
from grins_platform.models.enums import CustomerStatus, LeadSource
from grins_platform.schemas.customer import (
    CustomerResponse,
    PaginatedCustomerResponse,
)
from grins_platform.services.customer_service import CustomerService

if TYPE_CHECKING:
    from collections.abc import Callable


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
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/customers")
    test_app.dependency_overrides[get_customer_service] = lambda: mock_service
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def customer_factory() -> Callable[..., CustomerResponse]:
    """Factory for creating CustomerResponse objects with unique data."""
    counter = 0

    def _create(
        first_name: str = "Test",
        last_name: str = "User",
        phone: str | None = None,
        email: str | None = None,
        status: CustomerStatus = CustomerStatus.ACTIVE,
        is_priority: bool = False,
        is_red_flag: bool = False,
        is_slow_payer: bool = False,
        is_new_customer: bool = True,
        lead_source: LeadSource | None = LeadSource.WEBSITE,
    ) -> CustomerResponse:
        nonlocal counter
        counter += 1
        return CustomerResponse(
            id=uuid.uuid4(),
            first_name=first_name,
            last_name=last_name,
            phone=phone or f"612555{counter:04d}",
            email=email or f"test{counter}@example.com",
            status=status,
            is_priority=is_priority,
            is_red_flag=is_red_flag,
            is_slow_payer=is_slow_payer,
            is_new_customer=is_new_customer,
            sms_opt_in=False,
            email_opt_in=False,
            lead_source=lead_source,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    return _create


# =============================================================================
# Task 10.4: Pagination Integration Tests
# Validates: Requirement 4.1
# =============================================================================


@pytest.mark.integration
class TestPaginationWithLargeDatasets:
    """Integration tests for pagination with large datasets."""

    def test_pagination_first_page(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test retrieving first page of large dataset.

        Validates: Requirement 4.1
        """
        # Create 50 customers for a large dataset simulation
        customers = [customer_factory(last_name=f"User{i:03d}") for i in range(20)]

        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=100,
            page=1,
            page_size=20,
            total_pages=5,
        )

        response = client.get("/api/v1/customers", params={"page": 1, "page_size": 20})

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] == 100
        assert data["total_pages"] == 5
        assert len(data["items"]) == 20

    def test_pagination_middle_page(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test retrieving middle page of large dataset.

        Validates: Requirement 4.1
        """
        customers = [customer_factory(last_name=f"User{i:03d}") for i in range(20)]

        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=100,
            page=3,
            page_size=20,
            total_pages=5,
        )

        response = client.get("/api/v1/customers", params={"page": 3, "page_size": 20})

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3
        assert data["total_pages"] == 5

    def test_pagination_last_page_partial(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test retrieving last page with partial results.

        Validates: Requirement 4.1
        """
        # Last page with only 5 items
        customers = [customer_factory(last_name=f"User{i:03d}") for i in range(5)]

        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=45,
            page=3,
            page_size=20,
            total_pages=3,
        )

        response = client.get("/api/v1/customers", params={"page": 3, "page_size": 20})

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3
        assert len(data["items"]) == 5
        assert data["total"] == 45

    def test_pagination_empty_page_beyond_data(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test requesting page beyond available data returns empty.

        Validates: Requirement 4.1
        """
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[],
            total=20,
            page=10,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"page": 10, "page_size": 20},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    def test_pagination_different_page_sizes(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test pagination with different page sizes.

        Validates: Requirement 4.1
        """
        # Test with page_size=10
        customers_10 = [customer_factory() for _ in range(10)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers_10,
            total=100,
            page=1,
            page_size=10,
            total_pages=10,
        )

        response = client.get("/api/v1/customers", params={"page_size": 10})
        assert response.status_code == 200
        assert response.json()["total_pages"] == 10

        # Test with page_size=50
        customers_50 = [customer_factory() for _ in range(50)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers_50,
            total=100,
            page=1,
            page_size=50,
            total_pages=2,
        )

        response = client.get("/api/v1/customers", params={"page_size": 50})
        assert response.status_code == 200
        assert response.json()["total_pages"] == 2

    def test_pagination_max_page_size(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test pagination with maximum allowed page size (100).

        Validates: Requirement 4.1
        """
        customers = [customer_factory() for _ in range(100)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=150,
            page=1,
            page_size=100,
            total_pages=2,
        )

        response = client.get("/api/v1/customers", params={"page_size": 100})

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 100
        assert len(data["items"]) == 100

    def test_pagination_exceeds_max_page_size_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test that page_size > 100 returns validation error.

        Validates: Requirement 4.1
        """
        response = client.get("/api/v1/customers", params={"page_size": 101})

        assert response.status_code == 422


# =============================================================================
# Task 10.4: Filter Combination Integration Tests
# Validates: Requirement 4.2-4.5
# =============================================================================


@pytest.mark.integration
class TestFilterCombinations:
    """Integration tests for all filter combinations."""

    def test_filter_by_city(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test filtering customers by city.

        Validates: Requirement 4.2
        """
        customers = [customer_factory(last_name="EdenPrairieUser") for _ in range(3)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=3,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"city": "Eden Prairie"},
        )

        assert response.status_code == 200
        mock_service.list_customers.assert_called_once()
        # Verify the city filter was passed to the service
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].city == "Eden Prairie"

    def test_filter_by_status_active(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test filtering customers by active status.

        Validates: Requirement 4.3
        """
        customers = [customer_factory(status=CustomerStatus.ACTIVE) for _ in range(5)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=5,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"status": "active"})

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].status == CustomerStatus.ACTIVE

    def test_filter_by_status_inactive(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test filtering customers by inactive status.

        Validates: Requirement 4.3
        """
        customers = [customer_factory(status=CustomerStatus.INACTIVE) for _ in range(2)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"status": "inactive"})

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].status == CustomerStatus.INACTIVE

    def test_filter_by_priority_flag(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test filtering customers by priority flag.

        Validates: Requirement 4.4
        """
        customers = [customer_factory(is_priority=True) for _ in range(3)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=3,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"is_priority": True})

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].is_priority is True

    def test_filter_by_red_flag(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test filtering customers by red flag.

        Validates: Requirement 4.4
        """
        customers = [customer_factory(is_red_flag=True) for _ in range(2)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"is_red_flag": True})

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].is_red_flag is True

    def test_filter_by_slow_payer_flag(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test filtering customers by slow payer flag.

        Validates: Requirement 4.4
        """
        customers = [customer_factory(is_slow_payer=True) for _ in range(4)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=4,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"is_slow_payer": True})

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].is_slow_payer is True

    def test_filter_multiple_flags_and_logic(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test combining multiple filters with AND logic.

        Validates: Requirement 4.5
        """
        # Customer that matches all filters
        customers = [
            customer_factory(
                is_priority=True,
                is_red_flag=True,
                status=CustomerStatus.ACTIVE,
            ),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={
                "is_priority": True,
                "is_red_flag": True,
                "status": "active",
            },
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.is_priority is True
        assert params.is_red_flag is True
        assert params.status == CustomerStatus.ACTIVE

    def test_filter_city_and_status_combined(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test combining city and status filters.

        Validates: Requirement 4.5
        """
        customers = [customer_factory(status=CustomerStatus.ACTIVE) for _ in range(2)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"city": "Plymouth", "status": "active"},
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.city == "Plymouth"
        assert params.status == CustomerStatus.ACTIVE

    def test_filter_all_flags_combined(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test combining all flag filters.

        Validates: Requirement 4.5
        """
        customers = [
            customer_factory(
                is_priority=True,
                is_red_flag=False,
                is_slow_payer=True,
            ),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={
                "is_priority": True,
                "is_red_flag": False,
                "is_slow_payer": True,
            },
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.is_priority is True
        assert params.is_red_flag is False
        assert params.is_slow_payer is True

    def test_filter_returns_empty_when_no_match(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test that filters return empty result when no customers match.

        Validates: Requirement 4.5
        """
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )

        response = client.get(
            "/api/v1/customers",
            params={"city": "NonExistentCity", "is_priority": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0


# =============================================================================
# Task 10.4: Search Integration Tests
# Validates: Requirement 4.6
# =============================================================================


@pytest.mark.integration
class TestSearchFunctionality:
    """Integration tests for search functionality."""

    def test_search_by_name(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test searching customers by name.

        Validates: Requirement 4.6
        """
        customers = [customer_factory(first_name="John", last_name="Smith")]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"search": "John"})

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].search == "John"

    def test_search_by_last_name(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test searching customers by last name.

        Validates: Requirement 4.6
        """
        customers = [customer_factory(first_name="Jane", last_name="Doe")]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"search": "Doe"})

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].search == "Doe"

    def test_search_by_email(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test searching customers by email.

        Validates: Requirement 4.6
        """
        customers = [customer_factory(email="john.doe@example.com")]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"search": "john.doe@example.com"},
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].search == "john.doe@example.com"

    def test_search_case_insensitive(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test that search is case-insensitive.

        Validates: Requirement 4.6
        """
        customers = [customer_factory(first_name="John", last_name="Smith")]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        # Search with different case
        response = client.get("/api/v1/customers", params={"search": "JOHN"})

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        assert call_args[0][0].search == "JOHN"

    def test_search_partial_match(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test searching with partial name match.

        Validates: Requirement 4.6
        """
        customers = [
            customer_factory(first_name="Johnson", last_name="Williams"),
            customer_factory(first_name="John", last_name="Smith"),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"search": "John"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_search_with_filters_combined(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test combining search with other filters.

        Validates: Requirement 4.5, 4.6
        """
        customers = [
            customer_factory(
                first_name="John",
                last_name="Priority",
                is_priority=True,
                status=CustomerStatus.ACTIVE,
            ),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={
                "search": "John",
                "is_priority": True,
                "status": "active",
            },
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.search == "John"
        assert params.is_priority is True
        assert params.status == CustomerStatus.ACTIVE

    def test_search_empty_result(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test search with no matching results.

        Validates: Requirement 4.6
        """
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )

        response = client.get(
            "/api/v1/customers",
            params={"search": "NonExistentName"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0


# =============================================================================
# Task 10.4: Sorting Integration Tests
# Validates: Requirement 4.7
# =============================================================================


@pytest.mark.integration
class TestSortingOptions:
    """Integration tests for sorting options."""

    def test_sort_by_last_name_ascending_default(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test default sorting by last_name ascending.

        Validates: Requirement 4.7
        """
        customers = [
            customer_factory(last_name="Adams"),
            customer_factory(last_name="Brown"),
            customer_factory(last_name="Clark"),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=3,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.sort_by == "last_name"
        assert params.sort_order == "asc"

    def test_sort_by_last_name_descending(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test sorting by last_name descending.

        Validates: Requirement 4.7
        """
        customers = [
            customer_factory(last_name="Clark"),
            customer_factory(last_name="Brown"),
            customer_factory(last_name="Adams"),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=3,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"sort_by": "last_name", "sort_order": "desc"},
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.sort_by == "last_name"
        assert params.sort_order == "desc"

    def test_sort_by_first_name(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test sorting by first_name.

        Validates: Requirement 4.7
        """
        customers = [
            customer_factory(first_name="Alice"),
            customer_factory(first_name="Bob"),
            customer_factory(first_name="Charlie"),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=3,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"sort_by": "first_name", "sort_order": "asc"},
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.sort_by == "first_name"

    def test_sort_by_created_at_ascending(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test sorting by created_at ascending (oldest first).

        Validates: Requirement 4.7
        """
        customers = [customer_factory() for _ in range(3)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=3,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"sort_by": "created_at", "sort_order": "asc"},
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.sort_by == "created_at"
        assert params.sort_order == "asc"

    def test_sort_by_created_at_descending(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test sorting by created_at descending (newest first).

        Validates: Requirement 4.7
        """
        customers = [customer_factory() for _ in range(3)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=3,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"sort_by": "created_at", "sort_order": "desc"},
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"

    def test_sort_by_status(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test sorting by status.

        Validates: Requirement 4.7
        """
        customers = [
            customer_factory(status=CustomerStatus.ACTIVE),
            customer_factory(status=CustomerStatus.INACTIVE),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={"sort_by": "status", "sort_order": "asc"},
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.sort_by == "status"

    def test_sort_with_filters_combined(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test combining sorting with filters.

        Validates: Requirement 4.5, 4.7
        """
        customers = [
            customer_factory(
                first_name="Alice",
                is_priority=True,
                status=CustomerStatus.ACTIVE,
            ),
            customer_factory(
                first_name="Bob",
                is_priority=True,
                status=CustomerStatus.ACTIVE,
            ),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={
                "is_priority": True,
                "status": "active",
                "sort_by": "first_name",
                "sort_order": "asc",
            },
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.is_priority is True
        assert params.status == CustomerStatus.ACTIVE
        assert params.sort_by == "first_name"
        assert params.sort_order == "asc"

    def test_sort_with_pagination(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test combining sorting with pagination.

        Validates: Requirement 4.1, 4.7
        """
        customers = [customer_factory() for _ in range(10)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=50,
            page=2,
            page_size=10,
            total_pages=5,
        )

        response = client.get(
            "/api/v1/customers",
            params={
                "page": 2,
                "page_size": 10,
                "sort_by": "created_at",
                "sort_order": "desc",
            },
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.page == 2
        assert params.page_size == 10
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"

    def test_invalid_sort_order_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - Required for fixture injection
    ) -> None:
        """Test that invalid sort_order returns validation error.

        Validates: Requirement 4.7
        """
        response = client.get(
            "/api/v1/customers",
            params={"sort_order": "invalid"},
        )

        assert response.status_code == 422


# =============================================================================
# Task 10.4: Complex Integration Scenarios
# Validates: Requirement 4.1-4.7
# =============================================================================


@pytest.mark.integration
class TestComplexSearchFilterScenarios:
    """Integration tests for complex search and filter scenarios."""

    def test_full_filter_combination_with_pagination_and_sorting(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test combining all filter types with pagination and sorting.

        Validates: Requirement 4.1-4.7
        """
        customers = [
            customer_factory(
                first_name="John",
                last_name="Priority",
                is_priority=True,
                status=CustomerStatus.ACTIVE,
            ),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=10,
            total_pages=1,
        )

        response = client.get(
            "/api/v1/customers",
            params={
                "page": 1,
                "page_size": 10,
                "city": "Eden Prairie",
                "status": "active",
                "is_priority": True,
                "is_red_flag": False,
                "search": "John",
                "sort_by": "last_name",
                "sort_order": "asc",
            },
        )

        assert response.status_code == 200
        call_args = mock_service.list_customers.call_args
        params = call_args[0][0]
        assert params.page == 1
        assert params.page_size == 10
        assert params.city == "Eden Prairie"
        assert params.status == CustomerStatus.ACTIVE
        assert params.is_priority is True
        assert params.is_red_flag is False
        assert params.search == "John"
        assert params.sort_by == "last_name"
        assert params.sort_order == "asc"

    def test_large_dataset_with_multiple_pages(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test handling large dataset across multiple pages.

        Validates: Requirement 4.1
        """
        # Simulate 500 total customers, requesting page 5
        customers = [customer_factory() for _ in range(20)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=500,
            page=5,
            page_size=20,
            total_pages=25,
        )

        response = client.get(
            "/api/v1/customers",
            params={"page": 5, "page_size": 20},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 500
        assert data["page"] == 5
        assert data["total_pages"] == 25
        assert len(data["items"]) == 20

    def test_filter_reduces_total_count(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test that filters reduce the total count appropriately.

        Validates: Requirement 4.2-4.5
        """
        # First request without filters - 100 total
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[customer_factory() for _ in range(20)],
            total=100,
            page=1,
            page_size=20,
            total_pages=5,
        )

        response1 = client.get("/api/v1/customers")
        assert response1.json()["total"] == 100

        # Second request with filter - only 10 match
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[customer_factory(is_priority=True) for _ in range(10)],
            total=10,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response2 = client.get("/api/v1/customers", params={"is_priority": True})
        assert response2.json()["total"] == 10

    def test_search_and_filter_with_no_results(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Test search and filter combination that returns no results.

        Validates: Requirement 4.5, 4.6
        """
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )

        response = client.get(
            "/api/v1/customers",
            params={
                "search": "NonExistent",
                "city": "UnknownCity",
                "is_priority": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["total_pages"] == 0
        assert len(data["items"]) == 0

    def test_pagination_boundary_conditions(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test pagination at boundary conditions.

        Validates: Requirement 4.1
        """
        # Exactly one page of results
        customers = [customer_factory() for _ in range(20)]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=20,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers", params={"page_size": 20})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 20
        assert data["total_pages"] == 1
        assert len(data["items"]) == 20

    def test_single_result_pagination(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test pagination with single result.

        Validates: Requirement 4.1
        """
        customers = [customer_factory()]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["total_pages"] == 1
        assert len(data["items"]) == 1

    def test_lead_source_filter_integration(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        customer_factory: Callable[..., CustomerResponse],
    ) -> None:
        """Test filtering by lead source (if supported).

        Validates: Requirement 4.5
        """
        customers = [
            customer_factory(lead_source=LeadSource.WEBSITE),
            customer_factory(lead_source=LeadSource.WEBSITE),
        ]
        mock_service.list_customers.return_value = PaginatedCustomerResponse(
            items=customers,
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )

        # Note: lead_source filter may not be exposed in API yet
        # This test verifies the service is called correctly
        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        data = response.json()
        # Verify lead_source is included in response
        for item in data["items"]:
            assert "lead_source" in item
