"""Functional tests for AppointmentTimelineService.

Project convention (mirrors test_yrc_confirmation_functional.py): functional
tests use AsyncMock-backed DB sessions with local ``_make_*`` helpers rather
than a real DB / HTTP client. This file follows that convention.

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

# =============================================================================
# Helpers
# =============================================================================


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
    msg.lead_id = None
    msg.job_id = overrides.get("job_id", uuid4())
    msg.appointment_id = overrides.get("appointment_id", uuid4())
    msg.message_type = overrides.get("message_type", "appointment_confirmation")
    msg.message_content = overrides.get("message_content", "body")
    msg.content = overrides.get("message_content", "body")
    msg.recipient_phone = overrides.get("recipient_phone", "+15125550000")
    msg.recipient_name = overrides.get("recipient_name", "Jane Doe")
    msg.delivery_status = overrides.get("delivery_status", "delivered")
    msg.error_message = None
    msg.sent_at = overrides.get("sent_at", datetime.now(tz=timezone.utc))
    msg.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    msg.customer = None
    msg.lead = None
    return msg


def _make_inbound(**overrides: Any) -> MagicMock:
    row = MagicMock()
    row.id = overrides.get("id", uuid4())
    row.job_id = overrides.get("job_id", uuid4())
    row.appointment_id = overrides.get("appointment_id", uuid4())
    row.sent_message_id = None
    row.customer_id = overrides.get("customer_id", uuid4())
    row.from_phone = overrides.get("from_phone", "+15125550000")
    row.reply_keyword = overrides.get("reply_keyword", "confirm")
    row.raw_reply_body = overrides.get("raw_reply_body", "Y")
    row.provider_sid = None
    row.status = overrides.get("status", "processed")
    row.received_at = overrides.get("received_at", datetime.now(tz=timezone.utc))
    row.processed_at = None
    return row


def _make_reschedule(**overrides: Any) -> MagicMock:
    row = MagicMock()
    row.id = overrides.get("id", uuid4())
    row.job_id = overrides.get("job_id", uuid4())
    row.appointment_id = overrides.get("appointment_id", uuid4())
    row.customer_id = overrides.get("customer_id", uuid4())
    row.original_reply_id = None
    row.requested_alternatives = None
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


def _build_service(
    *,
    appointment: MagicMock | None,
    outbound: list[MagicMock] | None = None,
    inbound: list[MagicMock] | None = None,
    reschedules: list[MagicMock] | None = None,
    consent: MagicMock | None = None,
    customer_id: Any | None = None,
) -> AppointmentTimelineService:
    session = AsyncMock()
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

    return service


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestAppointmentTimelineEndToEnd:
    """Service-layer end-to-end exercises with all collaborators mocked.

    Validates: Gap 11.
    """

    async def test_populated_timeline_has_all_sources(self) -> None:
        appt = _make_appointment()
        now = datetime.now(tz=timezone.utc)
        outbound = _make_sent_message(sent_at=now - timedelta(hours=2))
        inbound = _make_inbound(received_at=now - timedelta(hours=1))
        reschedule = _make_reschedule(status="open", created_at=now)

        service = _build_service(
            appointment=appt,
            customer_id=uuid4(),
            outbound=[outbound],
            inbound=[inbound],
            reschedules=[reschedule],
        )

        result = await service.get_timeline(appt.id)

        # At least the three events (one outbound + one inbound + one opened)
        assert len(result.events) >= 3
        # Newest first — the reschedule "opened" event is at `now`.
        assert result.events[0].kind == TimelineEventKind.RESCHEDULE_OPENED
        assert result.pending_reschedule_request is not None

    async def test_empty_timeline_flags_all_none(self) -> None:
        appt = _make_appointment()
        service = _build_service(appointment=appt, customer_id=uuid4())

        result = await service.get_timeline(appt.id)

        assert result.events == []
        assert result.pending_reschedule_request is None
        assert result.needs_review_reason is None
        assert result.opt_out is None
        assert result.last_event_at is None

    async def test_appointment_not_found_raises(self) -> None:
        service = _build_service(appointment=None)

        with pytest.raises(AppointmentNotFoundError):
            await service.get_timeline(uuid4())

    async def test_opt_out_consent_surfaces_on_state(self) -> None:
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
