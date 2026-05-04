"""
Cross-feature regression tests for ASAP Platform Fixes.

Verifies that changes from the ASAP fixes (auth token duration, lead service
modifications, customer search changes) do not break existing functionality
across the platform.

Risk areas tested:
- Auth token changes (Req 3) → all authenticated API endpoints
- Lead service changes (Req 5, 6, 7) → Google Sheets poller, lead-to-estimate, SMS
- Customer search changes (Req 1) → customer detail, update, property listing

Validates: Requirements 9.4, 9.5, 9.6
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_auth_service,
    get_current_active_user,
    get_current_user,
    require_manager_or_admin,
)
from grins_platform.api.v1.dependencies import (
    get_customer_service,
    get_job_service,
    get_property_service,
)
from grins_platform.api.v1.leads import _get_lead_service
from grins_platform.exceptions import CustomerNotFoundError
from grins_platform.exceptions.auth import InvalidTokenError
from grins_platform.main import app
from grins_platform.models.enums import (
    LeadSituation,
    LeadStatus,
    StaffRole,
    UserRole,
)
from grins_platform.schemas.customer import PaginatedCustomerResponse
from grins_platform.schemas.lead import (
    LeadConversionRequest,
    LeadResponse,
    LeadSubmission,
    PaginatedLeadResponse,
)
from grins_platform.services.auth_service import AuthService
from grins_platform.services.lead_service import LeadService

# =============================================================================
# Helpers
# =============================================================================


def _mock_admin() -> MagicMock:
    """Create a mock admin staff member."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Admin User"
    staff.phone = "6125550001"
    staff.email = "admin@grins.com"
    staff.role = StaffRole.ADMIN.value
    staff.username = "admin"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


def _make_lead_model(**overrides: object) -> MagicMock:
    """Create a mock Lead model instance."""
    now = datetime.now(tz=timezone.utc)
    lead = MagicMock()
    lead.id = overrides.get("id", uuid.uuid4())
    lead.name = overrides.get("name", "Test Lead")
    lead.phone = overrides.get("phone", "6125551234")
    lead.email = overrides.get("email")
    lead.zip_code = overrides.get("zip_code", "55424")
    lead.situation = overrides.get("situation", LeadSituation.NEW_SYSTEM.value)
    lead.notes = overrides.get("notes")
    lead.source_site = overrides.get("source_site", "residential")
    lead.lead_source = overrides.get("lead_source", "website")
    lead.source_detail = overrides.get("source_detail")
    lead.intake_tag = overrides.get("intake_tag", "schedule")
    lead.sms_consent = overrides.get("sms_consent", False)
    lead.terms_accepted = overrides.get("terms_accepted", False)
    lead.status = overrides.get("status", LeadStatus.NEW.value)
    lead.assigned_to = overrides.get("assigned_to")
    lead.customer_id = overrides.get("customer_id")
    lead.contacted_at = overrides.get("contacted_at")
    lead.converted_at = overrides.get("converted_at")
    lead.city = overrides.get("city")
    lead.state = overrides.get("state")
    lead.address = overrides.get("address")
    lead.action_tags = overrides.get("action_tags")
    lead.customer_type = overrides.get("customer_type")
    lead.property_type = overrides.get("property_type")
    lead.created_at = overrides.get("created_at", now)
    lead.updated_at = overrides.get("updated_at", now)
    lead.moved_to = overrides.get("moved_to")
    lead.moved_at = overrides.get("moved_at")
    lead.last_contacted_at = overrides.get("last_contacted_at")
    lead.job_requested = overrides.get("job_requested")
    return lead


def _make_lead_response(**overrides: object) -> LeadResponse:
    """Create a LeadResponse with sensible defaults."""
    now = datetime.now(tz=timezone.utc)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": "Test Lead",
        "phone": "6125551234",
        "email": None,
        "zip_code": "55424",
        "situation": LeadSituation.NEW_SYSTEM,
        "notes": None,
        "source_site": "residential",
        "lead_source": "website",
        "source_detail": None,
        "intake_tag": "schedule",
        "sms_consent": False,
        "terms_accepted": False,
        "status": LeadStatus.NEW,
        "assigned_to": None,
        "customer_id": None,
        "contacted_at": None,
        "converted_at": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return LeadResponse(**defaults)  # type: ignore[arg-type]


