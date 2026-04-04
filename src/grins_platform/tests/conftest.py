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
        internal_notes=None,
        preferred_service_times=None,
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


# =============================================================================
# Google Sheet Submission Fixtures
# =============================================================================


@pytest.fixture
def sample_sheet_row() -> list[str]:
    """A complete 18-column Google Sheet row."""
    return [
        "2025-01-15 10:30:00",  # timestamp (A)
        "Yes",  # spring_startup (B)
        "",  # fall_blowout (C)
        "",  # summer_tuneup (D)
        "",  # repair_existing (E)
        "",  # new_system_install (F)
        "",  # addition_to_system (G)
        "",  # additional_services_info (H)
        "ASAP",  # date_work_needed_by (I)
        "Jane Smith",  # name (J)
        "6125559876",  # phone (K)
        "jane@example.com",  # email (L)
        "Eden Prairie",  # city (M)
        "456 Oak Ave",  # address (N)
        "new",  # client_type (O)
        "residential",  # property_type (P)
        "Google",  # referral_source (Q)
        "",  # landscape_hardscape (R)
    ]


@pytest.fixture
def sample_sheet_row_factory() -> Generator[
    ...,
    None,
    None,
]:
    """Factory for generating varied sheet rows."""
    counter = 0

    def _create(
        client_type: str = "new",
        name: str | None = None,
        phone: str | None = None,
        services: dict[str, str] | None = None,
    ) -> list[str]:
        nonlocal counter
        counter += 1
        row = [""] * 18
        row[0] = f"2025-01-{counter:02d} 10:00:00"
        row[9] = name or f"Test User {counter}"
        row[10] = phone or f"612555{counter:04d}"
        row[11] = f"test{counter}@example.com"
        row[12] = "Eden Prairie"
        row[14] = client_type
        row[15] = "residential"
        if services:
            service_idx = {
                "spring_startup": 1,
                "fall_blowout": 2,
                "summer_tuneup": 3,
                "repair_existing": 4,
                "new_system_install": 5,
                "addition_to_system": 6,
            }
            for key, val in services.items():
                idx = service_idx.get(key, -1)
                if idx >= 0:
                    row[idx] = val
        return row

    yield _create  # type: ignore[misc]


@pytest.fixture
def mock_sheets_service() -> AsyncMock:
    """Create a mock GoogleSheetsService."""
    return AsyncMock()


@pytest.fixture
def mock_sheets_repository() -> AsyncMock:
    """Create a mock GoogleSheetSubmissionRepository."""
    return AsyncMock()


@pytest.fixture
def sample_submission_model(sample_sheet_row: list[str]) -> MagicMock:
    """Create a mock GoogleSheetSubmission model instance."""
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.sheet_row_number = 2
    sub.timestamp = sample_sheet_row[0]
    sub.spring_startup = sample_sheet_row[1]
    sub.fall_blowout = sample_sheet_row[2]
    sub.summer_tuneup = sample_sheet_row[3]
    sub.repair_existing = sample_sheet_row[4]
    sub.new_system_install = sample_sheet_row[5]
    sub.addition_to_system = sample_sheet_row[6]
    sub.additional_services_info = sample_sheet_row[7]
    sub.date_work_needed_by = sample_sheet_row[8]
    sub.name = sample_sheet_row[9]
    sub.phone = sample_sheet_row[10]
    sub.email = sample_sheet_row[11]
    sub.city = sample_sheet_row[12]
    sub.address = sample_sheet_row[13]
    sub.client_type = sample_sheet_row[14]
    sub.property_type = sample_sheet_row[15]
    sub.referral_source = sample_sheet_row[16]
    sub.landscape_hardscape = sample_sheet_row[17]
    sub.content_hash = None
    sub.zip_code = None
    sub.work_requested = None
    sub.agreed_to_terms = None
    sub.processing_status = "imported"
    sub.processing_error = None
    sub.lead_id = None
    sub.lead = None
    sub.imported_at = datetime.now()
    sub.created_at = datetime.now()
    sub.updated_at = datetime.now()
    return sub
