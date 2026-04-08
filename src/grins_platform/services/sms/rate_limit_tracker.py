"""Header-based rate limit tracker for CallRail SMS.

Parses ``x-rate-limit-*`` response headers from CallRail, caches them in
Redis (120 s TTL) with an in-memory fallback, and exposes a ``check()``
method that refuses sends when remaining quota drops to ≤ 5.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 39
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from grins_platform.log_config import LoggerMixin, get_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis

_logger = get_logger(__name__)

# Redis key pattern and TTL
_REDIS_KEY_PREFIX = "sms:rl"
_REDIS_TTL = 120  # seconds

# Refuse when remaining ≤ this threshold
_SAFETY_MARGIN = 5


@dataclass
class RateLimitState:
    """Snapshot of CallRail rate-limit counters."""

    hourly_allowed: int = 0
    hourly_used: int = 0
    daily_allowed: int = 0
    daily_used: int = 0
    updated_at: float = 0.0

    @property
    def hourly_remaining(self) -> int:
        return max(self.hourly_allowed - self.hourly_used, 0)

    @property
    def daily_remaining(self) -> int:
        return max(self.daily_allowed - self.daily_used, 0)


@dataclass
class CheckResult:
    """Result of a rate-limit check."""

    allowed: bool
    retry_after_seconds: int
    state: RateLimitState


class SMSRateLimitTracker(LoggerMixin):
    """Tracks CallRail rate limits from response headers.

    CallRail is the source of truth — this tracker does NOT maintain its
    own counters.  It caches the latest header values in Redis (120 s TTL)
    with an in-memory fallback when Redis is unavailable.
    """

    DOMAIN = "sms"

    def __init__(
        self,
        provider: str = "callrail",
        account_id: str = "",
        redis_client: Redis | None = None,
    ) -> None:
        super().__init__()
        self._provider = provider
        self._account_id = account_id
        self._redis = redis_client
        self._mem: RateLimitState = RateLimitState()

    # -- Public API ----------------------------------------------------------

    async def update_from_headers(self, headers: Mapping[str, str]) -> None:
        """Parse ``x-rate-limit-*`` headers and cache the values."""
        state = self._parse_headers(headers)
        if state is None:
            return
        self._mem = state
        await self._save_to_redis(state)
        _logger.info(
            "sms.rate_limit.tracker_updated",
            hourly_remaining=state.hourly_remaining,
            daily_remaining=state.daily_remaining,
            hourly_used=state.hourly_used,
            daily_used=state.daily_used,
        )
        self.log_completed(
            "rate_limit_tracker_updated",
            hourly_remaining=state.hourly_remaining,
            daily_remaining=state.daily_remaining,
        )

    async def check(self) -> CheckResult:
        """Return whether a send is allowed right now."""
        state = await self._load_state()
        # If we have no data yet, allow (first request bootstraps the cache)
        if state.updated_at == 0.0:
            return CheckResult(allowed=True, retry_after_seconds=0, state=state)

        if state.hourly_remaining <= _SAFETY_MARGIN:
            retry = self._seconds_until_next_hour()
            self.log_rejected(
                "rate_limit_check",
                reason="hourly_exhausted",
                hourly_remaining=state.hourly_remaining,
            )
            return CheckResult(allowed=False, retry_after_seconds=retry, state=state)

        if state.daily_remaining <= _SAFETY_MARGIN:
            retry = self._seconds_until_utc_midnight()
            self.log_rejected(
                "rate_limit_check",
                reason="daily_exhausted",
                daily_remaining=state.daily_remaining,
            )
            return CheckResult(allowed=False, retry_after_seconds=retry, state=state)

        return CheckResult(allowed=True, retry_after_seconds=0, state=state)

    # -- Internal helpers ----------------------------------------------------

    @staticmethod
    def _parse_headers(headers: Mapping[str, str]) -> RateLimitState | None:
        """Extract rate-limit values from response headers."""
        mapping = {
            "x-rate-limit-hourly-allowed": "hourly_allowed",
            "x-rate-limit-hourly-used": "hourly_used",
            "x-rate-limit-daily-allowed": "daily_allowed",
            "x-rate-limit-daily-used": "daily_used",
        }
        found: dict[str, int] = {}
        for header, attr in mapping.items():
            val = headers.get(header)
            if val is not None:
                with contextlib.suppress(ValueError):
                    found[attr] = int(val)
        if not found:
            return None
        return RateLimitState(**found, updated_at=time.time())

    async def _load_state(self) -> RateLimitState:
        """Load state from Redis, falling back to in-memory cache."""
        if self._redis is not None:
            with contextlib.suppress(Exception):
                raw = await self._redis.get(self._redis_key)
                if raw is not None:
                    return self._deserialize(raw)
        return self._mem

    async def _save_to_redis(self, state: RateLimitState) -> None:
        if self._redis is None:
            return
        with contextlib.suppress(Exception):
            await self._redis.set(
                self._redis_key,
                self._serialize(state),
                ex=_REDIS_TTL,
            )

    @property
    def _redis_key(self) -> str:
        return f"{_REDIS_KEY_PREFIX}:{self._provider}:{self._account_id}"

    @staticmethod
    def _serialize(state: RateLimitState) -> str:
        return (
            f"{state.hourly_allowed},{state.hourly_used},"
            f"{state.daily_allowed},{state.daily_used},"
            f"{state.updated_at}"
        )

    @staticmethod
    def _deserialize(raw: str | bytes) -> RateLimitState:
        text = raw.decode() if isinstance(raw, bytes) else raw
        parts = text.split(",")
        return RateLimitState(
            hourly_allowed=int(parts[0]),
            hourly_used=int(parts[1]),
            daily_allowed=int(parts[2]),
            daily_used=int(parts[3]),
            updated_at=float(parts[4]),
        )

    @staticmethod
    def _seconds_until_next_hour() -> int:
        now = datetime.now(tz=timezone.utc)
        return 3600 - now.minute * 60 - now.second

    @staticmethod
    def _seconds_until_utc_midnight() -> int:
        now = datetime.now(tz=timezone.utc)
        return 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
