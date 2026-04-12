"""Integration tests for lead APIs.

Tests cover lead list with source/intake_tag filters, from-call endpoint,
follow-up queue with pagination, metrics by source with date range,
and dashboard summary including lead metrics.

Validates: Requirements 63.3
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
    require_manager_or_admin,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.api.v1.leads import _get_lead_service
from grins_platform.main import app
from grins_platform.models.enums import (
    LeadSituation,
    LeadStatus,
)
from grins_platform.schemas.lead import (
    FollowUpQueueItem,
    LeadMetricsBySourceResponse,
    LeadResponse,
    LeadSourceCount,
    LeadSubmissionResponse,
    PaginatedFollowUpQueueResponse,
    PaginatedLeadResponse,
)
from grins_platform.services.metrics_service import AgreementMetrics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_admin() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin"
    user.role = "admin"
    user.is_active = True
    return user


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_lead_service() -> AsyncMock:
    """Create a mock LeadService."""
    return AsyncMock()


@pytest_asyncio.fixture
async def admin_client(
    mock_lead_service: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated admin client with mocked lead service."""
    admin = _mock_admin()
    app.dependency_overrides[_get_lead_service] = lambda: mock_lead_service
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_active_user] = lambda: admin
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def public_client(
    mock_lead_service: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated client with mocked lead service."""
    app.dependency_overrides[_get_lead_service] = lambda: mock_lead_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# =========================================================================
# GET /api/v1/leads with lead_source multi-select filter
# =========================================================================


@pytest.mark.integration
class TestLeadListSourceFilter:
    """Integration tests for lead list with lead_source filter.

    Validates: Requirement 63.3
    """

    @pytest.mark.asyncio
    async def test_filter_by_single_lead_source(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Filter leads by a single lead_source value."""
        lead = _make_lead_response(lead_source="phone_call")
        mock_lead_service.list_leads = AsyncMock(
            return_value=PaginatedLeadResponse(
                items=[lead],
                total=1,
                page=1,
                page_size=20,
                total_pages=1,
            ),
        )

        resp = await admin_client.get("/api/v1/leads?lead_source=phone_call")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["lead_source"] == "phone_call"

        # Verify service was called with parsed lead_source list
        call_args = mock_lead_service.list_leads.call_args[0][0]
        assert call_args.lead_source == ["phone_call"]

    @pytest.mark.asyncio
    async def test_filter_by_multiple_lead_sources(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Filter leads by comma-separated lead_source values."""
        leads = [
            _make_lead_response(lead_source="website"),
            _make_lead_response(lead_source="referral"),
        ]
        mock_lead_service.list_leads = AsyncMock(
            return_value=PaginatedLeadResponse(
                items=leads,
                total=2,
                page=1,
                page_size=20,
                total_pages=1,
            ),
        )

        resp = await admin_client.get(
            "/api/v1/leads?lead_source=website,referral",
        )

        assert resp.status_code == 200
        assert resp.json()["total"] == 2

        call_args = mock_lead_service.list_leads.call_args[0][0]
        assert call_args.lead_source == ["website", "referral"]

    @pytest.mark.asyncio
    async def test_no_lead_source_filter_returns_all(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """No lead_source filter returns all leads."""
        mock_lead_service.list_leads = AsyncMock(
            return_value=PaginatedLeadResponse(
                items=[],
                total=0,
                page=1,
                page_size=20,
                total_pages=0,
            ),
        )

        resp = await admin_client.get("/api/v1/leads")

        assert resp.status_code == 200
        call_args = mock_lead_service.list_leads.call_args[0][0]
        assert call_args.lead_source is None


# =========================================================================
# GET /api/v1/leads with intake_tag filter
# =========================================================================


@pytest.mark.integration
class TestLeadListIntakeTagFilter:
    """Integration tests for lead list with intake_tag filter.

    Validates: Requirement 63.3
    """

    @pytest.mark.asyncio
    async def test_filter_by_intake_tag_schedule(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Filter leads by intake_tag=schedule."""
        lead = _make_lead_response(intake_tag="schedule")
        mock_lead_service.list_leads = AsyncMock(
            return_value=PaginatedLeadResponse(
                items=[lead],
                total=1,
                page=1,
                page_size=20,
                total_pages=1,
            ),
        )

        resp = await admin_client.get("/api/v1/leads?intake_tag=schedule")

        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        call_args = mock_lead_service.list_leads.call_args[0][0]
        assert call_args.intake_tag == "schedule"

    @pytest.mark.asyncio
    async def test_filter_by_intake_tag_follow_up(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Filter leads by intake_tag=follow_up."""
        lead = _make_lead_response(intake_tag="follow_up")
        mock_lead_service.list_leads = AsyncMock(
            return_value=PaginatedLeadResponse(
                items=[lead],
                total=1,
                page=1,
                page_size=20,
                total_pages=1,
            ),
        )

        resp = await admin_client.get("/api/v1/leads?intake_tag=follow_up")

        assert resp.status_code == 200
        call_args = mock_lead_service.list_leads.call_args[0][0]
        assert call_args.intake_tag == "follow_up"


# =========================================================================
# POST /api/v1/leads/from-call with authentication
# =========================================================================


@pytest.mark.integration
class TestFromCallEndpoint:
    """Integration tests for from-call lead creation.

    Validates: Requirement 63.3
    """

    @pytest.mark.asyncio
    async def test_from_call_creates_lead_with_auth(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Authenticated admin can create lead from call."""
        lead = _make_lead_response(
            lead_source="phone_call",
            source_detail="Inbound call",
            intake_tag=None,
        )
        mock_lead_service.create_from_call = AsyncMock(return_value=lead)

        resp = await admin_client.post(
            "/api/v1/leads/from-call",
            json={
                "name": "Jane Doe",
                "phone": "6125559876",
                "zip_code": "55346",
                "situation": "new_system",
                "address": "123 Main St, Denver, CO 80209",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["lead_source"] == "phone_call"
        mock_lead_service.create_from_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_from_call_requires_auth(
        self,
        public_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """From-call endpoint requires authentication."""
        resp = await public_client.post(
            "/api/v1/leads/from-call",
            json={
                "name": "Jane Doe",
                "phone": "6125559876",
                "zip_code": "55346",
                "situation": "new_system",
                "address": "123 Main St, Denver, CO 80209",
            },
        )

        # Should fail auth (401 or 403)
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_from_call_with_optional_fields(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """From-call with all optional fields."""
        lead = _make_lead_response(
            lead_source="phone_call",
            source_detail="Referral from neighbor",
            intake_tag="follow_up",
            notes="Needs estimate",
        )
        mock_lead_service.create_from_call = AsyncMock(return_value=lead)

        resp = await admin_client.post(
            "/api/v1/leads/from-call",
            json={
                "name": "Bob Smith",
                "phone": "6125551111",
                "zip_code": "55424",
                "situation": "repair",
                "notes": "Needs estimate",
                "source_detail": "Referral from neighbor",
                "intake_tag": "follow_up",
                "address": "123 Main St, Denver, CO 80209",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["intake_tag"] == "follow_up"


# =========================================================================
# GET /api/v1/leads/follow-up-queue with pagination
# =========================================================================


@pytest.mark.integration
class TestFollowUpQueueEndpoint:
    """Integration tests for follow-up queue endpoint.

    Validates: Requirement 63.3
    """

    @pytest.mark.asyncio
    async def test_follow_up_queue_returns_paginated_results(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Follow-up queue returns paginated response."""
        now = datetime.now(tz=timezone.utc)
        items = [
            FollowUpQueueItem(
                id=uuid.uuid4(),
                name="Lead A",
                phone="6125551111",
                email=None,
                situation=LeadSituation.REPAIR,
                notes=None,
                status=LeadStatus.NEW,
                intake_tag="follow_up",
                created_at=now - timedelta(hours=5),
                time_since_created=5.0,
            ),
            FollowUpQueueItem(
                id=uuid.uuid4(),
                name="Lead B",
                phone="6125552222",
                email=None,
                situation=LeadSituation.NEW_SYSTEM,
                notes=None,
                status=LeadStatus.CONTACTED,
                intake_tag="follow_up",
                created_at=now - timedelta(hours=2),
                time_since_created=2.0,
            ),
        ]
        mock_lead_service.get_follow_up_queue = AsyncMock(
            return_value=PaginatedFollowUpQueueResponse(
                items=items,
                total=2,
                page=1,
                page_size=20,
                total_pages=1,
            ),
        )

        resp = await admin_client.get("/api/v1/leads/follow-up-queue")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "Lead A"
        assert data["items"][0]["time_since_created"] == 5.0

    @pytest.mark.asyncio
    async def test_follow_up_queue_with_custom_pagination(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Follow-up queue respects page and page_size params."""
        mock_lead_service.get_follow_up_queue = AsyncMock(
            return_value=PaginatedFollowUpQueueResponse(
                items=[],
                total=5,
                page=2,
                page_size=2,
                total_pages=3,
            ),
        )

        resp = await admin_client.get(
            "/api/v1/leads/follow-up-queue?page=2&page_size=2",
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

        mock_lead_service.get_follow_up_queue.assert_called_once_with(
            page=2,
            page_size=2,
        )

    @pytest.mark.asyncio
    async def test_follow_up_queue_empty(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Follow-up queue returns empty when no follow-up leads."""
        mock_lead_service.get_follow_up_queue = AsyncMock(
            return_value=PaginatedFollowUpQueueResponse(
                items=[],
                total=0,
                page=1,
                page_size=20,
                total_pages=0,
            ),
        )

        resp = await admin_client.get("/api/v1/leads/follow-up-queue")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


# =========================================================================
# GET /api/v1/leads/metrics/by-source with date range
# =========================================================================


@pytest.mark.integration
class TestLeadMetricsBySourceEndpoint:
    """Integration tests for lead metrics by source endpoint.

    Validates: Requirement 63.3
    """

    @pytest.mark.asyncio
    async def test_metrics_by_source_default_date_range(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Metrics by source with default trailing 30 days."""
        now = datetime.now(tz=timezone.utc)
        mock_lead_service.get_metrics_by_source = AsyncMock(
            return_value=LeadMetricsBySourceResponse(
                items=[
                    LeadSourceCount(lead_source="website", count=10),
                    LeadSourceCount(lead_source="phone_call", count=5),
                    LeadSourceCount(lead_source="referral", count=3),
                ],
                total=18,
                date_from=now - timedelta(days=30),
                date_to=now,
            ),
        )

        resp = await admin_client.get("/api/v1/leads/metrics/by-source")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 18
        assert len(data["items"]) == 3
        assert data["items"][0]["lead_source"] == "website"
        assert data["items"][0]["count"] == 10

    @pytest.mark.asyncio
    async def test_metrics_by_source_custom_date_range(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Metrics by source with custom date range."""
        date_from = "2026-01-01T00:00:00Z"
        date_to = "2026-01-31T23:59:59Z"

        mock_lead_service.get_metrics_by_source = AsyncMock(
            return_value=LeadMetricsBySourceResponse(
                items=[
                    LeadSourceCount(lead_source="google_ad", count=7),
                ],
                total=7,
                date_from=datetime.fromisoformat(date_from),
                date_to=datetime.fromisoformat(date_to),
            ),
        )

        resp = await admin_client.get(
            f"/api/v1/leads/metrics/by-source?date_from={date_from}&date_to={date_to}",
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 7
        assert data["items"][0]["lead_source"] == "google_ad"

        # Verify service received parsed dates
        call_kwargs = mock_lead_service.get_metrics_by_source.call_args[1]
        assert call_kwargs["date_from"] is not None
        assert call_kwargs["date_to"] is not None

    @pytest.mark.asyncio
    async def test_metrics_by_source_empty(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Metrics by source returns empty when no leads in range."""
        now = datetime.now(tz=timezone.utc)
        mock_lead_service.get_metrics_by_source = AsyncMock(
            return_value=LeadMetricsBySourceResponse(
                items=[],
                total=0,
                date_from=now - timedelta(days=30),
                date_to=now,
            ),
        )

        resp = await admin_client.get("/api/v1/leads/metrics/by-source")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


# =========================================================================
# GET /api/v1/dashboard/summary including lead metrics
# =========================================================================


@pytest.mark.integration
class TestDashboardSummaryLeadMetrics:
    """Integration tests for dashboard summary with lead data.

    These tests are covered in test_agreement_integration.py but we
    verify the lead-specific aspects here for completeness.

    Validates: Requirement 63.3
    """

    @pytest.mark.asyncio
    async def test_dashboard_includes_lead_counts(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Dashboard summary includes new_leads_count and follow_up_queue_count.

        Note: The dashboard endpoint is in the agreements module and tested
        in test_agreement_integration.py. This test verifies the lead-specific
        fields are present in the response schema.
        """
        admin = _mock_admin()
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar=MagicMock(return_value=None)),
        )

        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[require_manager_or_admin] = lambda: admin
        app.dependency_overrides[get_db_session] = lambda: mock_db

        metrics = AgreementMetrics(
            active_count=2,
            mrr=Decimal("83.17"),
            arpa=Decimal("41.58"),
            renewal_rate=Decimal("90.00"),
            churn_rate=Decimal("10.00"),
            past_due_amount=Decimal("0.00"),
        )

        mock_lead_repo = AsyncMock()
        mock_lead_repo.count_new_today = AsyncMock(return_value=4)
        mock_lead_repo.get_follow_up_queue = AsyncMock(return_value=([], 3))
        mock_lead_repo.count_uncontacted = AsyncMock(return_value=0)

        mock_agr_repo = AsyncMock()
        mock_agr_repo.get_renewal_pipeline = AsyncMock(return_value=[])
        mock_agr_repo.get_failed_payments = AsyncMock(return_value=[])

        try:
            with (
                patch(
                    "grins_platform.api.v1.agreements.MetricsService",
                ) as mock_m,
                patch(
                    "grins_platform.api.v1.agreements.AgreementRepository",
                ) as mock_a,
                patch(
                    "grins_platform.api.v1.agreements.LeadRepository",
                ) as mock_l,
            ):
                mock_m.return_value = AsyncMock(
                    compute_metrics=AsyncMock(return_value=metrics),
                )
                mock_a.return_value = mock_agr_repo
                mock_l.return_value = mock_lead_repo

                resp = await admin_client.get("/api/v1/dashboard/summary")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["new_leads_count"] == 4
        assert data["follow_up_queue_count"] == 3
        assert data["leads_awaiting_contact_oldest_age_hours"] is None


# =========================================================================
# Cross-endpoint: list + filter consistency
# =========================================================================


@pytest.mark.integration
class TestLeadFilterConsistency:
    """Integration tests for filter consistency across endpoints.

    Validates: Requirement 63.3
    """

    @pytest.mark.asyncio
    async def test_source_and_intake_tag_filters_combined(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Both lead_source and intake_tag filters can be used together."""
        lead = _make_lead_response(
            lead_source="phone_call",
            intake_tag="follow_up",
        )
        mock_lead_service.list_leads = AsyncMock(
            return_value=PaginatedLeadResponse(
                items=[lead],
                total=1,
                page=1,
                page_size=20,
                total_pages=1,
            ),
        )

        resp = await admin_client.get(
            "/api/v1/leads?lead_source=phone_call&intake_tag=follow_up",
        )

        assert resp.status_code == 200
        call_args = mock_lead_service.list_leads.call_args[0][0]
        assert call_args.lead_source == ["phone_call"]
        assert call_args.intake_tag == "follow_up"

    @pytest.mark.asyncio
    async def test_public_submit_then_admin_list(
        self,
        admin_client: AsyncClient,
        public_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Public submission followed by admin list shows the lead."""
        lead_id = uuid.uuid4()

        # Step 1: Public submit
        mock_lead_service.submit_lead = AsyncMock(
            return_value=LeadSubmissionResponse(
                success=True,
                lead_id=lead_id,
            ),
        )

        submit_resp = await public_client.post(
            "/api/v1/leads",
            json={
                "name": "New Lead",
                "phone": "6125553333",
                "zip_code": "55424",
                "situation": "new_system",
                "source_site": "residential",
                "address": "123 Main St, Denver, CO 80209",
            },
        )
        assert submit_resp.status_code == 201
        assert submit_resp.json()["lead_id"] == str(lead_id)

        # Step 2: Admin list with source filter
        lead = _make_lead_response(id=lead_id, lead_source="website")
        mock_lead_service.list_leads = AsyncMock(
            return_value=PaginatedLeadResponse(
                items=[lead],
                total=1,
                page=1,
                page_size=20,
                total_pages=1,
            ),
        )

        list_resp = await admin_client.get(
            "/api/v1/leads?lead_source=website",
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 1
