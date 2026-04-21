"""Unit tests for the thread correlation hardening (gap-03).

Covers:

3.A  Confirmation-like correlation is widened (reschedule notification
     + reminder in addition to confirmation). Cancellation
     notifications route through a separate handler so a Y/R reply on
     a cancellation thread never silently re-confirms.
3.B  Prior confirmation-like rows are tombstoned with
     ``superseded_at`` when a new one is sent; a Y reply on a stale
     thread routes to a ``stale_thread_reply`` audit row rather than
     transitioning a date the customer never saw.

Validates: gap-03 (3.A, 3.B).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from grins_platform.models.enums import (
    AlertType,
    AppointmentStatus,
    ConfirmationKeyword,
    MessageType,
)
from grins_platform.services.job_confirmation_service import (
    JobConfirmationService,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_sent_message(
    *,
    appointment_id: Any | None = None,
    job_id: Any | None = None,
    customer_id: Any | None = None,
    message_type: str = MessageType.APPOINTMENT_CONFIRMATION.value,
    superseded_at: datetime | None = None,
) -> Mock:
    msg = Mock()
    msg.id = uuid4()
    msg.appointment_id = appointment_id or uuid4()
    msg.job_id = job_id or uuid4()
    msg.customer_id = customer_id or uuid4()
    msg.message_type = message_type
    msg.provider_thread_id = "thread-corr"
    msg.recipient_phone = "+19527373312"
    msg.superseded_at = superseded_at
    msg.created_at = datetime.now(tz=timezone.utc)
    return msg


def _make_appointment(*, status: str = AppointmentStatus.CANCELLED.value) -> Mock:
    appt = Mock()
    appt.id = uuid4()
    appt.status = status
    appt.scheduled_date = date(2026, 5, 1)
    appt.time_window_start = time(9, 0)
    appt.time_window_end = time(11, 0)
    return appt


def _make_open_request(*, appointment_id: Any | None = None) -> Mock:
    req = Mock()
    req.id = uuid4()
    req.appointment_id = appointment_id or uuid4()
    req.status = "open"
    req.raw_alternatives_text = None
    req.requested_alternatives = None
    return req


@pytest.fixture()
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = Mock()
    db.begin_nested = MagicMock(return_value=AsyncMock())
    return db


def _make_execute_side_effect(*return_values: Any) -> AsyncMock:
    """Build a db.execute mock that cycles through canned scalar results."""
    results = []
    for value in return_values:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = value
        results.append(result_mock)
    return AsyncMock(side_effect=results)


# ---------------------------------------------------------------------------
# Gap 3.A — widened confirmation-like correlation
# ---------------------------------------------------------------------------


class TestFindConfirmationMessage:
    """``find_confirmation_message`` resolves the confirmation-like set."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_with_appointment_confirmation_returns_row(
        self,
        mock_db: AsyncMock,
    ) -> None:
        row = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CONFIRMATION.value,
        )
        mock_db.execute = _make_execute_side_effect(row)
        svc = JobConfirmationService(mock_db)

        result = await svc.find_confirmation_message("thread-corr")

        assert result is row

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_with_appointment_reschedule_returns_row(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Gap 3.A: a reschedule-notification SMS is confirmation-like."""
        row = _make_sent_message(
            message_type=MessageType.APPOINTMENT_RESCHEDULE.value,
        )
        mock_db.execute = _make_execute_side_effect(row)
        svc = JobConfirmationService(mock_db)

        result = await svc.find_confirmation_message("thread-corr")

        assert result is row

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_with_appointment_reminder_returns_row(
        self,
        mock_db: AsyncMock,
    ) -> None:
        row = _make_sent_message(
            message_type=MessageType.APPOINTMENT_REMINDER.value,
        )
        mock_db.execute = _make_execute_side_effect(row)
        svc = JobConfirmationService(mock_db)

        result = await svc.find_confirmation_message("thread-corr")

        assert result is row

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_with_no_row_returns_none(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Cancellation is NOT confirmation-like. The DB filter excludes it
        directly; here we assert that when the DB has no matching row,
        ``find_confirmation_message`` returns None (the widened filter
        must not accidentally match ``APPOINTMENT_CANCELLATION``)."""
        mock_db.execute = _make_execute_side_effect(None)
        svc = JobConfirmationService(mock_db)

        result = await svc.find_confirmation_message("thread-corr")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_widened_filter_includes_three_confirmation_like_types(
        self,
    ) -> None:
        """The module-level constant matches the three confirmation-like types."""
        from grins_platform.services.job_confirmation_service import (
            _CONFIRMATION_LIKE_TYPES,
        )

        assert (
            frozenset(
                {
                    MessageType.APPOINTMENT_CONFIRMATION.value,
                    MessageType.APPOINTMENT_RESCHEDULE.value,
                    MessageType.APPOINTMENT_REMINDER.value,
                },
            )
            == _CONFIRMATION_LIKE_TYPES
        )
        assert (
            MessageType.APPOINTMENT_CANCELLATION.value not in _CONFIRMATION_LIKE_TYPES
        )


# ---------------------------------------------------------------------------
# Gap 3.A — cancellation thread lookup
# ---------------------------------------------------------------------------


class TestFindCancellationThread:
    """``find_cancellation_thread`` finds cancellation SMSes for a thread."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_with_cancellation_returns_row(
        self,
        mock_db: AsyncMock,
    ) -> None:
        row = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        )
        mock_db.execute = _make_execute_side_effect(row)
        svc = JobConfirmationService(mock_db)

        result = await svc.find_cancellation_thread("thread-corr")

        assert result is row

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_when_no_cancellation_row_returns_none(
        self,
        mock_db: AsyncMock,
    ) -> None:
        mock_db.execute = _make_execute_side_effect(None)
        svc = JobConfirmationService(mock_db)

        result = await svc.find_cancellation_thread("thread-corr")

        assert result is None


# ---------------------------------------------------------------------------
# Gap 3.A — post-cancellation reply handler
# ---------------------------------------------------------------------------


class TestPostCancellationHandler:
    """``handle_post_cancellation_reply`` routes R / Y / C / free text."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_on_cancellation_thread_opens_new_reschedule_request(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """R on a cancellation thread creates a new open RescheduleRequest."""
        cancel_msg = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        )
        # Order of execute calls:
        #   1. find_cancellation_thread → cancel_msg
        #   2. open-request lookup in _handle_post_cancel_reschedule → None
        mock_db.execute = _make_execute_side_effect(cancel_msg, None)
        svc = JobConfirmationService(mock_db)

        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        assert result["action"] == "post_cancel_reschedule_requested"
        assert "follow_up_sms" in result
        assert "reschedule_request_id" in result
        # A RescheduleRequest was added.
        added_types = {type(c.args[0]).__name__ for c in mock_db.add.call_args_list}
        assert "RescheduleRequest" in added_types
        assert "JobConfirmationResponse" in added_types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_on_cancellation_thread_with_existing_open_request_appends(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """A pre-existing open request folds the new R reply into it."""
        cancel_msg = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        )
        existing = _make_open_request(appointment_id=cancel_msg.appointment_id)
        existing.raw_alternatives_text = "earlier text"
        mock_db.execute = _make_execute_side_effect(cancel_msg, existing)
        svc = JobConfirmationService(mock_db)

        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        # Dedup path: no new RescheduleRequest, existing row grew.
        assert result.get("duplicate") is True
        assert "earlier text" in existing.raw_alternatives_text
        assert "R" in existing.raw_alternatives_text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_y_on_cancellation_thread_dispatches_reconsider_alert(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Y on a cancellation thread raises the reconsider alert; no transition."""
        cancel_msg = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        )
        cancelled_appt = _make_appointment(
            status=AppointmentStatus.CANCELLED.value,
        )
        mock_db.execute = _make_execute_side_effect(cancel_msg)
        mock_db.get = AsyncMock(return_value=cancelled_appt)

        svc = JobConfirmationService(mock_db)
        dispatch_spy = AsyncMock()
        svc._dispatch_reconsider_cancellation_alert = dispatch_spy  # type: ignore[method-assign]

        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="Y",
            from_phone="+19527373312",
        )

        assert result["action"] == "post_cancel_reconsider_pending"
        # Status unchanged.
        assert cancelled_appt.status == AppointmentStatus.CANCELLED.value
        dispatch_spy.assert_awaited_once()
        kwargs = dispatch_spy.await_args.kwargs
        assert kwargs["appointment_id"] == cancel_msg.appointment_id
        assert kwargs["appt"] is cancelled_appt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_c_on_cancellation_thread_routes_needs_review(
        self,
        mock_db: AsyncMock,
    ) -> None:
        cancel_msg = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        )
        mock_db.execute = _make_execute_side_effect(cancel_msg)
        svc = JobConfirmationService(mock_db)

        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.CANCEL,
            raw_body="C",
            from_phone="+19527373312",
        )

        assert result["action"] == "needs_review"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_free_text_on_cancellation_thread_routes_needs_review(
        self,
        mock_db: AsyncMock,
    ) -> None:
        cancel_msg = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        )
        mock_db.execute = _make_execute_side_effect(cancel_msg)
        svc = JobConfirmationService(mock_db)

        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-corr",
            keyword=None,
            raw_body="wait wait i changed my mind",
            from_phone="+19527373312",
        )

        assert result["action"] == "needs_review"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handler_returns_no_match_when_no_cancellation_thread(
        self,
        mock_db: AsyncMock,
    ) -> None:
        mock_db.execute = _make_execute_side_effect(None)
        svc = JobConfirmationService(mock_db)

        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        assert result["action"] == "no_match"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_race_integrity_error_falls_back_to_append(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """A concurrent insert that violates the partial unique index folds in."""
        cancel_msg = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        )
        existing = _make_open_request(appointment_id=cancel_msg.appointment_id)

        # Order: find_cancellation_thread → open lookup (None) →
        # post-IntegrityError re-query finds the winner.
        mock_db.execute = _make_execute_side_effect(cancel_msg, None, existing)

        # Have begin_nested's async __aexit__ raise IntegrityError to mimic
        # the partial-unique-index collision.
        class _FailingSavepoint:
            async def __aenter__(self) -> Any:
                return None

            async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
                stmt_text = "stmt"
                params_text = "params"
                cause_msg = "collision"
                raise IntegrityError(
                    stmt_text,
                    params_text,
                    Exception(cause_msg),
                )

        mock_db.begin_nested = MagicMock(return_value=_FailingSavepoint())

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_requested"
        assert result.get("duplicate") is True