def _make_mock_customer(**overrides: object) -> MagicMock:
    """Create a mock Customer model instance."""
    customer = MagicMock()
    customer.id = overrides.get("id", uuid.uuid4())
    customer.first_name = overrides.get("first_name", "John")
    customer.last_name = overrides.get("last_name", "Doe")
    customer.phone = overrides.get("phone", "6125551234")
    customer.email = overrides.get("email", "john@example.com")
    customer.status = overrides.get("status", "active")
    customer.is_priority = overrides.get("is_priority", False)
    customer.is_red_flag = overrides.get("is_red_flag", False)
    customer.is_slow_payer = overrides.get("is_slow_payer", False)
    customer.is_new_customer = overrides.get("is_new_customer", True)
    customer.sms_opt_in = overrides.get("sms_opt_in", False)
    customer.email_opt_in = overrides.get("email_opt_in", False)
    customer.lead_source = overrides.get("lead_source", "website")
    customer.is_deleted = overrides.get("is_deleted", False)
    customer.internal_notes = overrides.get("internal_notes")
    customer.preferred_service_times = overrides.get("preferred_service_times")
    customer.properties = overrides.get("properties", [])
    customer.created_at = datetime.now(timezone.utc)
    customer.updated_at = datetime.now(timezone.utc)
    return customer


def _make_mock_property(**overrides: object) -> MagicMock:
    """Create a mock Property model instance."""
    prop = MagicMock()
    prop.id = overrides.get("id", uuid.uuid4())
    prop.customer_id = overrides.get("customer_id", uuid.uuid4())
    prop.address = overrides.get("address", "123 Main St")
    prop.city = overrides.get("city", "Eden Prairie")
    prop.state = overrides.get("state", "MN")
    prop.zip_code = overrides.get("zip_code", "55344")
    prop.zone_count = overrides.get("zone_count", 6)
    prop.system_type = overrides.get("system_type", "standard")
    prop.property_type = overrides.get("property_type", "residential")
    prop.is_primary = overrides.get("is_primary", True)
    prop.access_instructions = overrides.get("access_instructions")
    prop.gate_code = overrides.get("gate_code")
    prop.has_dogs = overrides.get("has_dogs", False)
    prop.special_notes = overrides.get("special_notes")
    prop.latitude = overrides.get("latitude")
    prop.longitude = overrides.get("longitude")
    prop.created_at = datetime.now(timezone.utc)
    prop.updated_at = datetime.now(timezone.utc)
    return prop


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Create a mock auth service for testing."""
    service = MagicMock(spec=AuthService)
    service.authenticate = AsyncMock()
    service.verify_access_token = MagicMock()
    service.verify_refresh_token = MagicMock()
    service.refresh_access_token = AsyncMock()
    service.change_password = AsyncMock()
    service.get_current_user = AsyncMock()
    service.get_user_role = MagicMock(return_value=UserRole.ADMIN)
    return service


@pytest.fixture
def admin_user() -> MagicMock:
    """Create a mock admin user."""
    return _mock_admin()


@pytest.fixture
def mock_customer_service() -> AsyncMock:
    """Create a mock CustomerService."""
    return AsyncMock()


@pytest.fixture
def mock_job_service() -> AsyncMock:
    """Create a mock JobService."""
    return AsyncMock()


@pytest.fixture
def mock_property_service() -> AsyncMock:
    """Create a mock PropertyService."""
    return AsyncMock()


@pytest.fixture
def mock_lead_service() -> AsyncMock:
    """Create a mock LeadService."""
    return AsyncMock()


@pytest_asyncio.fixture
async def authenticated_client(
    mock_auth_service: MagicMock,
    admin_user: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated async HTTP client with admin role."""
    mock_auth_service.verify_access_token.return_value = {
        "sub": str(admin_user.id),
        "role": "admin",
        "type": "access",
    }
    mock_auth_service.get_current_user.return_value = admin_user
    mock_auth_service.get_user_role.return_value = UserRole.ADMIN

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    app.dependency_overrides[require_manager_or_admin] = lambda: admin_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({"Authorization": "Bearer valid-test-token"})
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Task 11.1: Auth Token Changes Don't Break Authenticated Endpoints
# Validates: Requirement 9.4
# =============================================================================


