"""Integration tests for the business-settings API (H-12).

Covers ``GET /api/v1/settings/business`` and ``PATCH /api/v1/settings/business``:

- GET works for any active user.
- PATCH requires ``require_manager_or_admin`` and persists each key via
  :class:`BusinessSettingService.set_value` (which in turn writes an audit
  row).

We mock ``BusinessSettingService`` because the FastAPI routes instantiate
it with the injected ``AsyncSession``; behavior-level coverage of the
service itself lives in ``test_business_setting_service.py``.

Validates: bughunt 2026-04-16 finding H-12.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
    require_admin,
    require_manager_or_admin,
)
from grins_platform.main import app
from grins_platform.models.enums import StaffRole


@pytest.fixture
def sample_admin_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "admin"
    user.email = "admin@grins.com"
    user.role = StaffRole.ADMIN.value
    user.is_active = True
    return user


@pytest.fixture
def sample_tech_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "tech"
    user.email = "tech@grins.com"
    user.role = StaffRole.TECH.value
    user.is_active = True
    return user


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.integration
class TestBusinessSettingsAPIGet:
    """GET /api/v1/settings/business."""

    @pytest.mark.asyncio
    async def test_get_business_settings_returns_flat_thresholds(
        self,
        async_client: AsyncClient,
        sample_admin_user: MagicMock,
    ) -> None:
        app.dependency_overrides[get_current_user] = lambda: sample_admin_user
        app.dependency_overrides[get_current_active_user] = lambda: sample_admin_user

        fake_service = MagicMock()
        fake_service.get_all = AsyncMock(
            return_value={
                "lien_days_past_due": 60,
                "lien_min_amount": "500",
                "upcoming_due_days": 7,
                "confirmation_no_reply_days": 3,
            },
        )

        try:
            with patch(
                "grins_platform.api.v1.settings.BusinessSettingService",
                return_value=fake_service,
            ):
                response = await async_client.get(
                    "/api/v1/settings/business",
                    headers={"Authorization": "Bearer test_token"},
                )
            assert response.status_code == 200
            body = response.json()
            assert body["lien_days_past_due"] == 60
            assert Decimal(str(body["lien_min_amount"])) == Decimal(500)
            assert body["upcoming_due_days"] == 7
            assert body["confirmation_no_reply_days"] == 3
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_business_settings_requires_auth(
        self,
        async_client: AsyncClient,
    ) -> None:
        """No bearer token → 401 (CurrentActiveUser dependency)."""
        app.dependency_overrides.clear()
        response = await async_client.get("/api/v1/settings/business")
        assert response.status_code in (401, 403)


@pytest.mark.integration
class TestBusinessSettingsAPIPatch:
    """PATCH /api/v1/settings/business — manager/admin only."""

    @pytest.mark.asyncio
    async def test_patch_business_settings_persists_and_audits(
        self,
        async_client: AsyncClient,
        sample_admin_user: MagicMock,
    ) -> None:
        """PATCH with a partial body writes only the supplied keys."""
        app.dependency_overrides[get_current_user] = lambda: sample_admin_user
        app.dependency_overrides[get_current_active_user] = lambda: sample_admin_user
        app.dependency_overrides[require_admin] = lambda: sample_admin_user
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_admin_user

        fake_service = MagicMock()
        fake_service.set_value = AsyncMock()
        fake_service.get_all = AsyncMock(
            return_value={
                "lien_days_past_due": 90,
                "lien_min_amount": "1000",
                "upcoming_due_days": 7,
                "confirmation_no_reply_days": 3,
            },
        )

        try:
            with patch(
                "grins_platform.api.v1.settings.BusinessSettingService",
                return_value=fake_service,
            ):
                response = await async_client.patch(
                    "/api/v1/settings/business",
                    json={
                        "lien_days_past_due": 90,
                        "lien_min_amount": "1000",
                    },
                    headers={"Authorization": "Bearer test_token"},
                )

            assert response.status_code == 200
            # Both supplied keys forwarded; the other two untouched.
            assert fake_service.set_value.await_count == 2
            calls_by_key = {
                call.kwargs["key"]: call.kwargs["value"]
                for call in fake_service.set_value.await_args_list
            }
            assert calls_by_key["lien_days_past_due"] == 90
            assert calls_by_key["lien_min_amount"] == "1000"
            # The updated_by is populated with the authenticated user ID.
            for call in fake_service.set_value.await_args_list:
                assert call.kwargs["updated_by"] == sample_admin_user.id
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_patch_business_settings_rejects_non_admin(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
    ) -> None:
        """Tech role → 403 from require_manager_or_admin."""
        from fastapi import HTTPException

        def _reject() -> None:
            raise HTTPException(status_code=403, detail="forbidden")

        app.dependency_overrides[get_current_user] = lambda: sample_tech_user
        app.dependency_overrides[get_current_active_user] = lambda: sample_tech_user
        app.dependency_overrides[require_manager_or_admin] = _reject

        try:
            response = await async_client.patch(
                "/api/v1/settings/business",
                json={"lien_days_past_due": 90},
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()
