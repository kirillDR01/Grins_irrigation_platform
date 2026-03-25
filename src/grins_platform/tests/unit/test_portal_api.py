"""Unit tests for Portal API endpoints.

Tests public portal endpoints for estimate viewing, approval, rejection,
and contract signing. All endpoints are public (no auth required).

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 78.5, 78.6
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.api.v1.portal import _get_estimate_service, router
from grins_platform.exceptions import (
    EstimateAlreadyApprovedError,
    EstimateNotFoundError,
    EstimateTokenExpiredError,
)
from grins_platform.schemas.estimate import EstimateResponse
from grins_platform.services.estimate_service import EstimateService

# =============================================================================
# Helpers
# =============================================================================


def _make_estimate_mock(
    *,
    status: str = "sent",
    token_readonly: bool = False,
    subtotal: Decimal = Decimal("500.00"),
    tax_amount: Decimal = Decimal("40.00"),
    discount_amount: Decimal = Decimal("0.00"),
    total: Decimal = Decimal("540.00"),
) -> MagicMock:
    """Create a mock Estimate model for portal tests."""
    est = MagicMock()
    est.id = uuid4()
    est.status = status
    est.line_items = [
        {"item": "Sprinkler Repair", "unit_price": "250.00", "quantity": "2"},
    ]
    est.options = None
    est.subtotal = subtotal
    est.tax_amount = tax_amount
    est.discount_amount = discount_amount
    est.total = total
    est.promotion_code = None
    est.valid_until = datetime.now(tz=timezone.utc) + timedelta(days=30)
    est.notes = "Test estimate"
    est.token_readonly = token_readonly
    est.customer_token = uuid4()
    est.token_expires_at = datetime.now(tz=timezone.utc) + timedelta(days=30)
    return est


def _make_estimate_response_mock(
    *,
    status: str = "approved",
) -> EstimateResponse:
    """Create a mock EstimateResponse for service return values."""
    now = datetime.now(tz=timezone.utc)
    return EstimateResponse(
        id=uuid4(),
        status=status,
        line_items=[
            {"item": "Sprinkler Repair", "unit_price": "250.00", "quantity": "2"},
        ],
        options=None,
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("40.00"),
        discount_amount=Decimal("0.00"),
        total=Decimal("540.00"),
        promotion_code=None,
        valid_until=now + timedelta(days=30),
        notes="Test estimate",
        customer_token=uuid4(),
        token_expires_at=now + timedelta(days=30),
        token_readonly=True,
        approved_at=now,
        rejected_at=None,
        rejection_reason=None,
        created_at=now,
        updated_at=now,
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_service() -> AsyncMock:
    """Create a mocked EstimateService."""
    return AsyncMock(spec=EstimateService)


@pytest.fixture
def app(mock_service: AsyncMock) -> FastAPI:
    """Create FastAPI app with mocked dependencies."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    test_app.dependency_overrides[_get_estimate_service] = lambda: mock_service
    test_app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# =============================================================================
# GET /api/v1/portal/estimates/{token} — View estimate
# =============================================================================


