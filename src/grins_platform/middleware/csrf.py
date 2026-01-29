"""
CSRF Protection Middleware.

This module provides CSRF (Cross-Site Request Forgery) protection middleware
for the FastAPI application. It validates CSRF tokens on state-changing requests.

Validates: Requirement 16.8
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from grins_platform.log_config import get_logger

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)

# Safe HTTP methods that don't require CSRF validation
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Cookie and header names
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    """Generate a secure CSRF token.

    Returns:
        A cryptographically secure random token string.

    Validates: Requirement 16.8
    """
    return secrets.token_urlsafe(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection.

    This middleware validates CSRF tokens on state-changing requests (POST, PUT,
    DELETE, PATCH). It compares the X-CSRF-Token header against the csrf_token
    cookie value.

    Safe methods (GET, HEAD, OPTIONS, TRACE) are skipped.

    Attributes:
        exempt_paths: Set of paths that are exempt from CSRF validation.

    Validates: Requirement 16.8
    """

    def __init__(
        self,
        app: object,
        exempt_paths: set[str] | None = None,
    ) -> None:
        """Initialize CSRF middleware.

        Args:
            app: The ASGI application.
            exempt_paths: Optional set of paths to exempt from CSRF validation.
                         Defaults to auth login endpoint.
        """
        super().__init__(app)  # type: ignore[arg-type]
        self.exempt_paths: set[str] = exempt_paths or {
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and validate CSRF token if needed.

        Args:
            request: The incoming request.
            call_next: The next middleware or route handler.

        Returns:
            The response from the next handler, or a 403 error if CSRF
            validation fails.

        Validates: Requirement 16.8
        """
        # Skip CSRF check for safe methods
        if request.method in SAFE_METHODS:
            return await call_next(request)

        # Skip CSRF check for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Get CSRF token from cookie
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)

        # Get CSRF token from header
        csrf_header = request.headers.get(CSRF_HEADER_NAME)

        # Validate CSRF token
        if not csrf_cookie or not csrf_header:
            logger.warning(
                "csrf.validation_failed",
                reason="missing_token",
                path=request.url.path,
                method=request.method,
                has_cookie=bool(csrf_cookie),
                has_header=bool(csrf_header),
            )
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "code": "CSRF_VALIDATION_FAILED",
                        "message": "CSRF token missing",
                    },
                },
            )

        # Compare tokens using constant-time comparison
        if not secrets.compare_digest(csrf_cookie, csrf_header):
            logger.warning(
                "csrf.validation_failed",
                reason="token_mismatch",
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "code": "CSRF_VALIDATION_FAILED",
                        "message": "CSRF token invalid",
                    },
                },
            )

        logger.debug(
            "csrf.validation_passed",
            path=request.url.path,
            method=request.method,
        )

        return await call_next(request)
