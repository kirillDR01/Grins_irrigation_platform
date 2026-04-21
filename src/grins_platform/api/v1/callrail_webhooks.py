"""CallRail inbound SMS webhook endpoint.

Receives inbound SMS from CallRail, verifies HMAC signature, deduplicates
via Redis (with a DB-fallback path for Redis outages), rejects stale
replays, and routes to :class:`SMSService` for business-logic processing.
Gap 07 — Webhook Security & Dedup layers apply here:

* 7.A — replay protection: ``created_at`` freshness window + extended
  Redis TTLs + dual-key dedup on ``resource_id``.
* 7.B — fail-open-to-DB: when Redis is unavailable, the
  ``webhook_processed_logs`` table answers "seen before?".
* 7.C — per-IP rate limiting: ``slowapi`` decorator with trusted-proxy
  awareness; returns 503 on limit-exceeded so providers retry.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 30, 44; Gap 07.
"""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request, Response, status

from grins_platform.database import get_db_session as get_db
from grins_platform.log_config import (
    DomainLogger,
    clear_request_id,
    get_logger,
    set_request_id,
)
from grins_platform.middleware.rate_limit import (
    WEBHOOK_LIMIT,
    limiter,
    webhook_client_key,
)
from grins_platform.repositories.webhook_processed_log_repository import (
    WebhookProcessedLogRepository,
)
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms.webhook_security import (
    check_freshness,
    emit_db_fallback_alert,
    emit_signature_flood_alert,
)
from grins_platform.services.sms_service import SMSService

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/callrail", tags=["callrail-webhooks"])

# Primary dedup: (conversation_id, created_at) — 7 days. The longer TTL
# (vs the previous 24h) covers legitimate multi-day provider retries.
_REDIS_KEY_PREFIX = "sms:webhook:processed:callrail"
_REDIS_TTL_SECONDS = 7 * 86400  # 7 days
# Secondary dedup: resource_id (the stable CallRail message id). A 30-day
# TTL catches replays that tamper with `created_at` but can't tamper
# with the HMAC-signed `resource_id`.
_REDIS_MSGID_KEY_PREFIX = "sms:webhook:msgid:callrail"
_REDIS_MSGID_TTL_SECONDS = 30 * 86400  # 30 days
# Signature-failure counter: rolling per-hour bucket.
_REDIS_SIG_FAIL_PREFIX = "sms:webhook:sig_fail"
_REDIS_SIG_FAIL_TTL_SECONDS = 3600
_SIG_FAIL_ALERT_THRESHOLD = 50

_PROVIDER = "callrail"


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


def _primary_key(conversation_id: str, created_at: str) -> str:
    """Build the (conversation_id, created_at) Redis dedup key."""
    return f"{_REDIS_KEY_PREFIX}:{conversation_id}:{created_at}"


def _msgid_key(provider_message_id: str) -> str:
    """Build the resource-id Redis dedup key."""
    return f"{_REDIS_MSGID_KEY_PREFIX}:{provider_message_id}"


async def _is_duplicate(
    redis: Redis | None,
    db: AsyncSession,
    provider: str,
    conversation_id: str,
    created_at: str,
    provider_message_id: str,
) -> bool:
    """Return True if this webhook has already been processed.

    Checks Redis first (fast path). On Redis error or ``None`` client,
    falls back to the ``webhook_processed_logs`` table (authoritative on
    Redis outage, per Gap 07.B).
    """
    # Fast path: Redis
    if redis is not None:
        primary_key = _primary_key(conversation_id, created_at)
        msgid_key = _msgid_key(provider_message_id) if provider_message_id else None
        try:
            if await redis.get(primary_key) is not None:
                return True
            if msgid_key is not None and await redis.get(msgid_key) is not None:
                return True
        except Exception:
            logger.warning(
                "sms.webhook.redis_unavailable",
                provider=provider,
            )
            # Fall through to DB fallback.
        else:
            return False

    # DB fallback: authoritative when Redis is down or keys missing.
    if not provider_message_id:
        return False
    try:
        repo = WebhookProcessedLogRepository(db)
        if await repo.exists(provider, provider_message_id):
            logger.info(
                "sms.webhook.db_fallback_hit",
                provider=provider,
                provider_message_id=provider_message_id,
            )
            await emit_db_fallback_alert(db, redis)
            return True
    except Exception:
        logger.exception("sms.webhook.db_fallback_failed", provider=provider)
    return False


