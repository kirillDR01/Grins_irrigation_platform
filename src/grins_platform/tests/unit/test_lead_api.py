"""
Unit tests for Lead API endpoints.

Tests cover public submission (no auth), admin CRUD with auth,
status transitions, conversion, and error handling.

Validates: Requirement 1, 5, 7, 13
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
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.leads import _get_lead_service
from grins_platform.exceptions import (
    InvalidLeadStatusTransitionError,
    LeadAlreadyConvertedError,
    LeadNotFoundError,
)
from grins_platform.main import app
from grins_platform.models.enums import (
    LeadSituation,
    LeadStatus,
)
from grins_platform.schemas.lead import (
    LeadConversionResponse,
    LeadResponse,
    LeadSubmissionResponse,
    PaginatedLeadResponse,
)


@pytest.fixture
def mock_lead_service() -> AsyncMock:
    """Create a mock LeadService."""
    return AsyncMock()


@pytest.fixture
def mock_admin_user() -> MagicMock:
    """Create a mock admin user for auth."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin User"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def _sample_lead_response() -> dict[str, object]:
    """Sample lead response data."""
    lead_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    return {
        "id": lead_id,
        "name": "John Doe",
        "phone": "6125551234",
        "email": "john@example.com",
        "zip_code": "55424",
        "situation": LeadSituation.NEW_SYSTEM,
        "notes": None,
        "source_site": "residential",
        "status": LeadStatus.NEW,
        "assigned_to": None,
        "customer_id": None,
        "contacted_at": None,
        "converted_at": None,
        "created_at": now,
        "updated_at": now,
    }


