"""Unit tests for SalesPipelineService and SignWellClient.

Validates: CRM Changes Update 2 Req 14.3, 14.6, 16.1, 16.2, 18.5
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest

from grins_platform.exceptions import (
    InvalidSalesTransitionError,
    SalesEntryNotFoundError,
    SignatureRequiredError,
)
from grins_platform.models.enums import SalesEntryStatus
from grins_platform.services.sales_pipeline_service import SalesPipelineService
from grins_platform.services.signwell.client import (
    SignWellClient,
    SignWellDocumentNotFoundError,
    SignWellError,
    SignWellWebhookVerificationError,
)
from grins_platform.services.signwell.config import SignWellSettings

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture()
def mock_job_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_audit_service() -> AsyncMock:
    svc = AsyncMock()
    svc.log_action = AsyncMock(return_value=Mock(id=uuid4()))
    return svc


@pytest.fixture()
def pipeline_service(
    mock_job_service: AsyncMock,
    mock_audit_service: AsyncMock,
) -> SalesPipelineService:
    return SalesPipelineService(
        job_service=mock_job_service,
        audit_service=mock_audit_service,
    )


@pytest.fixture()
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_entry(
    status: str = SalesEntryStatus.SCHEDULE_ESTIMATE.value,
    *,
    signwell_document_id: str | None = None,
) -> Mock:
    entry = Mock()
    entry.id = uuid4()
    entry.customer_id = uuid4()
    entry.property_id = uuid4()
    entry.lead_id = uuid4()
    entry.job_type = "estimate"
    entry.status = status
    entry.notes = "test notes"
    entry.signwell_document_id = signwell_document_id
    entry.override_flag = False
    entry.closed_reason = None
    entry.updated_at = datetime.now(tz=timezone.utc)
    return entry


# ===================================================================
# SalesPipelineService — Status Transitions
# ===================================================================


@pytest.mark.unit()
class TestSalesPipelineAdvanceStatus:
    """Test advance_status enforces one-step-forward transitions."""

    @pytest.mark.asyncio()
    async def test_advance_from_schedule_estimate(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.SCHEDULE_ESTIMATE.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )

        result = await pipeline_service.advance_status(mock_db, entry.id)
        assert result.status == SalesEntryStatus.ESTIMATE_SCHEDULED.value

    @pytest.mark.asyncio()
    async def test_advance_through_full_pipeline(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        """Advance step-by-step through the entire non-terminal pipeline."""
        expected_order = [
            SalesEntryStatus.ESTIMATE_SCHEDULED.value,
            SalesEntryStatus.SEND_ESTIMATE.value,
            SalesEntryStatus.PENDING_APPROVAL.value,
            SalesEntryStatus.SEND_CONTRACT.value,
            SalesEntryStatus.CLOSED_WON.value,
        ]
        entry = _make_entry(SalesEntryStatus.SCHEDULE_ESTIMATE.value)

        for expected in expected_order:
            mock_db.execute = AsyncMock(
                return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
            )
            await pipeline_service.advance_status(mock_db, entry.id)
            assert entry.status == expected


@pytest.mark.unit()
class TestSalesPipelineGateRelaxation:
    """As of the Q-B fix, advancing send_estimate → pending_approval no
    longer requires ``signwell_document_id``. Estimate approval is a
    portal click, not a signature. These tests lock in the corrected
    behavior.
    """

    @pytest.mark.asyncio()
    async def test_send_estimate_without_doc_now_advances(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(
            SalesEntryStatus.SEND_ESTIMATE.value,
            signwell_document_id=None,
        )
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        updated = await pipeline_service.advance_status(mock_db, entry.id)
        assert updated.status == SalesEntryStatus.PENDING_APPROVAL.value

    @pytest.mark.asyncio()
    async def test_send_estimate_with_doc_advances(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(
            SalesEntryStatus.SEND_ESTIMATE.value,
            signwell_document_id="doc-xyz",
        )
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        result = await pipeline_service.advance_status(mock_db, entry.id)
        assert result.status == SalesEntryStatus.PENDING_APPROVAL.value


@pytest.mark.unit()
class TestSalesPipelineTerminalStates:
    """Terminal states cannot be advanced."""

    @pytest.mark.asyncio()
    async def test_advance_closed_won_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.CLOSED_WON.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        with pytest.raises(InvalidSalesTransitionError):
            await pipeline_service.advance_status(mock_db, entry.id)

    @pytest.mark.asyncio()
    async def test_advance_closed_lost_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.CLOSED_LOST.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        with pytest.raises(InvalidSalesTransitionError):
            await pipeline_service.advance_status(mock_db, entry.id)


@pytest.mark.unit()
class TestSalesPipelineNotFound:
    @pytest.mark.asyncio()
    async def test_advance_nonexistent_entry_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None)),
        )
        with pytest.raises(SalesEntryNotFoundError):
            await pipeline_service.advance_status(mock_db, uuid4())


# ===================================================================
# SalesPipelineService — Convert to Job
# ===================================================================


@pytest.mark.unit()
class TestSalesPipelineConvertToJob:
    """Test convert_to_job with and without signature."""

    @pytest.mark.asyncio()
    async def test_convert_with_signature_succeeds(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        entry = _make_entry(
            SalesEntryStatus.SEND_CONTRACT.value,
            signwell_document_id="doc-123",
        )
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        mock_job = Mock(id=uuid4())
        mock_job_service.create_job.return_value = mock_job

        result = await pipeline_service.convert_to_job(mock_db, entry.id)

        # convert_to_job returns (job, ...) or job depending on impl
        job = result[0] if isinstance(result, tuple) else result
        assert job.id == mock_job.id
        assert entry.status == SalesEntryStatus.CLOSED_WON.value
        assert entry.override_flag is False

    @pytest.mark.asyncio()
    async def test_convert_without_signature_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.SEND_CONTRACT.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        with pytest.raises(SignatureRequiredError):
            await pipeline_service.convert_to_job(mock_db, entry.id)

    @pytest.mark.asyncio()
    async def test_force_convert_without_signature(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
        mock_job_service: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.SEND_CONTRACT.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        mock_job = Mock(id=uuid4())
        mock_job_service.create_job.return_value = mock_job

        result = await pipeline_service.convert_to_job(
            mock_db,
            entry.id,
            force=True,
            actor_id=uuid4(),
        )

        job = result[0] if isinstance(result, tuple) else result
        assert job.id == mock_job.id
        assert entry.status == SalesEntryStatus.CLOSED_WON.value
        assert entry.override_flag is True
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio()
    async def test_convert_terminal_entry_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.CLOSED_WON.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        with pytest.raises(InvalidSalesTransitionError):
            await pipeline_service.convert_to_job(mock_db, entry.id)


# ===================================================================
# SalesPipelineService — Mark Lost
# ===================================================================


@pytest.mark.unit()
class TestSalesPipelineMarkLost:
    @pytest.mark.asyncio()
    async def test_mark_lost_from_active_status(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.PENDING_APPROVAL.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )

        result = await pipeline_service.mark_lost(
            mock_db,
            entry.id,
            closed_reason="Customer unresponsive",
        )

        assert result.status == SalesEntryStatus.CLOSED_LOST.value
        assert result.closed_reason == "Customer unresponsive"

    @pytest.mark.asyncio()
    async def test_mark_lost_from_terminal_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.CLOSED_WON.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        with pytest.raises(InvalidSalesTransitionError):
            await pipeline_service.mark_lost(mock_db, entry.id)


# ===================================================================
# SalesPipelineService — Manual Override
# ===================================================================


@pytest.mark.unit()
class TestSalesPipelineManualOverride:
    @pytest.mark.asyncio()
    async def test_override_sets_any_status(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        entry = _make_entry(SalesEntryStatus.SCHEDULE_ESTIMATE.value)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )

        result = await pipeline_service.manual_override_status(
            mock_db,
            entry.id,
            SalesEntryStatus.SEND_CONTRACT,
        )

        assert result.status == SalesEntryStatus.SEND_CONTRACT.value
        mock_audit_service.log_action.assert_called_once()


# ===================================================================
# SignWellClient — HTTP calls (mocked httpx)
# ===================================================================


@pytest.fixture()
def signwell_settings() -> SignWellSettings:
    return SignWellSettings(
        signwell_api_key="test-key",
        signwell_webhook_secret="test-secret",
        signwell_api_base_url="https://api.signwell.test/api/v1",
    )


@pytest.fixture()
def signwell_client(signwell_settings: SignWellSettings) -> SignWellClient:
    return SignWellClient(settings=signwell_settings)


@pytest.mark.unit()
class TestSignWellClientCreateDocumentEmail:
    @pytest.mark.asyncio()
    async def test_create_document_for_email(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        mock_response = httpx.Response(
            200,
            json={"id": "doc-abc", "status": "pending"},
        )
        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await signwell_client.create_document_for_email(
                "https://example.com/contract.pdf",
                "<email>",
                "Test User",
            )
        assert result["id"] == "doc-abc"

    @pytest.mark.asyncio()
    async def test_create_document_api_error(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        mock_response = httpx.Response(500, text="Internal Server Error")
        with (
            patch("httpx.AsyncClient.request", return_value=mock_response),
            pytest.raises(SignWellError),
        ):
            await signwell_client.create_document_for_email(
                "https://example.com/contract.pdf",
                "<email>",
                "Test User",
            )


@pytest.mark.unit()
class TestSignWellClientCreateDocumentEmbedded:
    @pytest.mark.asyncio()
    async def test_create_document_for_embedded(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        mock_response = httpx.Response(
            200,
            json={"id": "doc-xyz", "embedded_signing": True},
        )
        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await signwell_client.create_document_for_embedded(
                "https://example.com/contract.pdf",
                "Signer Name",
            )
        assert result["id"] == "doc-xyz"


@pytest.mark.unit()
class TestSignWellClientGetEmbeddedUrl:
    @pytest.mark.asyncio()
    async def test_get_embedded_url(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        mock_response = httpx.Response(
            200,
            json={"embedded_signing_url": "https://app.signwell.com/sign/abc"},
        )
        with patch("httpx.AsyncClient.request", return_value=mock_response):
            url = await signwell_client.get_embedded_url("doc-abc")
        assert url == "https://app.signwell.com/sign/abc"

    @pytest.mark.asyncio()
    async def test_get_embedded_url_not_found(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        mock_response = httpx.Response(404, text="Not Found")
        with (
            patch("httpx.AsyncClient.request", return_value=mock_response),
            pytest.raises(SignWellDocumentNotFoundError),
        ):
            await signwell_client.get_embedded_url("nonexistent")


@pytest.mark.unit()
class TestSignWellClientFetchSignedPdf:
    @pytest.mark.asyncio()
    async def test_fetch_signed_pdf(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        pdf_bytes = b"%PDF-1.4 fake content"
        mock_response = httpx.Response(200, content=pdf_bytes)
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await signwell_client.fetch_signed_pdf("doc-abc")
        assert result == pdf_bytes

    @pytest.mark.asyncio()
    async def test_fetch_signed_pdf_not_found(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        mock_response = httpx.Response(404, text="Not Found")
        with (
            patch("httpx.AsyncClient.get", return_value=mock_response),
            pytest.raises(SignWellDocumentNotFoundError),
        ):
            await signwell_client.fetch_signed_pdf("nonexistent")


# ===================================================================
# SignWellClient — Webhook Signature Verification
# ===================================================================


@pytest.mark.unit()
class TestSignWellWebhookVerification:
    def test_valid_signature_returns_true(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        payload = b'{"event":"document_completed"}'
        expected_sig = hmac_mod.new(
            b"test-secret",
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert signwell_client.verify_webhook_signature(payload, expected_sig) is True

    def test_invalid_signature_raises(
        self,
        signwell_client: SignWellClient,
    ) -> None:
        payload = b'{"event":"document_completed"}'
        with pytest.raises(SignWellWebhookVerificationError):
            signwell_client.verify_webhook_signature(payload, "bad-signature")

    def test_missing_secret_raises(self) -> None:
        client = SignWellClient(
            settings=SignWellSettings(
                signwell_api_key="key",
                signwell_webhook_secret="",
                signwell_api_base_url="https://api.signwell.test/api/v1",
            ),
        )
        with pytest.raises(SignWellWebhookVerificationError):
            client.verify_webhook_signature(b"payload", "sig")
