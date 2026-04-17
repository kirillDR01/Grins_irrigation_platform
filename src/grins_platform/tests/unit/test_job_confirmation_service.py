"""Unit tests for JobConfirmationService.

Validates: CRM Changes Update 2 Req 24.2, 24.3, 24.4, 24.5, 24.7
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    AppointmentStatus,
    ConfirmationKeyword,
    MessageType,
)
from grins_platform.services.job_confirmation_service import (
    JobConfirmationService,
    parse_confirmation_reply,
)

# ---------------------------------------------------------------------------
# parse_confirmation_reply tests (Req 24.1)
# ---------------------------------------------------------------------------


class TestParseConfirmationReply:
    """Tests for the Y/R/C keyword parser."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ("y", ConfirmationKeyword.CONFIRM),
            ("Y", ConfirmationKeyword.CONFIRM),
            ("yes", ConfirmationKeyword.CONFIRM),
            ("YES", ConfirmationKeyword.CONFIRM),
            ("confirm", ConfirmationKeyword.CONFIRM),
            ("Confirmed", ConfirmationKeyword.CONFIRM),
            # bughunt M-3 synonyms
            ("ok", ConfirmationKeyword.CONFIRM),
            ("OK", ConfirmationKeyword.CONFIRM),
            ("okay", ConfirmationKeyword.CONFIRM),
            ("Okay", ConfirmationKeyword.CONFIRM),
            ("yup", ConfirmationKeyword.CONFIRM),
            ("yeah", ConfirmationKeyword.CONFIRM),
            ("1", ConfirmationKeyword.CONFIRM),
            ("r", ConfirmationKeyword.RESCHEDULE),
            ("R", ConfirmationKeyword.RESCHEDULE),
            ("reschedule", ConfirmationKeyword.RESCHEDULE),
            ("RESCHEDULE", ConfirmationKeyword.RESCHEDULE),
            # bughunt M-3 reschedule synonyms
            ("different time", ConfirmationKeyword.RESCHEDULE),
            ("Different Time", ConfirmationKeyword.RESCHEDULE),
            ("change time", ConfirmationKeyword.RESCHEDULE),
            ("2", ConfirmationKeyword.RESCHEDULE),
            ("c", ConfirmationKeyword.CANCEL),
            ("C", ConfirmationKeyword.CANCEL),
            ("cancel", ConfirmationKeyword.CANCEL),
            ("CANCEL", ConfirmationKeyword.CANCEL),
        ],
    )
    def test_known_keywords(self, body: str, expected: ConfirmationKeyword) -> None:
        assert parse_confirmation_reply(body) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize("body", ["hello", "maybe", "123", ""])
    def test_unknown_keywords_return_none(self, body: str) -> None:
        assert parse_confirmation_reply(body) is None

    @pytest.mark.unit
    @pytest.mark.parametrize("body", ["stop", "STOP", "Stop", "3"])
    def test_stop_and_3_are_not_cancel(self, body: str) -> None:
        """bughunt M-3: ``stop`` is a compliance opt-out keyword and must NOT
        collide with C/cancel. ``3`` was considered but excluded to avoid an
        ambiguous numeric mapping (1=CONFIRM, 2=RESCHEDULE only).
        """
        assert parse_confirmation_reply(body) is None

    @pytest.mark.unit
    def test_whitespace_trimmed(self) -> None:
        assert parse_confirmation_reply("  y  ") == ConfirmationKeyword.CONFIRM
        assert parse_confirmation_reply("\tcancel\n") == ConfirmationKeyword.CANCEL

    @pytest.mark.unit
    def test_case_insensitive(self) -> None:
        assert parse_confirmation_reply("yEs") == ConfirmationKeyword.CONFIRM
        assert parse_confirmation_reply("Reschedule") == ConfirmationKeyword.RESCHEDULE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sent_message(
    *,
    appointment_id: None | object = None,
    job_id: None | object = None,
    customer_id: None | object = None,
) -> Mock:
    msg = Mock()
    msg.id = uuid4()
    msg.appointment_id = appointment_id or uuid4()
    msg.job_id = job_id or uuid4()
    msg.customer_id = customer_id or uuid4()
    msg.message_type = MessageType.APPOINTMENT_CONFIRMATION.value
    msg.provider_thread_id = "thread-123"
    msg.created_at = datetime.now(tz=timezone.utc)
    return msg


