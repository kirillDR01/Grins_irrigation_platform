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
from slowapi.middleware import SlowAPIMiddleware
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
# Gap 07: inbound webhook per-client-IP limit. Generous enough that legitimate
# provider retries are not penalised.
WEBHOOK_LIMIT = "60/minute"


def rate_limit_exceeded_handler(
    request: Request,
    _exc: RateLimitExceeded,
) -> JSONResponse:
    """Return 429 for typical routes, 503 for /api/v1/webhooks/ paths.

    Webhook providers interpret 429 as a client-side bug; 503 cues them
    to retry on the documented cadence. We return the same JSON shape
    for both so downstream error parsers don't need to branch on path.
    """
    retry_after = 60
    path = request.url.path
    is_webhook = path.startswith("/api/v1/webhooks/")
    status_code = 503 if is_webhook else 429
    error_code = "WEBHOOK_RATE_LIMITED" if is_webhook else "RATE_LIMIT_EXCEEDED"
    message = (
        "Webhook endpoint is throttled. Please retry after the Retry-After window."
        if is_webhook
        else "Too many requests. Please try again later."
    )
    logger.warning(
        "security.rate_limit.exceeded",
        path=path,
        client=get_remote_address(request),
        retry_after=retry_after,
        status_code=status_code,
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
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
    app.add_middleware(SlowAPIMiddleware)
    logger.info(
        "security.rate_limit.configured",
        storage=_storage_uri.split("://")[0],
        default_limit=AUTHENTICATED_LIMIT,
    )


# Re-export the trusted-proxy-aware key func for webhook route decorators.
# Imported at the bottom of the module so `services.sms.webhook_security`
# never has to import from `middleware.rate_limit` (no circular arrow).
from grins_platform.services.sms.webhook_security import (  # noqa: E402
    webhook_client_key,
)

__all__ = [
    "AUTHENTICATED_LIMIT",
    "AUTH_LIMIT",
    "PORTAL_LIMIT",
    "PUBLIC_LIMIT",
    "UPLOAD_LIMIT",
    "WEBHOOK_LIMIT",
    "limiter",
    "rate_limit_exceeded_handler",
    "setup_rate_limiting",
    "webhook_client_key",
]
