"""
Cross-component integration tests.

Tests for interactions between authentication, schedule clear, and invoice
components to verify role-based access control across features.

Validates: Requirements 17.5-17.9
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_user,
    require_admin,
    require_manager_or_admin,
)
from grins_platform.api.v1.invoices import get_invoice_service
from grins_platform.api.v1.schedule_clear import get_schedule_clear_service
from grins_platform.main import app
from grins_platform.models.enums import (
    InvoiceStatus,
    StaffRole,
    UserRole,
)
from grins_platform.schemas.invoice import InvoiceResponse
from grins_platform.schemas.schedule_clear import ScheduleClearResponse
from grins_platform.services.invoice_service import InvoiceService
from grins_platform.services.schedule_clear_service import ScheduleClearService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


def _raise_forbidden() -> None:
    """Helper function to raise 403 Forbidden for testing."""
    raise HTTPException(status_code=403, detail="Forbidden")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_admin_user() -> MagicMock:
    """Create a mock admin user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin User"
    user.username = "admin"
    user.email = "admin@grins.com"
    user.role = StaffRole.ADMIN.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def sample_manager_user() -> MagicMock:
    """Create a mock manager user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Manager User"
    user.username = "manager"
    user.email = "manager@grins.com"
    user.role = UserRole.MANAGER.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def sample_tech_user() -> MagicMock:
    """Create a mock tech user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Tech User"
    user.username = "tech"
    user.email = "tech@grins.com"
    user.role = StaffRole.TECH.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def mock_invoice_service() -> MagicMock:
    """Create a mock invoice service."""
    service = MagicMock(spec=InvoiceService)
    service.generate_from_job = AsyncMock()
    service.send_lien_warning = AsyncMock()
    service.mark_lien_filed = AsyncMock()
    return service


@pytest.fixture
def mock_schedule_clear_service() -> MagicMock:
    """Create a mock schedule clear service."""
    service = MagicMock(spec=ScheduleClearService)
    service.clear_schedule = AsyncMock()
    service.get_recent_clears = AsyncMock()
    return service


