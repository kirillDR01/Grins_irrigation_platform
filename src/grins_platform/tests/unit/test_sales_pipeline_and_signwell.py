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

from grins_platform.api.v1.sales_pipeline import _entry_to_response
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
    nudges_paused_until: datetime | None = None,
    dismissed_at: datetime | None = None,
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
    entry.nudges_paused_until = nudges_paused_until
    entry.dismissed_at = dismissed_at
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


# ===================================================================
# _entry_to_response — denormalized customer_email field
# ===================================================================


def _make_response_entry_mock(
    *,
    customer: Mock | None,
    job_type: str | None = "spring_startup",
    nudges_paused_until: datetime | None = None,
    dismissed_at: datetime | None = None,
) -> Mock:
    entry = Mock()
    entry.id = uuid4()
    entry.customer_id = uuid4() if customer is None else customer.id
    entry.property_id = None
    entry.lead_id = None
    entry.job_type = job_type
    entry.status = SalesEntryStatus.SCHEDULE_ESTIMATE.value
    entry.last_contact_date = None
    entry.notes = None
    entry.override_flag = False
    entry.closed_reason = None
    entry.signwell_document_id = None
    entry.nudges_paused_until = nudges_paused_until
    entry.dismissed_at = dismissed_at
    entry.created_at = datetime.now(tz=timezone.utc)
    entry.updated_at = datetime.now(tz=timezone.utc)
    entry.customer = customer
    entry.property = None
    # Denormalized response fields must be plain values so Pydantic's
    # from_attributes loader doesn't pick up MagicMock proxies.
    entry.customer_name = None
    entry.customer_phone = None
    entry.customer_email = None
    entry.customer_internal_notes = None
    entry.property_address = None
    entry.job_type_display = None
    return entry


def _make_customer_mock(*, email: str | None) -> Mock:
    customer = Mock()
    customer.id = uuid4()
    customer.first_name = "Jane"
    customer.last_name = "Doe"
    customer.phone = "5551234567"
    customer.email = email
    customer.internal_notes = None
    return customer


@pytest.mark.unit()
class TestEntryToResponseCustomerEmail:
    """Verify _entry_to_response denormalizes customer.email onto the response."""

    def test_customer_email_populated_when_present(self) -> None:
        customer = _make_customer_mock(email="jane@example.com")
        entry = _make_response_entry_mock(customer=customer)

        resp = _entry_to_response(entry)

        assert resp.customer_email == "jane@example.com"
        assert resp.customer_name == "Jane Doe"
        assert resp.customer_phone == "5551234567"

    def test_customer_email_none_when_customer_email_null(self) -> None:
        customer = _make_customer_mock(email=None)
        entry = _make_response_entry_mock(customer=customer)

        resp = _entry_to_response(entry)

        assert resp.customer_email is None

    def test_customer_email_none_when_customer_missing(self) -> None:
        entry = _make_response_entry_mock(customer=None)

        resp = _entry_to_response(entry)

        assert resp.customer_email is None
        assert resp.customer_name is None
        assert resp.customer_phone is None


# ===================================================================
# NEW-D — pause/unpause nudges
# ===================================================================


@pytest.mark.unit()
class TestPauseUnpauseNudges:
    """``pause_nudges`` / ``unpause_nudges`` set/clear ``nudges_paused_until``."""

    @pytest.mark.asyncio()
    async def test_pause_sets_default_seven_day_window(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry()
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )

        result = await pipeline_service.pause_nudges(mock_db, entry.id)

        assert result is entry
        assert entry.nudges_paused_until is not None
        delta = entry.nudges_paused_until - datetime.now(tz=timezone.utc)
        # Default pause window is 7 days; allow generous slack for slow CI.
        assert 6 <= delta.days <= 7

    @pytest.mark.asyncio()
    async def test_pause_with_explicit_paused_until(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry()
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        target = datetime(2026, 6, 1, tzinfo=timezone.utc)

        result = await pipeline_service.pause_nudges(
            mock_db,
            entry.id,
            paused_until=target,
        )

        assert result.nudges_paused_until == target

    @pytest.mark.asyncio()
    async def test_unpause_clears_window(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry(
            nudges_paused_until=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )

        result = await pipeline_service.unpause_nudges(mock_db, entry.id)

        assert result.nudges_paused_until is None

    @pytest.mark.asyncio()
    async def test_pause_missing_entry_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None)),
        )
        with pytest.raises(SalesEntryNotFoundError):
            await pipeline_service.pause_nudges(mock_db, uuid4())


# ===================================================================
# NEW-D — send_text_confirmation
# ===================================================================