async def _mark_processed(
    redis: Redis | None,
    db: AsyncSession,
    provider: str,
    conversation_id: str,
    created_at: str,
    provider_message_id: str,
) -> None:
    """Record that this webhook was processed.

    The DB row is always written — it is the authoritative, durable
    record. Redis keys are best-effort (same server-side state that the
    read path checks on the fast path).
    """
    try:
        if provider_message_id:
            await WebhookProcessedLogRepository(db).mark_processed(
                provider,
                provider_message_id,
            )
    except Exception:
        logger.exception("sms.webhook.db_mark_failed", provider=provider)

    if redis is None:
        return
    try:
        await redis.set(
            _primary_key(conversation_id, created_at),
            "1",
            nx=True,
            ex=_REDIS_TTL_SECONDS,
        )
        if provider_message_id:
            await redis.set(
                _msgid_key(provider_message_id),
                "1",
                nx=True,
                ex=_REDIS_MSGID_TTL_SECONDS,
            )
    except Exception:
        logger.warning("sms.webhook.redis_mark_failed")


async def _record_signature_failure(
    redis: Redis | None,
    db: AsyncSession,
) -> None:
    """Bump the hourly signature-failure counter; emit an alert if needed."""
    if redis is None:
        return
    try:
        # UTC hour bucket to keep the key set bounded.
        from datetime import datetime, timezone  # noqa: PLC0415

        bucket = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")
        key = f"{_REDIS_SIG_FAIL_PREFIX}:{bucket}"
        count = await redis.incr(key)
        await redis.expire(key, _REDIS_SIG_FAIL_TTL_SECONDS)
        if int(count) >= _SIG_FAIL_ALERT_THRESHOLD:
            await emit_signature_flood_alert(db, redis, int(count))
    except Exception:
        logger.warning("sms.webhook.sig_fail_counter_failed")