@pytest_asyncio.fixture
async def public_client(
    mock_lead_service: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client for public endpoints (no auth override)."""
    app.dependency_overrides[_get_lead_service] = (
        lambda: mock_lead_service
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(
    mock_lead_service: AsyncMock,
    mock_admin_user: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with admin auth for protected endpoints."""
    app.dependency_overrides[_get_lead_service] = (
        lambda: mock_lead_service
    )
    app.dependency_overrides[get_current_user] = (
        lambda: mock_admin_user
    )
    app.dependency_overrides[get_current_active_user] = (
        lambda: mock_admin_user
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# =============================================================================
# POST /api/v1/leads — Public submission
# =============================================================================


@pytest.mark.unit
class TestSubmitLead:
    """Tests for public lead submission endpoint."""

    @pytest.mark.asyncio
    async def test_submit_valid_lead(
        self,
        public_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test successful lead submission."""
        lead_id = uuid.uuid4()
        mock_lead_service.submit_lead.return_value = (
            LeadSubmissionResponse(
                success=True,
                message="Thank you!",
                lead_id=lead_id,
            )
        )

        response = await public_client.post(
            "/api/v1/leads",
            json={
                "name": "John Doe",
                "phone": "(612) 555-1234",
                "zip_code": "55424",
                "situation": "new_system",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["lead_id"] == str(lead_id)
        mock_lead_service.submit_lead.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_validation_error(
        self,
        public_client: AsyncClient,
    ) -> None:
        """Test submission with invalid data returns 422."""
        response = await public_client.post(
            "/api/v1/leads",
            json={
                "name": "",
                "phone": "123",
                "zip_code": "abc",
                "situation": "invalid",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_honeypot_filled(
        self,
        public_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test honeypot-filled submission still returns 201."""
        mock_lead_service.submit_lead.return_value = (
            LeadSubmissionResponse(
                success=True,
                lead_id=None,
            )
        )

        response = await public_client.post(
            "/api/v1/leads",
            json={
                "name": "Bot",
                "phone": "(612) 555-9999",
                "zip_code": "55424",
                "situation": "repair",
                "website": "http://spam.com",
            },
        )

        assert response.status_code == 201


# =============================================================================
# GET /api/v1/leads — Admin list
# =============================================================================


@pytest.mark.unit
class TestListLeads:
    """Tests for admin lead listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_leads_success(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test listing leads with pagination."""
        mock_lead_service.list_leads.return_value = (
            PaginatedLeadResponse(
                items=[],
                total=0,
                page=1,
                page_size=20,
                total_pages=0,
            )
        )

        response = await admin_client.get("/api/v1/leads")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_leads_with_filters(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test listing leads with status filter."""
        mock_lead_service.list_leads.return_value = (
            PaginatedLeadResponse(
                items=[],
                total=0,
                page=1,
                page_size=20,
                total_pages=0,
            )
        )

        response = await admin_client.get(
            "/api/v1/leads?status=new&situation=repair",
        )

        assert response.status_code == 200
        mock_lead_service.list_leads.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_leads_unauthenticated(
        self,
        public_client: AsyncClient,
    ) -> None:
        """Test listing leads without auth returns 401."""
        response = await public_client.get("/api/v1/leads")

        assert response.status_code == 401


# =============================================================================
# GET /api/v1/leads/{id} — Admin get
# =============================================================================


@pytest.mark.unit
class TestGetLead:
    """Tests for admin get lead endpoint."""

    @pytest.mark.asyncio
    async def test_get_lead_success(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
        _sample_lead_response: dict[str, object],
    ) -> None:
        """Test getting a lead by ID."""
        mock_lead_service.get_lead.return_value = (
            LeadResponse(**_sample_lead_response)
        )

        lead_id = _sample_lead_response["id"]
        response = await admin_client.get(
            f"/api/v1/leads/{lead_id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_get_lead_not_found(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test getting non-existent lead returns 404."""
        lead_id = uuid.uuid4()
        mock_lead_service.get_lead.side_effect = (
            LeadNotFoundError(lead_id)
        )

        response = await admin_client.get(
            f"/api/v1/leads/{lead_id}",
        )

        assert response.status_code == 404


# =============================================================================
# PATCH /api/v1/leads/{id} — Admin update
# =============================================================================


@pytest.mark.unit
class TestUpdateLead:
    """Tests for admin update lead endpoint."""

    @pytest.mark.asyncio
    async def test_update_lead_status(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
        _sample_lead_response: dict[str, object],
    ) -> None:
        """Test updating lead status."""
        updated = {
            **_sample_lead_response,
            "status": LeadStatus.CONTACTED,
        }
        mock_lead_service.update_lead.return_value = (
            LeadResponse(**updated)
        )

        lead_id = _sample_lead_response["id"]
        response = await admin_client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"status": "contacted"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_lead_invalid_transition(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test invalid status transition returns 400."""
        lead_id = uuid.uuid4()
        mock_lead_service.update_lead.side_effect = (
            InvalidLeadStatusTransitionError(
                LeadStatus.CONVERTED,
                LeadStatus.NEW,
            )
        )

        response = await admin_client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"status": "new"},
        )

        assert response.status_code == 400


# =============================================================================
# POST /api/v1/leads/{id}/convert — Admin convert
# =============================================================================


@pytest.mark.unit
class TestConvertLead:
    """Tests for admin lead conversion endpoint."""

    @pytest.mark.asyncio
    async def test_convert_lead_success(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test successful lead conversion."""
        lead_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_lead_service.convert_lead.return_value = (
            LeadConversionResponse(
                lead_id=lead_id,
                customer_id=customer_id,
                job_id=job_id,
            )
        )

        response = await admin_client.post(
            f"/api/v1/leads/{lead_id}/convert",
            json={"create_job": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == str(customer_id)
        assert data["job_id"] == str(job_id)

    @pytest.mark.asyncio
    async def test_convert_already_converted(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test converting already-converted lead returns 400."""
        lead_id = uuid.uuid4()
        mock_lead_service.convert_lead.side_effect = (
            LeadAlreadyConvertedError(lead_id)
        )

        response = await admin_client.post(
            f"/api/v1/leads/{lead_id}/convert",
            json={"create_job": False},
        )

        assert response.status_code == 400


# =============================================================================
# DELETE /api/v1/leads/{id} — Admin delete
# =============================================================================


@pytest.mark.unit
class TestDeleteLead:
    """Tests for admin delete lead endpoint."""

    @pytest.mark.asyncio
    async def test_delete_lead_success(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test successful lead deletion."""
        lead_id = uuid.uuid4()
        mock_lead_service.delete_lead.return_value = None

        response = await admin_client.delete(
            f"/api/v1/leads/{lead_id}",
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_lead_not_found(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Test deleting non-existent lead returns 404."""
        lead_id = uuid.uuid4()
        mock_lead_service.delete_lead.side_effect = (
            LeadNotFoundError(lead_id)
        )

        response = await admin_client.delete(
            f"/api/v1/leads/{lead_id}",
        )

        assert response.status_code == 404