# ---------------------------------------------------------------------------
# Gap 3.A — reconsider-cancellation alert dispatch
# ---------------------------------------------------------------------------


class TestReconsiderCancellationAlert:
    """``_dispatch_reconsider_cancellation_alert`` log-and-swallow contract."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alert_dispatch_never_raises_on_email_failure(
        self,
        mock_db: AsyncMock,
    ) -> None:
        from unittest.mock import patch as _patch

        customer = Mock()
        customer.full_name = "Jane Doe"
        mock_db.get = AsyncMock(return_value=customer)
        svc = JobConfirmationService(mock_db)

        failing_notification = MagicMock()
        failing_notification.send_admin_reconsider_cancellation_alert = AsyncMock(
            side_effect=RuntimeError("SMTP unreachable"),
        )

        with _patch(
            "grins_platform.services.notification_service.NotificationService",
            return_value=failing_notification,
        ):
            # Must not raise even when the inner service errors.
            await svc._dispatch_reconsider_cancellation_alert(
                appointment_id=uuid4(),
                customer_id=uuid4(),
                appt=_make_appointment(status=AppointmentStatus.CANCELLED.value),
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alert_dispatch_rejects_when_customer_missing(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Customer not found → log rejected, swallow silently."""
        mock_db.get = AsyncMock(return_value=None)
        svc = JobConfirmationService(mock_db)
        # Should not raise; inner notification is never constructed.
        await svc._dispatch_reconsider_cancellation_alert(
            appointment_id=uuid4(),
            customer_id=uuid4(),
            appt=None,
        )

    @pytest.mark.unit
    def test_alert_type_enum_member_exists(self) -> None:
        assert (
            AlertType.CUSTOMER_RECONSIDER_CANCELLATION.value
            == "customer_reconsider_cancellation"
        )


# ---------------------------------------------------------------------------
# Gap 3.B — stale-thread reply telemetry
# ---------------------------------------------------------------------------


class TestStaleThreadReply:
    """A Y on a superseded confirmation thread routes to audit + auto-reply."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stale_thread_returns_stale_reply_action_and_auto_reply(
        self,
        mock_db: AsyncMock,
    ) -> None:
        superseded = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CONFIRMATION.value,
            superseded_at=datetime.now(tz=timezone.utc),
        )
        # Order: find_confirmation_message (None, active row missing) →
        #        _find_superseded_confirmation_for_thread → superseded row
        mock_db.execute = _make_execute_side_effect(None, superseded)
        svc = JobConfirmationService(mock_db)

        result = await svc.handle_confirmation(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="Y",
            from_phone="+19527373312",
        )

        assert result["action"] == "stale_thread_reply"
        assert result["recipient_phone"] == "+19527373312"
        assert "auto_reply" in result
        assert "updated" in result["auto_reply"].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stale_thread_writes_audit_row(
        self,
        mock_db: AsyncMock,
    ) -> None:
        superseded = _make_sent_message(
            message_type=MessageType.APPOINTMENT_RESCHEDULE.value,
            superseded_at=datetime.now(tz=timezone.utc),
        )
        mock_db.execute = _make_execute_side_effect(None, superseded)
        svc = JobConfirmationService(mock_db)

        await svc.handle_confirmation(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="Y",
            from_phone="+19527373312",
        )

        # A JobConfirmationResponse with status='stale_thread_reply' was added.
        added = [c.args[0] for c in mock_db.add.call_args_list]
        stale_rows = [
            o
            for o in added
            if type(o).__name__ == "JobConfirmationResponse"
            and getattr(o, "status", None) == "stale_thread_reply"
        ]
        assert len(stale_rows) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_legitimate_match_does_not_run_stale_path(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """When confirmation lookup matches, stale-thread branch never fires."""
        active = _make_sent_message(
            message_type=MessageType.APPOINTMENT_CONFIRMATION.value,
        )
        scheduled_appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        mock_db.execute = _make_execute_side_effect(active)
        mock_db.get = AsyncMock(return_value=scheduled_appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-corr",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="Y",
            from_phone="+19527373312",
        )

        assert result["action"] == "confirmed"
        # Only one execute call — no stale-thread lookup was attempted.
        assert mock_db.execute.await_count == 1
