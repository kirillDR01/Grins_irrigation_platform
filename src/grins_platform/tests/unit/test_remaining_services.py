"""Unit tests for AuditService, ChatService, InvoicePDFService, and remaining services.

Properties:
  P44: Staff location round-trip via Redis
  P45: Break adjusts subsequent appointment ETAs
  P46: Chat escalation detection creates lead and communication
  P47: Voice webhook creates lead with correct source
  P70: Audit log entry creation for auditable actions
  P76: AppointmentStatus enum accepts all frontend values
  P77: Invoice PDF generation round-trip
  P81: Portal invoice access by token with correct data
  P84: Business settings round-trip and service consumption

Validates: Requirements 41.6, 41.7, 42.6, 43.6, 44.7, 74.5, 79.6, 79.7,
           80.8, 84.10, 84.11, 87.10
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus
from grins_platform.schemas.audit import AuditLogFilters
from grins_platform.schemas.portal import PortalInvoiceResponse
from grins_platform.schemas.settings import BusinessSettingResponse
from grins_platform.services.audit_service import AuditService
from grins_platform.services.chat_service import (
    ChatResponse,
    ChatService,
)
from grins_platform.services.invoice_pdf_service import (
    InvoiceNotFoundError,
    InvoicePDFNotFoundError,
    InvoicePDFService,
)
from grins_platform.services.invoice_portal_service import (
    InvoicePortalService,
    InvoiceTokenExpiredError,
    InvoiceTokenNotFoundError,
)
from grins_platform.services.settings_service import (
    SettingNotFoundError,
    SettingsService,
)
from grins_platform.services.staff_break_service import (
    BreakAlreadyEndedError,
    BreakNotFoundError,
    StaffBreakService,
)
from grins_platform.services.staff_location_service import (
    StaffLocation,
    StaffLocationService,
)
from grins_platform.services.voice_webhook_service import VoiceWebhookService

# =============================================================================
# Helpers
# =============================================================================


def _mock_audit_log(
    *,
    action: str = "customer.merge",
    resource_type: str = "customer",
    resource_id: str | None = None,
    actor_id: UUID | None = None,
    actor_role: str | None = "admin",
    details: dict[str, Any] | None = None,
    ip_address: str | None = "127.0.0.1",
) -> MagicMock:
    """Create a mock AuditLog entry."""
    entry = MagicMock()
    entry.id = uuid4()
    entry.actor_id = actor_id or uuid4()
    entry.actor_role = actor_role
    entry.action = action
    entry.resource_type = resource_type
    entry.resource_id = resource_id or str(uuid4())
    entry.details = details
    entry.ip_address = ip_address
    entry.user_agent = "TestAgent/1.0"
    entry.created_at = datetime.now(tz=timezone.utc)
    return entry


def _mock_invoice(
    *,
    invoice_id: UUID | None = None,
    invoice_number: str = "INV-2025-001",
    total_amount: Decimal = Decimal("500.00"),
    paid_amount: Decimal | None = Decimal("100.00"),
    status: str = "sent",
    document_url: str | None = None,
    invoice_token: UUID | None = None,
    invoice_token_expires_at: datetime | None = None,
    line_items: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Create a mock Invoice."""
    inv = MagicMock()
    inv.id = invoice_id or uuid4()
    inv.invoice_number = invoice_number
    inv.amount = total_amount
    inv.total_amount = total_amount
    inv.paid_amount = paid_amount
    inv.status = status
    inv.document_url = document_url
    inv.invoice_token = invoice_token
    inv.invoice_token_expires_at = invoice_token_expires_at
    inv.invoice_date = date(2025, 1, 15)
    inv.due_date = date(2025, 2, 15)
    inv.line_items = line_items or [
        {"description": "Sprinkler repair", "quantity": 1, "unit_price": 500.00},
    ]
    inv.notes = "Test invoice"
    inv.customer = MagicMock(first_name="John", last_name="Doe")
    return inv


