"""Integration tests for SignWell webhook processing.

End-to-end flow: webhook payload → signature verification → PDF storage
→ CustomerDocument creation → sales entry status advance.

External services (SignWell API, S3) are mocked; the full internal flow
from HTTP request through DB writes is exercised.

Validates: CRM Changes Update 2 Req 14.6, 17.4, 18.4
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app
from grins_platform.models.enums import SalesEntryStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test-webhook-secret-key"
WEBHOOK_URL = "/api/v1/webhooks/signwell"


def _make_signature(payload_bytes: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 hex digest for webhook verification."""
    return hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256,
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
async def client() -> AsyncClient:
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration()
class TestSignWellWebhookIntegration:
    """Integration tests for the full SignWell webhook processing flow.

    Validates: CRM Changes Update 2 Req 14.6, 17.4, 18.4
    """

    # -- happy path -------------------------------------------------------

    async def test_document_completed_stores_pdf_and_advances_status(
        self,
        client: AsyncClient,
    ) -> None:
        """Full flow: valid webhook → PDF stored → status advances.

        **Validates: Requirements 14.6, 17.4, 18.4**

        1. Construct a document_completed payload with a known document ID.
        2. Generate a valid HMAC-SHA256 signature.
        3. POST to the webhook endpoint.
        4. Verify the signed PDF is stored as a CustomerDocument.
        5. Verify the sales entry status advances from pending_approval
           to send_contract.
        """
        document_id = "sw-doc-" + uuid.uuid4().hex[:12]
        customer_id = uuid.uuid4()
        entry = _make_sales_entry_mock(
            customer_id=customer_id,
            signwell_document_id=document_id,
            status=SalesEntryStatus.PENDING_APPROVAL.value,
        )

        payload = _make_document_completed_payload(document_id)
        payload_bytes = json.dumps(payload).encode()
        signature = _make_signature(payload_bytes)

        fake_pdf = b"%PDF-1.4 fake signed contract content"
        fake_upload = _FakeUploadResult(
            file_key=f"customer_documents/{uuid.uuid4()}.pdf",
            file_name=f"signed_contract_{document_id}.pdf",
            file_size=len(fake_pdf),
            content_type="application/pdf",
        )

        # Mock DB session — return the sales entry on query
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entry
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        # Mock SignWellClient
        mock_sw_client = MagicMock()
        mock_sw_client.verify_webhook_signature = MagicMock(return_value=True)
        mock_sw_client.fetch_signed_pdf = AsyncMock(return_value=fake_pdf)

        # Mock PhotoService
        mock_photo_svc = MagicMock()
        mock_photo_svc.upload_file.return_value = fake_upload

        # Wire dependency overrides
        from grins_platform.api.v1.signwell_webhooks import (
            _get_signwell_client,
        )
        from grins_platform.database import get_db_session

        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[_get_signwell_client] = lambda: mock_sw_client

        try:
            with patch(
                "grins_platform.services.photo_service.PhotoService",
                return_value=mock_photo_svc,
            ) as _mock_cls:
                response = await client.post(
                    WEBHOOK_URL,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Signwell-Signature": signature,
                    },
                )

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "processed"

            # Verify signature was checked
            mock_sw_client.verify_webhook_signature.assert_called_once()

            # Verify signed PDF was fetched from SignWell
            mock_sw_client.fetch_signed_pdf.assert_awaited_once_with(document_id)

            # Verify PDF was uploaded to S3 via PhotoService
            mock_photo_svc.upload_file.assert_called_once()
            upload_call = mock_photo_svc.upload_file.call_args
            assert (
                upload_call.kwargs.get("data") == fake_pdf
                or upload_call[1].get("data") == fake_pdf
            )

            # Verify CustomerDocument was added to DB session
            mock_db.add.assert_called_once()
            doc_arg = mock_db.add.call_args[0][0]
            assert doc_arg.customer_id == customer_id
            assert doc_arg.document_type == "signed_contract"
            assert doc_arg.mime_type == "application/pdf"
            assert doc_arg.file_key == fake_upload.file_key

            # Verify sales entry status advanced
            assert entry.status == SalesEntryStatus.SEND_CONTRACT.value

            # Verify DB commit was called
            mock_db.commit.assert_awaited_once()
        finally:
            app.dependency_overrides.clear()

    # -- signature verification -------------------------------------------

    async def test_invalid_signature_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Webhook with bad signature is rejected with 401.

        **Validates: Requirements 14.6**
        """
        from grins_platform.api.v1.signwell_webhooks import (
            _get_signwell_client,
        )
        from grins_platform.database import get_db_session
        from grins_platform.services.signwell.client import (
            SignWellWebhookVerificationError,
        )

        payload = _make_document_completed_payload("doc-123")
        payload_bytes = json.dumps(payload).encode()

        mock_db = AsyncMock()
        mock_sw_client = MagicMock()
        mock_sw_client.verify_webhook_signature = MagicMock(
            side_effect=SignWellWebhookVerificationError("Invalid webhook signature"),
        )

        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[_get_signwell_client] = lambda: mock_sw_client

        try:
            response = await client.post(
                WEBHOOK_URL,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Signwell-Signature": "totally-wrong-sig",
                },
            )

            assert response.status_code == 401
            assert "Invalid signature" in response.json()["error"]
            mock_db.commit.assert_not_awaited()
        finally:
            app.dependency_overrides.clear()

    # -- non-document_completed events ------------------------------------

    async def test_non_document_completed_event_is_ignored(
        self,
        client: AsyncClient,
    ) -> None:
        """Events other than document_completed return 200 with 'ignored'.

        **Validates: Requirements 14.6**
        """
        from grins_platform.api.v1.signwell_webhooks import (
            _get_signwell_client,
        )
        from grins_platform.database import get_db_session

        payload: dict[str, Any] = {
            "event_type": "document_viewed",
            "data": {"id": "doc-456"},
        }
        payload_bytes = json.dumps(payload).encode()

        mock_db = AsyncMock()
        mock_sw_client = MagicMock()
        mock_sw_client.verify_webhook_signature = MagicMock(return_value=True)

        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[_get_signwell_client] = lambda: mock_sw_client

        try:
            response = await client.post(
                WEBHOOK_URL,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Signwell-Signature": _make_signature(payload_bytes),
                },
            )

            assert response.status_code == 200
            assert response.json()["status"] == "ignored"
            mock_db.commit.assert_not_awaited()
        finally:
            app.dependency_overrides.clear()

    # -- no matching sales entry ------------------------------------------

    async def test_no_matching_sales_entry_returns_200_no_match(
        self,
        client: AsyncClient,
    ) -> None:
        """document_completed for unknown doc ID returns no_matching_entry.

        **Validates: Requirements 14.6**
        """
        from grins_platform.api.v1.signwell_webhooks import (
            _get_signwell_client,
        )
        from grins_platform.database import get_db_session

        payload = _make_document_completed_payload("unknown-doc-id")
        payload_bytes = json.dumps(payload).encode()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_sw_client = MagicMock()
        mock_sw_client.verify_webhook_signature = MagicMock(return_value=True)

        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[_get_signwell_client] = lambda: mock_sw_client

        try:
            response = await client.post(
                WEBHOOK_URL,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Signwell-Signature": _make_signature(payload_bytes),
                },
            )

            assert response.status_code == 200
            assert response.json()["status"] == "no_matching_entry"
            mock_db.commit.assert_not_awaited()
        finally:
            app.dependency_overrides.clear()

    # -- status not pending_approval stays unchanged ----------------------

    async def test_status_not_pending_approval_stores_pdf_but_no_advance(
        self,
        client: AsyncClient,
    ) -> None:
        """If entry is past pending_approval, PDF stored but no advance.

        **Validates: Requirements 17.4, 18.4**
        """
        document_id = "sw-doc-already-advanced"
        customer_id = uuid.uuid4()
        entry = _make_sales_entry_mock(
            customer_id=customer_id,
            signwell_document_id=document_id,
            status=SalesEntryStatus.SEND_CONTRACT.value,
        )

        payload = _make_document_completed_payload(document_id)
        payload_bytes = json.dumps(payload).encode()

        fake_pdf = b"%PDF-1.4 duplicate webhook delivery"
        fake_upload = _FakeUploadResult(
            file_key=f"customer_documents/{uuid.uuid4()}.pdf",
            file_name=f"signed_contract_{document_id}.pdf",
            file_size=len(fake_pdf),
            content_type="application/pdf",
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entry
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        mock_sw_client = MagicMock()
        mock_sw_client.verify_webhook_signature = MagicMock(return_value=True)
        mock_sw_client.fetch_signed_pdf = AsyncMock(return_value=fake_pdf)

        mock_photo_svc = MagicMock()
        mock_photo_svc.upload_file.return_value = fake_upload

        from grins_platform.api.v1.signwell_webhooks import (
            _get_signwell_client,
        )
        from grins_platform.database import get_db_session

        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[_get_signwell_client] = lambda: mock_sw_client

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
                        "X-Signwell-Signature": _make_signature(payload_bytes),
                    },
                )

            assert response.status_code == 200
            assert response.json()["status"] == "processed"

            # PDF still stored
            mock_db.add.assert_called_once()
            doc_arg = mock_db.add.call_args[0][0]
            assert doc_arg.document_type == "signed_contract"

            # Status NOT changed — still send_contract
            assert entry.status == SalesEntryStatus.SEND_CONTRACT.value
        finally:
            app.dependency_overrides.clear()

    # -- PDF fetch failure ------------------------------------------------

    async def test_pdf_fetch_failure_returns_502(
        self,
        client: AsyncClient,
    ) -> None:
        """If fetching the signed PDF from SignWell fails, return 502.

        **Validates: Requirements 18.4**
        """
        from grins_platform.services.signwell.client import SignWellError

        document_id = "sw-doc-fetch-fail"
        entry = _make_sales_entry_mock(
            signwell_document_id=document_id,
            status=SalesEntryStatus.PENDING_APPROVAL.value,
        )

        payload = _make_document_completed_payload(document_id)
        payload_bytes = json.dumps(payload).encode()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entry
        mock_db.execute.return_value = mock_result

        mock_sw_client = MagicMock()
        mock_sw_client.verify_webhook_signature = MagicMock(return_value=True)
        mock_sw_client.fetch_signed_pdf = AsyncMock(
            side_effect=SignWellError("API error 500: Internal Server Error"),
        )

        from grins_platform.api.v1.signwell_webhooks import (
            _get_signwell_client,
        )
        from grins_platform.database import get_db_session

        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[_get_signwell_client] = lambda: mock_sw_client

        try:
            response = await client.post(
                WEBHOOK_URL,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Signwell-Signature": _make_signature(payload_bytes),
                },
            )

            assert response.status_code == 502
            assert "Failed to fetch signed PDF" in response.json()["error"]

            # Status should NOT have advanced
            assert entry.status == SalesEntryStatus.PENDING_APPROVAL.value
            mock_db.commit.assert_not_awaited()
        finally:
            app.dependency_overrides.clear()
