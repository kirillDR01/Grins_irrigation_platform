"""Integration tests for agreement APIs.

Tests cover Stripe webhook endpoint with simulated payloads,
agreement CRUD endpoints with filtering/pagination,
metrics API, and dashboard summary extension.

Validates: Requirements 40.3
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import stripe as stripe_mod
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
    require_manager_or_admin,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.main import app
from grins_platform.services.metrics_service import AgreementMetrics

# Patch targets
_AGR_REPO = "grins_platform.api.v1.agreements.AgreementRepository"
_TIER_REPO = "grins_platform.api.v1.agreements.AgreementTierRepository"
_AGR_SVC = "grins_platform.api.v1.agreements.AgreementService"
_METRICS_SVC = "grins_platform.api.v1.agreements.MetricsService"
_COMPLIANCE_SVC = "grins_platform.api.v1.agreements.ComplianceService"
_LEAD_REPO = "grins_platform.api.v1.agreements.LeadRepository"
_STRIPE_CONSTRUCT = "stripe.Webhook.construct_event"
_STRIPE_SETTINGS = "grins_platform.api.v1.webhooks.StripeSettings"
_WEBHOOK_HANDLER = "grins_platform.api.v1.webhooks.StripeWebhookHandler"


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


def _mock_db() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_agreement(
    *,
    agr_id: uuid.UUID | None = None,
    status: str = "active",
    payment_status: str = "current",
    annual_price: Decimal = Decimal("499.00"),
) -> MagicMock:
    agr = MagicMock()
    agr.id = agr_id or uuid.uuid4()
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
    agr.stripe_subscription_id = "sub_123"
    agr.stripe_customer_id = "cus_123"
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
    tier = MagicMock()
    tier.id = tier_id or uuid.uuid4()
    tier.name = "Essential"
    tier.slug = "essential-residential"
    tier.description = "Basic package"
    tier.package_type = "residential"
    tier.annual_price = Decimal("499.00")
    tier.billing_frequency = "annual"
    tier.included_services = [{"service_type": "spring_startup"}]
    tier.perks = ["Priority scheduling"]
    tier.is_active = True
    tier.display_order = 1
    tier.stripe_product_id = "prod_123"
    tier.stripe_price_id = "price_123"
    tier.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tier.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return tier


def _make_disclosure(*, agreement_id: uuid.UUID | None = None) -> MagicMock:
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


def _default_metrics() -> AgreementMetrics:
    return AgreementMetrics(
        active_count=5,
        mrr=Decimal("207.92"),
        arpa=Decimal("41.58"),
        renewal_rate=Decimal("85.00"),
        churn_rate=Decimal("15.00"),
        past_due_amount=Decimal("499.00"),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_client() -> AsyncGenerator[AsyncClient, None]:
    admin = _mock_admin()
    db = _mock_db()
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_active_user] = lambda: admin
    app.dependency_overrides[require_manager_or_admin] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def public_client() -> AsyncGenerator[AsyncClient, None]:
    """Client without auth overrides for webhook endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =========================================================================
# Stripe Webhook Integration Tests
# =========================================================================


