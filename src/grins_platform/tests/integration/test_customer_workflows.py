"""
Integration tests for customer workflow operations.

This module contains integration tests that verify the complete customer
lifecycle through the API, testing the integration between API endpoints
and services with mocked repositories.

Validates: Requirement 1.1-1.12
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.customers import router as customer_router
from grins_platform.api.v1.dependencies import (
    get_customer_service,
    get_property_service,
)
from grins_platform.api.v1.properties import router as property_router
from grins_platform.schemas.customer import ServiceHistorySummary
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.property_service import PropertyService

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_customer_repository() -> AsyncMock:
    """Create a mock CustomerRepository."""
    return AsyncMock()


@pytest.fixture
def mock_property_repository() -> AsyncMock:
    """Create a mock PropertyRepository."""
    return AsyncMock()


@pytest.fixture
def customer_service(mock_customer_repository: AsyncMock) -> CustomerService:
    """Create CustomerService with mocked repository."""
    return CustomerService(repository=mock_customer_repository)


@pytest.fixture
def property_service(mock_property_repository: AsyncMock) -> PropertyService:
    """Create PropertyService with mocked repository."""
    return PropertyService(repository=mock_property_repository)


@pytest.fixture
def app(
    customer_service: CustomerService,
    property_service: PropertyService,
) -> FastAPI:
    """Create FastAPI app with mocked services."""
    app = FastAPI()
    app.include_router(customer_router, prefix="/api/v1/customers")
    app.include_router(property_router, prefix="/api/v1")

    # Override dependencies
    app.dependency_overrides[get_customer_service] = lambda: customer_service
    app.dependency_overrides[get_property_service] = lambda: property_service

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


def create_mock_customer(
    customer_id: uuid.UUID | None = None,
    first_name: str = "John",
    last_name: str = "Doe",
    phone: str = "6125551234",
    email: str | None = "john.doe@example.com",
    status: str = "active",
    is_priority: bool = False,
    is_red_flag: bool = False,
    is_slow_payer: bool = False,
    is_new_customer: bool = True,
    sms_opt_in: bool = False,
    email_opt_in: bool = False,
    lead_source: str | None = "website",
    is_deleted: bool = False,
    properties: list[MagicMock] | None = None,
) -> MagicMock:
    """Create a mock customer object."""
    customer = MagicMock()
    customer.id = customer_id or uuid.uuid4()
    customer.first_name = first_name
    customer.last_name = last_name
    customer.phone = phone
    customer.email = email
    customer.status = status
    customer.is_priority = is_priority
    customer.is_red_flag = is_red_flag
    customer.is_slow_payer = is_slow_payer
    customer.is_new_customer = is_new_customer
    customer.sms_opt_in = sms_opt_in
    customer.email_opt_in = email_opt_in
    customer.lead_source = lead_source
    customer.created_at = datetime.now()
    customer.updated_at = datetime.now()
    customer.is_deleted = is_deleted
    customer.properties = properties or []
    return customer


def create_mock_property(
    property_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    address: str = "123 Main St",
    city: str = "Eden Prairie",
    state: str = "MN",
    zip_code: str = "55344",
    zone_count: int = 6,
    system_type: str = "standard",
    property_type: str = "residential",
    is_primary: bool = True,
    access_instructions: str | None = None,
    gate_code: str | None = None,
    has_dogs: bool = False,
    special_notes: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> MagicMock:
    """Create a mock property object."""
    prop = MagicMock()
    prop.id = property_id or uuid.uuid4()
    prop.customer_id = customer_id or uuid.uuid4()
    prop.address = address
    prop.city = city
    prop.state = state
    prop.zip_code = zip_code
    prop.zone_count = zone_count
    prop.system_type = system_type
    prop.property_type = property_type
    prop.is_primary = is_primary
    prop.access_instructions = access_instructions
    prop.gate_code = gate_code
    prop.has_dogs = has_dogs
    prop.special_notes = special_notes
    prop.latitude = latitude
    prop.longitude = longitude
    prop.created_at = datetime.now()
    prop.updated_at = datetime.now()
    return prop


# =============================================================================
# Task 10.2: Customer Lifecycle Integration Tests
# Validates: Requirement 1.1-1.12
# =============================================================================


@pytest.mark.integration
class TestCustomerLifecycleWorkflow:
    """Integration tests for complete customer lifecycle (create, read, update, delete).

    Validates: Requirement 1.1-1.12
    """

    def test_complete_customer_lifecycle_create_read_update_delete(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test complete customer lifecycle: create -> get -> update -> delete.

        Validates: Requirement 1.1, 1.4, 1.5, 1.6
        """
        customer_id = uuid.uuid4()

        # Step 1: CREATE - Create a new customer
        created_customer = create_mock_customer(
            customer_id=customer_id,
            first_name="John",
            last_name="Doe",
            phone="6125551234",
            email="john.doe@example.com",
        )
        mock_customer_repository.find_by_phone.return_value = None
        mock_customer_repository.create.return_value = created_customer

        create_response = client.post(
            "/api/v1/customers",
            json={
                "first_name": "John",
                "last_name": "Doe",
                "phone": "612-555-1234",
                "email": "john.doe@example.com",
                "lead_source": "website",
            },
        )

        assert create_response.status_code == 201
        create_data = create_response.json()
        assert create_data["first_name"] == "John"
        assert create_data["last_name"] == "Doe"
        assert create_data["phone"] == "6125551234"
        mock_customer_repository.create.assert_called_once()

        # Step 2: READ - Get the customer with properties and service history
        mock_customer_repository.get_by_id.return_value = created_customer
        service_summary = ServiceHistorySummary(
            total_jobs=0,
            last_service_date=None,
            total_revenue=0.0,
        )
        mock_customer_repository.get_service_summary.return_value = service_summary

        get_response = client.get(f"/api/v1/customers/{customer_id}")

        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["id"] == str(customer_id)
        assert get_data["first_name"] == "John"
        assert "properties" in get_data
        assert "service_history_summary" in get_data

        # Step 3: UPDATE - Update customer information
        updated_customer = create_mock_customer(
            customer_id=customer_id,
            first_name="Jane",  # Updated name
            last_name="Doe",
            phone="6125551234",
            email="jane.doe@example.com",  # Updated email
        )
        mock_customer_repository.update.return_value = updated_customer

        update_response = client.put(
            f"/api/v1/customers/{customer_id}",
            json={
                "first_name": "Jane",
                "email": "jane.doe@example.com",
            },
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["first_name"] == "Jane"
        assert update_data["email"] == "jane.doe@example.com"

        # Step 4: DELETE - Soft delete the customer
        mock_customer_repository.soft_delete.return_value = True

        delete_response = client.delete(f"/api/v1/customers/{customer_id}")

        assert delete_response.status_code == 204
        mock_customer_repository.soft_delete.assert_called_once_with(customer_id)

    def test_customer_creation_with_default_values(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that new customers have correct default values.

        Validates: Requirement 1.11, 5.1, 5.2 (Property 5: Communication Opt-In Default)
        """
        customer_id = uuid.uuid4()
        created_customer = create_mock_customer(
            customer_id=customer_id,
            sms_opt_in=False,  # Default
            email_opt_in=False,  # Default
            is_new_customer=True,  # Default
        )
        mock_customer_repository.find_by_phone.return_value = None
        mock_customer_repository.create.return_value = created_customer

        response = client.post(
            "/api/v1/customers",
            json={
                "first_name": "Test",
                "last_name": "User",
                "phone": "612-555-9999",
            },
        )

        assert response.status_code == 201
        data = response.json()
        # Verify defaults are applied
        assert data["sms_opt_in"] is False
        assert data["email_opt_in"] is False
        assert data["is_new_customer"] is True
        assert data["status"] == "active"

    def test_customer_list_with_pagination(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test customer listing with pagination.

        Validates: Requirement 4.1, 4.7
        """
        # Create multiple mock customers
        customers = [
            create_mock_customer(
                customer_id=uuid.uuid4(),
                first_name=f"Customer{i}",
                last_name="Test",
                phone=f"612555{i:04d}",
            )
            for i in range(5)
        ]
        mock_customer_repository.list_with_filters.return_value = (customers, 50)

        response = client.get(
            "/api/v1/customers",
            params={"page": 1, "page_size": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 50
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert data["total_pages"] == 10
        assert len(data["items"]) == 5

    def test_customer_search_by_name(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test customer search by name.

        Validates: Requirement 4.6
        """
        customer = create_mock_customer(
            first_name="John",
            last_name="Smith",
        )
        mock_customer_repository.list_with_filters.return_value = ([customer], 1)

        response = client.get(
            "/api/v1/customers",
            params={"search": "John"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["first_name"] == "John"


@pytest.mark.integration
class TestCustomerWithMultipleProperties:
    """Integration tests for customers with multiple properties.

    Validates: Requirement 2.1, 2.5, 2.6, 2.7
    """

    def test_customer_with_multiple_properties(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
        mock_property_repository: AsyncMock,  # noqa: ARG002
    ) -> None:
        """Test customer can have multiple properties.

        Validates: Requirement 2.6
        """
        customer_id = uuid.uuid4()

        # Create properties
        property1 = create_mock_property(
            property_id=uuid.uuid4(),
            customer_id=customer_id,
            address="123 Main St",
            city="Eden Prairie",
            is_primary=True,
        )
        property2 = create_mock_property(
            property_id=uuid.uuid4(),
            customer_id=customer_id,
            address="456 Oak Ave",
            city="Plymouth",
            is_primary=False,
        )

        # Create customer with properties
        customer = create_mock_customer(
            customer_id=customer_id,
            properties=[property1, property2],
        )

        mock_customer_repository.get_by_id.return_value = customer
        service_summary = ServiceHistorySummary(
            total_jobs=5,
            last_service_date=datetime.now(),
            total_revenue=500.0,
        )
        mock_customer_repository.get_service_summary.return_value = service_summary

        response = client.get(f"/api/v1/customers/{customer_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["properties"]) == 2
        # Verify both properties are returned
        addresses = [p["address"] for p in data["properties"]]
        assert "123 Main St" in addresses
        assert "456 Oak Ave" in addresses

    def test_add_property_to_customer(
        self,
        client: TestClient,
        mock_property_repository: AsyncMock,
    ) -> None:
        """Test adding a property to a customer.

        Validates: Requirement 2.1
        """
        customer_id = uuid.uuid4()
        property_id = uuid.uuid4()

        new_property = create_mock_property(
            property_id=property_id,
            customer_id=customer_id,
            address="789 New St",
            city="Maple Grove",
            zone_count=8,
            is_primary=True,
        )

        mock_property_repository.count_by_customer_id.return_value = 0
        mock_property_repository.create.return_value = new_property

        response = client.post(
            f"/api/v1/customers/{customer_id}/properties",
            json={
                "address": "789 New St",
                "city": "Maple Grove",
                "state": "MN",
                "zip_code": "55369",
                "zone_count": 8,
                "system_type": "standard",
                "property_type": "residential",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["address"] == "789 New St"
        assert data["city"] == "Maple Grove"
        assert data["zone_count"] == 8
        assert data["is_primary"] is True  # First property is auto-primary

    def test_list_customer_properties(
        self,
        client: TestClient,
        mock_property_repository: AsyncMock,
    ) -> None:
        """Test listing all properties for a customer.

        Validates: Requirement 2.5
        """
        customer_id = uuid.uuid4()

        properties = [
            create_mock_property(
                customer_id=customer_id,
                address=f"{i} Test St",
                is_primary=(i == 0),
            )
            for i in range(3)
        ]

        mock_property_repository.get_by_customer_id.return_value = properties

        response = client.get(f"/api/v1/customers/{customer_id}/properties")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_primary_property_uniqueness(
        self,
        client: TestClient,
        mock_property_repository: AsyncMock,
    ) -> None:
        """Test that only one property can be primary per customer.

        Validates: Requirement 2.7 (Property 3: Primary Property Uniqueness)
        """
        customer_id = uuid.uuid4()
        property1_id = uuid.uuid4()
        property2_id = uuid.uuid4()

        # First property (currently primary)
        property1 = create_mock_property(
            property_id=property1_id,
            customer_id=customer_id,
            address="123 Main St",
            is_primary=True,
        )

        # Second property (will become primary)
        property2 = create_mock_property(
            property_id=property2_id,
            customer_id=customer_id,
            address="456 Oak Ave",
            is_primary=True,  # After set_primary
        )

        mock_property_repository.get_by_id.return_value = property1
        mock_property_repository.set_primary.return_value = property2

        # Set property2 as primary
        response = client.put(f"/api/v1/properties/{property2_id}/primary")

        assert response.status_code == 200
        data = response.json()
        assert data["is_primary"] is True


@pytest.mark.integration
class TestSoftDeleteBehavior:
    """Integration tests for soft delete behavior.

    Validates: Requirement 1.6, 6.8 (Property 2: Soft Delete Preservation)
    """

    def test_soft_delete_preserves_customer_data(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that soft delete preserves customer data.

        Validates: Requirement 1.6, 6.8
        """
        customer_id = uuid.uuid4()
        customer = create_mock_customer(customer_id=customer_id)

        mock_customer_repository.get_by_id.return_value = customer
        mock_customer_repository.soft_delete.return_value = True

        # Delete the customer
        delete_response = client.delete(f"/api/v1/customers/{customer_id}")

        assert delete_response.status_code == 204
        # Verify soft_delete was called (not hard delete)
        mock_customer_repository.soft_delete.assert_called_once_with(customer_id)

    def test_soft_delete_preserves_related_properties(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that soft delete preserves related properties.

        Validates: Requirement 6.8 (Property 2: Soft Delete Preservation)
        """
        customer_id = uuid.uuid4()

        # Create customer with properties
        property1 = create_mock_property(
            customer_id=customer_id,
            address="123 Main St",
        )
        property2 = create_mock_property(
            customer_id=customer_id,
            address="456 Oak Ave",
        )

        customer = create_mock_customer(
            customer_id=customer_id,
            properties=[property1, property2],
        )

        mock_customer_repository.get_by_id.return_value = customer
        mock_customer_repository.soft_delete.return_value = True

        # Delete the customer
        delete_response = client.delete(f"/api/v1/customers/{customer_id}")

        assert delete_response.status_code == 204
        # Properties should still exist (soft delete doesn't cascade delete)
        # The repository's soft_delete should only mark customer as deleted
        mock_customer_repository.soft_delete.assert_called_once_with(customer_id)

    def test_deleted_customer_not_found(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that deleted customers return 404.

        Validates: Requirement 1.6
        """
        customer_id = uuid.uuid4()

        # Simulate deleted customer (repository returns None for deleted)
        mock_customer_repository.get_by_id.return_value = None

        response = client.get(f"/api/v1/customers/{customer_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
class TestCustomerFlagManagement:
    """Integration tests for customer flag management.

    Validates: Requirement 3.1-3.6
    """

    def test_update_customer_flags(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test updating customer flags.

        Validates: Requirement 3.1-3.4
        """
        customer_id = uuid.uuid4()

        original_customer = create_mock_customer(
            customer_id=customer_id,
            is_priority=False,
            is_red_flag=False,
            is_slow_payer=False,
        )

        updated_customer = create_mock_customer(
            customer_id=customer_id,
            is_priority=True,
            is_red_flag=True,
            is_slow_payer=False,
        )

        mock_customer_repository.get_by_id.return_value = original_customer
        mock_customer_repository.update_flags.return_value = updated_customer

        response = client.put(
            f"/api/v1/customers/{customer_id}/flags",
            json={
                "is_priority": True,
                "is_red_flag": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_priority"] is True
        assert data["is_red_flag"] is True

    def test_multiple_flags_can_be_active(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that multiple flags can be active simultaneously.

        Validates: Requirement 3.6
        """
        customer_id = uuid.uuid4()

        customer = create_mock_customer(
            customer_id=customer_id,
            is_priority=True,
            is_red_flag=True,
            is_slow_payer=True,
        )

        mock_customer_repository.get_by_id.return_value = customer
        mock_customer_repository.update_flags.return_value = customer

        response = client.put(
            f"/api/v1/customers/{customer_id}/flags",
            json={
                "is_priority": True,
                "is_red_flag": True,
                "is_slow_payer": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_priority"] is True
        assert data["is_red_flag"] is True
        assert data["is_slow_payer"] is True

    def test_flags_included_in_customer_response(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that flags are included when retrieving customer.

        Validates: Requirement 3.5
        """
        customer_id = uuid.uuid4()

        customer = create_mock_customer(
            customer_id=customer_id,
            is_priority=True,
            is_red_flag=False,
            is_slow_payer=True,
            is_new_customer=False,
        )

        mock_customer_repository.get_by_id.return_value = customer
        service_summary = ServiceHistorySummary(
            total_jobs=10,
            last_service_date=datetime.now(),
            total_revenue=1500.0,
        )
        mock_customer_repository.get_service_summary.return_value = service_summary

        response = client.get(f"/api/v1/customers/{customer_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["is_priority"] is True
        assert data["is_red_flag"] is False
        assert data["is_slow_payer"] is True
        assert data["is_new_customer"] is False


@pytest.mark.integration
class TestCustomerLookupOperations:
    """Integration tests for customer lookup operations.

    Validates: Requirement 11.1-11.6
    """

    def test_lookup_by_phone_exact_match(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test phone lookup with exact match.

        Validates: Requirement 11.1
        """
        customer = create_mock_customer(phone="6125551234")
        mock_customer_repository.find_by_phone.return_value = customer

        response = client.get("/api/v1/customers/lookup/phone/6125551234")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["phone"] == "6125551234"

    def test_lookup_by_phone_partial_match(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test phone lookup with partial matching.

        Validates: Requirement 11.4
        """
        customers = [
            create_mock_customer(phone="6125551234"),
            create_mock_customer(phone="6125551235"),
        ]
        mock_customer_repository.find_by_phone_partial.return_value = customers

        response = client.get(
            "/api/v1/customers/lookup/phone/612555",
            params={"partial": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_lookup_by_phone_not_found_returns_empty(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test phone lookup returns empty array when not found.

        Validates: Requirement 11.3
        """
        mock_customer_repository.find_by_phone.return_value = None

        response = client.get("/api/v1/customers/lookup/phone/9999999999")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_lookup_by_email_case_insensitive(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test email lookup is case-insensitive.

        Validates: Requirement 11.2
        """
        customer = create_mock_customer(email="john.doe@example.com")
        mock_customer_repository.find_by_email.return_value = [customer]

        response = client.get("/api/v1/customers/lookup/email/JOHN.DOE@EXAMPLE.COM")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_lookup_by_email_not_found_returns_empty(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test email lookup returns empty array when not found.

        Validates: Requirement 11.3
        """
        mock_customer_repository.find_by_email.return_value = []

        response = client.get("/api/v1/customers/lookup/email/notfound@example.com")

        assert response.status_code == 200
        data = response.json()
        assert data == []


@pytest.mark.integration
class TestDuplicatePhoneHandling:
    """Integration tests for duplicate phone number handling.

    Validates: Requirement 6.6 (Property 1: Phone Number Uniqueness)
    """

    def test_create_customer_duplicate_phone_rejected(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that duplicate phone numbers are rejected.

        Validates: Requirement 6.6
        """
        existing_customer = create_mock_customer(
            customer_id=uuid.uuid4(),
            phone="6125551234",
        )
        mock_customer_repository.find_by_phone.return_value = existing_customer

        response = client.post(
            "/api/v1/customers",
            json={
                "first_name": "New",
                "last_name": "Customer",
                "phone": "612-555-1234",  # Same phone, different format
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_update_customer_duplicate_phone_rejected(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that updating to a duplicate phone is rejected.

        Validates: Requirement 6.6
        """
        customer_id = uuid.uuid4()
        other_customer_id = uuid.uuid4()

        current_customer = create_mock_customer(
            customer_id=customer_id,
            phone="6125551111",
        )
        other_customer = create_mock_customer(
            customer_id=other_customer_id,
            phone="6125552222",
        )

        mock_customer_repository.get_by_id.return_value = current_customer
        mock_customer_repository.find_by_phone.return_value = other_customer

        response = client.put(
            f"/api/v1/customers/{customer_id}",
            json={"phone": "612-555-2222"},  # Phone belongs to other customer
        )

        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]


@pytest.mark.integration
class TestCommunicationPreferences:
    """Integration tests for communication preferences.

    Validates: Requirement 5.1-5.7
    """

    def test_communication_preferences_default_to_opted_out(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that new customers default to opted-out for communications.

        Validates: Requirement 5.1, 5.2 (Property 5)
        """
        customer_id = uuid.uuid4()
        customer = create_mock_customer(
            customer_id=customer_id,
            sms_opt_in=False,
            email_opt_in=False,
        )

        mock_customer_repository.find_by_phone.return_value = None
        mock_customer_repository.create.return_value = customer

        response = client.post(
            "/api/v1/customers",
            json={
                "first_name": "Test",
                "last_name": "User",
                "phone": "612-555-8888",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["sms_opt_in"] is False
        assert data["email_opt_in"] is False

    def test_update_communication_preferences(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test updating communication preferences.

        Validates: Requirement 5.3, 5.4
        """
        customer_id = uuid.uuid4()

        original_customer = create_mock_customer(
            customer_id=customer_id,
            sms_opt_in=False,
            email_opt_in=False,
        )

        updated_customer = create_mock_customer(
            customer_id=customer_id,
            sms_opt_in=True,
            email_opt_in=True,
        )

        mock_customer_repository.get_by_id.return_value = original_customer
        mock_customer_repository.update.return_value = updated_customer

        response = client.put(
            f"/api/v1/customers/{customer_id}",
            json={
                "sms_opt_in": True,
                "email_opt_in": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sms_opt_in"] is True
        assert data["email_opt_in"] is True

    def test_communication_preferences_included_in_response(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that communication preferences are included in customer response.

        Validates: Requirement 5.5
        """
        customer_id = uuid.uuid4()
        customer = create_mock_customer(
            customer_id=customer_id,
            sms_opt_in=True,
            email_opt_in=False,
        )

        mock_customer_repository.get_by_id.return_value = customer
        summary = ServiceHistorySummary(
            total_jobs=0,
            last_service_date=None,
            total_revenue=0.0,
        )
        mock_customer_repository.get_service_summary.return_value = summary

        response = client.get(f"/api/v1/customers/{customer_id}")

        assert response.status_code == 200
        data = response.json()
        assert "sms_opt_in" in data
        assert "email_opt_in" in data
        assert data["sms_opt_in"] is True
        assert data["email_opt_in"] is False


@pytest.mark.integration
class TestServiceHistoryIntegration:
    """Integration tests for service history.

    Validates: Requirement 7.1-7.8
    """

    def test_get_service_history_summary(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test getting service history summary for a customer.

        Validates: Requirement 7.2, 7.8
        """
        customer_id = uuid.uuid4()
        customer = create_mock_customer(customer_id=customer_id)

        mock_customer_repository.get_by_id.return_value = customer
        summary = ServiceHistorySummary(
            total_jobs=15,
            last_service_date=datetime.now(),
            total_revenue=3500.0,
        )
        mock_customer_repository.get_service_summary.return_value = summary

        response = client.get(f"/api/v1/customers/{customer_id}/service-history")

        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 15
        assert data["total_revenue"] == 3500.0
        assert "last_service_date" in data

    def test_service_history_included_in_customer_detail(
        self,
        client: TestClient,
        mock_customer_repository: AsyncMock,
    ) -> None:
        """Test that service history is included in customer detail response.

        Validates: Requirement 7.2
        """
        customer_id = uuid.uuid4()
        customer = create_mock_customer(customer_id=customer_id)

        mock_customer_repository.get_by_id.return_value = customer
        summary = ServiceHistorySummary(
            total_jobs=5,
            last_service_date=datetime.now(),
            total_revenue=750.0,
        )
        mock_customer_repository.get_service_summary.return_value = summary

        response = client.get(f"/api/v1/customers/{customer_id}")

        assert response.status_code == 200
        data = response.json()
        assert "service_history_summary" in data
        assert data["service_history_summary"]["total_jobs"] == 5
        assert data["service_history_summary"]["total_revenue"] == 750.0
