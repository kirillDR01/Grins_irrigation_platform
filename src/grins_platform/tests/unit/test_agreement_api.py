"""Unit tests for agreement admin API endpoints.

Tests cover agreement CRUD, metrics, queues, compliance audit,
tier endpoints, and dashboard summary extension.

Validates: Requirements 19.1-19.7, 20.1-20.3, 21.1, 37.1, 38.1-38.3, 62.1
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime, timezone
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
from grins_platform.exceptions import AgreementNotFoundError
from grins_platform.main import app
from grins_platform.services.metrics_service import AgreementMetrics

_AGR_REPO = "grins_platform.api.v1.agreements.AgreementRepository"
_TIER_REPO = "grins_platform.api.v1.agreements.AgreementTierRepository"
_AGR_SVC = "grins_platform.api.v1.agreements.AgreementService"
_METRICS_SVC = "grins_platform.api.v1.agreements.MetricsService"
_COMPLIANCE_SVC = "grins_platform.api.v1.agreements.ComplianceService"
_LEAD_REPO = "grins_platform.api.v1.agreements.LeadRepository"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_admin_user() -> MagicMock:
    """Create a mock admin user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin User"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock async db session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_agreement(
    *,
    agreement_id: uuid.UUID | None = None,
    status: str = "active",
    payment_status: str = "current",
    annual_price: Decimal = Decimal("499.00"),
) -> MagicMock:
    """Create a mock ServiceAgreement."""
    agr = MagicMock()
    agr.id = agreement_id or uuid.uuid4()
    agr.agreement_number = "AGR-2026-001"
    agr.customer_id = uuid.uuid4()
    agr.tier_id = uuid.uuid4()
    agr.property_id = None
    agr.status = status
    agr.annual_price = annual_price
    agr.start_date = date(2026, 1, 1)
    agr.end_date = date(2026, 12, 31)
    agr.renewal_date = date(2026, 12, 1)
    agr.auto_renew = True
    agr.payment_status = payment_status
    agr.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    agr.stripe_subscription_id = None
    agr.stripe_customer_id = None
    agr.cancelled_at = None
    agr.cancellation_reason = None
    agr.cancellation_refund_amount = None
    agr.pause_reason = None
    agr.last_payment_date = None
    agr.last_payment_amount = None
    agr.renewal_approved_by = None
    agr.renewal_approved_at = None
    agr.consent_recorded_at = None
    agr.consent_method = None
    agr.last_annual_notice_sent = None
    agr.last_renewal_notice_sent = None
    agr.notes = None
    agr.jobs = []
    agr.status_logs = []
    customer = MagicMock()
    customer.full_name = "John Doe"
    agr.customer = customer
    tier = MagicMock()
    tier.name = "Essential"
    tier.package_type = "residential"
    agr.tier = tier
    return agr


def _make_tier(*, tier_id: uuid.UUID | None = None) -> MagicMock:
    """Create a mock ServiceAgreementTier."""
    tier = MagicMock()
    tier.id = tier_id or uuid.uuid4()
    tier.name = "Essential"
    tier.slug = "essential-residential"
    tier.description = "Basic package"
    tier.package_type = "residential"
    tier.annual_price = Decimal("499.00")
    tier.billing_frequency = "annual"
    tier.included_services = [{"service_type": "spring_startup", "frequency": 1}]
    tier.perks = ["Priority scheduling"]
    tier.is_active = True
    tier.display_order = 1
    return tier


def _make_disclosure(*, agreement_id: uuid.UUID | None = None) -> MagicMock:
    """Create a mock DisclosureRecord."""
    rec = MagicMock()
    rec.id = uuid.uuid4()
    rec.agreement_id = agreement_id or uuid.uuid4()
    rec.customer_id = uuid.uuid4()
    rec.disclosure_type = "pre_sale"
    rec.sent_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rec.sent_via = "email"
    rec.recipient_email = "test@example.com"
    rec.recipient_phone = None
    rec.delivery_confirmed = True
    rec.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return rec