def _make_appointment(*, status: str = AppointmentStatus.SCHEDULED.value) -> Mock:
    appt = Mock()
    appt.id = uuid4()
    appt.status = status
    return appt


@pytest.fixture()
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = Mock()
    return db


# ---------------------------------------------------------------------------
# JobConfirmationService.handle_confirmation tests
# ---------------------------------------------------------------------------


class TestHandleConfirmation:
    """Tests for the confirmation orchestrator."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_matching_thread_returns_no_match(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Req 24.7: unmatched thread_id returns no_match."""
        # execute() returns a result whose scalar_one_or_none() is None
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="unknown-thread",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="y",
            from_phone="+16125551234",
        )

        assert result["action"] == "no_match"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confirm_transitions_to_confirmed(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Req 24.2: Y keyword → SCHEDULED → CONFIRMED."""
        from datetime import date, time

        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        appt.scheduled_date = date(2026, 4, 20)
        appt.time_window_start = time(14, 0)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="y",
            from_phone="+16125551234",
        )

        assert result["action"] == "confirmed"
        assert appt.status == AppointmentStatus.CONFIRMED.value
        # bughunt M-4: confirm auto-reply must include date and time
        assert (
            result["auto_reply"] == "Your appointment has been confirmed. "
            "See you on April 20, 2026 at 2:00 PM!"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confirm_falls_back_when_date_time_missing(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """bughunt M-4: graceful fallback when appt has no date/time set."""
        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        # Mock without scheduled_date / time_window_start attrs returns None
        # via getattr() in the helper.
        appt.scheduled_date = None
        appt.time_window_start = None

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="y",
            from_phone="+16125551234",
        )

        assert (
            result["auto_reply"] == "Your appointment has been confirmed. See you then!"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reschedule_creates_request(self, mock_db: AsyncMock) -> None:
        """Req 24.3: R keyword → reschedule_request created."""
        sent_msg = _make_sent_message()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="reschedule please",
            from_phone="+16125551234",
        )

        assert result["action"] == "reschedule_requested"
        assert "reschedule_request_id" in result
        assert "auto_reply" in result
        # Verify db.add was called for both the response and the reschedule request
        assert mock_db.add.call_count >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_transitions_to_cancelled(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Req 24.4: C keyword → SCHEDULED → CANCELLED."""
        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        # clear_on_site_data now runs an invoice COUNT(*) query via
        # scalar_one (bughunt M-2). Default to 0 so the payment-flag
        # path matches old behavior.
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="c",
            from_phone="+16125551234",
        )

        assert result["action"] == "cancelled"
        assert appt.status == AppointmentStatus.CANCELLED.value
        assert "auto_reply" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_from_confirmed_state(self, mock_db: AsyncMock) -> None:
        """Req 24.4: C keyword also works from CONFIRMED state."""
        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.CONFIRMED.value)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="cancel",
            from_phone="+16125551234",
        )

        assert result["action"] == "cancelled"
        assert appt.status == AppointmentStatus.CANCELLED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_none_keyword_needs_review(self, mock_db: AsyncMock) -> None:
        """Req 24.5: unrecognised keyword → needs_review."""
        sent_msg = _make_sent_message()

        # First execute: find_confirmation_message returns sent_msg
        find_msg_result = MagicMock()
        find_msg_result.scalar_one_or_none.return_value = sent_msg

        # Second execute: _handle_needs_review checks for open reschedule request → None
        no_reschedule_result = MagicMock()
        no_reschedule_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[find_msg_result, no_reschedule_result],
        )

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=None,
            raw_body="maybe tomorrow?",
            from_phone="+16125551234",
        )

        assert result["action"] == "needs_review"
        assert "response_id" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_provider_sid_stored(self, mock_db: AsyncMock) -> None:
        """Verify provider_sid is passed through to the response record."""
        sent_msg = _make_sent_message()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=_make_appointment())

        svc = JobConfirmationService(mock_db)
        await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="y",
            from_phone="+16125551234",
            provider_sid="SM_abc123",
        )

        # The first db.add call should be the JobConfirmationResponse
        added_obj = mock_db.add.call_args_list[0][0][0]
        assert added_obj.provider_sid == "SM_abc123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_thread_id_correlation(self, mock_db: AsyncMock) -> None:
        """Req 24.7: correlation uses provider_thread_id on sent_messages."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="nonexistent-thread",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="y",
            from_phone="+16125551234",
        )

        # Should have queried the DB for the thread
        mock_db.execute.assert_awaited_once()
        assert result["action"] == "no_match"
        assert result["thread_id"] == "nonexistent-thread"


# ---------------------------------------------------------------------------
# Task 18.3: Reschedule follow-up SMS tests (Req 14.1, 14.3)
# ---------------------------------------------------------------------------


class TestRescheduleFollowUp:
    """Tests for reschedule follow-up SMS and alternative capture."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reschedule_reply_sends_acknowledgment_and_follow_up(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Req 14.1: 'R' reply → acknowledgment sent + follow-up SMS (two SMS total)."""
        sent_msg = _make_sent_message()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+16125551234",
        )

        assert result["action"] == "reschedule_requested"
        # Verify both auto_reply (acknowledgment) and follow_up_sms are present
        assert "auto_reply" in result
        assert "follow_up_sms" in result
        # bughunt M-5: spec-exact wording (§4 lines 251-254)
        assert (
            result["auto_reply"] == "We've received your reschedule request. "
            "We'll be in touch with a new time."
        )
        assert "2-3 dates" in result["follow_up_sms"]
        assert "we'd be happy to reschedule" in result["follow_up_sms"].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_customer_follow_up_reply_captured_in_requested_alternatives(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Req 14.3: customer follow-up reply → captured in requested_alternatives field."""
        sent_msg = _make_sent_message()
        appointment_id = sent_msg.appointment_id

        # Create a mock open reschedule request
        reschedule_req = Mock()
        reschedule_req.id = uuid4()
        reschedule_req.appointment_id = appointment_id
        reschedule_req.status = "open"
        reschedule_req.requested_alternatives = None

        # First call: find_confirmation_message returns sent_msg
        # Second call (in _handle_needs_review): returns the reschedule request
        find_msg_result = MagicMock()
        find_msg_result.scalar_one_or_none.return_value = sent_msg

        reschedule_result = MagicMock()
        reschedule_result.scalar_one_or_none.return_value = reschedule_req

        mock_db.execute = AsyncMock(
            side_effect=[find_msg_result, reschedule_result],
        )

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=None,  # Not a Y/R/C keyword — free-text reply
            raw_body="How about Tuesday at 2pm or Wednesday at 10am?",
            from_phone="+16125551234",
        )

        assert result["action"] == "reschedule_alternatives_received"
        assert (
            result["alternatives_text"]
            == "How about Tuesday at 2pm or Wednesday at 10am?"
        )
        # bughunt M-3: replies are appended under ``entries`` so the admin
        # queue sees multi-text follow-ups ("Tue 2pm", then "or Wed morning")
        # instead of only the latest body.
        assert reschedule_req.requested_alternatives is not None
        entries = reschedule_req.requested_alternatives["entries"]
        assert len(entries) == 1
        assert entries[0]["text"] == "How about Tuesday at 2pm or Wednesday at 10am?"
        assert "at" in entries[0]
        assert result["alternatives_count"] == 1


# ---------------------------------------------------------------------------
# Task 19.2: Cancellation SMS details tests (Req 15.1, 15.2)
# ---------------------------------------------------------------------------


class TestCancellationSMSDetails:
    """Tests for detailed cancellation SMS with service type, date, time, and phone."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_reply_includes_service_type_date_time_and_phone(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Req 15.1, 15.2: 'C' reply → cancellation SMS includes details."""
        from datetime import date, time

        monkeypatch.setenv("BUSINESS_PHONE_NUMBER", "(612) 555-9999")

        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        appt.job_id = sent_msg.job_id
        appt.scheduled_date = date(2025, 4, 15)
        appt.time_window_start = time(9, 30)

        job_mock = Mock()
        job_mock.id = sent_msg.job_id
        job_mock.job_type = "spring_startup"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)

        # db.get returns appointment first, then job
        mock_db.get = AsyncMock(side_effect=[appt, job_mock])

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+16125551234",
        )

        assert result["action"] == "cancelled"
        auto_reply = result["auto_reply"]
        # Verify service type
        assert "Spring Startup" in auto_reply
        # Verify date
        assert "April 15, 2025" in auto_reply
        # Verify time
        assert "9:30 AM" in auto_reply
        # Verify business phone
        assert "(612) 555-9999" in auto_reply
        # Verify the message structure
        assert "has been cancelled" in auto_reply
        assert "please call us at" in auto_reply.lower()


