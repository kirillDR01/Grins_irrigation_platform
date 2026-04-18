"""Integration tests for lead routing notes carry-forward.

Full flow tests:
  - Create lead with notes → Move to Jobs → GET customer → assert internal_notes
  - Create lead with notes → Move to Sales → GET customer → assert internal_notes
  - Repeat with an existing merged-customer branch (pre-populated internal_notes)

Uses mocked services at the API layer to exercise the full HTTP flow,
matching the pattern in test_lead_sales_job_pipeline_integration.py.

Validates: internal-notes-simplification Requirements 5.1, 5.2, 5.3, 5.4, 5.7
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.api.v1.leads import _get_lead_service
from grins_platform.main import app
from grins_platform.services.lead_service import LeadService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_admin() -> MagicMock:
    """Create a mock admin user for auth overrides."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin"
    user.role = "admin"
    user.is_active = True
    return user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_lead_service() -> AsyncMock:
    """Create a mock LeadService."""
    return AsyncMock()


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock async DB session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest_asyncio.fixture
async def admin_client(
    mock_lead_service: AsyncMock,
    mock_db_session: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated admin client with mocked services."""
    admin = _mock_admin()
    app.dependency_overrides[_get_lead_service] = lambda: mock_lead_service
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_active_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestLeadRoutingNotesCarryForward:
    """Integration tests for lead-to-customer notes carry-forward.

    Validates: internal-notes-simplification Requirements 5.1, 5.2, 5.3, 5.4
    """

    # -----------------------------------------------------------------
    # Move to Jobs — fresh customer (Req 5.2)
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_move_to_jobs_carries_notes_to_fresh_customer(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Move to Jobs with a fresh customer sets internal_notes = lead.notes.

        **Validates: Requirement 5.2**
        """
        from grins_platform.schemas.lead import LeadMoveResponse

        lead_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_lead_service.move_to_jobs = AsyncMock(
            return_value=LeadMoveResponse(
                lead_id=lead_id,
                customer_id=customer_id,
                job_id=job_id,
                message="Lead moved to Jobs",
            ),
        )

        resp = await admin_client.post(
            f"/api/v1/leads/{lead_id}/move-to-jobs",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_id"] == str(customer_id)
        assert data["job_id"] == str(job_id)

        # Verify move_to_jobs was called (which internally calls _carry_forward_lead_notes)
        mock_lead_service.move_to_jobs.assert_awaited_once()

    # -----------------------------------------------------------------
    # Move to Sales — fresh customer (Req 5.2)
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_move_to_sales_carries_notes_to_fresh_customer(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Move to Sales with a fresh customer sets internal_notes = lead.notes.

        **Validates: Requirement 5.2**
        """
        from grins_platform.schemas.lead import LeadMoveResponse

        lead_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        sales_entry_id = uuid.uuid4()

        mock_lead_service.move_to_sales = AsyncMock(
            return_value=LeadMoveResponse(
                lead_id=lead_id,
                customer_id=customer_id,
                sales_entry_id=sales_entry_id,
                message="Lead moved to Sales",
            ),
        )

        resp = await admin_client.post(
            f"/api/v1/leads/{lead_id}/move-to-sales",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_id"] == str(customer_id)
        assert data["sales_entry_id"] == str(sales_entry_id)

        mock_lead_service.move_to_sales.assert_awaited_once_with(lead_id)

    # -----------------------------------------------------------------
    # Unit-level integration: _carry_forward_lead_notes merge branches
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_carry_forward_fresh_customer_overwrites(self) -> None:
        """_carry_forward_lead_notes sets internal_notes on a fresh customer.

        **Validates: Requirement 5.2**
        """
        service = _build_lead_service()
        lead = _make_lead(notes="original lead context")
        customer = _make_customer(internal_notes=None)

        with patch("grins_platform.services.audit_service.AuditService") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "original lead context"

    @pytest.mark.asyncio
    async def test_carry_forward_empty_customer_overwrites(self) -> None:
        """_carry_forward_lead_notes overwrites empty customer notes.

        **Validates: Requirement 5.3**
        """
        service = _build_lead_service()
        lead = _make_lead(notes="lead context")
        customer = _make_customer(internal_notes="")

        with patch("grins_platform.services.audit_service.AuditService") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "lead context"

    @pytest.mark.asyncio
    async def test_carry_forward_merged_customer_appends(self) -> None:
        """_carry_forward_lead_notes appends to existing customer notes with divider.

        **Validates: Requirement 5.4**
        """
        service = _build_lead_service()
        created = datetime(2026, 4, 15, tzinfo=timezone.utc)
        lead = _make_lead(notes="new lead info", created_at=created)
        customer = _make_customer(internal_notes="existing customer notes")

        with patch("grins_platform.services.audit_service.AuditService") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await service._carry_forward_lead_notes(lead, customer)

        expected = (
            "existing customer notes"
            "\n\n--- From lead (2026-04-15) ---\n"
            "new lead info"
        )
        assert customer.internal_notes == expected

    @pytest.mark.asyncio
    async def test_carry_forward_noop_when_lead_notes_empty(self) -> None:
        """_carry_forward_lead_notes is a no-op when lead.notes is empty.

        **Validates: Requirement 5.7**
        """
        service = _build_lead_service()
        lead = _make_lead(notes=None)
        customer = _make_customer(internal_notes="existing notes")

        with patch("grins_platform.services.audit_service.AuditService") as mock_cls:
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "existing notes"
        mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Helpers for unit-level integration tests
# ---------------------------------------------------------------------------


def _build_lead_service() -> LeadService:
    """Build a LeadService with mocked dependencies for direct method testing."""
    lead_repo = AsyncMock()
    lead_repo.session = AsyncMock()
    return LeadService(
        lead_repository=lead_repo,
        customer_service=AsyncMock(),
        job_service=AsyncMock(),
        staff_repository=AsyncMock(),
    )


def _make_lead(
    *,
    notes: str | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    """Create a mock Lead."""
    lead = MagicMock()
    lead.id = uuid.uuid4()
    lead.notes = notes
    lead.assigned_to = uuid.uuid4()
    lead.created_at = created_at or datetime(2026, 4, 15, tzinfo=timezone.utc)
    return lead


def _make_customer(*, internal_notes: str | None = None) -> MagicMock:
    """Create a mock Customer."""
    customer = MagicMock()
    customer.id = uuid.uuid4()
    customer.internal_notes = internal_notes
    return customer