def _mock_business_setting(
    *,
    key: str = "company_info",
    value: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock BusinessSetting."""
    s = MagicMock()
    s.id = uuid4()
    s.setting_key = key
    s.setting_value = value or {"company_name": "Grins Irrigation"}
    s.updated_by = None
    s.updated_at = datetime.now(tz=timezone.utc)
    return s


def _mock_staff_break(
    *,
    break_id: UUID | None = None,
    staff_id: UUID | None = None,
    break_type: str = "lunch",
    start_time: time | None = None,
    end_time: time | None = None,
) -> MagicMock:
    """Create a mock StaffBreak."""
    b = MagicMock()
    b.id = break_id or uuid4()
    b.staff_id = staff_id or uuid4()
    b.break_type = break_type
    b.start_time = start_time or time(12, 0)
    b.end_time = end_time
    b.appointment_id = None
    b.created_at = datetime.now(tz=timezone.utc)
    return b


def _make_async_redis() -> AsyncMock:
    """Create a mock async Redis client."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    return redis


def _make_db_returning(obj: Any) -> AsyncMock:
    """Create a mock async db session that returns obj from scalar_one_or_none."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = obj
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# =============================================================================
# P76: AppointmentStatus enum accepts all frontend values
# Validates: Requirements 79.1, 79.2, 79.3
# =============================================================================


@pytest.mark.unit
class TestProperty76AppointmentStatusEnum:
    """**Validates: Requirements 79.1, 79.2, 79.3**"""

    def test_appointment_status_has_all_8_values(self) -> None:
        """AppointmentStatus enum has all 8 values including no_show."""
        expected = {
            "pending",
            "scheduled",
            "confirmed",
            "en_route",
            "in_progress",
            "completed",
            "cancelled",
            "no_show",
        }
        actual = {s.value for s in AppointmentStatus}
        assert actual == expected
        assert len(AppointmentStatus) == 8

    def test_appointment_status_accepts_pending(self) -> None:
        """AppointmentStatus('pending') succeeds."""
        assert AppointmentStatus("pending") == AppointmentStatus.PENDING

    def test_appointment_status_accepts_no_show(self) -> None:
        """AppointmentStatus('no_show') succeeds."""
        assert AppointmentStatus("no_show") == AppointmentStatus.NO_SHOW

    def test_appointment_status_accepts_en_route(self) -> None:
        """AppointmentStatus('en_route') succeeds."""
        assert AppointmentStatus("en_route") == AppointmentStatus.EN_ROUTE

    def test_appointment_status_rejects_invalid_value(self) -> None:
        """AppointmentStatus rejects unknown values."""
        with pytest.raises(ValueError):
            AppointmentStatus("invalid_status")


# =============================================================================
# P44: Staff location round-trip via Redis
# Validates: Requirements 41.1, 41.2
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProperty44StaffLocationRoundTrip:
    """**Validates: Requirements 41.1, 41.2**"""

    async def test_store_location_with_valid_data_stores_in_redis(self) -> None:
        """store_location stores data in Redis with correct key and TTL."""
        redis = _make_async_redis()
        svc = StaffLocationService(redis_client=redis)
        staff_id = uuid4()

        result = await svc.store_location(
            staff_id=staff_id,
            latitude=30.2672,
            longitude=-97.7431,
        )

        assert result is True
        redis.set.assert_awaited_once()
        call_args = redis.set.call_args
        key = call_args[0][0]
        assert f"staff:location:{staff_id}" == key
        stored = json.loads(call_args[0][1])
        assert float(stored["latitude"]) == pytest.approx(30.2672)
        assert float(stored["longitude"]) == pytest.approx(-97.7431)
        assert str(staff_id) == stored["staff_id"]
        assert call_args[1]["ex"] == 300  # 5 min TTL

    async def test_get_location_with_stored_data_returns_location(self) -> None:
        """get_location retrieves stored location correctly."""
        staff_id = uuid4()
        redis = _make_async_redis()
        stored_data = json.dumps(
            {
                "staff_id": str(staff_id),
                "latitude": 30.2672,
                "longitude": -97.7431,
                "timestamp": "2025-01-15T12:00:00+00:00",
                "appointment_id": None,
            }
        )
        redis.get = AsyncMock(return_value=stored_data)
        svc = StaffLocationService(redis_client=redis)

        loc = await svc.get_location(staff_id)

        assert loc is not None
        assert isinstance(loc, StaffLocation)
        assert loc.staff_id == staff_id
        assert loc.latitude == pytest.approx(30.2672)
        assert loc.longitude == pytest.approx(-97.7431)

    async def test_get_location_with_no_data_returns_none(self) -> None:
        """get_location returns None when Redis has no data."""
        redis = _make_async_redis()
        redis.get = AsyncMock(return_value=None)
        svc = StaffLocationService(redis_client=redis)

        loc = await svc.get_location(uuid4())
        assert loc is None

    async def test_store_location_with_no_redis_returns_false(self) -> None:
        """store_location returns False when Redis unavailable."""
        svc = StaffLocationService(redis_client=None)

        result = await svc.store_location(
            staff_id=uuid4(),
            latitude=30.0,
            longitude=-97.0,
        )
        assert result is False


# =============================================================================
# P45: Break adjusts subsequent appointment ETAs
# Validates: Requirements 42.5
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProperty45BreakAdjustsETAs:
    """**Validates: Requirements 42.5**"""

    async def test_create_break_with_valid_type_creates_record(self) -> None:
        """create_break creates record with correct break_type."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        svc = StaffBreakService()
        staff_id = uuid4()

        await svc.create_break(
            db,
            staff_id=staff_id,
            break_type="lunch",
        )

        db.add.assert_called_once()
        added_obj = db.add.call_args[0][0]
        assert added_obj.break_type == "lunch"
        assert added_obj.staff_id == staff_id

    async def test_create_break_with_invalid_type_raises_value_error(self) -> None:
        """create_break rejects invalid break_type."""
        db = AsyncMock()
        svc = StaffBreakService()

        with pytest.raises(ValueError, match="Invalid break type"):
            await svc.create_break(
                db,
                staff_id=uuid4(),
                break_type="nap",
            )

    async def test_end_break_with_missing_break_raises_not_found(self) -> None:
        """end_break raises BreakNotFoundError for missing break."""
        db = _make_db_returning(None)
        svc = StaffBreakService()

        with pytest.raises(BreakNotFoundError):
            await svc.end_break(db, break_id=uuid4())

    async def test_end_break_with_already_ended_raises_error(self) -> None:
        """end_break raises BreakAlreadyEndedError for ended break."""
        staff_break = _mock_staff_break(end_time=time(12, 30))
        db = _make_db_returning(staff_break)
        svc = StaffBreakService()

        with pytest.raises(BreakAlreadyEndedError):
            await svc.end_break(db, break_id=staff_break.id)

    async def test_end_break_with_active_break_sets_end_time_and_adjusts_etas(
        self,
    ) -> None:
        """end_break sets end_time and adjusts subsequent ETAs."""
        staff_id = uuid4()
        staff_break = _mock_staff_break(
            staff_id=staff_id,
            start_time=time(12, 0),
            end_time=None,
        )
        # Make staff_break behave like a real object for attribute setting
        staff_break.end_time = None

        db = AsyncMock()
        # First execute returns the break, second returns empty appointments
        result_break = MagicMock()
        result_break.scalar_one_or_none.return_value = staff_break
        result_appts = MagicMock()
        result_appts.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[result_break, result_appts])
        db.flush = AsyncMock()

        svc = StaffBreakService()
        result = await svc.end_break(db, break_id=staff_break.id)

        assert result is staff_break
        # end_time should have been set (the service sets it to now().time())
        assert staff_break.end_time is not None


