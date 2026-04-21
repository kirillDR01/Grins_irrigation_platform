"""Helpers backing the Gap 07 webhook security & dedup hardening.

Provides:

* :func:`check_freshness` — replay window check against the webhook
  body's ``created_at`` (defense against captured-and-replayed payloads).
* :func:`webhook_client_key` — slowapi ``key_func`` that respects a
  trusted-proxy allowlist for ``X-Forwarded-For``.
* :func:`autoreply_phone_throttled` — per-phone Redis throttle to cap
  how often a single number can trigger an auto-reply.
* :func:`autoreply_circuit_open` — global sliding-window circuit
  breaker over system-wide auto-reply sends.
* :func:`emit_db_fallback_alert`, :func:`emit_signature_flood_alert`,
  :func:`emit_circuit_open_alert` — alert emitters with Redis-guarded
  emit-once-per-window semantics.

All redis-dependent helpers fail **open** on Redis errors: dedup
correctness is owned by the DB-fallback layer, so these
cost-control/observability layers can skip gracefully during a Redis
outage without dropping legitimate traffic.

Validates: Gap 07 — Webhook Security & Dedup (7.A, 7.C, alerts)
"""

from __future__ import annotations

import ipaddress
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from grins_platform.log_config import get_logger
from grins_platform.models.alert import Alert
from grins_platform.models.enums import AlertSeverity, AlertType
from grins_platform.repositories.alert_repository import AlertRepository

if TYPE_CHECKING:
    from fastapi import Request
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


