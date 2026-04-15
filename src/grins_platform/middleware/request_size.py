"""
Request size limiting middleware.

Enforces maximum request body sizes: 10 MB default, 50 MB for upload paths.
Returns HTTP 413 when the limit is exceeded.

Validates: Requirements 73.1, 73.2, 73.3, 73.4
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import JSONResponse

from grins_platform.log_config import get_logger

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
UPLOAD_MAX_BYTES = 50 * 1024 * 1024  # 50 MB

_UPLOAD_SUFFIXES = frozenset(
    {
        "/photos",
        "/attachments",
        "/media",
        "/receipts",
        "/upload",
        "/extract-receipt",
        "/generate-pdf",
    }
)


def _is_upload_path(path: str) -> bool:
    """Return True if the path is an upload endpoint."""
    return any(path.endswith(s) for s in _UPLOAD_SUFFIXES)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the allowed max."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Check Content-Length before forwarding."""
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = 0

            max_bytes = (
                UPLOAD_MAX_BYTES
                if _is_upload_path(request.url.path)
                else DEFAULT_MAX_BYTES
            )

            if length > max_bytes:
                logger.warning(
                    "security.request_size.exceeded",
                    path=request.url.path,
                    content_length=length,
                    max_bytes=max_bytes,
                )
                msg = f"Request body exceeds maximum size of {max_bytes} bytes."
                return JSONResponse(
                    status_code=413,
                    content={
                        "success": False,
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": msg,
                            "max_bytes": max_bytes,
                        },
                    },
                )

        return await call_next(request)
