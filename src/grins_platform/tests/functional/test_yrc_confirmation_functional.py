"""Functional tests for Y/R/C appointment confirmation flow.

Tests the full confirmation lifecycle with mocked DB + SMS:
- Send confirmation → receive Y (confirm) → appointment transitions to CONFIRMED
- Send confirmation → receive R (reschedule) → reschedule_request created
- Send confirmation → receive C (cancel) → appointment transitions to CANCELLED
- Unknown reply → logged as needs_review

Validates: Requirements 24.2, 24.3, 24.4, 24.5
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus, ConfirmationKeyword
from grins_platform.models.job_confirmation import (
    JobConfirmationResponse,
    RescheduleRequest,
)
from grins_platform.services.job_confirmation_service import (
    JobConfirmationService,
    parse_confirmation_reply,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_sent_message(**overrides: Any) -> MagicMock:
    """Create a mock SentMessage representing an outbound confirmation SMS."""
    msg = MagicMock()
    msg.id = overrides.get("id", uuid4())
    msg.customer_id = overrides.get("customer_id", uuid4())
    msg.job_id = overrides.get("job_id", uuid4())
    msg.appointment_id = overrides.get("appointment_id", uuid4())
    msg.message_type = overrides.get("message_type", "appointment_confirmation")
    msg.provider_thread_id = overrides.get("provider_thread_id", "thread-abc-123")
    msg.recipient_phone = overrides.get("recipient_phone", "+15125551234")
    msg.delivery_status = overrides.get("delivery_status", "delivered")
    msg.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    return msg


def _make_appointment(**overrides: Any) -> MagicMock:
    """Create a mock Appointment with SCHEDULED status by default."""
    appt = MagicMock()
    appt.id = overrides.get("id", uuid4())
    appt.job_id = overrides.get("job_id", uuid4())
    appt.status = overrides.get("status", AppointmentStatus.SCHEDULED.value)
    return appt


def _build_mock_db(
    *,
    sent_message: MagicMock | None = None,
    appointment: MagicMock | None = None,
) -> AsyncMock:
    """Build a mock AsyncSession wired for confirmation flow queries.

    Handles:
    - SELECT sent_messages WHERE provider_thread_id (correlation lookup)
    - db.get(Appointment, id) for status transitions
    - db.add() for JobConfirmationResponse / RescheduleRequest
    - db.flush() for persistence
    """
    db = AsyncMock()

    # Track objects added via db.add()
    db._added_objects: list[Any] = []

    original_add = MagicMock()

    def _add_side_effect(obj: Any) -> None:
        # Assign a UUID if the object doesn't have one yet
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid4()
        db._added_objects.append(obj)
        original_add(obj)

    db.add = MagicMock(side_effect=_add_side_effect)

    # SELECT routing:
    # - ``find_confirmation_message``: ``select(SentMessage)`` → ``sent_message``
    # - Gap 02 appointment lock: ``select(Appointment).with_for_update()``
    #   → ``appointment``
    # - Everything else (e.g. open RescheduleRequest dedup): default to
    #   ``sent_message`` so existing behaviour is preserved.
    async def _execute_side_effect(stmt: Any, params: Any = None) -> MagicMock:
        result = MagicMock()
        try:
            entity = stmt.column_descriptions[0].get("entity")
            entity_name = getattr(entity, "__name__", "")
        except (AttributeError, IndexError, KeyError):
            entity_name = ""

        if entity_name == "Appointment":
            result.scalar_one_or_none.return_value = appointment
        else:
            result.scalar_one_or_none.return_value = sent_message
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)

    # db.get(Appointment, id) for status transitions
    async def _get_side_effect(model: Any, pk: Any) -> MagicMock | None:
        if appointment is not None and hasattr(model, "__tablename__"):
            if model.__tablename__ == "appointments":
                return appointment
        return appointment

    db.get = AsyncMock(side_effect=_get_side_effect)
    db.flush = AsyncMock()

    return db


# =============================================================================
# 1. Confirm (Y) — Appointment transitions to CONFIRMED
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestConfirmReplyFlow:
    """Send confirmation → receive Y → appointment transitions to CONFIRMED.

    Validates: Requirement 24.2
    """

    async def test_confirm_reply_transitions_appointment_to_confirmed(self) -> None:
        """Y reply sets appointment status to CONFIRMED and records response."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("Y")
        assert keyword == ConfirmationKeyword.CONFIRM

        result = await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=keyword,
            raw_body="Y",
            from_phone="+15125551234",
        )

        # Appointment status transitioned to CONFIRMED
        assert appointment.status == AppointmentStatus.CONFIRMED.value
        # Result indicates confirmed action
        assert result["action"] == "confirmed"
        assert result["appointment_id"] == str(appt_id)
        # Auto-reply message returned
        assert "auto_reply" in result
        assert "confirmed" in result["auto_reply"].lower()

    async def test_confirm_reply_persists_confirmation_response(self) -> None:
        """Y reply creates a JobConfirmationResponse record."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("yes")

        await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=keyword,
            raw_body="yes",
            from_phone="+15125551234",
        )

        # A JobConfirmationResponse was added to the session
        added = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        assert len(added) == 1
        response = added[0]
        assert response.reply_keyword == ConfirmationKeyword.CONFIRM.value
        assert response.status == "confirmed"
        assert response.processed_at is not None


# =============================================================================
# 1.b Gap 02 — Repeat Y on an already-confirmed appointment is idempotent
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestRepeatConfirmReplyFlow:
    """Second ``Y`` on an already-CONFIRMED appointment short-circuits.

    The appointment status stays CONFIRMED (no re-transition), the new
    ``JobConfirmationResponse`` is marked ``confirmed_repeat``, and the
    ``auto_reply`` contains the reassurance wording ("already confirmed")
    rather than a full re-confirmation.

    **Validates: gap-02.**
    """

    async def test_repeat_confirm_reply_short_circuits_on_already_confirmed(
        self,
    ) -> None:
        """Y on an already-CONFIRMED appointment → reassurance + dedup flag."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.CONFIRMED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("Y")
        assert keyword == ConfirmationKeyword.CONFIRM

        result = await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=keyword,
            raw_body="Y",
            from_phone="+19527373312",
        )

        # Appointment status unchanged — no re-transition.
        assert appointment.status == AppointmentStatus.CONFIRMED.value
        # Result signals the repeat with ``dedup=True`` and reassurance text.
        assert result["action"] == "confirmed"
        assert result["dedup"] is True
        assert result["auto_reply"]
        assert "already confirmed" in result["auto_reply"]
        # Exactly one JobConfirmationResponse was added, with status
        # ``confirmed_repeat`` (distinct from first-Y ``confirmed`` rows).
        added = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        assert len(added) == 1
        response = added[0]
        assert response.status == "confirmed_repeat"
        assert response.reply_keyword == ConfirmationKeyword.CONFIRM.value
        assert response.processed_at is not None