@pytest.mark.integration
class TestStripeWebhookIntegration:
    """Integration tests for Stripe webhook endpoint.

    Validates: Requirement 40.3 — webhook with simulated payloads
    """

    @pytest.mark.asyncio
    async def test_webhook_valid_signature_processes_event(
        self,
        public_client: AsyncClient,
    ) -> None:
        """Webhook with valid signature returns 200 and processes event."""
        mock_event: dict[str, Any] = {
            "id": f"evt_{uuid.uuid4().hex[:24]}",
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test", "metadata": {}}},
        }
        mock_settings = MagicMock()
        mock_settings.stripe_webhook_secret = "whsec_test"

        mock_handler_instance = AsyncMock()
        mock_handler_instance.handle_event = AsyncMock(
            return_value={"status": "processed"},
        )

        with (
            patch(_STRIPE_SETTINGS, return_value=mock_settings),
            patch(_STRIPE_CONSTRUCT, return_value=mock_event),
            patch(_WEBHOOK_HANDLER, return_value=mock_handler_instance),
        ):
            response = await public_client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(mock_event),
                headers={
                    "stripe-signature": "t=123,v1=abc",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "processed"

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_returns_400(
        self,
        public_client: AsyncClient,
    ) -> None:
        """Webhook with invalid signature returns 400."""
        mock_settings = MagicMock()
        mock_settings.stripe_webhook_secret = "whsec_test"

        with (
            patch(_STRIPE_SETTINGS, return_value=mock_settings),
            patch(
                _STRIPE_CONSTRUCT,
                side_effect=stripe_mod.SignatureVerificationError(  # type: ignore[no-untyped-call]
                    "bad sig",
                    "sig_header",
                ),
            ),
        ):
            response = await public_client.post(
                "/api/v1/webhooks/stripe",
                content=b'{"id":"evt_test"}',
                headers={
                    "stripe-signature": "invalid",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 400
        assert "Invalid signature" in response.json()["error"]

    @pytest.mark.asyncio
    async def test_webhook_missing_secret_returns_400(
        self,
        public_client: AsyncClient,
    ) -> None:
        """Webhook returns 400 when webhook secret not configured."""
        mock_settings = MagicMock()
        mock_settings.stripe_webhook_secret = ""

        with patch(_STRIPE_SETTINGS, return_value=mock_settings):
            response = await public_client.post(
                "/api/v1/webhooks/stripe",
                content=b'{"id":"evt_test"}',
                headers={
                    "stripe-signature": "t=123,v1=abc",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_duplicate_event_returns_already_processed(
        self,
        public_client: AsyncClient,
    ) -> None:
        """Duplicate event returns 200 with already_processed status."""
        event_id = f"evt_{uuid.uuid4().hex[:24]}"
        mock_event: dict[str, Any] = {
            "id": event_id,
            "type": "invoice.paid",
            "data": {"object": {"id": "in_test"}},
        }
        mock_settings = MagicMock()
        mock_settings.stripe_webhook_secret = "whsec_test"

        mock_handler_instance = AsyncMock()
        mock_handler_instance.handle_event = AsyncMock(
            return_value={"status": "already_processed"},
        )

        with (
            patch(_STRIPE_SETTINGS, return_value=mock_settings),
            patch(_STRIPE_CONSTRUCT, return_value=mock_event),
            patch(_WEBHOOK_HANDLER, return_value=mock_handler_instance),
        ):
            response = await public_client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(mock_event),
                headers={
                    "stripe-signature": "t=123,v1=abc",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "already_processed"


# =========================================================================
# Agreement CRUD Integration Tests
# =========================================================================


@pytest.mark.integration
class TestAgreementCRUDIntegration:
    """Integration tests for agreement CRUD endpoints.

    Validates: Requirement 40.3 — agreement CRUD with filtering/pagination
    """

    @pytest.mark.asyncio
    async def test_list_agreements_with_pagination(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """List agreements returns paginated response."""
        agrs = [_make_agreement() for _ in range(3)]
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                list_with_filters=AsyncMock(return_value=(agrs, 3)),
            )
            resp = await admin_client.get(
                "/api/v1/agreements?page=1&page_size=10",
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_agreements_with_status_filter(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """List agreements filters by status."""
        agr = _make_agreement(status="pending_renewal")
        with patch(_AGR_REPO) as mock_cls:
            mock_repo = AsyncMock(
                list_with_filters=AsyncMock(return_value=([agr], 1)),
            )
            mock_cls.return_value = mock_repo
            resp = await admin_client.get(
                "/api/v1/agreements?status=pending_renewal",
            )

        assert resp.status_code == 200
        mock_repo.list_with_filters.assert_called_once()
        call_kwargs = mock_repo.list_with_filters.call_args[1]
        assert call_kwargs["status"] == "pending_renewal"

    @pytest.mark.asyncio
    async def test_list_agreements_with_customer_filter(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """List agreements filters by customer_id."""
        cid = uuid.uuid4()
        with patch(_AGR_REPO) as mock_cls:
            mock_repo = AsyncMock(
                list_with_filters=AsyncMock(return_value=([], 0)),
            )
            mock_cls.return_value = mock_repo
            resp = await admin_client.get(
                f"/api/v1/agreements?customer_id={cid}",
            )

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_with_filters.call_args[1]
        assert call_kwargs["customer_id"] == cid

    @pytest.mark.asyncio
    async def test_list_agreements_expiring_soon(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """List agreements with expiring_soon filter."""
        with patch(_AGR_REPO) as mock_cls:
            mock_repo = AsyncMock(
                list_with_filters=AsyncMock(return_value=([], 0)),
            )
            mock_cls.return_value = mock_repo
            resp = await admin_client.get(
                "/api/v1/agreements?expiring_soon=true",
            )

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_with_filters.call_args[1]
        assert call_kwargs["expiring_soon"] is True

    @pytest.mark.asyncio
    async def test_get_agreement_detail(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Get agreement detail returns full response."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agr_id=agr_id)
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=agr),
            )
            resp = await admin_client.get(f"/api/v1/agreements/{agr_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["agreement_number"] == "AGR-2026-001"
        assert data["stripe_subscription_id"] == "sub_123"
        assert "jobs" in data
        assert "status_logs" in data

    @pytest.mark.asyncio
    async def test_get_agreement_not_found(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Get non-existent agreement returns 404."""
        agr_id = uuid.uuid4()
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=None),
            )
            resp = await admin_client.get(f"/api/v1/agreements/{agr_id}")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_agreement_status_valid(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Valid status transition succeeds."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agr_id=agr_id, status="active")
        with (
            patch(_AGR_REPO) as mock_repo_cls,
            patch(_TIER_REPO),
            patch(_AGR_SVC) as mock_svc_cls,
        ):
            mock_svc_cls.return_value = AsyncMock(
                transition_status=AsyncMock(),
            )
            mock_repo_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=agr),
            )
            resp = await admin_client.patch(
                f"/api/v1/agreements/{agr_id}/status",
                json={"status": "paused", "reason": "Payment issue"},
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_agreement_status_invalid(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Invalid status value returns 400."""
        agr_id = uuid.uuid4()
        with (
            patch(_AGR_REPO),
            patch(_TIER_REPO),
            patch(_AGR_SVC),
        ):
            resp = await admin_client.patch(
                f"/api/v1/agreements/{agr_id}/status",
                json={"status": "nonexistent_status"},
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_renewal(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Approve renewal returns updated agreement."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agr_id=agr_id, status="pending_renewal")
        with (
            patch(_AGR_REPO) as mock_repo_cls,
            patch(_TIER_REPO),
            patch(_AGR_SVC) as mock_svc_cls,
        ):
            mock_svc_cls.return_value = AsyncMock(
                approve_renewal=AsyncMock(),
            )
            mock_repo_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=agr),
            )
            resp = await admin_client.post(
                f"/api/v1/agreements/{agr_id}/approve-renewal",
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reject_renewal(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Reject renewal returns updated agreement."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agr_id=agr_id, status="pending_renewal")
        with (
            patch(_AGR_REPO) as mock_repo_cls,
            patch(_TIER_REPO),
            patch(_AGR_SVC) as mock_svc_cls,
        ):
            mock_svc_cls.return_value = AsyncMock(
                reject_renewal=AsyncMock(),
            )
            mock_repo_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=agr),
            )
            resp = await admin_client.post(
                f"/api/v1/agreements/{agr_id}/reject-renewal",
            )

        assert resp.status_code == 200


# =========================================================================
# Tier Endpoints Integration Tests
# =========================================================================


@pytest.mark.integration
class TestTierEndpointsIntegration:
    """Integration tests for agreement tier endpoints.

    Validates: Requirement 40.3
    """

    @pytest.mark.asyncio
    async def test_list_active_tiers(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """List active tiers returns tier data."""
        tiers = [_make_tier(), _make_tier(tier_id=uuid.uuid4())]
        with patch(_TIER_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                list_active=AsyncMock(return_value=tiers),
            )
            resp = await admin_client.get("/api/v1/agreement-tiers")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_tier_detail(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Get tier detail returns full tier info."""
        tid = uuid.uuid4()
        tier = _make_tier(tier_id=tid)
        with patch(_TIER_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=tier),
            )
            resp = await admin_client.get(f"/api/v1/agreement-tiers/{tid}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Essential"

    @pytest.mark.asyncio
    async def test_get_tier_not_found(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Get non-existent tier returns 404."""
        tid = uuid.uuid4()
        with patch(_TIER_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_by_id=AsyncMock(return_value=None),
            )
            resp = await admin_client.get(f"/api/v1/agreement-tiers/{tid}")

        assert resp.status_code == 404


# =========================================================================
# Metrics API Integration Tests
# =========================================================================


@pytest.mark.integration
class TestMetricsIntegration:
    """Integration tests for metrics API.

    Validates: Requirement 40.3 — metrics returning correct computed values
    """

    @pytest.mark.asyncio
    async def test_metrics_returns_computed_values(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Metrics endpoint returns correct computed values."""
        metrics = _default_metrics()
        with patch(_METRICS_SVC) as mock_cls:
            mock_cls.return_value = AsyncMock(
                compute_metrics=AsyncMock(return_value=metrics),
            )
            resp = await admin_client.get("/api/v1/agreements/metrics/summary")

        assert resp.status_code == 200
        data = resp.json()
        assert data["active_count"] == 5
        assert Decimal(data["mrr"]) == Decimal("207.92")
        assert Decimal(data["arpa"]) == Decimal("41.58")
        assert Decimal(data["renewal_rate"]) == Decimal("85.00")
        assert Decimal(data["churn_rate"]) == Decimal("15.00")
        assert Decimal(data["past_due_amount"]) == Decimal("499.00")

    @pytest.mark.asyncio
    async def test_renewal_pipeline_returns_pending_renewal(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Renewal pipeline returns PENDING_RENEWAL agreements."""
        agrs = [
            _make_agreement(status="pending_renewal"),
            _make_agreement(status="pending_renewal"),
        ]
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_renewal_pipeline=AsyncMock(return_value=agrs),
            )
            resp = await admin_client.get(
                "/api/v1/agreements/queues/renewal-pipeline",
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_failed_payments_returns_past_due(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Failed payments returns PAST_DUE/FAILED agreements."""
        agrs = [_make_agreement(payment_status="past_due")]
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_failed_payments=AsyncMock(return_value=agrs),
            )
            resp = await admin_client.get(
                "/api/v1/agreements/queues/failed-payments",
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_annual_notice_due(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Annual notice due returns agreements needing notice."""
        agrs = [_make_agreement()]
        with patch(_AGR_REPO) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_annual_notice_due=AsyncMock(return_value=agrs),
            )
            resp = await admin_client.get(
                "/api/v1/agreements/queues/annual-notice-due",
            )

        assert resp.status_code == 200
        assert len(resp.json()) == 1


# =========================================================================
# Compliance Audit Integration Tests
# =========================================================================


@pytest.mark.integration
class TestComplianceAuditIntegration:
    """Integration tests for compliance audit endpoints.

    Validates: Requirement 40.3
    """

    @pytest.mark.asyncio
    async def test_get_agreement_compliance(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Get compliance disclosures for an agreement."""
        agr_id = uuid.uuid4()
        disclosures = [
            _make_disclosure(agreement_id=agr_id),
            _make_disclosure(agreement_id=agr_id),
        ]
        with patch(_COMPLIANCE_SVC) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_disclosures_for_agreement=AsyncMock(
                    return_value=disclosures,
                ),
            )
            resp = await admin_client.get(
                f"/api/v1/agreements/{agr_id}/compliance",
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["disclosure_type"] == "pre_sale"

    @pytest.mark.asyncio
    async def test_get_customer_compliance(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Get compliance disclosures for a customer."""
        cid = uuid.uuid4()
        disclosures = [_make_disclosure()]
        with patch(_COMPLIANCE_SVC) as mock_cls:
            mock_cls.return_value = AsyncMock(
                get_disclosures_for_customer=AsyncMock(
                    return_value=disclosures,
                ),
            )
            resp = await admin_client.get(
                f"/api/v1/compliance/customer/{cid}",
            )

        assert resp.status_code == 200
        assert len(resp.json()) == 1


# =========================================================================
# Dashboard Summary Extension Integration Tests
# =========================================================================


@pytest.mark.integration
class TestDashboardSummaryIntegration:
    """Integration tests for dashboard summary extension.

    Validates: Requirement 40.3 — dashboard with agreement + lead data
    """

    @pytest.mark.asyncio
    async def test_dashboard_summary_with_agreement_and_lead_data(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Dashboard summary returns agreement and lead metrics."""
        metrics = _default_metrics()
        renewal_agrs = [_make_agreement(status="pending_renewal")]
        failed_agrs = [_make_agreement(payment_status="past_due")]

        mock_lead_repo = AsyncMock()
        mock_lead_repo.count_new_today = AsyncMock(return_value=3)
        mock_lead_repo.get_follow_up_queue = AsyncMock(return_value=([], 2))
        mock_lead_repo.count_uncontacted = AsyncMock(return_value=1)

        mock_agr_repo = AsyncMock()
        mock_agr_repo.get_renewal_pipeline = AsyncMock(
            return_value=renewal_agrs,
        )
        mock_agr_repo.get_failed_payments = AsyncMock(
            return_value=failed_agrs,
        )

        # Mock the db.execute for oldest lead age
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(
            return_value=datetime.now(timezone.utc) - timedelta(hours=5),
        )
        mock_db = _mock_db()
        mock_db.execute = AsyncMock(return_value=mock_result)

        admin = _mock_admin()
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[require_manager_or_admin] = lambda: admin
        app.dependency_overrides[get_db_session] = lambda: mock_db

        try:
            with (
                patch(_METRICS_SVC) as mock_metrics_cls,
                patch(_AGR_REPO) as mock_agr_cls,
                patch(_LEAD_REPO) as mock_lead_cls,
            ):
                mock_metrics_cls.return_value = AsyncMock(
                    compute_metrics=AsyncMock(return_value=metrics),
                )
                mock_agr_cls.return_value = mock_agr_repo
                mock_lead_cls.return_value = mock_lead_repo

                resp = await admin_client.get("/api/v1/dashboard/summary")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["active_agreement_count"] == 5
        assert Decimal(data["mrr"]) == Decimal("207.92")
        assert data["renewal_pipeline_count"] == 1
        assert data["failed_payment_count"] == 1
        assert data["new_leads_count"] == 3
        assert data["follow_up_queue_count"] == 2

    @pytest.mark.asyncio
    async def test_dashboard_summary_with_no_leads(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Dashboard summary handles zero leads gracefully."""
        metrics = _default_metrics()

        mock_lead_repo = AsyncMock()
        mock_lead_repo.count_new_today = AsyncMock(return_value=0)
        mock_lead_repo.get_follow_up_queue = AsyncMock(return_value=([], 0))
        mock_lead_repo.count_uncontacted = AsyncMock(return_value=0)

        mock_agr_repo = AsyncMock()
        mock_agr_repo.get_renewal_pipeline = AsyncMock(return_value=[])
        mock_agr_repo.get_failed_payments = AsyncMock(return_value=[])

        with (
            patch(_METRICS_SVC) as mock_metrics_cls,
            patch(_AGR_REPO) as mock_agr_cls,
            patch(_LEAD_REPO) as mock_lead_cls,
        ):
            mock_metrics_cls.return_value = AsyncMock(
                compute_metrics=AsyncMock(return_value=metrics),
            )
            mock_agr_cls.return_value = mock_agr_repo
            mock_lead_cls.return_value = mock_lead_repo

            resp = await admin_client.get("/api/v1/dashboard/summary")

        assert resp.status_code == 200
        data = resp.json()
        assert data["new_leads_count"] == 0
        assert data["follow_up_queue_count"] == 0
        assert data["renewal_pipeline_count"] == 0
        assert data["failed_payment_count"] == 0
        assert data["leads_awaiting_contact_oldest_age_hours"] is None


# =========================================================================
# Cross-Endpoint Integration Tests
# =========================================================================


@pytest.mark.integration
class TestCrossEndpointIntegration:
    """Integration tests spanning multiple agreement endpoints.

    Validates: Requirement 40.3
    """

    @pytest.mark.asyncio
    async def test_list_then_detail_consistency(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Agreement in list and detail have consistent data."""
        agr_id = uuid.uuid4()
        agr = _make_agreement(agr_id=agr_id)

        with patch(_AGR_REPO) as mock_cls:
            mock_repo = AsyncMock(
                list_with_filters=AsyncMock(return_value=([agr], 1)),
                get_by_id=AsyncMock(return_value=agr),
            )
            mock_cls.return_value = mock_repo

            list_resp = await admin_client.get("/api/v1/agreements")
            detail_resp = await admin_client.get(
                f"/api/v1/agreements/{agr_id}",
            )

        list_item = list_resp.json()["items"][0]
        detail = detail_resp.json()
        assert list_item["agreement_number"] == detail["agreement_number"]
        assert list_item["status"] == detail["status"]
        assert list_item["annual_price"] == detail["annual_price"]

    @pytest.mark.asyncio
    async def test_metrics_consistent_with_failed_payments_queue(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Metrics past_due_amount consistent with failed payments queue."""
        agr = _make_agreement(
            payment_status="past_due",
            annual_price=Decimal("499.00"),
        )
        metrics = AgreementMetrics(
            active_count=1,
            mrr=Decimal(0),
            arpa=Decimal(0),
            renewal_rate=Decimal(0),
            churn_rate=Decimal(0),
            past_due_amount=Decimal("499.00"),
        )

        with (
            patch(_AGR_REPO) as mock_repo_cls,
            patch(_METRICS_SVC) as mock_metrics_cls,
        ):
            mock_repo_cls.return_value = AsyncMock(
                get_failed_payments=AsyncMock(return_value=[agr]),
            )
            mock_metrics_cls.return_value = AsyncMock(
                compute_metrics=AsyncMock(return_value=metrics),
            )

            queue_resp = await admin_client.get(
                "/api/v1/agreements/queues/failed-payments",
            )
            metrics_resp = await admin_client.get(
                "/api/v1/agreements/metrics/summary",
            )

        assert len(queue_resp.json()) == 1
        assert Decimal(metrics_resp.json()["past_due_amount"]) == Decimal("499.00")