@router.post(
    "/inbound",
    status_code=status.HTTP_200_OK,
    summary="Handle inbound SMS from CallRail",
    description=(
        "Receives inbound SMS from CallRail, verifies HMAC signature, "
        "deduplicates, and processes STOP keywords via SMSService."
    ),
)
@limiter.limit(WEBHOOK_LIMIT, key_func=webhook_client_key)  # pyright: ignore[reportUntypedFunctionDecorator]
async def callrail_inbound(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Handle inbound SMS webhook from CallRail.

    Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 30, 44; Gap 07.
    """
    request_id = set_request_id()
    DomainLogger.api_event(
        logger,
        "webhook_inbound",
        "started",
        request_id=request_id,
        provider=_PROVIDER,
    )
    try:
        raw_body = await request.body()
        headers = dict(request.headers)

        # 1. Verify webhook signature.
        provider = get_sms_provider()
        sig_valid = await provider.verify_webhook_signature(headers, raw_body)
        if not sig_valid:
            logger.warning(
                "sms.webhook.signature_invalid",
                provider=_PROVIDER,
                request_id=request_id,
            )
            await _record_signature_failure(await _get_redis(), db)
            DomainLogger.api_event(
                logger,
                "webhook_inbound",
                "failed",
                request_id=request_id,
                provider=_PROVIDER,
                status_code=403,
                reason="signature_invalid",
            )
            return Response(
                content='{"error": "Invalid webhook signature"}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json",
            )

        # 2. Parse JSON payload.
        DomainLogger.validation_event(
            logger,
            "webhook_payload",
            "started",
            request_id=request_id,
            provider=_PROVIDER,
        )
        try:
            payload: dict[str, Any] = await request.json()
        except Exception:
            logger.warning(
                "sms.webhook.malformed_payload",
                provider=_PROVIDER,
                request_id=request_id,
            )
            DomainLogger.validation_event(
                logger,
                "webhook_payload",
                "rejected",
                request_id=request_id,
                reason="malformed_payload",
            )
            return Response(
                content='{"error": "Malformed payload"}',
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json",
            )

        # 3. Freshness / replay check (Gap 07.A).
        created_at = str(payload.get("created_at", ""))
        fresh, skew_seconds = check_freshness(created_at)
        if not fresh:
            logger.warning(
                "sms.webhook.replay_rejected",
                provider=_PROVIDER,
                request_id=request_id,
                created_at=created_at,
                skew_seconds=skew_seconds,
            )
            DomainLogger.validation_event(
                logger,
                "webhook_payload",
                "rejected",
                request_id=request_id,
                reason="replay_or_stale_timestamp",
                skew_seconds=skew_seconds,
            )
            return Response(
                content='{"error": "Stale or missing timestamp"}',
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json",
            )

        DomainLogger.validation_event(
            logger,
            "webhook_payload",
            "validated",
            request_id=request_id,
        )

        # 4. Idempotency: primary + secondary dedup key, DB fallback.
        conversation_id = str(
            payload.get("conversation_id") or payload.get("resource_id") or "",
        )
        provider_message_id = str(payload.get("resource_id", ""))
        redis = await _get_redis()
        try:
            if await _is_duplicate(
                redis,
                db,
                _PROVIDER,
                conversation_id,
                created_at,
                provider_message_id,
            ):
                logger.info(
                    "sms.webhook.duplicate_skipped",
                    provider=_PROVIDER,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    provider_message_id=provider_message_id,
                )
                DomainLogger.api_event(
                    logger,
                    "webhook_inbound",
                    "completed",
                    request_id=request_id,
                    provider=_PROVIDER,
                    status_code=200,
                    result_action="already_processed",
                )
                return Response(
                    content='{"status": "already_processed"}',
                    status_code=status.HTTP_200_OK,
                    media_type="application/json",
                )

            # 5. Parse inbound message and route to SMSService.
            try:
                inbound = provider.parse_inbound_webhook(payload)
            except Exception:
                logger.warning(
                    "sms.webhook.parse_failed",
                    provider=_PROVIDER,
                    request_id=request_id,
                )
                return Response(
                    content='{"error": "Failed to parse inbound payload"}',
                    status_code=status.HTTP_400_BAD_REQUEST,
                    media_type="application/json",
                )

            sms_service = SMSService(db, provider=provider)
            try:
                result = await sms_service.handle_inbound(
                    from_phone=inbound.from_phone,
                    body=inbound.body,
                    provider_sid=inbound.provider_sid,
                    thread_id=inbound.thread_id,
                )
            except Exception:
                logger.exception(
                    "sms.webhook.handle_inbound_failed",
                    provider=_PROVIDER,
                    request_id=request_id,
                )
                return Response(
                    content='{"status": "error_logged"}',
                    status_code=status.HTTP_200_OK,
                    media_type="application/json",
                )

            # 6. Mark processed — DB first (authoritative), then Redis.
            await _mark_processed(
                redis,
                db,
                _PROVIDER,
                conversation_id,
                created_at,
                provider_message_id,
            )

            logger.info(
                "sms.webhook.inbound",
                provider=_PROVIDER,
                request_id=request_id,
                action=result.get("action"),
                conversation_id=conversation_id,
            )
            DomainLogger.api_event(
                logger,
                "webhook_inbound",
                "completed",
                request_id=request_id,
                provider=_PROVIDER,
                status_code=200,
                result_action=result.get("action"),
            )
            return Response(
                content='{"status": "processed"}',
                status_code=status.HTTP_200_OK,
                media_type="application/json",
            )
        finally:
            if redis is not None:
                with contextlib.suppress(Exception):
                    await redis.aclose()
    finally:
        clear_request_id()