def _int_env(name: str, default: int) -> int:
    """Return the int value of env var ``name`` or ``default`` on error."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


CLOCK_SKEW_SECONDS = _int_env("WEBHOOK_CLOCK_SKEW_SECONDS", 300)
AUTOREPLY_PHONE_TTL_S = _int_env("WEBHOOK_AUTOREPLY_PHONE_TTL_S", 60)
AUTOREPLY_GLOBAL_WINDOW_S = _int_env("WEBHOOK_AUTOREPLY_GLOBAL_WINDOW_S", 10)
AUTOREPLY_GLOBAL_THRESHOLD = _int_env("WEBHOOK_AUTOREPLY_CIRCUIT_THRESHOLD", 30)
AUTOREPLY_CIRCUIT_OPEN_S = 300  # 5 minutes
SIGNATURE_FLOOD_THRESHOLD = _int_env("WEBHOOK_SIGNATURE_FLOOD_THRESHOLD", 50)
DB_FALLBACK_ALERT_TTL_S = 300  # once every 5 minutes
SIGNATURE_FLOOD_ALERT_TTL_S = 3600  # once per hour
CIRCUIT_OPEN_ALERT_TTL_S = 300  # once per circuit-open window

_REDIS_CIRCUIT_WINDOW_KEY = "sms:autoreply:global:window"
_REDIS_CIRCUIT_OPEN_KEY = "sms:autoreply:circuit:open"
_REDIS_PHONE_THROTTLE_PREFIX = "sms:autoreply:throttle"
_REDIS_FALLBACK_ALERT_KEY = "sms:webhook:fallback_alert:sent"
_REDIS_SIGFLOOD_ALERT_KEY = "sms:webhook:sig_fail_alert:sent"
_REDIS_CIRCUIT_ALERT_KEY = "sms:webhook:circuit_alert:sent"


def _trusted_proxy_cidrs() -> list[str]:
    """Read the trusted-proxy CIDR list from env on every call."""
    raw = os.environ.get("WEBHOOK_TRUSTED_PROXY_CIDRS", "")
    return [c.strip() for c in raw.split(",") if c.strip()]


def check_freshness(
    created_at_raw: str,
    now: datetime | None = None,
) -> tuple[bool, int]:
    """Return ``(is_fresh, skew_seconds)`` for a webhook ``created_at``.

    A payload is considered fresh when its ``created_at`` parses and the
    absolute skew from ``now`` is within :data:`CLOCK_SKEW_SECONDS`.
    Missing or unparseable timestamps are rejected as stale.

    Args:
        created_at_raw: ISO-8601 string from the webhook body.
        now: Current time (injected for testability).

    Returns:
        (is_fresh, skew_seconds) where ``skew_seconds`` is absolute and
        rounded down to the nearest integer.
    """
    if not created_at_raw:
        return False, 0
    raw = created_at_raw.strip()
    # Python 3.10 compat: normalize trailing Z to +00:00 before parsing.
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return False, 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    skew = int(abs((current - parsed).total_seconds()))
    return (skew <= CLOCK_SKEW_SECONDS), skew


def webhook_client_key(request: Request) -> str:
    """Return the slowapi rate-limit key for a webhook request.

    Honors ``X-Forwarded-For`` (leftmost hop) only when the direct peer
    IP is listed in ``WEBHOOK_TRUSTED_PROXY_CIDRS``. Defends against
    spoofed XFF headers from untrusted peers.

    Args:
        request: The inbound FastAPI/Starlette request.

    Returns:
        Opaque string identifying the client.
    """
    if request.client is None:
        return "unknown"
    peer_ip = request.client.host or "unknown"
    trusted = _trusted_proxy_cidrs()
    if not trusted:
        return peer_ip
    try:
        peer_addr = ipaddress.ip_address(peer_ip)
    except ValueError:
        return peer_ip
    is_trusted = False
    for cidr in trusted:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            logger.warning("sms.webhook.trusted_proxy_bad_cidr", cidr=cidr)
            continue
        if peer_addr in network:
            is_trusted = True
            break
    if not is_trusted:
        return peer_ip
    xff = request.headers.get("X-Forwarded-For")
    if not xff:
        return peer_ip
    leftmost = xff.split(",")[0].strip()
    return leftmost or peer_ip


async def autoreply_phone_throttled(
    redis: Redis | None,
    e164_phone: str,
) -> bool:
    """Return True if another auto-reply to ``e164_phone`` should be skipped.

    Sets a short-lived Redis key on the first call; subsequent calls
    within :data:`AUTOREPLY_PHONE_TTL_S` seconds see it and return True.

    Fails open on a missing or broken Redis: the DB-fallback dedup layer
    from Gap 07.B already protects against duplicate *processing*, so
    this cost-control layer can skip gracefully.

    Args:
        redis: Async Redis client (or None).
        e164_phone: Recipient phone in E.164 format.

    Returns:
        True if a recent auto-reply is recorded for this phone.
    """
    if redis is None:
        return False
    key = f"{_REDIS_PHONE_THROTTLE_PREFIX}:{e164_phone}"
    try:
        existing = await redis.get(key)
        if existing is not None:
            return True
        await redis.set(key, "1", nx=True, ex=AUTOREPLY_PHONE_TTL_S)
    except Exception:
        logger.warning("sms.auto_reply.phone_throttle_redis_unavailable")
        return False
    return False


async def autoreply_circuit_open(redis: Redis | None) -> bool:
    """Return True if the global auto-reply circuit breaker is open.

    Maintains a sliding-window counter over :data:`AUTOREPLY_GLOBAL_WINDOW_S`
    seconds. When the count exceeds :data:`AUTOREPLY_GLOBAL_THRESHOLD`,
    trips a breaker that stays open for :data:`AUTOREPLY_CIRCUIT_OPEN_S`
    seconds.

    Fails open on a missing or broken Redis (see note on
    :func:`autoreply_phone_throttled`).

    Args:
        redis: Async Redis client (or None).

    Returns:
        True when the breaker is open and auto-replies should be
        suppressed.
    """
    if redis is None:
        return False
    try:
        if await redis.get(_REDIS_CIRCUIT_OPEN_KEY) is not None:
            return True
        count = await redis.incr(_REDIS_CIRCUIT_WINDOW_KEY)
        # EXPIRE unconditionally is acceptable granularity on every INCR.
        await redis.expire(_REDIS_CIRCUIT_WINDOW_KEY, AUTOREPLY_GLOBAL_WINDOW_S)
        if int(count) > AUTOREPLY_GLOBAL_THRESHOLD:
            await redis.set(
                _REDIS_CIRCUIT_OPEN_KEY,
                "1",
                nx=True,
                ex=AUTOREPLY_CIRCUIT_OPEN_S,
            )
            logger.warning(
                "sms.auto_reply.circuit_open",
                counter=int(count),
            )
            return True
    except Exception:
        logger.warning("sms.auto_reply.circuit_redis_unavailable")
        return False
    return False


async def _claim_emit_slot(
    redis: Redis | None,
    key: str,
    ttl_s: int,
) -> bool:
    """Return True when this caller wins the emit-once slot for ``key``.

    Uses ``SET NX EX`` to atomically claim the slot. On Redis error we
    return True so that at least one alert fires per incident rather
    than silently dropping all alerts.
    """
    if redis is None:
        return True
    try:
        claimed = await redis.set(key, "1", nx=True, ex=ttl_s)
    except Exception:
        logger.warning("sms.webhook.alert_redis_unavailable", key=key)
        return True
    return bool(claimed)


async def emit_db_fallback_alert(
    db: AsyncSession,
    redis: Redis | None,
) -> None:
    """Emit a :data:`AlertType.WEBHOOK_REDIS_FALLBACK` alert (once per 5 min)."""
    if not await _claim_emit_slot(
        redis,
        _REDIS_FALLBACK_ALERT_KEY,
        DB_FALLBACK_ALERT_TTL_S,
    ):
        return
    try:
        alert = Alert(
            type=AlertType.WEBHOOK_REDIS_FALLBACK.value,
            severity=AlertSeverity.WARNING.value,
            entity_type="webhook",
            entity_id=uuid4(),
            message=(
                "Webhook dedup fell back to DB because Redis is unavailable. "
                "Investigate Redis health; correctness is preserved by the "
                "webhook_processed_logs table."
            ),
        )
        _ = await AlertRepository(db).create(alert)
    except Exception:
        logger.exception("sms.webhook.fallback_alert_failed")


async def emit_signature_flood_alert(
    db: AsyncSession,
    redis: Redis | None,
    count: int,
) -> None:
    """Emit a :data:`AlertType.WEBHOOK_SIGNATURE_FLOOD` alert (once per hour)."""
    if not await _claim_emit_slot(
        redis,
        _REDIS_SIGFLOOD_ALERT_KEY,
        SIGNATURE_FLOOD_ALERT_TTL_S,
    ):
        return
    try:
        alert = Alert(
            type=AlertType.WEBHOOK_SIGNATURE_FLOOD.value,
            severity=AlertSeverity.ERROR.value,
            entity_type="webhook",
            entity_id=uuid4(),
            message=(
                f"Webhook signature-failure flood: {count} invalid signatures "
                "in the last hour. Possible secret leak or hostile client."
            ),
        )
        _ = await AlertRepository(db).create(alert)
    except Exception:
        logger.exception("sms.webhook.sigflood_alert_failed")


async def emit_circuit_open_alert(
    db: AsyncSession,
    redis: Redis | None,
    counter: int,
) -> None:
    """Emit :data:`AlertType.WEBHOOK_AUTOREPLY_CIRCUIT_OPEN` once per window."""
    if not await _claim_emit_slot(
        redis,
        _REDIS_CIRCUIT_ALERT_KEY,
        CIRCUIT_OPEN_ALERT_TTL_S,
    ):
        return
    try:
        alert = Alert(
            type=AlertType.WEBHOOK_AUTOREPLY_CIRCUIT_OPEN.value,
            severity=AlertSeverity.ERROR.value,
            entity_type="webhook",
            entity_id=uuid4(),
            message=(
                "Auto-reply circuit opened: "
                f"{counter} auto-replies/"
                f"{AUTOREPLY_GLOBAL_WINDOW_S}s exceeded threshold "
                f"{AUTOREPLY_GLOBAL_THRESHOLD}. Auto-replies suppressed "
                f"for {AUTOREPLY_CIRCUIT_OPEN_S}s."
            ),
        )
        _ = await AlertRepository(db).create(alert)
    except Exception:
        logger.exception("sms.webhook.circuit_alert_failed")
