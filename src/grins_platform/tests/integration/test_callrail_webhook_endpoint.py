"""Integration tests for ``POST /api/v1/webhooks/callrail/inbound``.

Exercises Gap 07 — Webhook Security & Dedup end-to-end:

* 7.A replay protection (stale ``created_at`` → 400)
* 7.B DB fallback dedup (Redis-down + DB-row → 200 already_processed)
* 7.C per-IP slowapi rate limit (61st call → 503 with Retry-After)
* Signature handling (valid, invalid, missing)
* Replay of the same body returns ``already_processed``

Tests use the project's real Postgres backend. They monkeypatch the
env vars required by ``get_sms_provider()`` (which reads env live on
every call) and mock ``SMSService.handle_inbound`` so business-logic
side effects (SMS sends, campaign-response rows) stay out of scope.

Validates: Gap 07 — Webhook Security & Dedup
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app
from grins_platform.middleware.rate_limit import limiter
from grins_platform.models.webhook_processed_log import WebhookProcessedLog

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

pytestmark = pytest.mark.integration


WEBHOOK_PATH = "/api/v1/webhooks/callrail/inbound"
_TEST_SECRET = "test-secret-gap07"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sign(body: bytes, secret: str = _TEST_SECRET) -> str:
    """Return a base64-encoded HMAC-SHA1 of ``body`` using ``secret``."""
    return base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha1).digest(),
    ).decode()


def _payload(
    *,
    resource_id: str | None = None,
    created_at: str | None = None,
    timestamp_mode: str = "created_at",
) -> dict[str, Any]:
    """Build a CallRail-shaped inbound SMS payload for tests.

    ``timestamp_mode`` selects which top-level fields the payload
    carries:

    * ``"created_at"`` (default): the simulator-style payload — both
      ``created_at`` is set explicitly. ``created_at`` arg overrides.
    * ``"sent_at_only"``: drops ``created_at``, keeps ``sent_at`` —
      probes the Bug #3 secondary fallback.
    * ``"neither"``: drops both timestamp fields — mirrors the verified
      real CallRail inbound payload (see Bug #3); the endpoint must
      fall back to receipt time.
    """
    rid = resource_id or f"res_{uuid.uuid4().hex[:12]}"
    ts = created_at or datetime.now(tz=timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "resource_id": rid,
        "conversation_id": f"conv_{uuid.uuid4().hex[:6]}",
        "source_number": "+19527373312",
        "destination_number": "+19525293750",
        "content": "Y",
        "thread_resource_id": f"thread_{uuid.uuid4().hex[:6]}",
    }
    if timestamp_mode == "created_at":
        payload["created_at"] = ts
    elif timestamp_mode == "sent_at_only":
        payload["sent_at"] = ts
    elif timestamp_mode == "neither":
        pass
    else:  # pragma: no cover - defensive
        msg = f"Unknown timestamp_mode: {timestamp_mode}"
        raise ValueError(msg)
    return payload


def _encode_and_sign(payload: dict[str, Any]) -> tuple[bytes, str]:
    """Serialize ``payload`` and sign it for the webhook endpoint."""
    body = json.dumps(payload).encode()
    return body, _sign(body)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _callrail_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set env vars read live by :func:`get_sms_provider`."""
    monkeypatch.setenv("SMS_PROVIDER", "callrail")
    monkeypatch.setenv("CALLRAIL_WEBHOOK_SECRET", _TEST_SECRET)
    monkeypatch.setenv("CALLRAIL_API_KEY", "test-api-key")
    monkeypatch.setenv("CALLRAIL_ACCOUNT_ID", "ACCtest")
    monkeypatch.setenv("CALLRAIL_COMPANY_ID", "COMtest")
    monkeypatch.setenv("CALLRAIL_TRACKING_NUMBER", "+19525293750")


@pytest.fixture(autouse=True)
def _mock_handle_inbound() -> Any:
    """Short-circuit ``SMSService.handle_inbound`` to avoid fan-out I/O."""
    with patch(
        "grins_platform.api.v1.callrail_webhooks.SMSService.handle_inbound",
        new=AsyncMock(return_value={"action": "test_noop"}),
    ):
        yield


@pytest.fixture(autouse=True)
def _reset_limiter() -> Any:
    """Reset slowapi limiter state between tests so counts don't bleed."""
    limiter.reset()
    yield
    limiter.reset()


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test() -> Any:
    """Dispose the shared DB engine between tests to avoid connection reuse.

    ASGITransport + httpx reuse the singleton ``DatabaseManager`` across
    tests, and asyncpg connections that were borrowed by the previous
    request can end up in an inconsistent state by the time the next
    request tries to start a transaction on them. Disposing forces a
    fresh pool per test — cheap for a ~6-test suite.
    """
    yield
    from grins_platform.database import (
        get_database_manager,
    )

    mgr = get_database_manager()
    if mgr._engine is not None:  # type: ignore[attr-defined]
        with contextlib.suppress(Exception):
            await mgr._engine.dispose()  # type: ignore[attr-defined]
        mgr._engine = None  # type: ignore[attr-defined]
        mgr._session_factory = None  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an unauthenticated async HTTP client targeting the real app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _cleanup_log_rows(provider_message_ids: list[str]) -> None:
    """Delete any :class:`WebhookProcessedLog` rows the test inserted."""
    if not provider_message_ids:
        return
    from sqlalchemy import delete

    from grins_platform.database import (
        get_database_manager,
    )

    db_manager = get_database_manager()
    session_factory = db_manager.session_factory
    async with session_factory() as session:
        with contextlib.suppress(Exception):
            await session.execute(
                delete(WebhookProcessedLog).where(
                    WebhookProcessedLog.provider_message_id.in_(
                        provider_message_ids,
                    ),
                ),
            )
            await session.commit()


async def _insert_log_row(provider_message_id: str) -> None:
    """Pre-insert a processed-log row for DB-fallback tests."""
    from grins_platform.database import (
        get_database_manager,
    )
    from grins_platform.repositories.webhook_processed_log_repository import (
        WebhookProcessedLogRepository,
    )

    db_manager = get_database_manager()
    session_factory = db_manager.session_factory
    async with session_factory() as session:
        await WebhookProcessedLogRepository(session).mark_processed(
            "callrail",
            provider_message_id,
        )
        await session.commit()


# ---------------------------------------------------------------------------
# Signature handling
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCallrailWebhookSignature:
    """Signature-verify path."""

    @pytest.mark.asyncio
    async def test_webhook_with_invalid_signature_returns_403(
        self,
        async_client: AsyncClient,
    ) -> None:
        body, _sig = _encode_and_sign(_payload())
        response = await async_client.post(
            WEBHOOK_PATH,
            content=body,
            headers={
                "signature": "not-a-valid-sig",
                "content-type": "application/json",
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_webhook_with_missing_signature_returns_403(
        self,
        async_client: AsyncClient,
    ) -> None:
        body, _sig = _encode_and_sign(_payload())
        response = await async_client.post(
            WEBHOOK_PATH,
            content=body,
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Freshness / replay window
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCallrailWebhookFreshness:
    """Gap 07.A freshness checks."""

    @pytest.mark.asyncio
    async def test_webhook_with_stale_timestamp_returns_400(
        self,
        async_client: AsyncClient,
    ) -> None:
        stale = (datetime.now(tz=timezone.utc) - timedelta(seconds=600)).isoformat()
        payload = _payload(created_at=stale)
        body, sig = _encode_and_sign(payload)
        response = await async_client.post(
            WEBHOOK_PATH,
            content=body,
            headers={"signature": sig, "content-type": "application/json"},
        )
        assert response.status_code == 400
        assert "timestamp" in response.text.lower()

    @pytest.mark.asyncio
    async def test_webhook_with_malformed_timestamp_returns_400(
        self,
        async_client: AsyncClient,
    ) -> None:
        payload = _payload(created_at="not-a-timestamp")
        body, sig = _encode_and_sign(payload)
        response = await async_client.post(
            WEBHOOK_PATH,
            content=body,
            headers={"signature": sig, "content-type": "application/json"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_with_only_sent_at_succeeds(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Bug #3 — payloads that carry only ``sent_at`` must succeed.

        CallRail-style payloads where top-level ``created_at`` is absent
        previously 400ed; the freshness extractor now falls back to
        ``sent_at`` and resource-id dedup remains the primary replay
        barrier.
        """
        payload = _payload(timestamp_mode="sent_at_only")
        body, sig = _encode_and_sign(payload)
        response = await async_client.post(
            WEBHOOK_PATH,
            content=body,
            headers={"signature": sig, "content-type": "application/json"},
        )
        assert response.status_code == 200
        await _cleanup_log_rows([str(payload["resource_id"])])

    @pytest.mark.asyncio
    async def test_webhook_with_no_timestamp_falls_back_to_receipt_time(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Bug #3 — verified-real CallRail payload has no timestamp field.

        Endpoint must fall back to receipt time and return 200.
        """
        payload = _payload(timestamp_mode="neither")
        body, sig = _encode_and_sign(payload)
        response = await async_client.post(
            WEBHOOK_PATH,
            content=body,
            headers={"signature": sig, "content-type": "application/json"},
        )
        assert response.status_code == 200
        await _cleanup_log_rows([str(payload["resource_id"])])


# ---------------------------------------------------------------------------
# Happy path + replay dedup + DB fallback
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCallrailWebhookDedup:
    """Gap 07.A/B dedup paths."""

    @pytest.mark.asyncio
    async def test_webhook_with_fresh_valid_payload_processes_once(
        self,
        async_client: AsyncClient,
    ) -> None:
        payload = _payload()
        body, sig = _encode_and_sign(payload)
        response = await async_client.post(
            WEBHOOK_PATH,
            content=body,
            headers={"signature": sig, "content-type": "application/json"},
        )
        assert response.status_code == 200
        assert '"status": "processed"' in response.text
        await _cleanup_log_rows([payload["resource_id"]])

    @pytest.mark.asyncio
    async def test_webhook_with_replay_returns_already_processed(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Redis primary dedup: second POST of same body → already_processed."""
        # Force Redis off so DB fallback is exercised (works regardless of
        # whether Redis is running during the test run).
        payload = _payload()
        body, sig = _encode_and_sign(payload)
        try:
            with patch(
                "grins_platform.api.v1.callrail_webhooks._get_redis",
                new=AsyncMock(return_value=None),
            ):
                first = await async_client.post(
                    WEBHOOK_PATH,
                    content=body,
                    headers={
                        "signature": sig,
                        "content-type": "application/json",
                    },
                )
                assert first.status_code == 200
                assert '"status": "processed"' in first.text

                second = await async_client.post(
                    WEBHOOK_PATH,
                    content=body,
                    headers={
                        "signature": sig,
                        "content-type": "application/json",
                    },
                )
                assert second.status_code == 200
                assert '"status": "already_processed"' in second.text
        finally:
            await _cleanup_log_rows([payload["resource_id"]])

    @pytest.mark.asyncio
    async def test_webhook_with_preseeded_db_row_returns_already_processed(
        self,
        async_client: AsyncClient,
    ) -> None:
        """DB fallback: pre-insert row, then POST → 200 already_processed."""
        payload = _payload()
        body, sig = _encode_and_sign(payload)
        await _insert_log_row(str(payload["resource_id"]))

        try:
            with patch(
                "grins_platform.api.v1.callrail_webhooks._get_redis",
                new=AsyncMock(return_value=None),
            ):
                response = await async_client.post(
                    WEBHOOK_PATH,
                    content=body,
                    headers={
                        "signature": sig,
                        "content-type": "application/json",
                    },
                )
            assert response.status_code == 200
            assert '"status": "already_processed"' in response.text
        finally:
            await _cleanup_log_rows([payload["resource_id"]])


# ---------------------------------------------------------------------------
# Rate limit → 503
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCallrailWebhookRateLimit:
    """Gap 07.C per-IP slowapi rate limit."""

    @pytest.mark.asyncio
    async def test_webhook_rate_limit_returns_503_after_threshold(
        self,
        async_client: AsyncClient,
    ) -> None:
        # Fire enough fresh requests to breach the 60/minute limit in a
        # single synchronous burst. Each payload is distinct so only the
        # limiter — not the dedup layer — can answer.
        resource_ids: list[str] = []
        try:
            with patch(
                "grins_platform.api.v1.callrail_webhooks._get_redis",
                new=AsyncMock(return_value=None),
            ):
                response = None
                for _ in range(65):
                    payload = _payload()
                    resource_ids.append(payload["resource_id"])
                    body, sig = _encode_and_sign(payload)
                    response = await async_client.post(
                        WEBHOOK_PATH,
                        content=body,
                        headers={
                            "signature": sig,
                            "content-type": "application/json",
                        },
                    )
                    if response.status_code == 503:
                        break
                assert response is not None
                assert response.status_code == 503
                assert response.headers.get("Retry-After") == "60"
        finally:
            await _cleanup_log_rows(resource_ids)
