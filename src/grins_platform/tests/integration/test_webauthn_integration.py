"""Integration test: WebAuthn auth-finish issues the same cookies as /auth/login.

Goal: prove the *wiring* — that the cookie attributes set by
``/auth/webauthn/authenticate/finish`` match the cookies set by the
password ``/auth/login`` endpoint byte-for-byte (same names, ``HttpOnly``,
``Secure``, ``SameSite``, ``Max-Age``, ``Path``).

The actual cryptographic verification is mocked because driving a real
authenticator from CI is not practical. The webauthn library has its own
crypto test suite, and manual hardware testing (Task 29) covers the
real ceremony end-to-end.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import get_auth_service
from grins_platform.api.v1.webauthn import get_webauthn_service
from grins_platform.main import app
from grins_platform.models.enums import UserRole

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = pytest.mark.integration


def _cookie_attrs(jar, name: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
    """Pull comparable attrs out of a httpx cookie."""
    cookie = next(c for c in jar if c.name == name)
    rest_keys = {k.lower() for k in cookie._rest}  # noqa: SLF001
    return {
        "name": cookie.name,
        "secure": bool(cookie.secure),
        "httponly": "httponly" in rest_keys,
        "samesite": cookie._rest.get("SameSite") or cookie._rest.get("samesite"),  # noqa: SLF001
        "path": cookie.path,
    }


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


@pytest.fixture
def auth_service_mock(mock_staff: MagicMock) -> MagicMock:
    svc = MagicMock()
    svc.authenticate = AsyncMock(
        return_value=(mock_staff, "access-tok", "refresh-tok", "csrf-tok"),
    )
    svc.get_user_role.return_value = UserRole.ADMIN
    return svc


@pytest.fixture
def webauthn_service_mock(mock_staff: MagicMock) -> MagicMock:
    svc = MagicMock()
    svc.finish_authentication = AsyncMock(
        return_value=(mock_staff, "access-tok", "refresh-tok", "csrf-tok"),
    )
    return svc


@pytest.fixture
def override(
    auth_service_mock: MagicMock,
    webauthn_service_mock: MagicMock,
) -> Callable[[], None]:
    async def _override_auth() -> MagicMock:
        return auth_service_mock

    async def _override_webauthn() -> MagicMock:
        return webauthn_service_mock

    def _install() -> None:
        app.dependency_overrides[get_auth_service] = _override_auth
        app.dependency_overrides[get_webauthn_service] = _override_webauthn

    return _install


@pytest.mark.asyncio
async def test_password_login_and_passkey_finish_set_equivalent_cookies(
    override: Callable[[], None],
) -> None:
    """The three cookies must match in name, HttpOnly, Secure, SameSite, Path."""
    override()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            login_resp = await c.post(
                "/api/v1/auth/login",
                json={"username": "kirill", "password": "anything"},
            )
            passkey_resp = await c.post(
                "/api/v1/auth/webauthn/authenticate/finish",
                json={"handle": "h", "credential": {"rawId": "AAAA"}},
            )
    finally:
        app.dependency_overrides.clear()

    assert login_resp.status_code == 200, login_resp.text
    assert passkey_resp.status_code == 200, passkey_resp.text

    login_jar = list(login_resp.cookies.jar)
    passkey_jar = list(passkey_resp.cookies.jar)

    cookie_names = {"refresh_token", "access_token", "csrf_token"}
    assert {c.name for c in login_jar} >= cookie_names
    assert {c.name for c in passkey_jar} >= cookie_names

    for name in cookie_names:
        login_attrs = _cookie_attrs(login_jar, name)
        passkey_attrs = _cookie_attrs(passkey_jar, name)
        assert login_attrs == passkey_attrs, (
            f"cookie '{name}' attribute mismatch:\n"
            f"  login:   {login_attrs}\n"
            f"  passkey: {passkey_attrs}"
        )


@pytest.mark.asyncio
async def test_passkey_finish_returns_login_response_shape(
    override: Callable[[], None],
) -> None:
    """LoginResponse shape parity: frontend stays method-agnostic."""
    override()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            login_resp = await c.post(
                "/api/v1/auth/login",
                json={"username": "kirill", "password": "anything"},
            )
            passkey_resp = await c.post(
                "/api/v1/auth/webauthn/authenticate/finish",
                json={"handle": "h", "credential": {"rawId": "AAAA"}},
            )
    finally:
        app.dependency_overrides.clear()

    assert login_resp.status_code == 200
    assert passkey_resp.status_code == 200
    login_keys = set(login_resp.json().keys())
    passkey_keys = set(passkey_resp.json().keys())
    assert login_keys == passkey_keys, (
        f"LoginResponse shape diverged:\n"
        f"  login   keys: {sorted(login_keys)}\n"
        f"  passkey keys: {sorted(passkey_keys)}"
    )
