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
            ("r", ConfirmationKeyword.RESCHEDULE),
            ("R", ConfirmationKeyword.RESCHEDULE),
            ("reschedule", ConfirmationKeyword.RESCHEDULE),
            ("RESCHEDULE", ConfirmationKeyword.RESCHEDULE),
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
        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)

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
        assert "auto_reply" in result

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

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=result_mock)

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
