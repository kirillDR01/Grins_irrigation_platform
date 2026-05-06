"""Unit tests for AppointmentTimelineService.

Validates: Gap 11.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import AppointmentNotFoundError
from grins_platform.schemas.appointment_timeline import TimelineEventKind
from grins_platform.services.appointment_timeline_service import (
    AppointmentTimelineService,
)


def _make_appointment(**overrides: Any) -> MagicMock:
    appt = MagicMock()
    appt.id = overrides.get("id", uuid4())
    appt.job_id = overrides.get("job_id", uuid4())
    appt.needs_review_reason = overrides.get("needs_review_reason")
    return appt


def _make_sent_message(**overrides: Any) -> MagicMock:
    msg = MagicMock()
    msg.id = overrides.get("id", uuid4())
    msg.customer_id = overrides.get("customer_id", uuid4())
    msg.lead_id = overrides.get("lead_id")
    msg.job_id = overrides.get("job_id", uuid4())
    msg.appointment_id = overrides.get("appointment_id", uuid4())
    msg.message_type = overrides.get("message_type", "appointment_confirmation")
    msg.message_content = overrides.get("message_content", "body")
    # SentMessageResponse accepts both "content" and "message_content" via
    # AliasChoices; clear the auto-child so Pydantic reads the string alias.
    msg.content = overrides.get("message_content", "body")
    msg.recipient_phone = overrides.get("recipient_phone", "+15125550000")
    msg.recipient_name = overrides.get("recipient_name", "Jane Doe")
    msg.delivery_status = overrides.get("delivery_status", "delivered")
    msg.error_message = overrides.get("error_message")
    msg.sent_at = overrides.get("sent_at", datetime.now(tz=timezone.utc))
    msg.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    msg.customer = overrides.get("customer")
    msg.lead = overrides.get("lead")
    return msg


def _make_inbound(**overrides: Any) -> MagicMock:
    row = MagicMock()
    row.id = overrides.get("id", uuid4())
    row.job_id = overrides.get("job_id", uuid4())
    row.appointment_id = overrides.get("appointment_id", uuid4())
    # Polymorphic FK (migration 20260509_120000): default to None on the
    # appointment-side fixture so the schema validation passes.
    row.sales_calendar_event_id = overrides.get("sales_calendar_event_id")
    row.sent_message_id = overrides.get("sent_message_id")
    row.customer_id = overrides.get("customer_id", uuid4())
    row.from_phone = overrides.get("from_phone", "+15125550000")
    row.reply_keyword = overrides.get("reply_keyword", "confirm")
    row.raw_reply_body = overrides.get("raw_reply_body", "Y")
    row.provider_sid = overrides.get("provider_sid")
    row.status = overrides.get("status", "processed")
    row.received_at = overrides.get("received_at", datetime.now(tz=timezone.utc))
    row.processed_at = overrides.get("processed_at")
    return row


def _make_reschedule(**overrides: Any) -> MagicMock:
    row = MagicMock()
    row.id = overrides.get("id", uuid4())
    row.job_id = overrides.get("job_id", uuid4())
    row.appointment_id = overrides.get("appointment_id", uuid4())
    row.sales_calendar_event_id = overrides.get("sales_calendar_event_id")
    row.customer_id = overrides.get("customer_id", uuid4())
    row.original_reply_id = overrides.get("original_reply_id")
    row.requested_alternatives = overrides.get("requested_alternatives")
    row.raw_alternatives_text = overrides.get("raw_alternatives_text", "Tuesday at 3")
    row.status = overrides.get("status", "open")
    row.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    row.resolved_at = overrides.get("resolved_at")
    return row


def _make_consent(**overrides: Any) -> MagicMock:
    row = MagicMock()
    row.id = overrides.get("id", uuid4())
    row.customer_id = overrides.get("customer_id", uuid4())
    row.phone_number = overrides.get("phone_number", "+15125550000")
    row.consent_given = overrides.get("consent_given", True)
    row.consent_timestamp = overrides.get(
        "consent_timestamp",
        datetime.now(tz=timezone.utc),
    )
    row.consent_method = overrides.get("consent_method", "web_form")
    row.opt_out_timestamp = overrides.get("opt_out_timestamp")
    row.opt_out_method = overrides.get("opt_out_method")
    row.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    return row


def _make_paid_invoice(**overrides: Any) -> MagicMock:
    inv = MagicMock()
    inv.id = overrides.get("id", uuid4())
    inv.invoice_number = overrides.get("invoice_number", "INV-2026-0001")
    inv.payment_method = overrides.get("payment_method", "cash")
    inv.payment_reference = overrides.get("payment_reference")
    from decimal import Decimal as _D  # noqa: PLC0415

    inv.paid_amount = overrides.get("paid_amount", _D("100.00"))
    inv.total_amount = overrides.get("total_amount", _D("100.00"))
    inv.paid_at = overrides.get("paid_at", datetime.now(tz=timezone.utc))
    inv.updated_at = overrides.get("updated_at", datetime.now(tz=timezone.utc))
    inv.status = overrides.get("status", "paid")
    return inv


def _build_service(
    *,
    appointment: MagicMock | None,
    customer_id: Any | None = None,
    outbound: list[MagicMock] | None = None,
    inbound: list[MagicMock] | None = None,
    reschedules: list[MagicMock] | None = None,
    consent: MagicMock | None = None,
    paid_invoices: list[MagicMock] | None = None,
) -> AppointmentTimelineService:
    """Build a service with all collaborators patched via AsyncMock."""
    session = AsyncMock()
    # Mock the Job.customer_id query on the session.
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = customer_id
    session.execute = AsyncMock(return_value=exec_result)

    service = AppointmentTimelineService(session=session)

    service.appointment_repo.get_by_id = AsyncMock(return_value=appointment)
    service.sent_message_repo.list_by_appointment = AsyncMock(
        return_value=outbound or [],
    )
    service.confirmation_service.list_responses_by_appointment = AsyncMock(
        return_value=inbound or [],
    )
    service.confirmation_service.list_reschedule_requests_by_appointment = AsyncMock(
        return_value=reschedules or [],
    )
    service.consent_repo.get_latest_for_customer = AsyncMock(return_value=consent)
    # Stub the paid-invoice lookup so the suite avoids a second SQL query
    # path through the AsyncMock session.
    service._list_paid_invoices = AsyncMock(  # type: ignore[method-assign]
        return_value=paid_invoices or [],
    )

    return service


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestAppointmentTimelineService:
    async def test_raises_when_appointment_missing(self) -> None:
        service = _build_service(appointment=None)
        with pytest.raises(AppointmentNotFoundError):
            await service.get_timeline(uuid4())

    async def test_empty_timeline_has_no_events(self) -> None:
        appt = _make_appointment()
        service = _build_service(appointment=appt, customer_id=uuid4())

        result = await service.get_timeline(appt.id)

        assert result.appointment_id == appt.id
        assert result.events == []
        assert result.pending_reschedule_request is None
        assert result.needs_review_reason is None
        assert result.opt_out is None
        assert result.last_event_at is None

    async def test_one_outbound_and_one_inbound_sorted_newest_first(self) -> None:
        appt = _make_appointment()
        now = datetime.now(tz=timezone.utc)
        outbound = _make_sent_message(sent_at=now - timedelta(hours=1))
        inbound = _make_inbound(received_at=now)

        service = _build_service(
            appointment=appt,
            customer_id=uuid4(),
            outbound=[outbound],
            inbound=[inbound],
        )

        result = await service.get_timeline(appt.id)

        assert len(result.events) == 2
        assert result.events[0].kind == TimelineEventKind.INBOUND_REPLY
        assert result.events[1].kind == TimelineEventKind.OUTBOUND_SMS
        assert result.last_event_at == result.events[0].occurred_at

    async def test_open_reschedule_populates_pending_field(self) -> None:
        appt = _make_appointment()
        rr = _make_reschedule(status="open")

        service = _build_service(
            appointment=appt,
            customer_id=uuid4(),
            reschedules=[rr],
        )

        result = await service.get_timeline(appt.id)

        assert result.pending_reschedule_request is not None
        assert result.pending_reschedule_request.id == rr.id
        # Only the opened event, not a resolved one
        assert any(e.kind == TimelineEventKind.RESCHEDULE_OPENED for e in result.events)
        assert not any(
            e.kind == TimelineEventKind.RESCHEDULE_RESOLVED for e in result.events
        )

    async def test_resolved_reschedule_emits_both_events(self) -> None:
        appt = _make_appointment()
        now = datetime.now(tz=timezone.utc)
        rr = _make_reschedule(
            status="resolved",
            created_at=now - timedelta(hours=2),
            resolved_at=now - timedelta(hours=1),
        )

        service = _build_service(
            appointment=appt,
            customer_id=uuid4(),
            reschedules=[rr],
        )

        result = await service.get_timeline(appt.id)

        kinds = [e.kind for e in result.events]
        assert TimelineEventKind.RESCHEDULE_OPENED in kinds
        assert TimelineEventKind.RESCHEDULE_RESOLVED in kinds
        assert result.pending_reschedule_request is None

    async def test_opt_out_consent_produces_state_and_event(self) -> None:
        appt = _make_appointment()
        now = datetime.now(tz=timezone.utc)
        consent = _make_consent(
            consent_given=False,
            opt_out_timestamp=now,
            opt_out_method="text_stop",
        )

        service = _build_service(
            appointment=appt,
            customer_id=uuid4(),
            consent=consent,
        )

        result = await service.get_timeline(appt.id)

        assert result.opt_out is not None
        assert result.opt_out.consent_given is False
        assert result.opt_out.method == "text_stop"
        assert any(e.kind == TimelineEventKind.OPT_OUT for e in result.events)

    async def test_needs_review_reason_is_copied_to_response(self) -> None:
        appt = _make_appointment(needs_review_reason="no_confirmation_response")
        service = _build_service(appointment=appt, customer_id=uuid4())

        result = await service.get_timeline(appt.id)

        assert result.needs_review_reason == "no_confirmation_response"

    async def test_mixed_sources_sorted_correctly(self) -> None:
        appt = _make_appointment()
        base = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
        outbound = _make_sent_message(sent_at=base)  # 10:00
        inbound = _make_inbound(received_at=base + timedelta(minutes=5))  # 10:05
        rr = _make_reschedule(
            status="open",
            created_at=base + timedelta(hours=1),
        )  # 11:00

        service = _build_service(
            appointment=appt,
            customer_id=uuid4(),
            outbound=[outbound],
            inbound=[inbound],
            reschedules=[rr],
        )

        result = await service.get_timeline(appt.id)

        kinds_in_order = [e.kind for e in result.events]
        assert kinds_in_order == [
            TimelineEventKind.RESCHEDULE_OPENED,
            TimelineEventKind.INBOUND_REPLY,
            TimelineEventKind.OUTBOUND_SMS,
        ]

    async def test_paid_invoice_emits_payment_received_event(self) -> None:
        """Phase 4.2: paid invoices on the job surface as PAYMENT_RECEIVED."""
        from decimal import Decimal as _D  # noqa: PLC0415

        appt = _make_appointment()
        now = datetime.now(tz=timezone.utc)
        inv = _make_paid_invoice(
            paid_amount=_D("125.50"),
            total_amount=_D("125.50"),
            payment_method="cash",
            invoice_number="INV-2026-0042",
            paid_at=now,
        )

        service = _build_service(
            appointment=appt,
            customer_id=uuid4(),
            paid_invoices=[inv],
        )

        result = await service.get_timeline(appt.id)

        payment_events = [
            e for e in result.events if e.kind == TimelineEventKind.PAYMENT_RECEIVED
        ]
        assert len(payment_events) == 1
        evt = payment_events[0]
        assert evt.source_id == inv.id
        assert "125.50" in evt.summary
        assert "cash" in evt.summary
        assert evt.details["invoice_number"] == "INV-2026-0042"
        assert evt.details["payment_method"] == "cash"

    async def test_multiple_paid_invoices_each_emit_event(self) -> None:
        """Phase 4.2: a job with deposit + final invoice yields two events."""
        appt = _make_appointment()
        base = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
        inv_a = _make_paid_invoice(paid_at=base)
        inv_b = _make_paid_invoice(paid_at=base + timedelta(hours=1))

        service = _build_service(
            appointment=appt,
            customer_id=uuid4(),
            paid_invoices=[inv_a, inv_b],
        )

        result = await service.get_timeline(appt.id)

        payment_events = [
            e for e in result.events if e.kind == TimelineEventKind.PAYMENT_RECEIVED
        ]
        assert len(payment_events) == 2

    async def test_skips_consent_lookup_when_no_customer(self) -> None:
        appt = _make_appointment()
        # customer_id resolves to None (job has no customer record in this test)
        service = _build_service(appointment=appt, customer_id=None)

        result = await service.get_timeline(appt.id)

        assert result.opt_out is None
        service.consent_repo.get_latest_for_customer.assert_not_called()
