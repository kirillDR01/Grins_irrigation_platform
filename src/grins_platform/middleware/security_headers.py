"""
Security headers middleware.

Adds standard security headers to all responses:
X-Content-Type-Options, X-Frame-Options, X-XSS-Protection,
Referrer-Policy, Permissions-Policy, Content-Security-Policy,
and HSTS (production only).

Validates: Requirements 70.1, 70.2, 70.3
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from grins_platform.log_config import get_logger

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)

_IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

# CSP built as a single string to avoid long lines
_CSP_DIRECTIVES = [
    "default-src 'self'",
    (
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://maps.googleapis.com https://js.stripe.com"
    ),
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    ("img-src 'self' data: blob: https://*.googleapis.com https://*.gstatic.com"),
    "font-src 'self' https://fonts.gstatic.com",
    ("connect-src 'self' https://*.googleapis.com https://api.stripe.com"),
    "frame-src https://js.stripe.com https://maps.google.com",
]
_CSP = "; ".join(_CSP_DIRECTIVES)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Add security headers after the response is generated."""
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(self), payment=()"
        )
        response.headers["Content-Security-Policy"] = _CSP

        if _IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response
