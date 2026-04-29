"""Unit tests for the SignWell webhook endpoint.

Specifically covers the ``document_completed`` advance path's pre-state
behaviour (bughunt H-10): happy path, unexpected pre-state WARN log, and
response-code guarantee even when the advance is skipped.

Mirrors the fixture/mock patterns used in
``src/grins_platform/tests/integration/test_signwell_webhook_integration.py``.

Validates: CRM Changes Update 2 Req 14.6, 17.4, 18.4; bughunt H-10.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app
from grins_platform.models.enums import SalesEntryStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from _pytest.logging import LogCaptureFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test-webhook-secret-key"
WEBHOOK_URL = "/api/v1/webhooks/signwell"


def _make_signature(payload_bytes: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 hex digest for webhook verification."""
    return hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def _make_document_completed_payload(
    document_id: str,
    **extra: Any,
) -> dict[str, Any]:
    """Build a minimal document_completed webhook payload."""
    payload: dict[str, Any] = {
        "event_type": "document_completed",
        "data": {
            "id": document_id,
            "name": "Signed Contract",
            **extra,
        },
    }
    return payload


def _make_sales_entry_mock(
    *,
    entry_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    signwell_document_id: str = "",
    status: str = SalesEntryStatus.PENDING_APPROVAL.value,
) -> MagicMock:
    """Create a mock SalesEntry row."""
    entry = MagicMock()
    entry.id = entry_id or uuid.uuid4()
    entry.customer_id = customer_id or uuid.uuid4()
    entry.signwell_document_id = signwell_document_id
    entry.status = status
    entry.updated_at = datetime.now(tz=timezone.utc)
    return entry


@dataclass
class _FakeUploadResult:
    file_key: str
    file_name: str
    file_size: int
    content_type: str


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _install_overrides(mock_db: Any, mock_sw_client: Any) -> None:
    """Wire dependency overrides on the FastAPI app."""
    from grins_platform.api.v1.signwell_webhooks import _get_signwell_client
    from grins_platform.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[_get_signwell_client] = lambda: mock_sw_client


def _make_db_for_entry(entry: MagicMock) -> AsyncMock:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = entry
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    return mock_db


def _make_signwell_client_mock(pdf_bytes: bytes) -> MagicMock:
    mock_sw_client = MagicMock()
    mock_sw_client.verify_webhook_signature = MagicMock(return_value=True)
    mock_sw_client.fetch_signed_pdf = AsyncMock(return_value=pdf_bytes)
    return mock_sw_client


def _make_upload_result(document_id: str, pdf_bytes: bytes) -> _FakeUploadResult:
    return _FakeUploadResult(
        file_key=f"customer_documents/{uuid.uuid4()}.pdf",
        file_name=f"signed_contract_{document_id}.pdf",
        file_size=len(pdf_bytes),
        content_type="application/pdf",
    )


