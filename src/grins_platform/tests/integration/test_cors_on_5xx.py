"""Integration test for Bug 4 — 5xx responses carry CORS headers.

Without the top-level ``Exception`` handler, Starlette's
``ServerErrorMiddleware`` emits 500s outside ``CORSMiddleware`` and the
browser sees an opaque CORS error instead of the real 500 + JSON body.

Validates: bughunt 2026-04-28 §Bug 4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    # raise_app_exceptions=False lets the registered Exception handler
    # return its JSONResponse instead of re-raising into the test runner.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_5xx_response_carries_cors_header(
    async_client: AsyncClient,
) -> None:
    """A handler that raises ``RuntimeError`` returns a JSON 500 wrapped by CORS."""
    fastapi_app: FastAPI = app

    @fastapi_app.get("/__force_500_test")  # type: ignore[untyped-decorator]
    async def force_500() -> dict[str, str]:
        msg = "intentional"
        raise RuntimeError(msg)

    try:
        response = await async_client.get(
            "/__force_500_test",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 500
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:5173"
        )
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INTERNAL_ERROR"
    finally:
        # Pop the test-only route so it doesn't leak into other tests.
        fastapi_app.router.routes = [
            r
            for r in fastapi_app.router.routes
            if getattr(r, "path", None) != "/__force_500_test"
        ]