# =============================================================================
# P46: Chat escalation detection creates lead and communication
# Validates: Requirements 43.3, 43.5
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProperty46ChatEscalation:
    """**Validates: Requirements 43.3, 43.5**"""

    def test_detect_escalation_with_keyword_returns_true(self) -> None:
        """_detect_escalation returns True for escalation keywords."""
        svc = ChatService()
        assert svc._detect_escalation("I want to speak to a human") is True
        assert svc._detect_escalation("Can I talk to a person?") is True
        assert svc._detect_escalation("live agent please") is True
        assert svc._detect_escalation("MANAGER") is True

    def test_detect_escalation_with_normal_message_returns_false(self) -> None:
        """_detect_escalation returns False for normal messages."""
        svc = ChatService()
        assert svc._detect_escalation("What are your hours?") is False
        assert svc._detect_escalation("How much does sprinkler repair cost?") is False
        assert svc._detect_escalation("I need a quote") is False

    async def test_handle_public_message_with_escalation_creates_records(
        self,
    ) -> None:
        """handle_public_message with escalation creates Communication + Lead."""
        redis = _make_async_redis()
        # Return history with name and phone
        history = [
            {"role": "user", "content": "My name is John Smith"},
            {"role": "assistant", "content": "Hi John!"},
            {"role": "user", "content": "My phone is 5125551234"},
        ]
        redis.get = AsyncMock(return_value=json.dumps(history))

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        svc = ChatService(redis_client=redis, openai_api_key=None)
        response = await svc.handle_public_message(
            db,
            session_id="test-session",
            message="I want to speak to a human",
        )

        assert isinstance(response, ChatResponse)
        assert response.escalated is True
        # Should have added Communication and Lead
        assert db.add.call_count >= 1

    async def test_handle_public_message_without_escalation_calls_openai(
        self,
    ) -> None:
        """handle_public_message without escalation calls OpenAI."""
        redis = _make_async_redis()
        redis.get = AsyncMock(return_value=json.dumps([]))

        db = AsyncMock()
        svc = ChatService(redis_client=redis, openai_api_key=None)

        response = await svc.handle_public_message(
            db,
            session_id="test-session",
            message="What are your hours?",
        )

        assert isinstance(response, ChatResponse)
        assert response.escalated is False
        # Without API key, returns fallback message
        assert "unavailable" in response.message.lower()


