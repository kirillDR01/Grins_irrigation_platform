"""Tests for the X-Request-ID middleware + CORS sanity on public endpoints.

Validates: E-BUG-B observability hook.
"""

from __future__ import annotations

import re

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_response_carries_x_request_id() -> None:
    """Every response must include an ``X-Request-ID`` header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert "x-request-id" in {k.lower() for k in response.headers}
    rid = response.headers["x-request-id"]
    assert _UUID_RE.match(rid), f"Request ID must be a UUID, got {rid}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_incoming_request_id_is_echoed_back() -> None:
    """If the client sets ``X-Request-ID``, the server echoes it back."""
    incoming = "test-request-abc-123"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/health",
            headers={"X-Request-ID": incoming},
        )

    assert response.headers.get("x-request-id") == incoming


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cors_preflight_for_public_lead_endpoint() -> None:
    """OPTIONS on ``/api/v1/leads`` from a local dev origin must pass.

    The marketing site submits from a Vercel origin; dev uses localhost.
    CORS is configured via ``CORS_ORIGINS`` env; default dev includes
    ``http://localhost:5173``.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/leads",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )
