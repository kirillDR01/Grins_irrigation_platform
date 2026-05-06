"""Unit tests for the estimate-visit Y/R/C handlers in JobConfirmationService.

The dispatcher (``handle_confirmation``) routes inbound replies to either
the appointment-side handlers or the new
``_handle_estimate_visit_*`` handlers based on
``ConfirmationTarget.kind`` — the discriminator is which FK is set on
the correlated ``SentMessage``. These tests exercise the sales-side
branch directly: Y → confirmed, R → reschedule_requested + open
``RescheduleRequest`` + reuse-the-2-3-dates ack, C → cancelled + admin
alert.

Validates: sales-pipeline-estimate-visit-confirmation-lifecycle Task 18.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from grins_platform.models.enums import ConfirmationKeyword, MessageType
from grins_platform.services.job_confirmation_service import (
    JobConfirmationService,
)


def _make_estimate_sent_message(
    *,
    sales_calendar_event_id: object | None = None,
    customer_id: object | None = None,
) -> Mock:
    msg = Mock()
    msg.id = uuid4()
    # Polymorphic FK: estimate-visit thread carries
    # ``sales_calendar_event_id`` and leaves ``appointment_id`` null.
    msg.appointment_id = None
    msg.sales_calendar_event_id = sales_calendar_event_id or uuid4()
    msg.job_id = None
    msg.customer_id = customer_id or uuid4()
    msg.message_type = MessageType.ESTIMATE_VISIT_CONFIRMATION.value
    msg.provider_thread_id = "thread-est-1"
    msg.recipient_phone = "+19527373312"
    msg.created_at = datetime.now(tz=timezone.utc)
    return msg


def _make_event(
    *,
    event_id: object | None = None,
    confirmation_status: str = "pending",
) -> Mock:
    event = Mock()
    event.id = event_id or uuid4()
    event.confirmation_status = confirmation_status
    event.confirmation_status_at = None
    event.scheduled_date = None
    event.start_time = None
    return event


@pytest.fixture()
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    # Reschedule insert wraps in SAVEPOINT (begin_nested context manager).
    db.begin_nested = MagicMock(return_value=AsyncMock())
    return db


# ---------------------------------------------------------------------------
# Y → confirmed
# ---------------------------------------------------------------------------


class TestEstimateVisitConfirm:
    """Y reply on an estimate-visit thread."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_y_transitions_pending_to_confirmed(
        self,
        mock_db: AsyncMock,
    ) -> None:
        sent_msg = _make_estimate_sent_message()
        event = _make_event(
            event_id=sent_msg.sales_calendar_event_id,
            confirmation_status="pending",
        )

        # execute() order in handle_confirmation (estimate-visit branch):
        # find_confirmation_message → estimate-visit confirm SELECT FOR UPDATE
        find_msg_result = MagicMock()
        find_msg_result.scalar_one_or_none.return_value = sent_msg
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = event
        mock_db.execute = AsyncMock(side_effect=[find_msg_result, event_result])

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-est-1",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="y",
            from_phone="+19527373312",
        )

        assert result["action"] == "confirmed"
        assert result["sales_calendar_event_id"] == str(event.id)
        assert event.confirmation_status == "confirmed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_second_y_is_idempotent_dedup(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Replying Y twice — the second is a silent ack, not a duplicate transition."""
        sent_msg = _make_estimate_sent_message()
        event = _make_event(
            event_id=sent_msg.sales_calendar_event_id,
            confirmation_status="confirmed",
        )

        find_msg_result = MagicMock()
        find_msg_result.scalar_one_or_none.return_value = sent_msg
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = event
        mock_db.execute = AsyncMock(side_effect=[find_msg_result, event_result])

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-est-1",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="Y",
            from_phone="+19527373312",
        )

        assert result["action"] == "confirmed"
        assert result.get("dedup") is True
        # No demotion or re-stamp.
        assert event.confirmation_status == "confirmed"


# ---------------------------------------------------------------------------
# R → reschedule_requested
# ---------------------------------------------------------------------------


class TestEstimateVisitReschedule:
    """R reply on an estimate-visit thread."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_creates_reschedule_request_and_flips_status(
        self,
        mock_db: AsyncMock,
    ) -> None:
        sent_msg = _make_estimate_sent_message()
        event = _make_event(
            event_id=sent_msg.sales_calendar_event_id,
            confirmation_status="pending",
        )

        # execute() order: find_confirmation_message → open-reschedule
        # dedup lookup (None so the insert path runs).
        find_msg_result = MagicMock()
        find_msg_result.scalar_one_or_none.return_value = sent_msg
        no_existing_result = MagicMock()
        no_existing_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(
            side_effect=[find_msg_result, no_existing_result],
        )
        mock_db.get = AsyncMock(return_value=event)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-est-1",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="please reschedule",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_requested"
        assert result["sales_calendar_event_id"] == str(event.id)
        assert "reschedule_request_id" in result
        # OQ-8: ack reuses the existing 2-3 dates prompt verbatim.
        ack = result["auto_reply"]
        assert "2-3 dates" in ack or "2 or 3 dates" in ack
        # OQ-10: event flips to reschedule_requested (not cancelled).
        assert event.confirmation_status == "reschedule_requested"
        # The response row + reschedule row are both added.
        assert mock_db.add.call_count >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_double_r_appends_to_existing_request_no_duplicate(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """A second R while a request is already open appends the new
        message to ``raw_alternatives_text`` instead of opening a duplicate.
        """
        sent_msg = _make_estimate_sent_message()
        existing = Mock()
        existing.id = uuid4()
        existing.raw_alternatives_text = "first try"

        find_msg_result = MagicMock()
        find_msg_result.scalar_one_or_none.return_value = sent_msg
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(
            side_effect=[find_msg_result, existing_result],
        )

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-est-1",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="actually Tuesday at 3",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_requested"
        assert result.get("duplicate") is True
        assert result["reschedule_request_id"] == str(existing.id)
        assert "actually Tuesday at 3" in existing.raw_alternatives_text
        assert "first try" in existing.raw_alternatives_text


# ---------------------------------------------------------------------------
# C → cancelled
# ---------------------------------------------------------------------------


class TestEstimateVisitCancel:
    """C reply on an estimate-visit thread."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_c_flips_event_to_cancelled(
        self,
        mock_db: AsyncMock,
    ) -> None:
        sent_msg = _make_estimate_sent_message()
        event = _make_event(
            event_id=sent_msg.sales_calendar_event_id,
            confirmation_status="pending",
        )

        find_msg_result = MagicMock()
        find_msg_result.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=find_msg_result)
        mock_db.get = AsyncMock(return_value=event)

        # Stub out the admin-alert dispatch so we don't hit AlertRepository.
        svc = JobConfirmationService(mock_db)
        svc._dispatch_estimate_visit_cancellation_alert = AsyncMock()

        result = await svc.handle_confirmation(
            thread_id="thread-est-1",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="c",
            from_phone="+19527373312",
        )

        assert result["action"] == "cancelled"
        assert result["sales_calendar_event_id"] == str(event.id)
        assert event.confirmation_status == "cancelled"
        # Admin alert raised.
        svc._dispatch_estimate_visit_cancellation_alert.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_second_c_is_silent_no_repeat_alert(
        self,
        mock_db: AsyncMock,
    ) -> None:
        sent_msg = _make_estimate_sent_message()
        event = _make_event(
            event_id=sent_msg.sales_calendar_event_id,
            confirmation_status="cancelled",
        )

        find_msg_result = MagicMock()
        find_msg_result.scalar_one_or_none.return_value = sent_msg
        mock_db.execute = AsyncMock(return_value=find_msg_result)
        mock_db.get = AsyncMock(return_value=event)

        svc = JobConfirmationService(mock_db)
        svc._dispatch_estimate_visit_cancellation_alert = AsyncMock()

        result = await svc.handle_confirmation(
            thread_id="thread-est-1",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        assert result["action"] == "cancelled"
        # Already-cancelled branch returns early — no admin alert re-raised.
        svc._dispatch_estimate_visit_cancellation_alert.assert_not_called()
