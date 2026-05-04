"""Regression tests for Bug J — HSTS header must be emitted unconditionally.

Bug J (live verified on dev): `curl -sI https://grins-dev-dev.up.railway.app/health`
returned every other security header but no `strict-transport-security`. Root
cause: `SecurityHeadersMiddleware` gated HSTS on `ENVIRONMENT=production`,
and Railway dev runs with `ENVIRONMENT=development`. Browsers ignore HSTS on
plain http:// regardless of environment, so emitting it unconditionally is
safe everywhere and required wherever https:// is reachable.

Validates: e2e-signoff Bug J regression
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from grins_platform.middleware.security_headers import SecurityHeadersMiddleware

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

pytestmark = pytest.mark.unit

_EXPECTED_HSTS = "max-age=63072000; includeSubDomains; preload"


async def _ok(_request: Request) -> Response:
    return JSONResponse({"ok": True})


def _build_app() -> Starlette:
    app = Starlette(routes=[Route("/test", _ok)])
    app.add_middleware(SecurityHeadersMiddleware)
    return app


class TestHSTSUnconditional:
    """HSTS must be present regardless of `ENVIRONMENT`."""

    def test_hsts_present_in_development(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(_build_app())
            resp = client.get("/test")
            assert resp.headers["Strict-Transport-Security"] == _EXPECTED_HSTS

    def test_hsts_present_in_production(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            client = TestClient(_build_app())
            resp = client.get("/test")
            assert resp.headers["Strict-Transport-Security"] == _EXPECTED_HSTS

    def test_hsts_present_when_env_unset(self) -> None:
        env: dict[str, Any] = {
            k: v for k, v in os.environ.items() if k != "ENVIRONMENT"
        }
        with patch.dict(os.environ, env, clear=True):
            client = TestClient(_build_app())
            resp = client.get("/test")
            assert resp.headers["Strict-Transport-Security"] == _EXPECTED_HSTS