# ---------------------------------------------------------------------------
# Tests — H-10 pre-state behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestSignWellWebhookDocumentSignedPreState:
    """Coverage for the ``document_completed`` pre-state branches.

    Validates: bughunt H-10.
    """

    @pytest.mark.asyncio()
    async def test_document_signed_advances_when_pending_approval(
        self,
        client: AsyncClient,
        caplog: LogCaptureFixture,
    ) -> None:
        """Happy path: PENDING_APPROVAL → SEND_CONTRACT, no warning log."""
        document_id = "sw-doc-" + uuid.uuid4().hex[:12]
        entry = _make_sales_entry_mock(
            signwell_document_id=document_id,
            status=SalesEntryStatus.PENDING_APPROVAL.value,
        )

        payload = _make_document_completed_payload(document_id)
        payload_bytes = json.dumps(payload).encode()
        signature = _make_signature(payload_bytes)

        fake_pdf = b"%PDF-1.4 happy path"
        fake_upload = _make_upload_result(document_id, fake_pdf)

        mock_db = _make_db_for_entry(entry)
        mock_sw_client = _make_signwell_client_mock(fake_pdf)
        mock_photo_svc = MagicMock()
        mock_photo_svc.upload_file.return_value = fake_upload

        _install_overrides(mock_db, mock_sw_client)

        try:
            with (
                patch(
                    "grins_platform.services.photo_service.PhotoService",
                    return_value=mock_photo_svc,
                ),
                caplog.at_level("WARNING"),
            ):
                response = await client.post(
                    WEBHOOK_URL,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Signwell-Signature": signature,
                    },
                )

            assert response.status_code == 200
            assert response.json()["status"] == "processed"

            # Status advanced to SEND_CONTRACT.
            assert entry.status == SalesEntryStatus.SEND_CONTRACT.value

            # No unexpected-pre-state WARN was emitted.
            for record in caplog.records:
                assert "signwell.document_signed.unexpected_pre_state" not in (
                    record.message
                )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio()
    async def test_document_signed_logs_warning_when_not_pending_approval(
        self,
        client: AsyncClient,
        caplog: LogCaptureFixture,
    ) -> None:
        """Unexpected pre-state: status unchanged, structured WARN emitted."""
        document_id = "sw-doc-" + uuid.uuid4().hex[:12]
        pre_state = SalesEntryStatus.CLOSED_WON.value
        entry = _make_sales_entry_mock(
            signwell_document_id=document_id,
            status=pre_state,
        )

        payload = _make_document_completed_payload(document_id)
        payload_bytes = json.dumps(payload).encode()
        signature = _make_signature(payload_bytes)

        fake_pdf = b"%PDF-1.4 unexpected pre-state"
        fake_upload = _make_upload_result(document_id, fake_pdf)

        mock_db = _make_db_for_entry(entry)
        mock_sw_client = _make_signwell_client_mock(fake_pdf)
        mock_photo_svc = MagicMock()
        mock_photo_svc.upload_file.return_value = fake_upload

        _install_overrides(mock_db, mock_sw_client)

        try:
            with (
                patch(
                    "grins_platform.services.photo_service.PhotoService",
                    return_value=mock_photo_svc,
                ),
                caplog.at_level("WARNING"),
            ):
                response = await client.post(
                    WEBHOOK_URL,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Signwell-Signature": signature,
                    },
                )

            # Still 2xx — SignWell must not retry.
            assert response.status_code == 200

            # Status must NOT change.
            assert entry.status == pre_state

            # Exactly one WARN with the expected event name + context.
            matching = [
                json.loads(r.message)
                for r in caplog.records
                if "signwell.document_signed.unexpected_pre_state" in r.message
            ]
            assert len(matching) == 1
            log_entry = matching[0]
            assert log_entry["event"] == "signwell.document_signed.unexpected_pre_state"
            assert log_entry["entry_id"] == str(entry.id)
            assert log_entry["pre_state"] == pre_state
            assert log_entry["expected"] == SalesEntryStatus.PENDING_APPROVAL.value
            assert log_entry["document_id"] == document_id
            assert log_entry["level"] == "warning"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio()
    async def test_document_signed_returns_200_even_on_unexpected_pre_state(
        self,
        client: AsyncClient,
    ) -> None:
        """Explicit response-code guarantee for the unexpected-pre-state branch.

        SignWell retries on non-2xx, which we do NOT want here — the document
        was received fine; the problem is local state.
        """
        document_id = "sw-doc-" + uuid.uuid4().hex[:12]
        entry = _make_sales_entry_mock(
            signwell_document_id=document_id,
            status=SalesEntryStatus.CLOSED_LOST.value,
        )

        payload = _make_document_completed_payload(document_id)
        payload_bytes = json.dumps(payload).encode()
        signature = _make_signature(payload_bytes)

        fake_pdf = b"%PDF-1.4 closed lost"
        fake_upload = _make_upload_result(document_id, fake_pdf)

        mock_db = _make_db_for_entry(entry)
        mock_sw_client = _make_signwell_client_mock(fake_pdf)
        mock_photo_svc = MagicMock()
        mock_photo_svc.upload_file.return_value = fake_upload

        _install_overrides(mock_db, mock_sw_client)

        try:
            with patch(
                "grins_platform.services.photo_service.PhotoService",
                return_value=mock_photo_svc,
            ):
                response = await client.post(
                    WEBHOOK_URL,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Signwell-Signature": signature,
                    },
                )

            assert response.status_code == 200
            assert response.json()["status"] == "processed"
            # Commit still happened (PDF was stored) even though the advance
            # was skipped.
            mock_db.commit.assert_awaited_once()
        finally:
            app.dependency_overrides.clear()
