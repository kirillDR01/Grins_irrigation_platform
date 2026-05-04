"""Regression tests for B-6 (2026-05-04 sign-off).

``LeadService.delete_lead`` previously had no error handling for FK
violations. When a lead had associated rows (e.g. ``sms_consent_records``),
the ``DELETE`` raised ``IntegrityError`` and surfaced as HTTP 500. The fix:
catch the IntegrityError, roll back the session, and raise the new
``LeadHasReferencesError`` domain exception. The route translates that to
HTTP 409 — and also catches ``LeadNotFoundError`` for HTTP 404 (previously
also a 500).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from grins_platform.api.v1.leads import (
    _get_lead_service,
    router as leads_router,
)
from grins_platform.exceptions import LeadHasReferencesError, LeadNotFoundError
from grins_platform.services.lead_service import LeadService


def _build_service_with_repo() -> tuple[LeadService, AsyncMock]:
    repo = AsyncMock()
    repo.session = AsyncMock()
    service = LeadService(
        lead_repository=repo,
        customer_service=AsyncMock(),
        job_service=AsyncMock(),
        staff_repository=AsyncMock(),
    )
    return service, repo


@pytest.mark.unit
class TestDeleteLeadIntegrityErrorService:
    """B-6 — service-layer translation of IntegrityError."""

    @pytest.mark.asyncio
    async def test_integrity_error_raises_lead_has_references_error(self) -> None:
        service, repo = _build_service_with_repo()
        lead_id = uuid4()
        lead = MagicMock()
        lead.id = lead_id
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.delete = AsyncMock(
            side_effect=IntegrityError("stmt", {}, Exception("FK violation"))
        )

        with pytest.raises(LeadHasReferencesError):
            await service.delete_lead(lead_id)

        repo.session.rollback.assert_awaited()

    @pytest.mark.asyncio
    async def test_not_found_raises_lead_not_found(self) -> None:
        service, repo = _build_service_with_repo()
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(LeadNotFoundError):
            await service.delete_lead(uuid4())


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(leads_router, prefix="/api/v1/leads")
    return test_app


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.is_active = True
    return user


@pytest.mark.unit
class TestDeleteLeadRoute:
    """B-6 — route classification: 404 vs 409 vs 204."""

    @pytest.mark.asyncio
    async def test_route_404_when_lead_not_found(self, app: FastAPI) -> None:
        lead_id = uuid4()
        mock_service = AsyncMock()
        mock_service.delete_lead.side_effect = LeadNotFoundError(lead_id)

        app.dependency_overrides[_get_lead_service] = lambda: mock_service
        from grins_platform.api.v1.auth_dependencies import get_current_active_user

        app.dependency_overrides[get_current_active_user] = _mock_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/leads/{lead_id}")
        assert resp.status_code == 404
        assert str(lead_id) in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_route_409_when_fk_references_block_delete(
        self, app: FastAPI
    ) -> None:
        lead_id = uuid4()
        mock_service = AsyncMock()
        mock_service.delete_lead.side_effect = LeadHasReferencesError(lead_id)

        app.dependency_overrides[_get_lead_service] = lambda: mock_service
        from grins_platform.api.v1.auth_dependencies import get_current_active_user

        app.dependency_overrides[get_current_active_user] = _mock_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/leads/{lead_id}")
        assert resp.status_code == 409
        assert "FK" in resp.json()["detail"] or "references" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_route_204_on_happy_path(self, app: FastAPI) -> None:
        lead_id = uuid4()
        mock_service = AsyncMock()
        mock_service.delete_lead.return_value = None

        app.dependency_overrides[_get_lead_service] = lambda: mock_service
        from grins_platform.api.v1.auth_dependencies import get_current_active_user

        app.dependency_overrides[get_current_active_user] = _mock_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/leads/{lead_id}")
        assert resp.status_code == 204
