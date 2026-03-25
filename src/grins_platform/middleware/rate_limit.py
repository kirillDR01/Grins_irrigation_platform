"""
Rate limiting middleware using slowapi with Redis backend.

Provides per-endpoint rate limits via slowapi decorators and a global fallback.

Validates: Requirements 69.1, 69.2, 69.3, 69.4
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from grins_platform.log_config import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.requests import Request

logger = get_logger(__name__)

# Redis URL for rate limit storage; falls back to in-memory
_redis_url = os.getenv("REDIS_URL")
_storage_uri = _redis_url if _redis_url else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
    default_limits=["200/minute"],
)

# Rate limit constants for use in route decorators
AUTH_LIMIT = "5/minute"
PUBLIC_LIMIT = "10/minute"
UPLOAD_LIMIT = "20/minute"
PORTAL_LIMIT = "20/minute"
AUTHENTICATED_LIMIT = "200/minute"


def rate_limit_exceeded_handler(
    request: Request,
    _exc: RateLimitExceeded,
) -> JSONResponse:
    """Return 429 with Retry-After header."""
    retry_after = 60
    logger.warning(
        "security.rate_limit.exceeded",
        path=request.url.path,
        client=get_remote_address(request),
        retry_after=retry_after,
    )
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "retry_after": retry_after,
            },
        },
        headers={"Retry-After": str(retry_after)},
    )


def setup_rate_limiting(app: FastAPI) -> None:
    """Register the rate limiter and exception handler on the app."""
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )
    logger.info(
        "security.rate_limit.configured",
        storage=_storage_uri.split("://")[0],
        default_limit=AUTHENTICATED_LIMIT,
    )