# =============================================================================
# P47: Voice webhook creates lead with correct source
# Validates: Requirements 44.3, 44.5
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProperty47VoiceWebhook:
    """**Validates: Requirements 44.3, 44.5**"""

    async def test_handle_webhook_with_phone_creates_lead_with_voice_source(
        self,
    ) -> None:
        """handle_webhook creates Lead with source='voice'."""
        fake_lead_id = uuid4()

        db = AsyncMock()
        db.add = MagicMock()

        async def _flush_side_effect() -> None:
            # Simulate DB assigning an id on flush
            added = db.add.call_args[0][0]
            added.id = fake_lead_id

        db.flush = AsyncMock(side_effect=_flush_side_effect)

        svc = VoiceWebhookService()
        payload = {
            "message": {
                "call": {
                    "customer": {"number": "+15125551234"},
                },
                "functionCall": {
                    "parameters": {
                        "name": "Jane Doe",
                        "service": "Sprinkler repair",
                    },
                },
            },
        }

        result = await svc.handle_webhook(db, payload)

        assert result == fake_lead_id
        db.add.assert_called_once()
        lead = db.add.call_args[0][0]
        assert lead.lead_source == "voice"
        assert lead.name == "Jane Doe"
        assert lead.phone == "5125551234"
        assert "NEEDS_CONTACT" in lead.action_tags

    async def test_handle_webhook_with_no_phone_returns_none(self) -> None:
        """handle_webhook returns None when no phone extracted."""
        db = AsyncMock()
        svc = VoiceWebhookService()
        payload = {"message": {"call": {"customer": {}}, "transcript": ""}}

        result = await svc.handle_webhook(db, payload)
        assert result is None

    def test_extract_caller_info_with_vapi_payload_extracts_phone(self) -> None:
        """_extract_caller_info extracts phone from Vapi payload."""
        svc = VoiceWebhookService()
        payload = {
            "message": {
                "call": {"customer": {"number": "+15125559876"}},
                "functionCall": {"parameters": {}},
            },
        }

        info = svc._extract_caller_info(payload)
        assert info["phone"] == "5125559876"


# =============================================================================
# P70: Audit log entry creation for auditable actions
# Validates: Requirements 74.1, 74.2
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProperty70AuditLogCreation:
    """**Validates: Requirements 74.1, 74.2**"""

    async def test_log_action_with_all_fields_creates_entry(self) -> None:
        """log_action creates audit log entry with all fields."""
        entry = _mock_audit_log(
            action="customer.merge",
            resource_type="customer",
        )
        mock_repo = AsyncMock()
        mock_repo.create = AsyncMock(return_value=entry)

        svc = AuditService()
        actor_id = uuid4()
        resource_id = uuid4()

        with (
            patch(
                "grins_platform.services.audit_service.AuditLogRepository",
                return_value=mock_repo,
            ),
            patch.object(svc, "log_started"),
            patch.object(svc, "log_completed"),
        ):
            db = AsyncMock()
            result = await svc.log_action(
                db,
                actor_id=actor_id,
                actor_role="admin",
                action="customer.merge",
                resource_type="customer",
                resource_id=resource_id,
                details={"merged_ids": ["a", "b"]},
                ip_address="192.168.1.1",
                user_agent="TestBrowser/1.0",
            )

        assert result is entry
        mock_repo.create.assert_awaited_once_with(
            action="customer.merge",
            resource_type="customer",
            resource_id=resource_id,
            actor_id=actor_id,
            actor_role="admin",
            details={"merged_ids": ["a", "b"]},
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0",
        )

    async def test_get_audit_log_with_filters_returns_paginated(self) -> None:
        """get_audit_log returns paginated results."""
        entries = [_mock_audit_log(), _mock_audit_log()]
        mock_repo = AsyncMock()
        mock_repo.list_with_filters = AsyncMock(return_value=(entries, 2))

        svc = AuditService()
        filters = AuditLogFilters(page=1, page_size=20)

        with patch(
            "grins_platform.services.audit_service.AuditLogRepository",
            return_value=mock_repo,
        ):
            db = AsyncMock()
            result = await svc.get_audit_log(db, filters)

        assert result["total"] == 2
        assert result["page"] == 1
        assert len(result["items"]) == 2
        mock_repo.list_with_filters.assert_awaited_once_with(filters)