@pytest.mark.integration
class TestAuthTokenRegressionCustomerAPI:
    """Verify auth token changes don't break customer API CRUD."""

    @pytest.mark.asyncio
    async def test_customer_list_accepts_valid_token(
        self,
        authenticated_client: AsyncClient,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Customer list endpoint still works with valid auth tokens.

        Validates: Requirement 9.4
        """
        mock_customer_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        app.dependency_overrides[get_customer_service] = lambda: mock_customer_service

        response = await authenticated_client.get("/api/v1/customers")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_customer_create_accepts_valid_token(
        self,
        authenticated_client: AsyncClient,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Customer create endpoint still works with valid auth tokens.

        Validates: Requirement 9.4
        """
        customer = _make_mock_customer()
        mock_customer_service.create_customer.return_value = customer
        mock_customer_service.find_by_phone.return_value = None
        app.dependency_overrides[get_customer_service] = lambda: mock_customer_service

        response = await authenticated_client.post(
            "/api/v1/customers",
            json={
                "first_name": "John",
                "last_name": "Doe",
                "phone": "6125551234",
            },
        )
        # 201 or 200 — just verify not 401/403
        assert response.status_code not in (401, 403)


@pytest.mark.integration
class TestAuthTokenRegressionLeadAPI:
    """Verify auth token changes don't break lead API CRUD."""

    @pytest.mark.asyncio
    async def test_lead_list_accepts_valid_token(
        self,
        authenticated_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Lead list endpoint still works with valid auth tokens.

        Validates: Requirement 9.4
        """
        mock_lead_service.list_leads.return_value = PaginatedLeadResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        app.dependency_overrides[_get_lead_service] = lambda: mock_lead_service

        response = await authenticated_client.get("/api/v1/leads")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lead_get_accepts_valid_token(
        self,
        authenticated_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Lead detail endpoint still works with valid auth tokens.

        Validates: Requirement 9.4
        """
        lead_id = uuid.uuid4()
        mock_lead_service.get_lead.return_value = _make_lead_response(id=lead_id)
        app.dependency_overrides[_get_lead_service] = lambda: mock_lead_service

        response = await authenticated_client.get(f"/api/v1/leads/{lead_id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lead_delete_accepts_valid_token(
        self,
        authenticated_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Lead delete endpoint still works with valid auth tokens.

        Validates: Requirement 9.4
        """
        lead_id = uuid.uuid4()
        mock_lead_service.delete_lead.return_value = None
        app.dependency_overrides[_get_lead_service] = lambda: mock_lead_service

        response = await authenticated_client.delete(f"/api/v1/leads/{lead_id}")
        assert response.status_code in (200, 204)


@pytest.mark.integration
class TestAuthTokenRegressionJobAPI:
    """Verify auth token changes don't break job API CRUD."""

    @pytest.mark.asyncio
    async def test_job_list_accepts_valid_token(
        self,
        authenticated_client: AsyncClient,
        mock_job_service: AsyncMock,
    ) -> None:
        """Job list endpoint still works with valid auth tokens.

        Validates: Requirement 9.4
        """
        mock_job_service.list_jobs.return_value = ([], 0)
        app.dependency_overrides[get_job_service] = lambda: mock_job_service

        response = await authenticated_client.get("/api/v1/jobs")
        assert response.status_code == 200


@pytest.mark.integration
class TestAuthTokenRegressionInvoiceAPI:
    """Verify auth token changes don't break invoice API.

    Invoice endpoints use ManagerOrAdminUser auth dependency,
    so they properly reject unauthenticated requests.
    """

    @pytest.mark.asyncio
    async def test_invoice_list_rejects_without_token(self) -> None:
        """Invoice list endpoint rejects requests without auth token.

        Validates: Requirement 9.4
        """
        app.dependency_overrides.clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/invoices")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invoice_create_rejects_without_token(self) -> None:
        """Invoice create endpoint rejects requests without auth token.

        Validates: Requirement 9.4
        """
        app.dependency_overrides.clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/invoices",
                json={"job_id": str(uuid.uuid4())},
            )
            assert response.status_code == 401


@pytest.mark.integration
class TestAuthTokenRegressionScheduleAPI:
    """Verify auth token changes don't break schedule API."""

    @pytest.mark.asyncio
    async def test_schedule_jobs_ready_accepts_valid_token(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Schedule jobs-ready endpoint still works with valid auth tokens.

        Validates: Requirement 9.4
        """
        response = await authenticated_client.get(
            "/api/v1/schedule/jobs-ready-to-schedule",
        )
        # Not 401/403 — may be 200 or 500 depending on DB
        assert response.status_code not in (401, 403)


@pytest.mark.integration
class TestAuthTokenRegressionAgreementAPI:
    """Verify auth token changes don't break agreement API.

    Agreement endpoints use ManagerOrAdminUser auth dependency.
    """

    @pytest.mark.asyncio
    async def test_agreement_list_rejects_without_token(self) -> None:
        """Agreement list endpoint rejects requests without auth token.

        Validates: Requirement 9.4
        """
        app.dependency_overrides.clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/agreements")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_agreement_tiers_rejects_without_token(self) -> None:
        """Agreement tiers endpoint rejects requests without auth token.

        Validates: Requirement 9.4
        """
        app.dependency_overrides.clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/agreement-tiers")
            assert response.status_code == 401


@pytest.mark.integration
class TestAuthTokenRegressionRefreshFlow:
    """Verify token refresh still works after duration changes."""

    @pytest.mark.asyncio
    async def test_refresh_token_still_returns_new_access_token(
        self,
        mock_auth_service: MagicMock,
    ) -> None:
        """Token refresh endpoint still issues new access tokens.

        Validates: Requirement 9.4
        """
        mock_auth_service.verify_refresh_token.return_value = {
            "sub": str(uuid.uuid4()),
            "type": "refresh",
        }
        mock_auth_service.refresh_access_token.return_value = (
            "new_access_token",
            60 * 60,
        )

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/refresh",
                    cookies={"refresh_token": "valid_refresh_token"},
                )
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert data["expires_in"] == 60 * 60
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_expired_refresh_token_still_rejected(
        self,
        mock_auth_service: MagicMock,
    ) -> None:
        """Expired refresh tokens are still properly rejected.

        Validates: Requirement 9.4
        """
        mock_auth_service.refresh_access_token.side_effect = InvalidTokenError(
            "Token expired",
        )

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/refresh",
                    cookies={"refresh_token": "expired_token"},
                )
                assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Task 11.2: Lead Service Changes Don't Break Existing Flows
# Validates: Requirement 9.5
# =============================================================================


@pytest.mark.integration
class TestLeadServiceRegressionGoogleSheetsPoller:
    """Verify lead service changes don't break Google Sheets poller flow.

    The Google Sheets poller creates leads via submit_lead with
    lead_source="google_sheets". After ASAP changes to delete_lead,
    convert_lead, and create_manual_lead, the poller flow must still work.

    Validates: Requirement 9.5
    """

    @pytest.mark.asyncio
    async def test_google_sheets_lead_creation_still_works(self) -> None:
        """Google Sheets poller lead creation via submit_lead still works.

        Validates: Requirement 9.5
        """
        mock_lead_repo = AsyncMock()
        mock_customer_service = AsyncMock()
        mock_job_service = AsyncMock()
        mock_staff_repo = AsyncMock()

        new_lead = _make_lead_model(
            lead_source="google_sheets",
            source_detail="Sheet Row 42",
            status=LeadStatus.NEW.value,
        )
        mock_lead_repo.create = AsyncMock(return_value=new_lead)
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        mock_lead_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)

        service = LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=mock_staff_repo,
        )

        submission = LeadSubmission(
            name="Sheet Lead",
            phone="(612) 555-7777",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
            address="456 Oak Ave, Minneapolis, MN 55424",
        )
        result = await service.submit_lead(submission)

        assert result.success is True
        assert result.lead_id == new_lead.id
        mock_lead_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_google_sheets_duplicate_detection_still_works(self) -> None:
        """Duplicate detection for Google Sheets leads still works.

        Validates: Requirement 9.5
        """
        mock_lead_repo = AsyncMock()
        mock_customer_service = AsyncMock()
        mock_job_service = AsyncMock()
        mock_staff_repo = AsyncMock()

        existing_lead = _make_lead_model(
            phone="6125557777",
            lead_source="google_sheets",
            email=None,
            address=None,
            notes=None,
        )
        # No recent duplicate (within 24h) — allows merge path
        mock_lead_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        # Active lead found by phone — triggers merge/update
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(
            return_value=existing_lead,
        )
        mock_lead_repo.update = AsyncMock(return_value=existing_lead)

        service = LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=mock_staff_repo,
        )

        submission = LeadSubmission(
            name="Sheet Lead Dup",
            phone="(612) 555-7777",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            source_site="residential",
            address="456 Oak Ave, Minneapolis, MN 55424",
        )
        result = await service.submit_lead(submission)

        assert result.success is True
        assert result.lead_id == existing_lead.id
        # Should update (merge), not create
        mock_lead_repo.create.assert_not_called()
        mock_lead_repo.update.assert_called_once()


@pytest.mark.integration
class TestLeadServiceRegressionLeadToEstimate:
    """Verify lead service changes don't break lead-to-estimate pipeline.

    Validates: Requirement 9.5
    """

    @pytest.mark.asyncio
    async def test_lead_conversion_still_creates_customer_and_job(self) -> None:
        """Lead conversion still creates customer and job for estimate pipeline.

        Validates: Requirement 9.5
        """
        mock_lead_repo = AsyncMock()
        mock_customer_service = AsyncMock()
        mock_job_service = AsyncMock()
        mock_staff_repo = AsyncMock()

        lead_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        qualified_lead = _make_lead_model(
            id=lead_id,
            name="Estimate Lead",
            phone="6125558888",
            status=LeadStatus.QUALIFIED.value,
            situation=LeadSituation.NEW_SYSTEM.value,
        )
        mock_lead_repo.get_by_id = AsyncMock(return_value=qualified_lead)

        customer = MagicMock()
        customer.id = customer_id
        customer.first_name = "Estimate"
        customer.last_name = "Lead"
        mock_customer_service.create_customer = AsyncMock(return_value=customer)

        job = MagicMock()
        job.id = job_id
        mock_job_service.create_job = AsyncMock(return_value=job)

        converted_lead = _make_lead_model(
            id=lead_id,
            status=LeadStatus.CONVERTED.value,
            customer_id=customer_id,
        )
        mock_lead_repo.update = AsyncMock(return_value=converted_lead)

        service = LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=mock_staff_repo,
        )

        conversion = LeadConversionRequest(
            create_job=True,
            job_description="New irrigation system estimate",
            force=True,
        )
        result = await service.convert_lead(lead_id, conversion)

        assert result.success is True
        assert result.customer_id == customer_id
        assert result.job_id == job_id
        mock_customer_service.create_customer.assert_called_once()
        mock_job_service.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_lead_conversion_without_job_still_works(self) -> None:
        """Lead conversion without job creation still works.

        Validates: Requirement 9.5
        """
        mock_lead_repo = AsyncMock()
        mock_customer_service = AsyncMock()
        mock_job_service = AsyncMock()
        mock_staff_repo = AsyncMock()

        lead_id = uuid.uuid4()
        customer_id = uuid.uuid4()

        lead = _make_lead_model(
            id=lead_id,
            name="No Job Lead",
            status=LeadStatus.QUALIFIED.value,
        )
        mock_lead_repo.get_by_id = AsyncMock(return_value=lead)

        customer = MagicMock()
        customer.id = customer_id
        mock_customer_service.create_customer = AsyncMock(return_value=customer)

        converted = _make_lead_model(
            id=lead_id,
            status=LeadStatus.CONVERTED.value,
            customer_id=customer_id,
        )
        mock_lead_repo.update = AsyncMock(return_value=converted)

        service = LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=mock_staff_repo,
        )

        conversion = LeadConversionRequest(create_job=False, force=True)
        result = await service.convert_lead(lead_id, conversion)

        assert result.success is True
        assert result.customer_id == customer_id
        assert result.job_id is None
        mock_job_service.create_job.assert_not_called()


@pytest.mark.integration
class TestLeadServiceRegressionSMSDeferred:
    """Verify lead service changes don't break lead SMS deferred processing.

    Validates: Requirement 9.5
    """

    @pytest.mark.asyncio
    async def test_sms_confirmation_still_sent_for_consenting_leads(self) -> None:
        """SMS confirmation is scheduled post-commit when lead has sms_consent=True.

        After BUG-001 fix (2026-04-14), confirmations are deferred to a
        post-commit BackgroundTasks job rather than being sent inline.
        This regression locks in that the deferred path is still scheduled.

        Validates: Requirement 9.5
        """
        from fastapi import BackgroundTasks

        mock_lead_repo = AsyncMock()
        mock_customer_service = AsyncMock()
        mock_job_service = AsyncMock()
        mock_staff_repo = AsyncMock()
        mock_sms_service = AsyncMock()

        new_lead = _make_lead_model(sms_consent=True, phone="6125559999")
        mock_lead_repo.create = AsyncMock(return_value=new_lead)
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        mock_lead_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)

        service = LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=mock_staff_repo,
            sms_service=mock_sms_service,
        )

        submission = LeadSubmission(
            name="SMS Lead",
            phone="(612) 555-9999",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            source_site="residential",
            sms_consent=True,
            address="789 Pine St, Minneapolis, MN 55424",
        )

        background_tasks = BackgroundTasks()
        result = await service.submit_lead(
            submission, background_tasks=background_tasks,
        )

        assert result.success is True
        assert len(background_tasks.tasks) == 1
        assert background_tasks.tasks[0].args == (new_lead.id,)

    @pytest.mark.asyncio
    async def test_sms_not_sent_without_consent(self) -> None:
        """SMS confirmation is NOT sent when lead has sms_consent=False.

        Validates: Requirement 9.5
        """
        mock_lead_repo = AsyncMock()
        mock_customer_service = AsyncMock()
        mock_job_service = AsyncMock()
        mock_staff_repo = AsyncMock()
        mock_sms_service = AsyncMock()

        new_lead = _make_lead_model(sms_consent=False)
        mock_lead_repo.create = AsyncMock(return_value=new_lead)
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        mock_lead_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)

        service = LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=mock_staff_repo,
            sms_service=mock_sms_service,
        )

        submission = LeadSubmission(
            name="No SMS Lead",
            phone="(612) 555-0000",
            zip_code="55424",
            situation=LeadSituation.EXPLORING,
            source_site="residential",
            address="100 Elm St, Minneapolis, MN 55424",
        )
        result = await service.submit_lead(submission)

        assert result.success is True
        mock_sms_service.send_automated_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_sms_service_unavailable_does_not_break_lead_creation(
        self,
    ) -> None:
        """Lead creation succeeds even when SMS service is unavailable.

        Validates: Requirement 9.5
        """
        mock_lead_repo = AsyncMock()
        mock_customer_service = AsyncMock()
        mock_job_service = AsyncMock()
        mock_staff_repo = AsyncMock()

        new_lead = _make_lead_model(sms_consent=True)
        mock_lead_repo.create = AsyncMock(return_value=new_lead)
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        mock_lead_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)

        service = LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=mock_staff_repo,
            sms_service=None,
        )

        submission = LeadSubmission(
            name="No SMS Service Lead",
            phone="(612) 555-1111",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            source_site="residential",
            address="200 Birch St, Minneapolis, MN 55424",
        )
        result = await service.submit_lead(submission)

        assert result.success is True
        assert result.lead_id == new_lead.id


# =============================================================================
# Task 11.3: Customer Search Changes Don't Break Customer Operations
# Validates: Requirement 9.6
# =============================================================================


@pytest.mark.integration
class TestCustomerSearchRegressionDetailRetrieval:
    """Verify customer search changes don't break customer detail retrieval.

    Validates: Requirement 9.6
    """

    @pytest.mark.asyncio
    async def test_customer_detail_retrieval_still_works(
        self,
        authenticated_client: AsyncClient,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Customer detail endpoint still returns full customer data.

        Validates: Requirement 9.6
        """
        customer_id = uuid.uuid4()
        customer = _make_mock_customer(id=customer_id)
        mock_customer_service.get_customer.return_value = customer
        app.dependency_overrides[get_customer_service] = lambda: mock_customer_service

        response = await authenticated_client.get(
            f"/api/v1/customers/{customer_id}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"

    @pytest.mark.asyncio
    async def test_customer_detail_not_found_still_returns_404(
        self,
        authenticated_client: AsyncClient,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Customer detail endpoint still returns 404 for missing customers.

        Validates: Requirement 9.6
        """
        customer_id = uuid.uuid4()
        mock_customer_service.get_customer.side_effect = CustomerNotFoundError(
            customer_id,
        )
        app.dependency_overrides[get_customer_service] = lambda: mock_customer_service

        response = await authenticated_client.get(
            f"/api/v1/customers/{customer_id}",
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestCustomerSearchRegressionUpdate:
    """Verify customer search changes don't break customer update.

    Validates: Requirement 9.6
    """

    @pytest.mark.asyncio
    async def test_customer_update_still_works(
        self,
        authenticated_client: AsyncClient,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Customer update endpoint still accepts and processes updates.

        Validates: Requirement 9.6
        """
        customer_id = uuid.uuid4()
        updated_customer = _make_mock_customer(
            id=customer_id,
            first_name="Jane",
            last_name="Smith",
        )
        mock_customer_service.update_customer.return_value = updated_customer
        app.dependency_overrides[get_customer_service] = lambda: mock_customer_service

        response = await authenticated_client.put(
            f"/api/v1/customers/{customer_id}",
            json={
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "6125551234",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Smith"


@pytest.mark.integration
class TestCustomerSearchRegressionPropertyListing:
    """Verify customer search changes don't break property listing.

    Validates: Requirement 9.6
    """

    @pytest.mark.asyncio
    async def test_customer_property_listing_still_works(
        self,
        authenticated_client: AsyncClient,
        mock_property_service: AsyncMock,
    ) -> None:
        """Property listing via customer API still works.

        Validates: Requirement 9.6
        """
        customer_id = uuid.uuid4()
        prop = _make_mock_property(customer_id=customer_id)
        mock_property_service.get_customer_properties.return_value = [prop]
        app.dependency_overrides[get_property_service] = lambda: mock_property_service

        response = await authenticated_client.get(
            f"/api/v1/customers/{customer_id}/properties",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_customer_search_with_pagination_still_works(
        self,
        authenticated_client: AsyncClient,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Customer list with search and pagination still works.

        Validates: Requirement 9.6
        """
        mock_customer_service.list_customers.return_value = PaginatedCustomerResponse(
            items=[],
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )
        app.dependency_overrides[get_customer_service] = lambda: mock_customer_service

        response = await authenticated_client.get(
            "/api/v1/customers",
            params={"search": "Alice", "page": 1, "page_size": 20},
        )
        assert response.status_code == 200
