"""Unit tests for Sheet Submissions API endpoints.

Tests cover all 5 endpoints with mocked service, auth checks,
404/409 error handling, and query parameter validation.

Validates: Requirements 5.7, 12.1, 12.4
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.dependencies import get_sheets_service
from grins_platform.main import app
from grins_platform.schemas.google_sheet_submission import (
    PaginatedSubmissionResponse,
    SyncStatusResponse,
)


@pytest.fixture
def mock_sheets_service() -> AsyncMock:
    """Create a mock GoogleSheetsService."""
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


def _make_submission_dict(**overrides: object) -> dict[str, object]:
    """Build a sample submission response dict."""
    now = datetime.now(tz=timezone.utc)
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "sheet_row_number": 2,
        "timestamp": "2025-06-01 10:00:00",
        "spring_startup": "Yes",
        "fall_blowout": None,
        "summer_tuneup": None,
        "repair_existing": None,
        "new_system_install": None,
        "addition_to_system": None,
        "additional_services_info": None,
        "date_work_needed_by": "ASAP",
        "name": "Jane Doe",
        "phone": "6125551234",
        "email": "jane@example.com",
        "city": "Minneapolis",
        "address": "123 Main St",
        "client_type": "New Client",
        "property_type": "Residential",
        "referral_source": "Google",
        "landscape_hardscape": None,
        "content_hash": "abc123hash",
        "zip_code": "55401",
        "work_requested": "Spring startup",
        "agreed_to_terms": "Yes",
        "processing_status": "imported",
        "processing_error": None,
        "lead_id": None,
        "imported_at": now,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


@pytest_asyncio.fixture
async def unauth_client(
    mock_sheets_service: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client without auth for testing 401."""
    app.dependency_overrides[get_sheets_service] = lambda: mock_sheets_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(
    mock_sheets_service: AsyncMock,
    mock_admin_user: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with admin auth for protected endpoints."""
    app.dependency_overrides[get_sheets_service] = lambda: mock_sheets_service
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# =============================================================================
# Authentication — 401 for unauthenticated requests
# =============================================================================


@pytest.mark.unit
class TestSheetSubmissionsAuth:
    """All endpoints require admin auth."""

    @pytest.mark.asyncio
    async def test_list_unauthenticated(
        self,
        unauth_client: AsyncClient,
    ) -> None:
        response = await unauth_client.get("/api/v1/sheet-submissions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_unauthenticated(
        self,
        unauth_client: AsyncClient,
    ) -> None:
        response = await unauth_client.get(
            f"/api/v1/sheet-submissions/{uuid.uuid4()}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_lead_unauthenticated(
        self,
        unauth_client: AsyncClient,
    ) -> None:
        response = await unauth_client.post(
            f"/api/v1/sheet-submissions/{uuid.uuid4()}/create-lead",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_status_unauthenticated(
        self,
        unauth_client: AsyncClient,
    ) -> None:
        response = await unauth_client.get(
            "/api/v1/sheet-submissions/sync-status",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_sync_unauthenticated(
        self,
        unauth_client: AsyncClient,
    ) -> None:
        response = await unauth_client.post(
            "/api/v1/sheet-submissions/trigger-sync",
        )
        assert response.status_code == 401


# =============================================================================
# GET /api/v1/sheet-submissions — paginated list
# =============================================================================


@pytest.mark.unit
class TestListSubmissions:
    """Tests for listing sheet submissions."""

    @pytest.mark.asyncio
    async def test_list_success(
        self,
        admin_client: AsyncClient,
        mock_sheets_service: AsyncMock,
    ) -> None:
        mock_sheets_service.list_submissions.return_value = PaginatedSubmissionResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        response = await admin_client.get("/api/v1/sheet-submissions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_with_filters(
        self,
        admin_client: AsyncClient,
        mock_sheets_service: AsyncMock,
    ) -> None:
        mock_sheets_service.list_submissions.return_value = PaginatedSubmissionResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        response = await admin_client.get(
            "/api/v1/sheet-submissions?processing_status=imported&client_type=New+Client",
        )
        assert response.status_code == 200
        mock_sheets_service.list_submissions.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_invalid_sort_order_returns_422(
        self,
        admin_client: AsyncClient,
    ) -> None:
        response = await admin_client.get(
            "/api/v1/sheet-submissions?sort_order=invalid",
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_page_below_min_returns_422(
        self,
        admin_client: AsyncClient,
    ) -> None:
        response = await admin_client.get(
            "/api/v1/sheet-submissions?page=0",
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_page_size_above_max_returns_422(
        self,
        admin_client: AsyncClient,
    ) -> None:
        response = await admin_client.get(
            "/api/v1/sheet-submissions?page_size=101",
        )
        assert response.status_code == 422


# =============================================================================
# GET /api/v1/sheet-submissions/{id} — single submission
# =============================================================================


@pytest.mark.unit
class TestGetSubmission:
    """Tests for getting a single submission."""

    @pytest.mark.asyncio
    async def test_get_success(
        self,
        admin_client: AsyncClient,
        mock_sheets_service: AsyncMock,
    ) -> None:
        sub = MagicMock()
        d = _make_submission_dict()
        for k, v in d.items():
            setattr(sub, k, v)
        mock_sheets_service.get_submission.return_value = sub

        response = await admin_client.get(
            f"/api/v1/sheet-submissions/{d['id']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Jane Doe"
        assert data["processing_status"] == "imported"

    @pytest.mark.asyncio
    async def test_get_not_found(
        self,
        admin_client: AsyncClient,
        mock_sheets_service: AsyncMock,
    ) -> None:
        mock_sheets_service.get_submission.return_value = None
        response = await admin_client.get(
            f"/api/v1/sheet-submissions/{uuid.uuid4()}",
        )
        assert response.status_code == 404


# =============================================================================
# POST /api/v1/sheet-submissions/{id}/create-lead
# =============================================================================


@pytest.mark.unit
class TestCreateLeadFromSubmission:
    """Tests for manual lead creation from submission."""

    @pytest.mark.asyncio
    async def test_create_lead_success(
        self,
        admin_client: AsyncClient,
        mock_sheets_service: AsyncMock,
    ) -> None:
        lead_id = uuid.uuid4()
        sub = MagicMock()
        d = _make_submission_dict(
            processing_status="lead_created",
            lead_id=lead_id,
        )
        for k, v in d.items():
            setattr(sub, k, v)
        mock_sheets_service.create_lead_from_submission.return_value = sub

        response = await admin_client.post(
            f"/api/v1/sheet-submissions/{d['id']}/create-lead",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["lead_id"] == str(lead_id)
        assert data["processing_status"] == "lead_created"

    @pytest.mark.asyncio
    async def test_create_lead_not_found(
        self,
        admin_client: AsyncClient,
        mock_sheets_service: AsyncMock,
    ) -> None:
        sid = uuid.uuid4()
        mock_sheets_service.create_lead_from_submission.side_effect = ValueError(
            f"Submission {sid} not found",
        )
        response = await admin_client.post(
            f"/api/v1/sheet-submissions/{sid}/create-lead",
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_lead_already_linked_returns_409(
        self,
        admin_client: AsyncClient,
        mock_sheets_service: AsyncMock,
    ) -> None:
        mock_sheets_service.create_lead_from_submission.side_effect = ValueError(
            "Submission already has a linked lead",
        )
        response = await admin_client.post(
            f"/api/v1/sheet-submissions/{uuid.uuid4()}/create-lead",
        )
        assert response.status_code == 409


# =============================================================================
# GET /api/v1/sheet-submissions/sync-status
# =============================================================================


@pytest.mark.unit
class TestSyncStatus:
    """Tests for sync status endpoint."""

    @pytest.mark.asyncio
    async def test_sync_status_no_poller(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """When no poller is attached, returns default stopped status."""
        # Ensure no poller on app.state
        if hasattr(app.state, "sheets_poller"):
            delattr(app.state, "sheets_poller")

        response = await admin_client.get(
            "/api/v1/sheet-submissions/sync-status",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_running"] is False
        assert data["last_sync"] is None

    @pytest.mark.asyncio
    async def test_sync_status_with_poller(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """When poller exists, returns its sync_status."""
        now = datetime.now(tz=timezone.utc)
        mock_poller = MagicMock()
        type(mock_poller).sync_status = PropertyMock(
            return_value=SyncStatusResponse(
                last_sync=now,
                is_running=True,
                last_error=None,
            ),
        )
        app.state.sheets_poller = mock_poller
        try:
            response = await admin_client.get(
                "/api/v1/sheet-submissions/sync-status",
            )
            assert response.status_code == 200
            data = response.json()
            assert data["is_running"] is True
            assert data["last_sync"] is not None
        finally:
            delattr(app.state, "sheets_poller")


# =============================================================================
# POST /api/v1/sheet-submissions/trigger-sync
# =============================================================================


@pytest.mark.unit
class TestTriggerSync:
    """Tests for trigger sync endpoint."""

    @pytest.mark.asyncio
    async def test_trigger_sync_no_poller_returns_503(
        self,
        admin_client: AsyncClient,
    ) -> None:
        if hasattr(app.state, "sheets_poller"):
            delattr(app.state, "sheets_poller")

        response = await admin_client.post(
            "/api/v1/sheet-submissions/trigger-sync",
        )
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_trigger_sync_success(
        self,
        admin_client: AsyncClient,
    ) -> None:
        mock_poller = AsyncMock()
        mock_poller.trigger_sync.return_value = 3
        app.state.sheets_poller = mock_poller
        try:
            response = await admin_client.post(
                "/api/v1/sheet-submissions/trigger-sync",
            )
            assert response.status_code == 200
            data = response.json()
            assert data["new_rows_imported"] == 3
            mock_poller.trigger_sync.assert_called_once()
        finally:
            delattr(app.state, "sheets_poller")