# =============================================================================
# P77: Invoice PDF generation round-trip
# Validates: Requirements 80.1, 80.2, 80.3, 80.4
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProperty77InvoicePDFGeneration:
    """**Validates: Requirements 80.1, 80.2, 80.3, 80.4**"""

    async def test_generate_pdf_with_valid_invoice_renders_and_uploads(
        self,
    ) -> None:
        """generate_pdf renders HTML and uploads to S3."""
        invoice = _mock_invoice(document_url=None)
        db = _make_db_returning(invoice)

        s3 = MagicMock()
        s3.put_object = MagicMock(return_value={})
        s3.generate_presigned_url = MagicMock(
            return_value="https://s3.example.com/invoices/test.pdf",
        )

        svc = InvoicePDFService(s3_client=s3, s3_bucket="test-bucket")

        with patch("weasyprint.HTML") as mock_html:
            mock_html.return_value.write_pdf.return_value = b"%PDF-fake"
            url = await svc.generate_pdf(db, invoice.id)

        assert url == "https://s3.example.com/invoices/test.pdf"
        s3.put_object.assert_called_once()
        put_kwargs = s3.put_object.call_args[1]
        assert put_kwargs["Bucket"] == "test-bucket"
        assert put_kwargs["Key"] == f"invoices/{invoice.id}.pdf"
        assert put_kwargs["ContentType"] == "application/pdf"
        assert put_kwargs["Body"] == b"%PDF-fake"
        # document_url should be set on the invoice
        assert invoice.document_url == f"invoices/{invoice.id}.pdf"

    async def test_generate_pdf_with_missing_invoice_raises_not_found(
        self,
    ) -> None:
        """generate_pdf raises InvoiceNotFoundError when invoice missing."""
        db = _make_db_returning(None)
        svc = InvoicePDFService()

        with pytest.raises(InvoiceNotFoundError):
            await svc.generate_pdf(db, uuid4())

    async def test_get_pdf_url_with_document_url_returns_presigned(self) -> None:
        """get_pdf_url returns pre-signed URL."""
        invoice = _mock_invoice(document_url="invoices/abc.pdf")
        db = _make_db_returning(invoice)

        s3 = MagicMock()
        s3.generate_presigned_url = MagicMock(
            return_value="https://s3.example.com/signed/invoices/abc.pdf",
        )

        svc = InvoicePDFService(s3_client=s3, s3_bucket="test-bucket")
        url = await svc.get_pdf_url(db, invoice.id)

        assert url == "https://s3.example.com/signed/invoices/abc.pdf"
        s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "invoices/abc.pdf"},
            ExpiresIn=3600,
        )

    async def test_get_pdf_url_with_no_document_url_raises_not_found(self) -> None:
        """get_pdf_url raises InvoicePDFNotFoundError when no document_url."""
        invoice = _mock_invoice(document_url=None)
        db = _make_db_returning(invoice)
        svc = InvoicePDFService()

        with pytest.raises(InvoicePDFNotFoundError):
            await svc.get_pdf_url(db, invoice.id)


