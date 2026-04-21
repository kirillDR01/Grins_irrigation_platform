"""Unit tests for :mod:`grins_platform.services.sms.webhook_security`.

Covers freshness window, trusted-proxy key function, per-phone
auto-reply throttle, and the global sliding-window circuit breaker.

Validates: Gap 07 — Webhook Security & Dedup (7.A, 7.C).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from grins_platform.services.sms import webhook_security as ws


def _request(
    peer: str | None = "127.0.0.1",
    xff: str | None = None,
) -> SimpleNamespace:
    """Build a minimal request-like object for ``webhook_client_key``."""
    client = None if peer is None else SimpleNamespace(host=peer)
    headers: dict[str, str] = {}
    if xff is not None:
        headers["X-Forwarded-For"] = xff

    class _Headers(dict[str, str]):
        def get(
            self,
            key: str,
            default: str | None = None,
        ) -> str | None:  # type: ignore[override]
            for k, v in self.items():
                if k.lower() == key.lower():
                    return v
            return default

    return SimpleNamespace(client=client, headers=_Headers(headers))


@pytest.mark.unit
class TestCheckFreshness:
    """Tests for :func:`check_freshness`."""

    def test_check_freshness_with_stale_timestamp_returns_false(self) -> None:
        """A skew of > CLOCK_SKEW_SECONDS is rejected as replay."""
        now = datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)
        stale = (now - timedelta(seconds=ws.CLOCK_SKEW_SECONDS + 1)).isoformat()
        fresh, skew = ws.check_freshness(stale, now=now)
        assert fresh is False
        assert skew > ws.CLOCK_SKEW_SECONDS

    def test_check_freshness_with_fresh_timestamp_returns_true(self) -> None:
        """A skew inside the window passes."""
        now = datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)
        fresh_ts = (now - timedelta(seconds=ws.CLOCK_SKEW_SECONDS - 1)).isoformat()
        fresh, skew = ws.check_freshness(fresh_ts, now=now)
        assert fresh is True
        assert skew < ws.CLOCK_SKEW_SECONDS

    def test_check_freshness_with_missing_timestamp_returns_false(self) -> None:
        """Empty string is rejected without raising."""
        fresh, skew = ws.check_freshness("")
        assert fresh is False
        assert skew == 0

    def test_check_freshness_with_malformed_timestamp_returns_false(
        self,
    ) -> None:
        """Unparseable timestamp is rejected."""
        fresh, skew = ws.check_freshness("not-a-date")
        assert fresh is False
        assert skew == 0

    def test_check_freshness_with_z_suffix_parses_on_py310_and_later(
        self,
    ) -> None:
        """``Z``-suffixed ISO-8601 must round-trip (Py3.10 compat shim)."""
        now = datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)
        raw = "2026-04-21T12:00:00Z"
        fresh, skew = ws.check_freshness(raw, now=now)
        assert fresh is True
        assert skew == 0

    def test_check_freshness_with_naive_timestamp_treats_as_utc(self) -> None:
        """A tz-naive timestamp is interpreted as UTC."""
        now = datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)
        raw = "2026-04-21T12:00:00"  # no tz
        fresh, _ = ws.check_freshness(raw, now=now)
        assert fresh is True


@pytest.mark.unit
class TestWebhookClientKey:
    """Tests for :func:`webhook_client_key`."""

    def test_webhook_client_key_with_no_proxy_returns_peer_ip(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty CIDR list → leftmost is ignored, peer IP used."""
        monkeypatch.setenv("WEBHOOK_TRUSTED_PROXY_CIDRS", "")
        request = _request(peer="1.2.3.4", xff="5.6.7.8, 9.9.9.9")
        assert ws.webhook_client_key(request) == "1.2.3.4"

    def test_webhook_client_key_with_trusted_peer_returns_xff_leftmost(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Trusted proxy peer → leftmost X-Forwarded-For wins."""
        monkeypatch.setenv("WEBHOOK_TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
        request = _request(peer="10.0.1.5", xff="203.0.113.1, 10.0.0.2")
        assert ws.webhook_client_key(request) == "203.0.113.1"

    def test_webhook_client_key_with_untrusted_peer_ignores_xff(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Untrusted peer → X-Forwarded-For is ignored (spoofing defense)."""
        monkeypatch.setenv("WEBHOOK_TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
        request = _request(peer="1.2.3.4", xff="203.0.113.1")
        assert ws.webhook_client_key(request) == "1.2.3.4"

    def test_webhook_client_key_with_missing_client_returns_unknown(
        self,
    ) -> None:
        """``request.client is None`` does not blow up."""
        request = _request(peer=None)
        assert ws.webhook_client_key(request) == "unknown"

    def test_webhook_client_key_with_malformed_cidr_falls_back_to_peer(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A bogus CIDR entry doesn't crash; peer IP is returned."""
        monkeypatch.setenv("WEBHOOK_TRUSTED_PROXY_CIDRS", "bogus,10.0.0.0/8")
        request = _request(peer="1.2.3.4", xff="203.0.113.1")
        assert ws.webhook_client_key(request) == "1.2.3.4"


@pytest.mark.unit
class TestAutoreplyPhoneThrottled:
    """Tests for :func:`autoreply_phone_throttled`."""

    @pytest.mark.asyncio
    async def test_phone_throttled_with_no_redis_returns_false(self) -> None:
        """``redis=None`` → fail open, do not throttle."""
        assert await ws.autoreply_phone_throttled(None, "+15551234567") is False

    @pytest.mark.asyncio
    async def test_phone_throttled_with_first_call_sets_key_returns_false(
        self,
    ) -> None:
        """First call sets the guard and does NOT throttle."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        assert await ws.autoreply_phone_throttled(redis, "+15551234567") is False
        redis.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_phone_throttled_with_existing_key_returns_true(self) -> None:
        """Second call within TTL returns True (throttled)."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="1")
        assert await ws.autoreply_phone_throttled(redis, "+15551234567") is True

    @pytest.mark.asyncio
    async def test_phone_throttled_on_redis_exception_returns_false(
        self,
    ) -> None:
        """Redis failure → fail open (do not drop auto-replies)."""
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=Exception("boom"))
        assert await ws.autoreply_phone_throttled(redis, "+15551234567") is False


@pytest.mark.unit
class TestAutoreplyCircuitOpen:
    """Tests for :func:`autoreply_circuit_open`."""

    @pytest.mark.asyncio
    async def test_circuit_open_with_no_redis_returns_false(self) -> None:
        """``redis=None`` → circuit never opens."""
        assert await ws.autoreply_circuit_open(None) is False

    @pytest.mark.asyncio
    async def test_circuit_open_with_count_below_threshold_returns_false(
        self,
    ) -> None:
        """Below threshold → do not trip the breaker."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.incr = AsyncMock(return_value=ws.AUTOREPLY_GLOBAL_THRESHOLD)
        redis.expire = AsyncMock(return_value=True)
        redis.set = AsyncMock()
        assert await ws.autoreply_circuit_open(redis) is False
        redis.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_circuit_open_with_count_above_threshold_returns_true(
        self,
    ) -> None:
        """Above threshold → trip the breaker and set the open key."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.incr = AsyncMock(return_value=ws.AUTOREPLY_GLOBAL_THRESHOLD + 5)
        redis.expire = AsyncMock(return_value=True)
        redis.set = AsyncMock()
        assert await ws.autoreply_circuit_open(redis) is True
        redis.set.assert_awaited()

    @pytest.mark.asyncio
    async def test_circuit_open_with_existing_open_key_returns_true(
        self,
    ) -> None:
        """Pre-existing open key → stay open without touching the counter."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="1")
        assert await ws.autoreply_circuit_open(redis) is True

    @pytest.mark.asyncio
    async def test_circuit_open_on_redis_exception_returns_false(self) -> None:
        """Redis error → fail open (DB-fallback dedup protects correctness)."""
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=Exception("redis down"))
        assert await ws.autoreply_circuit_open(redis) is False