# =============================================================================
# 2. Reschedule (R) — reschedule_request created
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestRescheduleReplyFlow:
    """Send confirmation → receive R → reschedule_request created.

    Validates: Requirement 24.3
    """

    async def test_reschedule_reply_creates_reschedule_request(self) -> None:
        """R reply creates a RescheduleRequest and returns follow-up info."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("R")
        assert keyword == ConfirmationKeyword.RESCHEDULE

        result = await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=keyword,
            raw_body="R",
            from_phone="+15125551234",
        )

        # Result indicates reschedule action
        assert result["action"] == "reschedule_requested"
        assert result["appointment_id"] == str(appt_id)
        assert "reschedule_request_id" in result
        # Auto-reply about rescheduling returned
        assert "auto_reply" in result
        assert "reschedule" in result["auto_reply"].lower()

    async def test_reschedule_reply_persists_both_records(self) -> None:
        """R reply creates both a JobConfirmationResponse and RescheduleRequest."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("reschedule")

        await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=keyword,
            raw_body="reschedule",
            from_phone="+15125551234",
        )

        # Both a confirmation response and reschedule request were added
        confirmations = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        reschedules = [
            o for o in db._added_objects if isinstance(o, RescheduleRequest)
        ]
        assert len(confirmations) == 1
        assert len(reschedules) == 1

        conf = confirmations[0]
        assert conf.reply_keyword == ConfirmationKeyword.RESCHEDULE.value
        assert conf.status == "reschedule_requested"

        resched = reschedules[0]
        assert resched.job_id == job_id
        assert resched.appointment_id == appt_id
        assert resched.customer_id == customer_id
        assert resched.status == "open"


