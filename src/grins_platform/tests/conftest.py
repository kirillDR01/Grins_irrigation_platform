"""
Shared test fixtures for all test tiers.

This module provides fixtures for unit, functional, and integration tests
including database sessions, test clients, and sample data generators.

Validates: Requirement 9.5
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app
from grins_platform.models.enums import (
    CustomerStatus,
    LeadSource,
    PropertyType,
    SystemType,
)
from grins_platform.schemas.customer import CustomerCreate, CustomerResponse
from grins_platform.schemas.property import PropertyCreate, PropertyResponse

# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (Tier 1)")
    config.addinivalue_line("markers", "functional: Functional tests (Tier 2)")
    config.addinivalue_line("markers", "integration: Integration tests (Tier 3)")


# =============================================================================
# Sample Data Generators
# =============================================================================


@pytest.fixture
def sample_customer_id() -> uuid.UUID:
    """Generate a sample customer UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_property_id() -> uuid.UUID:
    """Generate a sample property UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_customer_create() -> CustomerCreate:
    """Create a sample CustomerCreate schema."""
    return CustomerCreate(
        first_name="John",
        last_name="Doe",
        phone="6125551234",
        email="john.doe@example.com",
        lead_source=LeadSource.WEBSITE,
    )


@pytest.fixture
def sample_customer_create_factory() -> Generator[CustomerCreate, None, None]:
    """Factory fixture for creating unique CustomerCreate instances."""
    counter = 0

    def _create(
        first_name: str = "Test",
        last_name: str = "User",
        phone: str | None = None,
        email: str | None = None,
        lead_source: LeadSource | None = LeadSource.WEBSITE,
    ) -> CustomerCreate:
        nonlocal counter
        counter += 1
        return CustomerCreate(
            first_name=first_name,
            last_name=last_name,
            phone=phone or f"612555{counter:04d}",
            email=email or f"test{counter}@example.com",
            lead_source=lead_source,
        )

    yield _create  # type: ignore[misc]


@pytest.fixture
def sample_customer_response(sample_customer_id: uuid.UUID) -> CustomerResponse:
    """Create a sample CustomerResponse."""
    return CustomerResponse(
        id=sample_customer_id,
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
def sample_property_create() -> PropertyCreate:
    """Create a sample PropertyCreate schema."""
    return PropertyCreate(
        address="123 Main St",
        city="Eden Prairie",
        state="MN",
        zip_code="55344",
        zone_count=6,
        system_type=SystemType.STANDARD,
        property_type=PropertyType.RESIDENTIAL,
        is_primary=True,
    )


@pytest.fixture
def sample_property_create_factory() -> Generator[PropertyCreate, None, None]:
    """Factory fixture for creating unique PropertyCreate instances."""
    counter = 0

    def _create(
        address: str | None = None,
        city: str = "Eden Prairie",
        state: str = "MN",
        zip_code: str = "55344",
        zone_count: int = 6,
        system_type: SystemType = SystemType.STANDARD,
        property_type: PropertyType = PropertyType.RESIDENTIAL,
        is_primary: bool = False,
    ) -> PropertyCreate:
        nonlocal counter
        counter += 1
        return PropertyCreate(
            address=address or f"{counter} Test Street",
            city=city,
            state=state,
            zip_code=zip_code,
            zone_count=zone_count,
            system_type=system_type,
            property_type=property_type,
            is_primary=is_primary,
        )

    yield _create  # type: ignore[misc]


@pytest.fixture
def sample_property_response(
    sample_property_id: uuid.UUID,
    sample_customer_id: uuid.UUID,
) -> PropertyResponse:
    """Create a sample PropertyResponse."""
    return PropertyResponse(
        id=sample_property_id,
        customer_id=sample_customer_id,
        address="123 Main St",
        city="Eden Prairie",
        state="MN",
        zip_code="55344",
        zone_count=6,
        system_type=SystemType.STANDARD,
        property_type=PropertyType.RESIDENTIAL,
        is_primary=True,
        access_instructions=None,
        gate_code=None,
        has_dogs=False,
        special_notes=None,
        latitude=None,
        longitude=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# =============================================================================
# Mock Fixtures for Unit Tests
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
def mock_customer_model(sample_customer_id: uuid.UUID) -> MagicMock:
    """Create a mock Customer model instance."""
    customer = MagicMock()
    customer.id = sample_customer_id
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
def mock_property_model(
    sample_property_id: uuid.UUID,
    sample_customer_id: uuid.UUID,
) -> MagicMock:
    """Create a mock Property model instance."""
    prop = MagicMock()
    prop.id = sample_property_id
    prop.customer_id = sample_customer_id
    prop.address = "123 Main St"
    prop.city = "Eden Prairie"
    prop.state = "MN"
    prop.zip_code = "55344"
    prop.zone_count = 6
    prop.system_type = SystemType.STANDARD.value
    prop.property_type = PropertyType.RESIDENTIAL.value
    prop.is_primary = True
    prop.access_instructions = None
    prop.gate_code = None
    prop.has_dogs = False
    prop.special_notes = None
    prop.latitude = None
    prop.longitude = None
    prop.created_at = datetime.now()
    prop.updated_at = datetime.now()
    return prop


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Add mock authentication token
        ac.headers.update({"Authorization": "Bearer test-token"})
        yield ac