# ---------------------------------------------------------------------------
# CR-3 / 2026-04-14 E2E-3 — Repeat 'C' is a no-op (spec line 1070)
# ---------------------------------------------------------------------------


class TestRepeatCancelIsNoOp:
    """Repeat cancellation short-circuits without a duplicate SMS.

    **Validates: CR-3 (2026-04-14 E2E-3/H-2 survivor).** A second ``C`` reply
    on an already-CANCELLED appointment must not rebuild the cancellation
    message or dispatch another SMS; ``auto_reply`` must be empty so the
    SMS service's ``if auto_reply`` guard suppresses the send.
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_cancel_short_circuits_when_already_cancelled(
        self,
        mock_db: AsyncMock,
    ) -> None:
        sent_msg = _make_sent_message()
        cancelled_appt = _make_appointment(status=AppointmentStatus.CANCELLED.value)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=cancelled_appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        assert result["action"] == "cancelled"
        assert result["auto_reply"] == ""  # falsy → sms_service skips send

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_cancel_does_not_rebuild_message_when_already_cancelled(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sent_msg = _make_sent_message()
        cancelled_appt = _make_appointment(status=AppointmentStatus.CANCELLED.value)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=cancelled_appt)

        build_mock = Mock(return_value="SHOULD_NOT_BUILD")
        monkeypatch.setattr(
            JobConfirmationService,
            "_build_cancellation_message",
            staticmethod(build_mock),
        )

        svc = JobConfirmationService(mock_db)
        await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        build_mock.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_cancel_still_cancels_from_scheduled(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Regression: 'C' from SCHEDULED still transitions and returns a real auto-reply."""
        from datetime import date, time

        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        appt.job_id = sent_msg.job_id
        appt.scheduled_date = date(2025, 4, 15)
        appt.time_window_start = time(9, 30)

        job_mock = Mock()
        job_mock.id = sent_msg.job_id
        job_mock.job_type = "spring_startup"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(side_effect=[appt, job_mock])

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        assert result["action"] == "cancelled"
        assert result["auto_reply"]  # non-empty
        assert "has been cancelled" in result["auto_reply"]
        assert appt.status == AppointmentStatus.CANCELLED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_cancel_still_cancels_from_confirmed(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Regression: 'C' from CONFIRMED still transitions and returns a real auto-reply."""
        from datetime import date, time

        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.CONFIRMED.value)
        appt.job_id = sent_msg.job_id
        appt.scheduled_date = date(2025, 4, 15)
        appt.time_window_start = time(9, 30)

        job_mock = Mock()
        job_mock.id = sent_msg.job_id
        job_mock.job_type = "spring_startup"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(side_effect=[appt, job_mock])

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        assert result["action"] == "cancelled"
        assert result["auto_reply"]
        assert appt.status == AppointmentStatus.CANCELLED.value


# ---------------------------------------------------------------------------
# bughunt M-8: customer-SMS cancel writes an audit log row
# ---------------------------------------------------------------------------


class TestCustomerSmsCancelAudit:
    """The admin-side cancel path already audits via
    ``AppointmentService._record_cancellation_audit``. The customer-SMS
    path now does the same with ``source="customer_sms"`` so the admin
    history view can answer "who cancelled this?"."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_customer_sms_cancel_writes_audit_with_source(
        self,
        mock_db: AsyncMock,
    ) -> None:
        from datetime import date, time
        from unittest.mock import patch

        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        appt.job_id = sent_msg.job_id
        appt.scheduled_date = date(2026, 4, 22)
        appt.time_window_start = time(9, 30)

        job_mock = Mock()
        job_mock.id = sent_msg.job_id
        job_mock.job_type = "spring_startup"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(side_effect=[appt, job_mock])

        audit_create = AsyncMock()
        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository.create",
            audit_create,
        ):
            svc = JobConfirmationService(mock_db)
            await svc.handle_confirmation(
                thread_id="thread-123",
                keyword=ConfirmationKeyword.CANCEL,
                raw_body="C",
                from_phone="+19527373312",
            )

        audit_create.assert_awaited()
        call = audit_create.await_args
        assert call.kwargs["action"] == "appointment.cancel"
        assert call.kwargs["actor_id"] is None
        details = call.kwargs["details"]
        assert details["source"] == "customer_sms"
        assert details["pre_cancel_status"] == AppointmentStatus.SCHEDULED.value
        assert details["from_phone"] == "+19527373312"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_repeat_c_does_not_double_audit(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """CR-3 short-circuit must skip the audit row too — repeat C is a
        complete no-op (no SMS, no DB write, no audit)."""
        from unittest.mock import patch

        sent_msg = _make_sent_message()
        cancelled_appt = _make_appointment(status=AppointmentStatus.CANCELLED.value)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=cancelled_appt)

        audit_create = AsyncMock()
        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository.create",
            audit_create,
        ):
            svc = JobConfirmationService(mock_db)
            await svc.handle_confirmation(
                thread_id="thread-123",
                keyword=ConfirmationKeyword.CANCEL,
                raw_body="C",
                from_phone="+19527373312",
            )

        audit_create.assert_not_awaited()