@pytest_asyncio.fixture
async def admin_client(
    mock_admin_user: MagicMock,
    mock_db_session: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with admin auth and mocked DB session."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user
    app.dependency_overrides[require_manager_or_admin] = lambda: mock_admin_user
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# =============================================================================
# GET /api/v1/agreements
# =============================================================================


@pytest.mark.unit
class TestListAgreements:
    """Tests for list agreements endpoint."""

    @pytest.mark.asyncio
    async def test_list_returns_paginated(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test listing agreements returns paginated response."""
        agr = _make_agreement()
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                list_with_filters=AsyncMock(return_value=([agr], 1)),
            )
            response = await admin_client.get("/api/v1/agreements")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["agreement_number"] == "AGR-2026-001"

    @pytest.mark.asyncio
    async def test_list_with_status_filter(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test listing agreements with status filter."""
        with patch(_AGR_REPO) as mock_cls:
            mock_repo = AsyncMock(
                list_with_filters=AsyncMock(return_value=([], 0)),
            )
            mock_cls.return_value = mock_repo
            response = await admin_client.get("/api/v1/agreements?status=active")

        assert response.status_code == 200
        call_kwargs = mock_repo.list_with_filters.call_args[1]
        assert call_kwargs["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_with_all_filters(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test listing with tier_id, customer_id, payment_status, expiring_soon."""
        tid = uuid.uuid4()
        cid = uuid.uuid4()
        with patch(_AGR_REPO) as mock_cls:
            mock_repo = AsyncMock(
                list_with_filters=AsyncMock(return_value=([], 0)),
            )
            mock_cls.return_value = mock_repo
            response = await admin_client.get(
                f"/api/v1/agreements?tier_id={tid}&customer_id={cid}"
                "&payment_status=past_due&expiring_soon=true&page=2&page_size=10",
            )

        assert response.status_code == 200
        kw = mock_repo.list_with_filters.call_args[1]
        assert kw["tier_id"] == tid
        assert kw["customer_id"] == cid
        assert kw["payment_status"] == "past_due"
        assert kw["expiring_soon"] is True
        assert kw["page"] == 2
        assert kw["page_size"] == 10


# =============================================================================
# GET /api/v1/agreements/{id}
# =============================================================================


@pytest.mark.unit
class TestGetAgreement:
    """Tests for get agreement detail endpoint."""

    @pytest.mark.asyncio
    async def test_found(self, admin_client: AsyncClient) -> None:
        """Test getting an existing agreement."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agreement_id=agr_id)
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=agr),
            )
            response = await admin_client.get(f"/api/v1/agreements/{agr_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(agr_id)
        assert data["customer_name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_not_found(self, admin_client: AsyncClient) -> None:
        """Test getting a non-existent agreement returns 404."""
        agr_id = uuid.uuid4()
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=None),
            )
            response = await admin_client.get(f"/api/v1/agreements/{agr_id}")

        assert response.status_code == 404


# =============================================================================
# PATCH /api/v1/agreements/{id}/status
# =============================================================================


@pytest.mark.unit
class TestUpdateAgreementStatus:
    """Tests for update agreement status endpoint."""

    @pytest.mark.asyncio
    async def test_valid_transition(self, admin_client: AsyncClient) -> None:
        """Test valid status transition succeeds."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agreement_id=agr_id, status="active")
        with (
            patch(_AGR_REPO) as mock_repo_cls,
            patch(_TIER_REPO),
            patch(_AGR_SVC) as mock_svc_cls,
        ):
            mock_repo_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=agr),
            )
            mock_svc_cls.return_value = AsyncMock(
                transition_status=AsyncMock(return_value=agr),
            )
            response = await admin_client.patch(
                f"/api/v1/agreements/{agr_id}/status",
                json={"status": "paused", "reason": "Payment issue"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_status_value(self, admin_client: AsyncClient) -> None:
        """Test invalid status value returns 400."""
        agr_id = uuid.uuid4()
        with patch(_AGR_REPO), patch(_TIER_REPO):
            response = await admin_client.patch(
                f"/api/v1/agreements/{agr_id}/status",
                json={"status": "nonexistent_status"},
            )

        assert response.status_code == 400


# =============================================================================
# POST /api/v1/agreements/{id}/approve-renewal
# =============================================================================


@pytest.mark.unit
class TestApproveRenewal:
    """Tests for approve renewal endpoint."""

    @pytest.mark.asyncio
    async def test_success(self, admin_client: AsyncClient) -> None:
        """Test successful renewal approval."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agreement_id=agr_id)
        with (
            patch(_AGR_REPO) as mock_repo_cls,
            patch(_TIER_REPO),
            patch(_AGR_SVC) as mock_svc_cls,
        ):
            mock_repo_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=agr),
            )
            mock_svc_cls.return_value = AsyncMock(
                approve_renewal=AsyncMock(return_value=agr),
            )
            response = await admin_client.post(
                f"/api/v1/agreements/{agr_id}/approve-renewal",
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_not_found(self, admin_client: AsyncClient) -> None:
        """Test approve renewal for non-existent agreement."""
        agr_id = uuid.uuid4()
        with (
            patch(_AGR_REPO),
            patch(_TIER_REPO),
            patch(_AGR_SVC) as mock_svc_cls,
        ):
            mock_svc_cls.return_value = AsyncMock(
                approve_renewal=AsyncMock(
                    side_effect=AgreementNotFoundError(agr_id),
                ),
            )
            response = await admin_client.post(
                f"/api/v1/agreements/{agr_id}/approve-renewal",
            )

        assert response.status_code == 404


# =============================================================================
# POST /api/v1/agreements/{id}/reject-renewal
# =============================================================================


@pytest.mark.unit
class TestRejectRenewal:
    """Tests for reject renewal endpoint."""

    @pytest.mark.asyncio
    async def test_success(self, admin_client: AsyncClient) -> None:
        """Test successful renewal rejection."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agreement_id=agr_id)
        with (
            patch(_AGR_REPO) as mock_repo_cls,
            patch(_TIER_REPO),
            patch(_AGR_SVC) as mock_svc_cls,
        ):
            mock_repo_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=agr),
            )
            mock_svc_cls.return_value = AsyncMock(
                reject_renewal=AsyncMock(return_value=agr),
            )
            response = await admin_client.post(
                f"/api/v1/agreements/{agr_id}/reject-renewal",
            )

        assert response.status_code == 200


# =============================================================================
# GET /api/v1/agreement-tiers
# =============================================================================


@pytest.mark.unit
class TestListTiers:
    """Tests for list tiers endpoint."""

    @pytest.mark.asyncio
    async def test_list_active(self, admin_client: AsyncClient) -> None:
        """Test listing active tiers."""
        tier = _make_tier()
        with patch(_TIER_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                list_active=AsyncMock(return_value=[tier]),
            )
            response = await admin_client.get("/api/v1/agreement-tiers")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Essential"


# =============================================================================
# GET /api/v1/agreement-tiers/{id}
# =============================================================================


@pytest.mark.unit
class TestGetTier:
    """Tests for get tier detail endpoint."""

    @pytest.mark.asyncio
    async def test_found(self, admin_client: AsyncClient) -> None:
        """Test getting an existing tier."""
        tid = uuid.uuid4()
        tier = _make_tier(tier_id=tid)
        with patch(_TIER_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=tier),
            )
            response = await admin_client.get(f"/api/v1/agreement-tiers/{tid}")

        assert response.status_code == 200
        assert response.json()["slug"] == "essential-residential"

    @pytest.mark.asyncio
    async def test_not_found(self, admin_client: AsyncClient) -> None:
        """Test getting a non-existent tier returns 404."""
        tid = uuid.uuid4()
        with patch(_TIER_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=None),
            )
            response = await admin_client.get(f"/api/v1/agreement-tiers/{tid}")

        assert response.status_code == 404