@pytest.fixture
def sample_invoice_response() -> InvoiceResponse:
    """Create a sample invoice response."""
    return InvoiceResponse(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        invoice_number="INV-2025-0001",
        amount=Decimal("150.00"),
        late_fee_amount=Decimal("0.00"),
        total_amount=Decimal("150.00"),
        invoice_date=date.today(),
        due_date=date.today(),
        status=InvoiceStatus.DRAFT,
        payment_method=None,
        payment_reference=None,
        paid_at=None,
        paid_amount=None,
        reminder_count=0,
        last_reminder_sent=None,
        lien_eligible=False,
        lien_warning_sent=None,
        lien_filed_date=None,
        line_items=[],
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_schedule_clear_response() -> ScheduleClearResponse:
    """Create a sample schedule clear response."""
    return ScheduleClearResponse(
        audit_id=uuid.uuid4(),
        schedule_date=date.today(),
        appointments_deleted=5,
        jobs_reset=3,
        cleared_at=datetime.now(timezone.utc),
    )


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# Test Invoice Generation Requires Auth
# =============================================================================


@pytest.mark.integration
class TestInvoiceGenerationRequiresAuth:
    """Tests that invoice generation requires authentication."""

    @pytest.mark.asyncio
    async def test_generate_invoice_without_auth_returns_401(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that generating invoice without auth returns 401.

        Validates: Requirement 17.7
        """
        job_id = uuid.uuid4()
        response = await async_client.post(
            f"/api/v1/invoices/generate-from-job/{job_id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_invoice_with_tech_returns_403(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
        mock_invoice_service: MagicMock,
    ) -> None:
        """Test that tech user cannot generate invoices.

        Validates: Requirement 17.7
        """
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        # Tech should be blocked by require_manager_or_admin
        app.dependency_overrides[require_manager_or_admin] = _raise_forbidden

        try:
            job_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/generate-from-job/{job_id}",
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_invoice_with_manager_succeeds(
        self,
        async_client: AsyncClient,
        sample_manager_user: MagicMock,
        mock_invoice_service: MagicMock,
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test that manager can generate invoices.

        Validates: Requirement 17.7
        """
        mock_invoice_service.generate_from_job.return_value = sample_invoice_response

        app.dependency_overrides[get_current_user] = lambda: sample_manager_user
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service

        try:
            job_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/generate-from-job/{job_id}",
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_invoice_with_admin_succeeds(
        self,
        async_client: AsyncClient,
        sample_admin_user: MagicMock,
        mock_invoice_service: MagicMock,
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test that admin can generate invoices.

        Validates: Requirement 17.7
        """
        mock_invoice_service.generate_from_job.return_value = sample_invoice_response

        app.dependency_overrides[get_current_user] = lambda: sample_admin_user
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_admin_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service

        try:
            job_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/generate-from-job/{job_id}",
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Schedule Clear Requires Manager Role
# =============================================================================


@pytest.mark.integration
class TestScheduleClearRequiresManagerRole:
    """Tests that schedule clear requires manager or admin role."""

    @pytest.mark.asyncio
    async def test_clear_schedule_without_auth_returns_401(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that clearing schedule without auth returns 401.

        Validates: Requirement 17.5
        """
        response = await async_client.post(
            "/api/v1/schedule/clear",
            json={"schedule_date": str(date.today())},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_clear_schedule_with_tech_returns_403(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
        mock_schedule_clear_service: MagicMock,
    ) -> None:
        """Test that tech user cannot clear schedules.

        Validates: Requirement 17.5
        """
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user
        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = _raise_forbidden

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": str(date.today())},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clear_schedule_with_manager_succeeds(
        self,
        async_client: AsyncClient,
        sample_manager_user: MagicMock,
        mock_schedule_clear_service: MagicMock,
        sample_schedule_clear_response: ScheduleClearResponse,
    ) -> None:
        """Test that manager can clear schedules.

        Validates: Requirement 17.5
        """
        mock_schedule_clear_service.clear_schedule.return_value = (
            sample_schedule_clear_response
        )

        app.dependency_overrides[get_current_user] = lambda: sample_manager_user
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user
        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": str(date.today())},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clear_schedule_with_admin_succeeds(
        self,
        async_client: AsyncClient,
        sample_admin_user: MagicMock,
        mock_schedule_clear_service: MagicMock,
        sample_schedule_clear_response: ScheduleClearResponse,
    ) -> None:
        """Test that admin can clear schedules.

        Validates: Requirement 17.6
        """
        mock_schedule_clear_service.clear_schedule.return_value = (
            sample_schedule_clear_response
        )

        app.dependency_overrides[get_current_user] = lambda: sample_admin_user
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_admin_user
        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": str(date.today())},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_recent_clears_with_tech_returns_403(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
        mock_schedule_clear_service: MagicMock,
    ) -> None:
        """Test that tech user cannot view recent clears.

        Validates: Requirement 17.5
        """
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user
        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = _raise_forbidden

        try:
            response = await async_client.get("/api/v1/schedule/clear/recent")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Lien Warning Requires Admin Role
# =============================================================================


@pytest.mark.integration
class TestLienWarningRequiresAdminRole:
    """Tests that lien warning requires admin role."""

    @pytest.mark.asyncio
    async def test_send_lien_warning_without_auth_returns_401(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that sending lien warning without auth returns 401.

        Validates: Requirement 17.8
        """
        invoice_id = uuid.uuid4()
        response = await async_client.post(
            f"/api/v1/invoices/{invoice_id}/lien-warning",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_send_lien_warning_with_tech_returns_403(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
        mock_invoice_service: MagicMock,
    ) -> None:
        """Test that tech user cannot send lien warnings.

        Validates: Requirement 17.8
        """
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_admin] = _raise_forbidden

        try:
            invoice_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/lien-warning",
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_send_lien_warning_with_manager_returns_403(
        self,
        async_client: AsyncClient,
        sample_manager_user: MagicMock,
        mock_invoice_service: MagicMock,
    ) -> None:
        """Test that manager cannot send lien warnings (admin only).

        Validates: Requirement 17.8
        """
        app.dependency_overrides[get_current_user] = lambda: sample_manager_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_admin] = _raise_forbidden

        try:
            invoice_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/lien-warning",
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_send_lien_warning_with_admin_succeeds(
        self,
        async_client: AsyncClient,
        sample_admin_user: MagicMock,
        mock_invoice_service: MagicMock,
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test that admin can send lien warnings.

        Validates: Requirement 17.8
        """
        mock_invoice_service.send_lien_warning.return_value = sample_invoice_response

        app.dependency_overrides[get_current_user] = lambda: sample_admin_user
        app.dependency_overrides[require_admin] = lambda: sample_admin_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service

        try:
            invoice_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/lien-warning",
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mark_lien_filed_with_tech_returns_403(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
        mock_invoice_service: MagicMock,
    ) -> None:
        """Test that tech user cannot mark lien as filed.

        Validates: Requirement 17.9
        """
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_admin] = _raise_forbidden

        try:
            invoice_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/lien-filed",
                json={"filing_date": str(date.today())},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mark_lien_filed_with_manager_returns_403(
        self,
        async_client: AsyncClient,
        sample_manager_user: MagicMock,
        mock_invoice_service: MagicMock,
    ) -> None:
        """Test that manager cannot mark lien as filed (admin only).

        Validates: Requirement 17.9
        """
        app.dependency_overrides[get_current_user] = lambda: sample_manager_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_admin] = _raise_forbidden

        try:
            invoice_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/lien-filed",
                json={"filing_date": str(date.today())},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mark_lien_filed_with_admin_succeeds(
        self,
        async_client: AsyncClient,
        sample_admin_user: MagicMock,
        mock_invoice_service: MagicMock,
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test that admin can mark lien as filed.

        Validates: Requirement 17.9
        """
        mock_invoice_service.mark_lien_filed.return_value = sample_invoice_response

        app.dependency_overrides[get_current_user] = lambda: sample_admin_user
        app.dependency_overrides[require_admin] = lambda: sample_admin_user
        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service

        try:
            invoice_id = uuid.uuid4()
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/lien-filed",
                json={"filing_date": str(date.today())},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
