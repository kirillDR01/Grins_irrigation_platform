"""CallRail inbound SMS webhook endpoint.

Receives inbound SMS from CallRail, verifies HMAC signature,
deduplicates via Redis, and routes to SMSService.handle_inbound().

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 30, 44
"""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request, Response, status

from grins_platform.database import get_db_session as get_db
from grins_platform.log_config import get_logger
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms_service import SMSService

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/callrail", tags=["callrail-webhooks"])

# Redis key prefix and TTL for webhook idempotency
_REDIS_KEY_PREFIX = "sms:webhook:processed:callrail"
_REDIS_TTL_SECONDS = 86400  # 24 hours


async def _get_redis() -> Redis | None:
    """Return an async Redis client, or None if unavailable."""
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None
    try:
        from redis.asyncio import Redis as _Redis  # noqa: PLC0415

        return _Redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


async def _is_duplicate(
    redis: Redis | None,
    conversation_id: str,
    created_at: str,
) -> bool:
    """Check if this webhook was already processed via Redis SET NX.

    Returns True if already seen (duplicate).
    """
    if redis is None:
        return False
    key = f"{_REDIS_KEY_PREFIX}:{conversation_id}:{created_at}"
    try:
        added = await redis.set(key, "1", nx=True, ex=_REDIS_TTL_SECONDS)
    except Exception:
        logger.warning("sms.webhook.redis_unavailable")
        return False
    else:
        return added is None  # None means key already existed


@router.post(
    "/inbound",
    status_code=status.HTTP_200_OK,
    summary="Handle inbound SMS from CallRail",
    description=(
        "Receives inbound SMS from CallRail, verifies HMAC signature, "
        "deduplicates, and processes STOP keywords via SMSService."
    ),
)
async def callrail_inbound(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Handle inbound SMS webhook from CallRail.

    Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 30, 44
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    # 1. Verify webhook signature
    provider = get_sms_provider()
    sig_valid = await provider.verify_webhook_signature(headers, raw_body)
    if not sig_valid:
        # DEV DIAGNOSTIC: log full request shape so we can reverse-engineer
        # CallRail's actual signing format. The parent CallRail spec notes
        # the HMAC mechanism is unverified — first real inbound rejection
        # is the only way to confirm header name + algorithm + encoding.
        # Sensitive headers are stripped; body is truncated to 4 KB.
        SAFE_SKIP = {"authorization", "cookie", "set-cookie", "x-api-key"}
        debug_headers = {
            k: v for k, v in headers.items() if k.lower() not in SAFE_SKIP
        }
        body_preview = raw_body[:4096].decode("utf-8", errors="replace")
        body_truncated = len(raw_body) > 4096

        # Compute what we *expected* using each plausible variant so we
        # can spot the mismatch by eye in the logs without another
        # round-trip.
        import hashlib  # noqa: PLC0415
        import hmac  # noqa: PLC0415

        secret = os.environ.get("CALLRAIL_WEBHOOK_SECRET", "")
        diag_signatures: dict[str, str] = {}
        if secret:
            for label, key_bytes in (
                ("secret_utf8", secret.encode()),
                ("secret_hex_decoded", bytes.fromhex(secret) if all(
                    c in "0123456789abcdefABCDEF" for c in secret
                ) and len(secret) % 2 == 0 else b""),
            ):
                if not key_bytes:
                    continue
                for algo_name, algo in (
                    ("sha256_hex", hashlib.sha256),
                    ("sha1_hex", hashlib.sha1),
                ):
                    h = hmac.new(key_bytes, raw_body, algo).hexdigest()
                    diag_signatures[f"{label}__{algo_name}"] = h
                # base64-encoded variants
                import base64  # noqa: PLC0415
                for algo_name, algo in (
                    ("sha256_b64", hashlib.sha256),
                    ("sha1_b64", hashlib.sha1),
                ):
                    h = base64.b64encode(
                        hmac.new(key_bytes, raw_body, algo).digest(),
                    ).decode()
                    diag_signatures[f"{label}__{algo_name}"] = h

        logger.warning(
            "sms.webhook.signature_invalid",
            provider="callrail",
            request_headers=debug_headers,
            request_body_preview=body_preview,
            request_body_truncated=body_truncated,
            request_body_length=len(raw_body),
            expected_signatures_for_diff=diag_signatures,
        )
        return Response(
            content='{"error": "Invalid webhook signature"}',
            status_code=status.HTTP_403_FORBIDDEN,
            media_type="application/json",
        )

    # 2. Parse JSON payload
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        logger.warning("sms.webhook.malformed_payload", provider="callrail")
        return Response(
            content='{"error": "Malformed payload"}',
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json",
        )

    # 3. Idempotency dedupe via Redis
    conversation_id = str(payload.get("id", ""))
    created_at = str(payload.get("created_at", ""))
    redis = await _get_redis()
    try:
        if await _is_duplicate(redis, conversation_id, created_at):
            logger.info(
                "sms.webhook.duplicate_skipped",
                provider="callrail",
                conversation_id=conversation_id,
            )
            return Response(
                content='{"status": "already_processed"}',
                status_code=status.HTTP_200_OK,
                media_type="application/json",
            )
    finally:
        if redis is not None:
            with contextlib.suppress(Exception):
                await redis.aclose()

    # 4. Parse inbound message and route to SMSService
    try:
        inbound = provider.parse_inbound_webhook(payload)
    except Exception:
        logger.warning(
            "sms.webhook.parse_failed",
            provider="callrail",
        )
        return Response(
            content='{"error": "Failed to parse inbound payload"}',
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json",
        )

    sms_service = SMSService(db)
    result = await sms_service.handle_inbound(
        from_phone=inbound.from_phone,
        body=inbound.body,
        provider_sid=inbound.provider_sid,
    )

    logger.info(
        "sms.webhook.inbound",
        provider="callrail",
        action=result.get("action"),
        conversation_id=conversation_id,
    )

    return Response(
        content='{"status": "processed"}',
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )
