"""Bug A regression cover: route MUST commit failed-login increment before 401.

These tests prove the route layer awaits ``auth_service.repository.session.commit()``
on the InvalidCredentialsError branch (so the failed-login UPDATE flushed by
``_handle_failed_login`` is durable across the FastAPI session-dependency
rollback that fires when the 401 propagates), and that the AccountLockedError
branch does NOT call commit (read-only path).

Validates: Requirements 16.5-16.7 (lockout counter persistence).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import get_auth_service
from grins_platform.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
)
from grins_platform.main import app
from grins_platform.middleware.rate_limit import limiter
from grins_platform.services.auth_service import AuthService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture(autouse=True)
def _reset_limiter_storage() -> None:
    """Reset slowapi per-IP buckets so tests don't 429 each other."""
    limiter.reset()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _make_service_with_commit_spy() -> tuple[MagicMock, AsyncMock]:
    svc = MagicMock(spec=AuthService)
    svc.authenticate = AsyncMock(side_effect=InvalidCredentialsError("bad"))
    commit_spy = AsyncMock()
    svc.repository = MagicMock()
    svc.repository.session = MagicMock()
    svc.repository.session.commit = commit_spy
    return svc, commit_spy


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_credentials_branch_commits_before_401(
    async_client: AsyncClient,
) -> None:
    """Route MUST commit the failed-login increment before raising the 401.

    Without this commit, get_session()'s exception branch rolls back the
    failed-login UPDATE flushed by _handle_failed_login, and the lockout
    counter never reaches MAX_FAILED_ATTEMPTS=5 (Bug A).
    """
    svc, commit_spy = _make_service_with_commit_spy()
    app.dependency_overrides[get_auth_service] = lambda: svc
    try:
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "x", "password": "y"},
        )
        assert resp.status_code == 401
        assert commit_spy.await_count == 1, (
            "Route must commit the failed-login UPDATE before raising 401 "
            "(Bug A: e2e-signoff 2026-05-04)."
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_locked_branch_does_not_commit(async_client: AsyncClient) -> None:
    """The AccountLockedError branch must NOT call commit (no pending writes)."""
    svc = MagicMock(spec=AuthService)
    svc.authenticate = AsyncMock(side_effect=AccountLockedError("locked"))
    svc.repository = MagicMock()
    svc.repository.session = MagicMock()
    svc.repository.session.commit = AsyncMock()
    app.dependency_overrides[get_auth_service] = lambda: svc
    try:
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "x", "password": "y"},
        )
        assert resp.status_code == 401
        assert svc.repository.session.commit.await_count == 0
    finally:
        app.dependency_overrides.clear()