@pytest.mark.unit()
class TestSendTextConfirmation:
    """``send_text_confirmation`` delegates to ``SMSService.send_message``."""

    @pytest.mark.asyncio()
    async def test_delegates_to_sms_service(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry()
        customer = Mock()
        customer.id = entry.customer_id
        customer.first_name = "Jane"
        customer.last_name = "Doe"
        customer.phone = "+15551234567"
        customer.email = "jane@example.com"
        # Two execute calls: first returns entry, second returns customer.
        mock_db.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=entry)),
                Mock(scalar_one_or_none=Mock(return_value=customer)),
            ],
        )
        sms_service = AsyncMock()
        sms_service.send_message = AsyncMock(
            return_value={"message_id": "m-123", "status": "sent"},
        )

        result = await pipeline_service.send_text_confirmation(
            mock_db,
            entry.id,
            sms_service=sms_service,
        )

        sms_service.send_message.assert_called_once()
        recipient_arg = sms_service.send_message.call_args.args[0]
        assert recipient_arg.phone == customer.phone
        assert recipient_arg.customer_id == customer.id
        assert result == {"message_id": "m-123", "status": "sent"}

    @pytest.mark.asyncio()
    async def test_missing_phone_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        from grins_platform.exceptions import CustomerHasNoPhoneError

        entry = _make_entry()
        customer = Mock()
        customer.id = entry.customer_id
        customer.first_name = "Jane"
        customer.last_name = "Doe"
        customer.phone = None
        mock_db.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=entry)),
                Mock(scalar_one_or_none=Mock(return_value=customer)),
            ],
        )
        sms_service = AsyncMock()

        with pytest.raises(CustomerHasNoPhoneError):
            await pipeline_service.send_text_confirmation(
                mock_db,
                entry.id,
                sms_service=sms_service,
            )
        sms_service.send_message.assert_not_called()


# ===================================================================
# NEW-D — dismiss_entry
# ===================================================================


@pytest.mark.unit()
class TestDismissSalesEntry:
    """``dismiss_entry`` is idempotent: second call leaves timestamp untouched."""

    @pytest.mark.asyncio()
    async def test_first_dismiss_sets_timestamp(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        entry = _make_entry()
        assert entry.dismissed_at is None
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )

        result = await pipeline_service.dismiss_entry(mock_db, entry.id)

        assert result.dismissed_at is not None

    @pytest.mark.asyncio()
    async def test_second_dismiss_is_idempotent(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        original_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entry = _make_entry(dismissed_at=original_ts)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )

        result = await pipeline_service.dismiss_entry(mock_db, entry.id)

        assert result.dismissed_at == original_ts

    @pytest.mark.asyncio()
    async def test_dismiss_missing_entry_raises(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None)),
        )
        with pytest.raises(SalesEntryNotFoundError):
            await pipeline_service.dismiss_entry(mock_db, uuid4())


# ===================================================================
# _entry_to_response — NEW-D nudges_paused_until + dismissed_at
# ===================================================================


@pytest.mark.unit()
class TestEntryToResponseExposesNewFields:
    """``_entry_to_response`` round-trips ``nudges_paused_until`` and
    ``dismissed_at`` from the SQLAlchemy model onto the Pydantic response."""

    def test_nudges_paused_until_populated(self) -> None:
        target = datetime(2026, 5, 1, tzinfo=timezone.utc)
        customer = _make_customer_mock(email=None)
        entry = _make_response_entry_mock(
            customer=customer,
            nudges_paused_until=target,
        )

        resp = _entry_to_response(entry)

        assert resp.nudges_paused_until == target

    def test_dismissed_at_populated(self) -> None:
        target = datetime(2026, 5, 1, tzinfo=timezone.utc)
        customer = _make_customer_mock(email=None)
        entry = _make_response_entry_mock(
            customer=customer,
            dismissed_at=target,
        )

        resp = _entry_to_response(entry)

        assert resp.dismissed_at == target

    def test_defaults_none_when_unset(self) -> None:
        customer = _make_customer_mock(email=None)
        entry = _make_response_entry_mock(customer=customer)

        resp = _entry_to_response(entry)

        assert resp.nudges_paused_until is None
        assert resp.dismissed_at is None


# ===================================================================
# CustomerDocumentResponse — sales_entry_id round-trip (Bug #9)
# ===================================================================


@pytest.mark.unit()
class TestCustomerDocumentResponseExposesSalesEntryId:
    """Bug #9: response schema must surface the column so the frontend
    can scope ``hasSignedAgreement`` to the right entry."""

    def test_sales_entry_id_round_trip(self) -> None:
        from grins_platform.schemas.customer_document import (
            CustomerDocumentResponse,
        )

        sales_entry_id = uuid4()
        doc = Mock()
        doc.id = uuid4()
        doc.customer_id = uuid4()
        doc.sales_entry_id = sales_entry_id
        doc.file_key = "k"
        doc.file_name = "f.pdf"
        doc.document_type = "contract"
        doc.mime_type = "application/pdf"
        doc.size_bytes = 1024
        doc.uploaded_at = datetime.now(tz=timezone.utc)
        doc.uploaded_by = None

        resp = CustomerDocumentResponse.model_validate(doc)
        assert resp.sales_entry_id == sales_entry_id

    def test_legacy_null_sales_entry_id_is_none(self) -> None:
        from grins_platform.schemas.customer_document import (
            CustomerDocumentResponse,
        )

        doc = Mock()
        doc.id = uuid4()
        doc.customer_id = uuid4()
        doc.sales_entry_id = None
        doc.file_key = "k"
        doc.file_name = "f.pdf"
        doc.document_type = "estimate"
        doc.mime_type = "application/pdf"
        doc.size_bytes = 1024
        doc.uploaded_at = datetime.now(tz=timezone.utc)
        doc.uploaded_by = None

        resp = CustomerDocumentResponse.model_validate(doc)
        assert resp.sales_entry_id is None
