"""Bug C regression cover: per-IP rate limit on /api/v1/auth/login.

Validates: Requirements 69.1-69.4. The 6th attempt within one minute must
return 429 with body ``error.code == "RATE_LIMIT_EXCEEDED"`` and a
``Retry-After`` header.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import get_auth_service
from grins_platform.exceptions.auth import InvalidCredentialsError
from grins_platform.main import app
from grins_platform.middleware.rate_limit import limiter
from grins_platform.services.auth_service import AuthService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture(autouse=True)
def _reset_limiter_storage() -> None:
    """Ensure each test starts with a clean per-IP bucket.

    slowapi 0.1.9 exposes Limiter.reset() at extension.py:354. With the
    in-memory backend (REDIS_URL unset) it succeeds; with a Redis backend
    it logs a warning and is a no-op.
    """
    limiter.reset()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _override_auth_with_invalid() -> None:
    svc = MagicMock(spec=AuthService)
    svc.authenticate = AsyncMock(side_effect=InvalidCredentialsError("bad"))
    svc.repository = MagicMock()
    svc.repository.session = MagicMock()
    svc.repository.session.commit = AsyncMock()
    app.dependency_overrides[get_auth_service] = lambda: svc


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_429_after_5_attempts_per_minute(
    async_client: AsyncClient,
) -> None:
    """Bug C regression: 5/min on /auth/login. The 6th hit returns 429."""
    _override_auth_with_invalid()
    try:
        codes: list[int] = []
        for _ in range(6):
            r = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "x", "password": "y"},
            )
            codes.append(r.status_code)
        assert codes[:5] == [401] * 5, codes
        assert codes[5] == 429, codes

        last = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "x", "password": "y"},
        )
        assert last.status_code == 429
        body = last.json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in {k.title() for k in last.headers}
    finally:
        app.dependency_overrides.clear()
