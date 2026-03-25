"""
Unit tests for Estimate and Template API endpoints (Task 7.5).

Tests: estimate CRUD, send estimate, estimate template CRUD, contract template CRUD.

Validates: CRM Gap Closure Req 17.3, 17.4, 48.2, 48.3
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.dependencies import get_estimate_service
from grins_platform.api.v1.estimates import router as estimates_router
from grins_platform.api.v1.templates import router as templates_router
from grins_platform.models.enums import EstimateStatus
from grins_platform.schemas.estimate import EstimateResponse, EstimateSendResponse
from grins_platform.services.estimate_service import EstimateService

# =============================================================================
# Helpers
# =============================================================================

_NOW = datetime.now(tz=timezone.utc)


def _mock_estimate(
    estimate_id: uuid.UUID | None = None,
    status: str = EstimateStatus.DRAFT.value,
) -> MagicMock:
    """Create a mock estimate object."""
    est = MagicMock()
    est.id = estimate_id or uuid.uuid4()
    est.lead_id = uuid.uuid4()
    est.customer_id = uuid.uuid4()
    est.job_id = None
    est.template_id = None
    est.status = status
    est.line_items = [{"item": "Sprinkler repair", "quantity": 1, "unit_price": 150}]
    est.options = None
    est.subtotal = Decimal("150.00")
    est.tax_amount = Decimal("12.00")
    est.discount_amount = Decimal("0.00")
    est.total = Decimal("162.00")
    est.promotion_code = None
    est.valid_until = _NOW
    est.notes = None
    est.customer_token = uuid.uuid4()
    est.token_expires_at = _NOW
    est.token_readonly = False
    est.approved_at = None
    est.rejected_at = None
    est.rejection_reason = None
    est.created_at = _NOW
    est.updated_at = _NOW
    return est


def _mock_estimate_template(
    template_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock estimate template object."""
    tpl = MagicMock()
    tpl.id = template_id or uuid.uuid4()
    tpl.name = "Standard Repair"
    tpl.description = "Standard irrigation repair template"
    tpl.line_items = [{"item": "Repair", "quantity": 1, "unit_price": 100}]
    tpl.terms = "Net 30"
    tpl.is_active = True
    tpl.created_at = _NOW
    tpl.updated_at = _NOW
    return tpl