# ---------------------------------------------------------------------------
# bughunt 2026-04-16 H-5 — admin cancellation alert on customer-SMS cancel
# ---------------------------------------------------------------------------


class TestAdminCancellationAlert:
    """When a customer cancels via SMS, the admin must be notified.

    D-4 (2026-04-16): both email and Alert row. The notification fires
    only on a real state transition — a repeat ``C`` reply hits the CR-3
    short-circuit and must not re-alert. Email failures are swallowed
    inside the notification service.

    Validates: bughunt 2026-04-16 finding H-5
    """

    @staticmethod
    def _patch_notification_service(
        monkeypatch: pytest.MonkeyPatch,
    ) -> AsyncMock:
        """Install a mock :class:`NotificationService` and return its alert hook."""
        send_alert_mock = AsyncMock()
        notification_svc_mock = MagicMock()
        notification_svc_mock.send_admin_cancellation_alert = send_alert_mock

        monkeypatch.setattr(
            "grins_platform.services.notification_service.NotificationService",
            MagicMock(return_value=notification_svc_mock),
        )
        # Neutralise the default EmailService constructor so tests never
        # touch pydantic_settings / env vars.
        monkeypatch.setattr(
            "grins_platform.services.email_service.EmailService",
            MagicMock(return_value=MagicMock()),
        )
        return send_alert_mock

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_cancel_notifies_admin_on_first_cancellation(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """First ``C`` reply on a SCHEDULED appointment dispatches the alert.

        Validates: bughunt 2026-04-16 finding H-5
        """
        from datetime import date, time

        send_alert_mock = self._patch_notification_service(monkeypatch)

        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        # Align the appointment row with the sent_message's FK so
        # ``handle_confirmation``'s appointment_id (from the sent message)
        # matches the Appointment we load from the DB mock.
        appt.id = sent_msg.appointment_id
        appt.job_id = sent_msg.job_id
        appt.scheduled_date = date(2026, 4, 17)
        appt.time_window_start = time(9, 0)

        job_mock = Mock()
        job_mock.id = sent_msg.job_id
        job_mock.job_type = "spring_startup"

        customer_mock = Mock()
        customer_mock.id = sent_msg.customer_id
        customer_mock.first_name = "Jane"
        customer_mock.last_name = "Doe"
        customer_mock.full_name = "Jane Doe"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)
        # get(Appointment), get(Job), get(Customer)
        mock_db.get = AsyncMock(side_effect=[appt, job_mock, customer_mock])

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        assert result["action"] == "cancelled"
        send_alert_mock.assert_awaited_once()
        call_kwargs = send_alert_mock.await_args.kwargs
        assert call_kwargs["appointment_id"] == sent_msg.appointment_id
        assert call_kwargs["customer_id"] == sent_msg.customer_id
        assert call_kwargs["customer_name"] == "Jane Doe"
        assert call_kwargs["source"] == "customer_sms"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_cancel_does_not_notify_admin_when_already_cancelled(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CR-3 short-circuit — repeat ``C`` must NOT re-alert.

        Validates: bughunt 2026-04-16 finding H-5 (idempotency with CR-3)
        """
        send_alert_mock = self._patch_notification_service(monkeypatch)

        sent_msg = _make_sent_message()
        cancelled_appt = _make_appointment(status=AppointmentStatus.CANCELLED.value)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(return_value=cancelled_appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        assert result["action"] == "cancelled"
        assert result["auto_reply"] == ""
        send_alert_mock.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_cancel_still_responds_when_admin_notification_fails(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Notification raising must not break the customer-facing reply.

        Validates: bughunt 2026-04-16 finding H-5
        """
        from datetime import date, time

        # Install a NotificationService whose send hook raises.
        send_alert_mock = AsyncMock(side_effect=RuntimeError("boom"))
        notification_svc_mock = MagicMock()
        notification_svc_mock.send_admin_cancellation_alert = send_alert_mock
        monkeypatch.setattr(
            "grins_platform.services.notification_service.NotificationService",
            MagicMock(return_value=notification_svc_mock),
        )
        monkeypatch.setattr(
            "grins_platform.services.email_service.EmailService",
            MagicMock(return_value=MagicMock()),
        )

        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        appt.job_id = sent_msg.job_id
        appt.scheduled_date = date(2026, 4, 17)
        appt.time_window_start = time(9, 0)

        job_mock = Mock()
        job_mock.id = sent_msg.job_id
        job_mock.job_type = "spring_startup"

        customer_mock = Mock()
        customer_mock.id = sent_msg.customer_id
        customer_mock.full_name = "Jane Doe"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.get = AsyncMock(side_effect=[appt, job_mock, customer_mock])

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        # Customer reply still produced despite the admin-alert failure.
        assert result["action"] == "cancelled"
        assert result["auto_reply"]  # non-empty — customer gets their SMS
        send_alert_mock.assert_awaited_once()