@pytest.mark.unit
class TestGetPortalEstimate:
    """Tests for GET /api/v1/portal/estimates/{token}.

    Validates: Requirements 16.1, 78.5, 78.6
    """

    def test_get_estimate_with_valid_token_returns_200(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Valid token returns estimate without internal IDs."""
        estimate = _make_estimate_mock()
        mock_service.get_by_portal_token.return_value = estimate

        token = uuid4()
        resp = client.get(f"/api/v1/portal/estimates/{token}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "sent"
        assert data["total"] == "540.00"
        assert data["readonly"] is False
        # Req 78.6: No internal IDs
        assert "customer_id" not in data
        assert "lead_id" not in data
        assert "staff_id" not in data
        assert "job_id" not in data
        assert "id" not in data

    def test_get_estimate_with_invalid_token_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Unknown token returns 404."""
        mock_service.get_by_portal_token.side_effect = EstimateNotFoundError(
            "unknown",
        )

        token = uuid4()
        resp = client.get(f"/api/v1/portal/estimates/{token}")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_estimate_with_expired_token_returns_410(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Expired token returns 410 Gone."""
        token = uuid4()
        mock_service.get_by_portal_token.side_effect = EstimateTokenExpiredError(
            token,
        )

        resp = client.get(f"/api/v1/portal/estimates/{token}")

        assert resp.status_code == 410
        assert "expired" in resp.json()["detail"].lower()

    def test_get_estimate_with_readonly_token_returns_readonly_true(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Approved estimate shows readonly=True."""
        estimate = _make_estimate_mock(
            status="approved",
            token_readonly=True,
        )
        mock_service.get_by_portal_token.return_value = estimate

        token = uuid4()
        resp = client.get(f"/api/v1/portal/estimates/{token}")

        assert resp.status_code == 200
        assert resp.json()["readonly"] is True

    def test_get_estimate_response_excludes_internal_ids(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Portal response must not contain any internal IDs (Req 78.6)."""
        estimate = _make_estimate_mock()
        mock_service.get_by_portal_token.return_value = estimate

        token = uuid4()
        resp = client.get(f"/api/v1/portal/estimates/{token}")

        data = resp.json()
        forbidden_keys = {
            "id", "customer_id", "lead_id", "job_id",
            "template_id", "staff_id", "created_by",
        }
        assert not forbidden_keys.intersection(data.keys())


# =============================================================================
# POST /api/v1/portal/estimates/{token}/approve — Approve estimate
# =============================================================================


@pytest.mark.unit
class TestApprovePortalEstimate:
    """Tests for POST /api/v1/portal/estimates/{token}/approve.

    Validates: Requirements 16.2, 78.4, 78.5
    """

    def test_approve_with_valid_token_returns_200(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Valid approval returns estimate with readonly=True."""
        result = _make_estimate_response_mock(status="approved")
        mock_service.approve_via_portal.return_value = result

        token = uuid4()
        resp = client.post(f"/api/v1/portal/estimates/{token}/approve")

        assert resp.status_code == 200
        data = resp.json()
        assert data["readonly"] is True
        # No internal IDs
        assert "customer_id" not in data
        assert "lead_id" not in data

    def test_approve_with_body_uses_provided_ip_and_ua(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Approval with body uses provided IP and user agent."""
        result = _make_estimate_response_mock(status="approved")
        mock_service.approve_via_portal.return_value = result

        token = uuid4()
        resp = client.post(
            f"/api/v1/portal/estimates/{token}/approve",
            json={
                "ip_address": "192.168.1.1",
                "user_agent": "CustomBrowser/1.0",
            },
        )

        assert resp.status_code == 200
        mock_service.approve_via_portal.assert_called_once_with(
            token=token,
            ip_address="192.168.1.1",
            user_agent="CustomBrowser/1.0",
        )

    def test_approve_with_invalid_token_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Unknown token returns 404."""
        mock_service.approve_via_portal.side_effect = EstimateNotFoundError(
            "unknown",
        )

        token = uuid4()
        resp = client.post(f"/api/v1/portal/estimates/{token}/approve")

        assert resp.status_code == 404

    def test_approve_with_expired_token_returns_410(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Expired token returns 410 Gone."""
        token = uuid4()
        mock_service.approve_via_portal.side_effect = EstimateTokenExpiredError(
            token,
        )

        resp = client.post(f"/api/v1/portal/estimates/{token}/approve")

        assert resp.status_code == 410

    def test_approve_with_already_decided_returns_409(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Already approved/rejected estimate returns 409."""
        mock_service.approve_via_portal.side_effect = EstimateAlreadyApprovedError(
            uuid4(),
        )

        token = uuid4()
        resp = client.post(f"/api/v1/portal/estimates/{token}/approve")

        assert resp.status_code == 409
        assert "already" in resp.json()["detail"].lower()


# =============================================================================
# POST /api/v1/portal/estimates/{token}/reject — Reject estimate
# =============================================================================


@pytest.mark.unit
class TestRejectPortalEstimate:
    """Tests for POST /api/v1/portal/estimates/{token}/reject.

    Validates: Requirements 16.3, 78.5
    """

    def test_reject_with_valid_token_returns_200(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Valid rejection returns estimate with readonly=True."""
        result = _make_estimate_response_mock(status="rejected")
        mock_service.reject_via_portal.return_value = result

        token = uuid4()
        resp = client.post(
            f"/api/v1/portal/estimates/{token}/reject",
            json={"reason": "Too expensive"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["readonly"] is True

    def test_reject_with_no_reason_returns_200(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Rejection without reason body still succeeds."""
        result = _make_estimate_response_mock(status="rejected")
        mock_service.reject_via_portal.return_value = result

        token = uuid4()
        resp = client.post(f"/api/v1/portal/estimates/{token}/reject")

        assert resp.status_code == 200
        mock_service.reject_via_portal.assert_called_once_with(
            token=token,
            reason=None,
        )

    def test_reject_with_invalid_token_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Unknown token returns 404."""
        mock_service.reject_via_portal.side_effect = EstimateNotFoundError(
            "unknown",
        )

        token = uuid4()
        resp = client.post(f"/api/v1/portal/estimates/{token}/reject")

        assert resp.status_code == 404

    def test_reject_with_expired_token_returns_410(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Expired token returns 410 Gone."""
        token = uuid4()
        mock_service.reject_via_portal.side_effect = EstimateTokenExpiredError(
            token,
        )

        resp = client.post(f"/api/v1/portal/estimates/{token}/reject")

        assert resp.status_code == 410

    def test_reject_with_already_decided_returns_409(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Already decided estimate returns 409."""
        mock_service.reject_via_portal.side_effect = EstimateAlreadyApprovedError(
            uuid4(),
        )

        token = uuid4()
        resp = client.post(f"/api/v1/portal/estimates/{token}/reject")

        assert resp.status_code == 409


# =============================================================================
# POST /api/v1/portal/contracts/{token}/sign — Sign contract
# =============================================================================


@pytest.mark.unit
class TestSignPortalContract:
    """Tests for POST /api/v1/portal/contracts/{token}/sign.

    Validates: Requirements 16.4, 78.5
    """

    def test_sign_with_valid_token_returns_200(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Valid signature returns estimate with readonly=True."""
        result = _make_estimate_response_mock(status="approved")
        mock_service.approve_via_portal.return_value = result

        token = uuid4()
        resp = client.post(
            f"/api/v1/portal/contracts/{token}/sign",
            json={
                "signature_data": "data:image/png;base64,iVBORw0KGgo=",
                "ip_address": "10.0.0.1",
                "user_agent": "Mobile/1.0",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["readonly"] is True
        # No internal IDs
        assert "customer_id" not in data

    def test_sign_without_signature_data_returns_422(
        self,
        client: TestClient,
        mock_service: AsyncMock,  # noqa: ARG002 - needed for app fixture
    ) -> None:
        """Missing signature_data returns validation error."""
        token = uuid4()
        resp = client.post(
            f"/api/v1/portal/contracts/{token}/sign",
            json={},
        )

        assert resp.status_code == 422

    def test_sign_with_invalid_token_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Unknown token returns 404."""
        mock_service.approve_via_portal.side_effect = EstimateNotFoundError(
            "unknown",
        )

        token = uuid4()
        resp = client.post(
            f"/api/v1/portal/contracts/{token}/sign",
            json={"signature_data": "base64data"},
        )

        assert resp.status_code == 404

    def test_sign_with_expired_token_returns_410(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Expired token returns 410 Gone."""
        token = uuid4()
        mock_service.approve_via_portal.side_effect = EstimateTokenExpiredError(
            token,
        )

        resp = client.post(
            f"/api/v1/portal/contracts/{token}/sign",
            json={"signature_data": "base64data"},
        )

        assert resp.status_code == 410

    def test_sign_with_already_signed_returns_409(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Already signed contract returns 409."""
        mock_service.approve_via_portal.side_effect = EstimateAlreadyApprovedError(
            uuid4(),
        )

        token = uuid4()
        resp = client.post(
            f"/api/v1/portal/contracts/{token}/sign",
            json={"signature_data": "base64data"},
        )

        assert resp.status_code == 409
        assert "already" in resp.json()["detail"].lower()