# =============================================================================
# 3. Cancel (C) — Appointment transitions to CANCELLED
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCancelReplyFlow:
    """Send confirmation → receive C → appointment transitions to CANCELLED.

    Validates: Requirement 24.4
    """

    async def test_cancel_reply_transitions_appointment_to_cancelled(self) -> None:
        """C reply sets appointment status to CANCELLED."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("C")
        assert keyword == ConfirmationKeyword.CANCEL

        result = await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=keyword,
            raw_body="C",
            from_phone="+15125551234",
        )

        # Appointment status transitioned to CANCELLED
        assert appointment.status == AppointmentStatus.CANCELLED.value
        # Result indicates cancelled action
        assert result["action"] == "cancelled"
        assert result["appointment_id"] == str(appt_id)
        # Auto-reply about cancellation returned
        assert "auto_reply" in result
        assert "cancelled" in result["auto_reply"].lower()

    async def test_cancel_reply_persists_confirmation_response(self) -> None:
        """C reply creates a JobConfirmationResponse with cancelled status."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("cancel")

        await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=keyword,
            raw_body="cancel",
            from_phone="+15125551234",
        )

        added = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        assert len(added) == 1
        response = added[0]
        assert response.reply_keyword == ConfirmationKeyword.CANCEL.value
        assert response.status == "cancelled"
        assert response.processed_at is not None

    async def test_two_consecutive_c_replies_send_exactly_one_sms(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CR-3: two consecutive 'C' replies dispatch exactly one cancellation SMS.

        The second reply short-circuits because the appointment is already
        CANCELLED; auto_reply returns empty so ``sms_service._try_confirmation_reply``
        skips its ``provider.send_text`` call. **Validates: CR-3 / 2026-04-14 E2E-3.**

        ``clear_on_site_data`` is patched to a no-op here: the shared
        ``_build_mock_db`` helper doesn't stub the invoice-count query path
        (pre-existing harness limitation, unrelated to CR-3).
        """
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        clear_on_site_mock = AsyncMock()
        monkeypatch.setattr(
            "grins_platform.services.appointment_service.clear_on_site_data",
            clear_on_site_mock,
        )

        service = JobConfirmationService(db)

        # First C — cancels and returns a real auto-reply.
        first = await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )
        assert appointment.status == AppointmentStatus.CANCELLED.value
        assert first["auto_reply"]  # truthy → provider would be called once

        # Second C — appointment is already CANCELLED, so auto_reply is empty.
        second = await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )
        assert second["action"] == "cancelled"
        assert second["auto_reply"] == ""  # falsy → provider NOT called second time

        # clear_on_site_data is only called on the first transition, not the second.
        assert clear_on_site_mock.await_count == 1


# =============================================================================
# 4. Unknown Reply — logged as needs_review
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestUnknownReplyFlow:
    """Unknown reply → logged as needs_review for manual processing.

    Validates: Requirement 24.5
    """

    async def test_unknown_reply_logged_as_needs_review(self) -> None:
        """Unrecognised reply text is logged with needs_review status."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("maybe tomorrow?")
        assert keyword is None

        result = await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=keyword,
            raw_body="maybe tomorrow?",
            from_phone="+15125551234",
        )

        # Result indicates needs_review action
        assert result["action"] == "needs_review"
        assert "response_id" in result

        # Appointment status unchanged (still SCHEDULED)
        assert appointment.status == AppointmentStatus.SCHEDULED.value

    async def test_unknown_reply_persists_with_needs_review_status(self) -> None:
        """Unrecognised reply creates a response record with needs_review."""
        appt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=appt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=appt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        service = JobConfirmationService(db)

        await service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=None,
            raw_body="what time again?",
            from_phone="+15125551234",
        )

        added = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        assert len(added) == 1
        response = added[0]
        assert response.reply_keyword is None
        assert response.status == "needs_review"
        assert response.raw_reply_body == "what time again?"
        assert response.processed_at is not None


# =============================================================================
# 5. No matching thread — graceful handling
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestNoMatchingThreadFlow:
    """Reply with no matching confirmation message returns no_match.

    Validates: Requirement 24.8 (correlation via thread_id)
    """

    async def test_no_matching_thread_returns_no_match(self) -> None:
        """Reply to unknown thread_id returns no_match without error."""
        db = _build_mock_db(sent_message=None, appointment=None)

        service = JobConfirmationService(db)
        keyword = parse_confirmation_reply("Y")

        result = await service.handle_confirmation(
            thread_id="unknown-thread-999",
            keyword=keyword,
            raw_body="Y",
            from_phone="+15125551234",
        )

        assert result["action"] == "no_match"
        assert result["thread_id"] == "unknown-thread-999"
        # No objects added to session
        assert len(db._added_objects) == 0