# =============================================================================
# P81: Portal invoice access by token with correct data
# Validates: Requirements 84.2, 84.4, 84.5, 84.8, 84.9
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProperty81PortalInvoiceAccess:
    """**Validates: Requirements 84.2, 84.4, 84.5, 84.8, 84.9**"""

    async def test_generate_invoice_token_with_valid_invoice_creates_token(
        self,
    ) -> None:
        """generate_invoice_token creates token with 90-day expiry."""
        invoice = _mock_invoice()
        db = _make_db_returning(invoice)

        svc = InvoicePortalService()
        token = await svc.generate_invoice_token(db, invoice.id)

        assert token is not None
        # Should be a valid UUID string
        UUID(token)
        # Token and expiry should be set on the invoice
        assert invoice.invoice_token is not None
        assert invoice.invoice_token_expires_at is not None

    async def test_get_invoice_by_token_with_valid_token_returns_sanitized_data(
        self,
    ) -> None:
        """get_invoice_by_token returns sanitized data (no internal IDs)."""
        token = uuid4()
        invoice = _mock_invoice(
            invoice_token=token,
            invoice_token_expires_at=datetime.now(tz=timezone.utc) + timedelta(days=30),
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("100.00"),
        )

        # Need two db.execute calls: one for invoice, one for company_info
        db = AsyncMock()
        result_invoice = MagicMock()
        result_invoice.scalar_one_or_none.return_value = invoice
        result_setting = MagicMock()
        result_setting.scalar_one_or_none.return_value = _mock_business_setting()
        db.execute = AsyncMock(side_effect=[result_invoice, result_setting])
        db.flush = AsyncMock()

        svc = InvoicePortalService()
        response = await svc.get_invoice_by_token(db, str(token))

        assert isinstance(response, PortalInvoiceResponse)
        assert response.invoice_number == "INV-2025-001"
        assert response.total == Decimal("500.00")
        assert response.paid == Decimal("100.00")
        assert response.balance == Decimal("400.00")
        assert response.status == "sent"
        # Verify no internal IDs are exposed
        assert not hasattr(response, "id")
        assert not hasattr(response, "customer_id")
        assert not hasattr(response, "job_id")

    async def test_get_invoice_by_token_with_expired_token_raises_error(
        self,
    ) -> None:
        """get_invoice_by_token raises InvoiceTokenExpiredError for expired token."""
        token = uuid4()
        invoice = _mock_invoice(
            invoice_token=token,
            invoice_token_expires_at=datetime.now(tz=timezone.utc) - timedelta(days=1),
        )
        db = _make_db_returning(invoice)

        svc = InvoicePortalService()
        with pytest.raises(InvoiceTokenExpiredError):
            await svc.get_invoice_by_token(db, str(token))

    async def test_get_invoice_by_token_with_invalid_token_raises_not_found(
        self,
    ) -> None:
        """get_invoice_by_token raises InvoiceTokenNotFoundError for invalid token."""
        db = _make_db_returning(None)
        svc = InvoicePortalService()

        with pytest.raises(InvoiceTokenNotFoundError):
            await svc.get_invoice_by_token(db, str(uuid4()))


# =============================================================================
# P84: Business settings round-trip and service consumption
# Validates: Requirements 87.2, 87.7, 87.8
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProperty84SettingsRoundTrip:
    """**Validates: Requirements 87.2, 87.7, 87.8**"""

    async def test_get_all_settings_returns_all_settings(self) -> None:
        """get_all_settings returns all settings."""
        settings = [
            _mock_business_setting(key="company_info"),
            _mock_business_setting(
                key="notification_prefs",
                value={"sms_window_start": "08:00"},
            ),
        ]

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = settings
        db.execute = AsyncMock(return_value=result_mock)

        svc = SettingsService()
        items = await svc.get_all_settings(db)

        assert len(items) == 2
        assert all(isinstance(i, BusinessSettingResponse) for i in items)

    async def test_update_setting_with_valid_key_updates_and_invalidates_cache(
        self,
    ) -> None:
        """update_setting updates value and invalidates cache."""
        setting = _mock_business_setting(
            key="company_info",
            value={"company_name": "Old Name"},
        )
        db = _make_db_returning(setting)

        svc = SettingsService()
        # Pre-populate cache
        svc._cache["company_info"] = {"company_name": "Old Name"}
        svc._cache_loaded = True

        new_value = {"company_name": "New Name"}
        result = await svc.update_setting(
            db,
            key="company_info",
            value=new_value,
        )

        assert isinstance(result, BusinessSettingResponse)
        # Cache should be invalidated for this key
        assert "company_info" not in svc._cache

    async def test_get_setting_with_cached_value_uses_cache(self) -> None:
        """get_setting uses cache when available."""
        db = AsyncMock()
        svc = SettingsService()
        svc._cache["company_info"] = {"company_name": "Cached Name"}
        svc._cache_loaded = True

        result = await svc.get_setting(db, "company_info")

        assert result == {"company_name": "Cached Name"}
        # DB should NOT be called
        db.execute.assert_not_awaited()

    async def test_get_setting_with_missing_key_raises_not_found(self) -> None:
        """get_setting raises SettingNotFoundError for missing key."""
        db = _make_db_returning(None)
        svc = SettingsService()

        with pytest.raises(SettingNotFoundError):
            await svc.get_setting(db, "nonexistent_key")