def _mock_contract_template(
    template_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock contract template object."""
    tpl = MagicMock()
    tpl.id = template_id or uuid.uuid4()
    tpl.name = "Standard Contract"
    tpl.body = "This contract is between..."
    tpl.terms_and_conditions = "Standard T&C"
    tpl.is_active = True
    tpl.created_at = _NOW
    tpl.updated_at = _NOW
    return tpl


# =============================================================================
# Fixtures
# =============================================================================


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
def mock_estimate_service() -> AsyncMock:
    """Create a mock EstimateService."""
    svc = AsyncMock(spec=EstimateService)
    svc.repo = AsyncMock()
    return svc


@pytest.fixture
async def estimate_client(
    mock_estimate_service: AsyncMock,
    mock_admin_user: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client for estimate endpoints with auth."""
    app = FastAPI()
    app.include_router(estimates_router, prefix="/api/v1/estimates")
    app.dependency_overrides[get_estimate_service] = lambda: mock_estimate_service
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def template_client(
    mock_estimate_service: AsyncMock,
    mock_admin_user: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client for template endpoints with auth."""
    app = FastAPI()
    app.include_router(templates_router, prefix="/api/v1/templates")
    app.dependency_overrides[get_estimate_service] = lambda: mock_estimate_service
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Estimate CRUD Tests — Req 48.2
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_estimate_returns_201(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test POST /estimates creates an estimate and returns 201."""
    est_mock = _mock_estimate()
    response_obj = EstimateResponse.model_validate(est_mock)
    mock_estimate_service.create_estimate.return_value = response_obj

    resp = await estimate_client.post(
        "/api/v1/estimates",
        json={
            "line_items": [{"item": "Repair", "quantity": 1, "unit_price": 150}],
            "subtotal": "150.00",
            "tax_amount": "12.00",
            "total": "162.00",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["total"] == "162.00"
    mock_estimate_service.create_estimate.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_estimates_returns_paginated(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test GET /estimates returns paginated list."""
    est1 = _mock_estimate()
    est2 = _mock_estimate()
    mock_estimate_service.repo.list_with_filters.return_value = ([est1, est2], 2)

    resp = await estimate_client.get("/api/v1/estimates")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_estimate_returns_200(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test GET /estimates/{id} returns estimate."""
    est = _mock_estimate()
    mock_estimate_service.repo.get_by_id.return_value = est

    resp = await estimate_client.get(f"/api/v1/estimates/{est.id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(est.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_estimate_with_invalid_id_returns_404(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test GET /estimates/{id} returns 404 for missing estimate."""
    mock_estimate_service.repo.get_by_id.return_value = None

    resp = await estimate_client.get(f"/api/v1/estimates/{uuid.uuid4()}")

    assert resp.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_estimate_with_draft_returns_200(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test PATCH /estimates/{id} updates a DRAFT estimate."""
    est = _mock_estimate(status=EstimateStatus.DRAFT.value)
    updated = _mock_estimate(status=EstimateStatus.DRAFT.value)
    updated.notes = "Updated notes"

    mock_estimate_service.repo.get_by_id.return_value = est
    mock_estimate_service.repo.update.return_value = updated

    resp = await estimate_client.patch(
        f"/api/v1/estimates/{est.id}",
        json={"notes": "Updated notes"},
    )

    assert resp.status_code == 200
    mock_estimate_service.repo.update.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_estimate_with_sent_status_returns_400(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test PATCH /estimates/{id} rejects update on non-DRAFT estimate."""
    est = _mock_estimate(status=EstimateStatus.SENT.value)
    mock_estimate_service.repo.get_by_id.return_value = est

    resp = await estimate_client.patch(
        f"/api/v1/estimates/{est.id}",
        json={"notes": "Should fail"},
    )

    assert resp.status_code == 400


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_estimate_returns_204(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test DELETE /estimates/{id} deletes and returns 204."""
    mock_estimate_service.repo.delete.return_value = True

    resp = await estimate_client.delete(f"/api/v1/estimates/{uuid.uuid4()}")

    assert resp.status_code == 204


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_estimate_with_invalid_id_returns_404(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test DELETE /estimates/{id} returns 404 for missing estimate."""
    mock_estimate_service.repo.delete.return_value = False

    resp = await estimate_client.delete(f"/api/v1/estimates/{uuid.uuid4()}")

    assert resp.status_code == 404


# =============================================================================
# Send Estimate — Req 48.3
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_estimate_returns_portal_url(
    estimate_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test POST /estimates/{id}/send returns portal URL."""
    est_id = uuid.uuid4()
    mock_estimate_service.send_estimate.return_value = EstimateSendResponse(
        estimate_id=est_id,
        portal_url="https://portal.grins.com/estimates/abc123",
        sent_via=["sms"],
    )

    resp = await estimate_client.post(f"/api/v1/estimates/{est_id}/send")

    assert resp.status_code == 200
    data = resp.json()
    assert "portal_url" in data
    assert data["sent_via"] == ["sms"]


# =============================================================================
# Estimate Template CRUD — Req 17.3
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_estimate_template_returns_201(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test POST /templates/estimates creates a template."""
    tpl = _mock_estimate_template()
    mock_estimate_service.repo.create_template.return_value = tpl

    resp = await template_client.post(
        "/api/v1/templates/estimates",
        json={"name": "Standard Repair", "line_items": []},
    )

    assert resp.status_code == 201
    assert resp.json()["name"] == "Standard Repair"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_estimate_templates_returns_list(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test GET /templates/estimates returns list."""
    tpl1 = _mock_estimate_template()
    tpl2 = _mock_estimate_template()
    mock_estimate_service.repo.list_templates.return_value = [tpl1, tpl2]

    resp = await template_client.get("/api/v1/templates/estimates")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_estimate_template_returns_200(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test GET /templates/estimates/{id} returns template."""
    tpl = _mock_estimate_template()
    mock_estimate_service.repo.get_template_by_id.return_value = tpl

    resp = await template_client.get(f"/api/v1/templates/estimates/{tpl.id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(tpl.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_estimate_template_with_invalid_id_returns_404(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test GET /templates/estimates/{id} returns 404 for missing."""
    mock_estimate_service.repo.get_template_by_id.return_value = None

    resp = await template_client.get(
        f"/api/v1/templates/estimates/{uuid.uuid4()}",
    )

    assert resp.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_estimate_template_returns_200(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test PATCH /templates/estimates/{id} updates template."""
    tpl = _mock_estimate_template()
    tpl.name = "Updated Name"
    mock_estimate_service.repo.update_template.return_value = tpl

    resp = await template_client.patch(
        f"/api/v1/templates/estimates/{tpl.id}",
        json={"name": "Updated Name"},
    )

    assert resp.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_estimate_template_returns_204(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test DELETE /templates/estimates/{id} soft-deletes."""
    mock_estimate_service.repo.delete_template.return_value = True

    resp = await template_client.delete(
        f"/api/v1/templates/estimates/{uuid.uuid4()}",
    )

    assert resp.status_code == 204


# =============================================================================
# Contract Template CRUD — Req 17.4
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_contract_template_returns_201(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test POST /templates/contracts creates a contract template."""
    tpl = _mock_contract_template()
    mock_estimate_service.repo.create_contract_template.return_value = tpl

    resp = await template_client.post(
        "/api/v1/templates/contracts",
        json={"name": "Standard Contract", "body": "Contract body text"},
    )

    assert resp.status_code == 201
    assert resp.json()["name"] == "Standard Contract"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_contract_templates_returns_list(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test GET /templates/contracts returns list."""
    tpl1 = _mock_contract_template()
    tpl2 = _mock_contract_template()
    mock_estimate_service.repo.list_contract_templates.return_value = [tpl1, tpl2]

    resp = await template_client.get("/api/v1/templates/contracts")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_contract_template_returns_200(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test GET /templates/contracts/{id} returns template."""
    tpl = _mock_contract_template()
    mock_estimate_service.repo.get_contract_template_by_id.return_value = tpl

    resp = await template_client.get(f"/api/v1/templates/contracts/{tpl.id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(tpl.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_contract_template_returns_200(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test PATCH /templates/contracts/{id} updates template."""
    tpl = _mock_contract_template()
    tpl.name = "Updated Contract"
    mock_estimate_service.repo.update_contract_template.return_value = tpl

    resp = await template_client.patch(
        f"/api/v1/templates/contracts/{tpl.id}",
        json={"name": "Updated Contract"},
    )

    assert resp.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_contract_template_returns_204(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test DELETE /templates/contracts/{id} soft-deletes."""
    mock_estimate_service.repo.delete_contract_template.return_value = True

    resp = await template_client.delete(
        f"/api/v1/templates/contracts/{uuid.uuid4()}",
    )

    assert resp.status_code == 204


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_contract_template_with_invalid_id_returns_404(
    template_client: AsyncClient,
    mock_estimate_service: AsyncMock,
) -> None:
    """Test DELETE /templates/contracts/{id} returns 404 for missing."""
    mock_estimate_service.repo.delete_contract_template.return_value = False

    resp = await template_client.delete(
        f"/api/v1/templates/contracts/{uuid.uuid4()}",
    )

    assert resp.status_code == 404