# =============================================================================
# GET /api/v1/agreements/metrics/summary
# =============================================================================


@pytest.mark.unit
class TestAgreementMetrics:
    """Tests for agreement metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_metrics(self, admin_client: AsyncClient) -> None:
        """Test getting agreement metrics."""
        metrics = AgreementMetrics(
            active_count=10,
            mrr=Decimal("415.83"),
            arpa=Decimal("41.58"),
            renewal_rate=Decimal("85.00"),
            churn_rate=Decimal("5.00"),
            past_due_amount=Decimal("499.00"),
        )
        with patch(_METRICS_SVC) as mock_cls:
            mock_cls.return_value = AsyncMock(
                compute_metrics=AsyncMock(return_value=metrics),
            )
            response = await admin_client.get(
                "/api/v1/agreements/metrics/summary",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 10
        assert float(data["mrr"]) == pytest.approx(415.83)


# =============================================================================
# GET /api/v1/agreements/queues/renewal-pipeline
# =============================================================================


@pytest.mark.unit
class TestRenewalPipeline:
    """Tests for renewal pipeline endpoint."""

    @pytest.mark.asyncio
    async def test_get_pipeline(self, admin_client: AsyncClient) -> None:
        """Test getting renewal pipeline."""
        agr = _make_agreement(status="pending_renewal")
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_renewal_pipeline=AsyncMock(return_value=[agr]),
            )
            response = await admin_client.get(
                "/api/v1/agreements/queues/renewal-pipeline",
            )

        assert response.status_code == 200
        assert len(response.json()) == 1


# =============================================================================
# GET /api/v1/agreements/queues/failed-payments
# =============================================================================


@pytest.mark.unit
class TestFailedPayments:
    """Tests for failed payments endpoint."""

    @pytest.mark.asyncio
    async def test_get_failed(self, admin_client: AsyncClient) -> None:
        """Test getting failed payments."""
        agr = _make_agreement(payment_status="past_due")
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_failed_payments=AsyncMock(return_value=[agr]),
            )
            response = await admin_client.get(
                "/api/v1/agreements/queues/failed-payments",
            )

        assert response.status_code == 200
        assert len(response.json()) == 1


# =============================================================================
# GET /api/v1/agreements/queues/annual-notice-due
# =============================================================================


@pytest.mark.unit
class TestAnnualNoticeDue:
    """Tests for annual notice due endpoint."""

    @pytest.mark.asyncio
    async def test_get_due(self, admin_client: AsyncClient) -> None:
        """Test getting agreements needing annual notice."""
        agr = _make_agreement(status="active")
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_annual_notice_due=AsyncMock(return_value=[agr]),
            )
            response = await admin_client.get(
                "/api/v1/agreements/queues/annual-notice-due",
            )

        assert response.status_code == 200
        assert len(response.json()) == 1


# =============================================================================
# GET /api/v1/agreements/{id}/compliance
# =============================================================================


@pytest.mark.unit
class TestAgreementCompliance:
    """Tests for agreement compliance endpoint."""

    @pytest.mark.asyncio
    async def test_get_disclosures(self, admin_client: AsyncClient) -> None:
        """Test getting compliance disclosures for an agreement."""
        agr_id = uuid.uuid4()
        disclosure = _make_disclosure(agreement_id=agr_id)
        with patch(_COMPLIANCE_SVC) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_disclosures_for_agreement=AsyncMock(return_value=[disclosure]),
            )
            response = await admin_client.get(
                f"/api/v1/agreements/{agr_id}/compliance",
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["disclosure_type"] == "pre_sale"


# =============================================================================
# GET /api/v1/compliance/customer/{customer_id}
# =============================================================================


@pytest.mark.unit
class TestCustomerCompliance:
    """Tests for customer compliance endpoint."""

    @pytest.mark.asyncio
    async def test_get_disclosures(self, admin_client: AsyncClient) -> None:
        """Test getting compliance disclosures for a customer."""
        cid = uuid.uuid4()
        disclosure = _make_disclosure()
        with patch(_COMPLIANCE_SVC) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_disclosures_for_customer=AsyncMock(return_value=[disclosure]),
            )
            response = await admin_client.get(f"/api/v1/compliance/customer/{cid}")

        assert response.status_code == 200
        assert len(response.json()) == 1


# =============================================================================
# GET /api/v1/dashboard/summary
# =============================================================================


@pytest.mark.unit
class TestDashboardSummary:
    """Tests for dashboard summary extension endpoint."""

    @pytest.mark.asyncio
    async def test_get_summary(self, admin_client: AsyncClient) -> None:
        """Test getting extended dashboard summary."""
        metrics = AgreementMetrics(
            active_count=5,
            mrr=Decimal("207.92"),
            arpa=Decimal("41.58"),
            renewal_rate=Decimal("90.00"),
            churn_rate=Decimal("3.00"),
            past_due_amount=Decimal("0.00"),
        )
        with (
            patch(_METRICS_SVC) as mock_m_cls,
            patch(_AGR_REPO) as mock_a_cls,
            patch(_LEAD_REPO) as mock_l_cls,
        ):
            mock_m_cls.return_value = AsyncMock(
                compute_metrics=AsyncMock(return_value=metrics),
            )
            mock_a_cls.return_value = AsyncMock(
                get_renewal_pipeline=AsyncMock(return_value=[]),
                get_failed_payments=AsyncMock(return_value=[]),
            )
            mock_l_cls.return_value = AsyncMock(
                count_new_today=AsyncMock(return_value=3),
                get_follow_up_queue=AsyncMock(return_value=([], 2)),
                count_uncontacted=AsyncMock(return_value=0),
            )
            response = await admin_client.get("/api/v1/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["active_agreement_count"] == 5
        assert float(data["mrr"]) == pytest.approx(207.92)
        assert data["new_leads_count"] == 3
        assert data["follow_up_queue_count"] == 2
