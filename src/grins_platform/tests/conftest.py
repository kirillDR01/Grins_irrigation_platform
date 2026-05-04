"""
Shared test fixtures for all test tiers.

This module provides fixtures for unit, functional, and integration tests
including database sessions, test clients, and sample data generators.

Validates: Requirement 9.5
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Default to NullProvider in tests so SMSService(session) without an explicit
# provider never reaches CallRail/Twilio. Tests that exercise a specific
# provider should use ``patch.dict(os.environ, {"SMS_PROVIDER": "..."})``.
os.environ.setdefault("SMS_PROVIDER", "null")

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
# Default auth override for tests that build their own FastAPI app
# =============================================================================
#
# CR-5 added ``CurrentActiveUser`` dependencies to many endpoints. Existing
# unit tests that construct a test app via ``create_app()`` and hit those
# endpoints now fail with 401 unless they override the auth dependencies.
#
# Rather than touch every test file, this module-level autouse fixture
# installs a default override on every FastAPI app produced by
# ``create_app`` in the current test session. Tests that exercise auth
# explicitly (e.g. ``test_auth_guards.py``) use ``grins_platform.main.app``
# directly, which is NOT touched here.


def _install_auth_overrides(application: object) -> object:
    """Override ``get_current_active_user`` / ``get_current_user`` deps.

    Installs a fake Staff-like MagicMock so dependent endpoints pass
    authentication in unit tests. Idempotent — safe to call multiple times
    on the same app.
    """
    from unittest.mock import MagicMock  # noqa: PLC0415

    from grins_platform.api.v1.auth_dependencies import (  # noqa: PLC0415
        get_current_active_user,
        get_current_user,
    )

    fake_user = MagicMock()
    fake_user.id = uuid.uuid4()
    fake_user.username = "test-admin"
    fake_user.email = "test-admin@example.com"
    fake_user.role = "admin"
    fake_user.is_active = True

    application.dependency_overrides[get_current_user] = lambda: fake_user  # type: ignore[attr-defined]
    application.dependency_overrides[get_current_active_user] = (  # type: ignore[attr-defined]
        lambda: fake_user
    )
    return application


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Reset the slowapi limiter's in-memory storage between tests.

    The ``limiter`` is a module-level singleton (``middleware/rate_limit.py``).
    Without this reset, requests across tests share the same per-IP bucket and
    earlier tests can push the bucket over the limit, causing later tests to
    receive 429 instead of the expected status.
    """
    from grins_platform.middleware.rate_limit import limiter  # noqa: PLC0415

    limiter.reset()


@pytest.fixture(autouse=True)
def _patch_create_app_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrap ``grins_platform.app.create_app`` so every returned app has
    auth overridden. Monkeypatches the attribute on the ``app`` module
    and on test modules that may have already imported the symbol.
    """
    import importlib  # noqa: PLC0415
    import sys  # noqa: PLC0415

    app_module = importlib.import_module("grins_platform.app")
    original = app_module.create_app

    def _wrapped() -> object:
        return _install_auth_overrides(original())

    # Patch the canonical location first.
    monkeypatch.setattr(app_module, "create_app", _wrapped)

    # Then patch every already-imported test module that did
    # ``from grins_platform.app import create_app``. Those modules hold
    # a direct reference to the original function; without this loop
    # they keep calling the un-wrapped version.
    for module in list(sys.modules.values()):
        if module is None or module is app_module:
            continue
        if getattr(module, "create_app", None) is original:
            monkeypatch.setattr(module, "create_app", _wrapped)


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
