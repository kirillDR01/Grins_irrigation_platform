"""Unit tests for the Resend bounce/complaint webhook endpoint.

Validates: Feature — estimate approval email portal (bounce handling).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

WEBHOOK_URL = "/api/v1/webhooks/resend"


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _install_db_override(mock_db: AsyncMock) -> None:
    from grins_platform.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: mock_db


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _make_bounce_payload(
    *,
    to: list[str] | None = None,
    bounce_type: str = "Permanent",
    estimate_id: str | None = "est-123",
) -> dict[str, Any]:
    tags = [{"name": "estimate_id", "value": estimate_id}] if estimate_id else []
    return {
        "type": "email.bounced",
        "data": {
            "to": to or ["alice@example.com"],
            "bounce": {
                "type": bounce_type,
                "message": "550 5.1.1 mailbox does not exist",
            },
            "tags": tags,
        },
    }


@pytest.mark.unit
class TestResendWebhook:
    @pytest.mark.asyncio
    async def test_with_invalid_signature_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        mock_db = AsyncMock()
        _install_db_override(mock_db)
        try:
            with patch(
                "grins_platform.api.v1.resend_webhooks.verify_resend_webhook_signature",
                side_effect=__import__(
                    "grins_platform.services.resend_webhook_security",
                    fromlist=["ResendWebhookVerificationError"],
                ).ResendWebhookVerificationError("bad sig"),
            ):
                resp = await client.post(WEBHOOK_URL, content=b"{}")
            assert resp.status_code == 401
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_with_unknown_event_returns_200_and_skips(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("INTERNAL_NOTIFICATION_EMAIL", raising=False)
        monkeypatch.delenv("INTERNAL_NOTIFICATION_PHONE", raising=False)
        mock_db = AsyncMock()
        _install_db_override(mock_db)
        try:
            with patch(
                "grins_platform.api.v1.resend_webhooks.verify_resend_webhook_signature",
                return_value={"type": "email.delivery_delayed", "data": {}},
            ):
                resp = await client.post(WEBHOOK_URL, content=json.dumps({}).encode())
            assert resp.status_code == 200
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_permanent_bounce_stamps_customer_email_bounced_at(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("INTERNAL_NOTIFICATION_EMAIL", raising=False)
        monkeypatch.delenv("INTERNAL_NOTIFICATION_PHONE", raising=False)
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        _install_db_override(mock_db)
        try:
            with patch(
                "grins_platform.api.v1.resend_webhooks.verify_resend_webhook_signature",
                return_value=_make_bounce_payload(),
            ):
                resp = await client.post(WEBHOOK_URL, content=b"{}")
            assert resp.status_code == 200
            mock_db.execute.assert_awaited_once()
            mock_db.commit.assert_awaited_once()
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_transient_bounce_does_not_stamp_customer(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("INTERNAL_NOTIFICATION_EMAIL", raising=False)
        monkeypatch.delenv("INTERNAL_NOTIFICATION_PHONE", raising=False)
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        _install_db_override(mock_db)
        try:
            with patch(
                "grins_platform.api.v1.resend_webhooks.verify_resend_webhook_signature",
                return_value=_make_bounce_payload(bounce_type="Temporary"),
            ):
                resp = await client.post(WEBHOOK_URL, content=b"{}")
            assert resp.status_code == 200
            mock_db.execute.assert_not_awaited()
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_no_recipient_returns_200_and_logs(
        self,
        client: AsyncClient,
    ) -> None:
        mock_db = AsyncMock()
        _install_db_override(mock_db)
        try:
            with patch(
                "grins_platform.api.v1.resend_webhooks.verify_resend_webhook_signature",
                return_value=_make_bounce_payload(to=[]),
            ):
                resp = await client.post(WEBHOOK_URL, content=b"{}")
            assert resp.status_code == 200
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_valid_bounce_dispatches_internal_email(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("INTERNAL_NOTIFICATION_EMAIL", "staff@x.com")
        monkeypatch.delenv("INTERNAL_NOTIFICATION_PHONE", raising=False)
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        _install_db_override(mock_db)
        try:
            with (
                patch(
                    "grins_platform.api.v1.resend_webhooks."
                    "verify_resend_webhook_signature",
                    return_value=_make_bounce_payload(),
                ),
                patch(
                    "grins_platform.api.v1.resend_webhooks.EmailService"
                ) as mock_email_cls,
            ):
                inst = MagicMock()
                inst.send_internal_estimate_bounce_email = MagicMock(return_value=True)
                mock_email_cls.return_value = inst
                resp = await client.post(WEBHOOK_URL, content=b"{}")
            assert resp.status_code == 200
            inst.send_internal_estimate_bounce_email.assert_called_once()
        finally:
            _clear_overrides()
