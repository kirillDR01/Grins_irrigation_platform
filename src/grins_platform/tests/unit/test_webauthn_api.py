"""HTTP-level tests for the WebAuthn endpoints.

The :class:`WebAuthnService` is dependency-overridden with a MagicMock so
these tests only exercise the FastAPI wiring — schema validation, status
codes, exception → HTTP mapping, and cookie issuance on
``/authenticate/finish``.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.webauthn import get_webauthn_service
from grins_platform.exceptions.auth import (
    WebAuthnChallengeNotFoundError,
    WebAuthnVerificationError,
)
from grins_platform.main import app
from grins_platform.models.enums import UserRole

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def mock_service() -> MagicMock:
    s = MagicMock()
    s.start_authentication = AsyncMock()
    s.finish_authentication = AsyncMock()
    s.start_registration = AsyncMock()
    s.finish_registration = AsyncMock()
    s.list_credentials = AsyncMock()
    s.revoke_credential = AsyncMock()
    return s


@pytest.fixture
def override_service(mock_service: MagicMock) -> Callable[[], MagicMock]:
    async def _override() -> MagicMock:
        return mock_service

    return _override  # type: ignore[return-value]


@pytest.fixture
def mock_staff() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.username = "kirill"
    s.email = "kirill@example.com"
    s.name = "Kirill Test"
    s.role = UserRole.ADMIN.value
    s.is_active = True
    s.is_login_enabled = True
    return s


@pytest.mark.unit
class TestAuthenticateBegin:
    @pytest.mark.asyncio
    async def test_returns_handle_and_options(
        self,
        mock_service: MagicMock,
        override_service: Callable[[], MagicMock],
    ) -> None:
        mock_service.start_authentication.return_value = (
            "h",
            {"challenge": "c"},
        )
        app.dependency_overrides[get_webauthn_service] = override_service
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as c:
                resp = await c.post(
                    "/api/v1/auth/webauthn/authenticate/begin",
                    json={"username": "kirill"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["handle"] == "h"
            assert data["options"] == {"challenge": "c"}
        finally:
            app.dependency_overrides.clear()


@pytest.mark.unit
class TestAuthenticateFinish:
    @pytest.mark.asyncio
    async def test_sets_login_cookies_on_success(
        self,
        mock_service: MagicMock,
        override_service: Callable[[], MagicMock],
        mock_staff: MagicMock,
    ) -> None:
        from grins_platform.api.v1.auth_dependencies import get_auth_service

        auth_svc = MagicMock()
        auth_svc.get_user_role.return_value = UserRole.ADMIN

        async def _override_auth() -> MagicMock:
            return auth_svc

        mock_service.finish_authentication.return_value = (
            mock_staff,
            "access-tok",
            "refresh-tok",
            "csrf-tok",
        )
        app.dependency_overrides[get_webauthn_service] = override_service
        app.dependency_overrides[get_auth_service] = _override_auth
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as c:
                resp = await c.post(
                    "/api/v1/auth/webauthn/authenticate/finish",
                    json={"handle": "h", "credential": {"rawId": "AAAA"}},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["access_token"] == "access-tok"
            assert data["csrf_token"] == "csrf-tok"
            # All three cookies present, matching password /auth/login.
            assert "refresh_token" in resp.cookies
            assert "access_token" in resp.cookies
            assert "csrf_token" in resp.cookies
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_verification_error_returns_401(
        self,
        mock_service: MagicMock,
        override_service: Callable[[], MagicMock],
    ) -> None:
        mock_service.finish_authentication.side_effect = WebAuthnVerificationError()
        app.dependency_overrides[get_webauthn_service] = override_service
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as c:
                resp = await c.post(
                    "/api/v1/auth/webauthn/authenticate/finish",
                    json={"handle": "h", "credential": {}},
                )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_challenge_not_found_returns_400(
        self,
        mock_service: MagicMock,
        override_service: Callable[[], MagicMock],
    ) -> None:
        mock_service.finish_authentication.side_effect = (
            WebAuthnChallengeNotFoundError()
        )
        app.dependency_overrides[get_webauthn_service] = override_service
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as c:
                resp = await c.post(
                    "/api/v1/auth/webauthn/authenticate/finish",
                    json={"handle": "h", "credential": {}},
                )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.clear()


@pytest.mark.unit
class TestProtectedEndpointsRequireAuth:
    """The 4 protected endpoints must reject unauthenticated requests."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("post", "/api/v1/auth/webauthn/register/begin"),
            (
                "post",
                "/api/v1/auth/webauthn/register/finish",
            ),
            ("get", "/api/v1/auth/webauthn/credentials"),
            (
                "delete",
                f"/api/v1/auth/webauthn/credentials/{uuid.uuid4()}",
            ),
        ],
    )
    async def test_returns_401_without_auth(
        self,
        method: str,
        path: str,
    ) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            req = getattr(c, method)
            if method in ("post",):
                resp = await req(path, json={})
            else:
                resp = await req(path)
        assert resp.status_code == 401
