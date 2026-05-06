"""Unit tests for the reschedule lifecycle hardening (gap-01).

Covers three lifecycle defects in the customer-facing "R" reply flow:

1.A  Duplicate ``RescheduleRequest`` rows from repeated "R" replies.
1.B  "R" accepted while the appointment is already in a field-work or
     terminal state.
1.C  Free-text alternatives text not attaching to the open request
     because thread correlation filtered out ``RESCHEDULE_FOLLOWUP``.

Validates: gap-01 (1.A, 1.B, 1.C).
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
) -> Mock:
    msg = Mock()
    msg.id = uuid4()
    msg.appointment_id = appointment_id or uuid4()
    msg.job_id = job_id or uuid4()
    msg.customer_id = customer_id or uuid4()
    msg.message_type = message_type
    msg.provider_thread_id = "thread-123"
    msg.recipient_phone = "+19527373312"
    msg.created_at = datetime.now(tz=timezone.utc)
    return msg


def _make_appointment(*, status: str = AppointmentStatus.SCHEDULED.value) -> Mock:
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
    # begin_nested is used for the savepoint around the insert. AsyncMock()
    # natively supports async-context-manager usage.
    db.begin_nested = MagicMock(return_value=AsyncMock())
    return db


def _make_execute_side_effect(*return_values: Any) -> AsyncMock:
    """Build an `AsyncMock` for db.execute that cycles through canned results.

    Each positional value becomes the ``scalar_one_or_none`` return value of
    the next ``db.execute`` call — the pattern already used by
    ``test_job_confirmation_service.py``.
    """
    results = []
    for value in return_values:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = value
        results.append(result_mock)
    return AsyncMock(side_effect=results)


# ---------------------------------------------------------------------------
# Gap 1.A — idempotency
# ---------------------------------------------------------------------------


class TestRescheduleIdempotency:
    """A second "R" for the same appointment folds into the existing row."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_second_r_reply_reuses_open_request(
        self,
        mock_db: AsyncMock,
    ) -> None:
        sent_msg = _make_sent_message()
        scheduled_appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        existing = _make_open_request(appointment_id=sent_msg.appointment_id)
        existing.raw_alternatives_text = "first body"

        # Order: find_confirmation_message -> open-request lookup
        mock_db.execute = _make_execute_side_effect(sent_msg, existing)
        mock_db.get = AsyncMock(return_value=scheduled_appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="second R",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_requested"
        assert result["duplicate"] is True
        assert result["reschedule_request_id"] == str(existing.id)
        # A new RescheduleRequest was NOT added — only the response row.
        added_models = [c.args[0] for c in mock_db.add.call_args_list]
        assert not any(
            type(obj).__name__ == "RescheduleRequest" for obj in added_models
        )
        # Existing row grew with the new body.
        assert "first body" in existing.raw_alternatives_text
        assert "second R" in existing.raw_alternatives_text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_second_r_reply_omits_followup_sms(
        self,
        mock_db: AsyncMock,
    ) -> None:
        sent_msg = _make_sent_message()
        scheduled_appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        existing = _make_open_request(appointment_id=sent_msg.appointment_id)

        mock_db.execute = _make_execute_side_effect(sent_msg, existing)
        mock_db.get = AsyncMock(return_value=scheduled_appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R again",
            from_phone="+19527373312",
        )

        assert "follow_up_sms" not in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resolved_request_does_not_block_new_r(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """A ``status='resolved'`` row must NOT short-circuit a new "R"."""
        sent_msg = _make_sent_message()
        scheduled_appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)

        # Open-request lookup filters to status='open', so resolved rows
        # are simply not returned. Simulate with None.
        mock_db.execute = _make_execute_side_effect(sent_msg, None)
        mock_db.get = AsyncMock(return_value=scheduled_appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_requested"
        # User directive 2026-05-05: collapsed receipt + follow-up nudge
        # into one actionable auto_reply. The legacy ``follow_up_sms``
        # slot is intentionally absent now.
        assert "auto_reply" in result
        assert "2-3 dates" in result["auto_reply"]
        assert "follow_up_sms" not in result
        assert result.get("duplicate") is not True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_integrity_error_on_race_treated_as_dedup(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """A partial-index IntegrityError on flush maps to the duplicate branch."""
        sent_msg = _make_sent_message()
        scheduled_appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        winner = _make_open_request(appointment_id=sent_msg.appointment_id)
        winner.raw_alternatives_text = "race winner body"

        # execute() calls, in order:
        #   1. find_confirmation_message → sent_msg
        #   2. open-request lookup before insert → None
        #   3. re-run lookup after IntegrityError → winner row
        mock_db.execute = _make_execute_side_effect(sent_msg, None, winner)
        mock_db.get = AsyncMock(return_value=scheduled_appt)

        # Savepoint raises IntegrityError on __aexit__ to simulate the
        # concurrent insert winning the race.
        nested_cm = AsyncMock()
        nested_cm.__aenter__ = AsyncMock(return_value=None)
        nested_cm.__aexit__ = AsyncMock(
            side_effect=IntegrityError("duplicate", None, Exception("dup")),
        )
        mock_db.begin_nested = MagicMock(return_value=nested_cm)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="loser body",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_requested"
        assert result["duplicate"] is True
        assert result["reschedule_request_id"] == str(winner.id)
        assert "loser body" in winner.raw_alternatives_text


# ---------------------------------------------------------------------------
# Gap 1.B — state guard
# ---------------------------------------------------------------------------


class TestRescheduleStateGuard:
    """ "R" replies during field-work or terminal states are rejected."""

    async def _run(
        self,
        mock_db: AsyncMock,
        status: str,
        *,
        monkeypatch: pytest.MonkeyPatch | None = None,
    ) -> dict[str, Any]:
        if monkeypatch is not None:
            monkeypatch.setenv("BUSINESS_PHONE_NUMBER", "(612) 555-9999")
        sent_msg = _make_sent_message()
        appt = _make_appointment(status=status)
        mock_db.execute = _make_execute_side_effect(sent_msg)
        mock_db.get = AsyncMock(return_value=appt)

        # Stub the alert dispatch so the test is isolated to the handler.
        svc = JobConfirmationService(mock_db)
        svc._dispatch_late_reschedule_alert = AsyncMock()  # type: ignore[method-assign]

        return await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_in_en_route_returns_late_reply_and_no_request(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = await self._run(
            mock_db,
            AppointmentStatus.EN_ROUTE.value,
            monkeypatch=monkeypatch,
        )

        assert result["action"] == "reschedule_rejected"
        assert result["current_status"] == AppointmentStatus.EN_ROUTE.value
        assert "on the way" in result["auto_reply"]
        added_models = [c.args[0] for c in mock_db.add.call_args_list]
        assert not any(
            type(obj).__name__ == "RescheduleRequest" for obj in added_models
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_in_in_progress_returns_on_site_message(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = await self._run(
            mock_db,
            AppointmentStatus.IN_PROGRESS.value,
            monkeypatch=monkeypatch,
        )

        assert result["action"] == "reschedule_rejected"
        assert "on site" in result["auto_reply"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_in_completed_returns_completed_message(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = await self._run(
            mock_db,
            AppointmentStatus.COMPLETED.value,
            monkeypatch=monkeypatch,
        )

        assert result["action"] == "reschedule_rejected"
        assert "completed" in result["auto_reply"].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_in_cancelled_returns_inactive_message(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = await self._run(
            mock_db,
            AppointmentStatus.CANCELLED.value,
            monkeypatch=monkeypatch,
        )

        assert result["action"] == "reschedule_rejected"
        assert "no longer active" in result["auto_reply"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_in_no_show_returns_inactive_message(
        self,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = await self._run(
            mock_db,
            AppointmentStatus.NO_SHOW.value,
            monkeypatch=monkeypatch,
        )

        assert result["action"] == "reschedule_rejected"
        assert "no longer active" in result["auto_reply"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_late_reschedule_dispatches_alert(
        self,
        mock_db: AsyncMock,
    ) -> None:
        sent_msg = _make_sent_message()
        appt = _make_appointment(status=AppointmentStatus.EN_ROUTE.value)
        mock_db.execute = _make_execute_side_effect(sent_msg)
        mock_db.get = AsyncMock(return_value=appt)

        svc = JobConfirmationService(mock_db)
        dispatch_spy = AsyncMock()
        svc._dispatch_late_reschedule_alert = dispatch_spy  # type: ignore[method-assign]

        await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        dispatch_spy.assert_awaited_once()
        kwargs = dispatch_spy.await_args.kwargs
        assert kwargs["appointment_id"] == sent_msg.appointment_id
        assert kwargs["customer_id"] == sent_msg.customer_id
        assert kwargs["appt"] is appt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_with_missing_appointment_falls_through_to_normal_path(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """``appt is None`` is a silent edge case; the happy path runs."""
        sent_msg = _make_sent_message()
        # find_confirmation_message, then open-request lookup (None).
        mock_db.execute = _make_execute_side_effect(sent_msg, None)
        mock_db.get = AsyncMock(return_value=None)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_requested"
        # User directive 2026-05-05: single actionable auto_reply
        # replaces the prior receipt + follow-up two-SMS flow.
        assert "2-3 dates" in result["auto_reply"]
        assert "follow_up_sms" not in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_r_in_scheduled_still_works(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """SCHEDULED is not in the blocked set — happy path is untouched."""
        sent_msg = _make_sent_message()
        scheduled_appt = _make_appointment(status=AppointmentStatus.SCHEDULED.value)
        mock_db.execute = _make_execute_side_effect(sent_msg, None)
        mock_db.get = AsyncMock(return_value=scheduled_appt)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_requested"
        # User directive 2026-05-05: single actionable auto_reply
        # replaces the prior receipt + follow-up two-SMS flow.
        assert "2-3 dates" in result["auto_reply"]
        assert "follow_up_sms" not in result


# ---------------------------------------------------------------------------
# Gap 1.C — follow-up correlation
# ---------------------------------------------------------------------------


class TestFollowupCorrelation:
    """Free-text replies on the reschedule-followup thread land on the open row."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_followup_thread_lookup_matches_reschedule_followup_message_type(
        self,
        mock_db: AsyncMock,
    ) -> None:
        followup_msg = _make_sent_message(
            message_type=MessageType.RESCHEDULE_FOLLOWUP.value,
        )
        mock_db.execute = _make_execute_side_effect(followup_msg)

        svc = JobConfirmationService(mock_db)
        result = await svc.find_reschedule_thread("thread-123")

        assert result is followup_msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_free_text_reply_on_followup_thread_attaches_to_open_request(
        self,
        mock_db: AsyncMock,
    ) -> None:
        followup_msg = _make_sent_message(
            message_type=MessageType.RESCHEDULE_FOLLOWUP.value,
        )
        open_req = _make_open_request(appointment_id=followup_msg.appointment_id)

        # Order of execute calls:
        #   1. find_confirmation_message → None (follow-up-only thread)
        #   2. find_reschedule_thread   → followup_msg
        #   3. _handle_needs_review open-request lookup → open_req
        mock_db.execute = _make_execute_side_effect(None, followup_msg, open_req)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=None,
            raw_body="How about Tuesday at 2pm?",
            from_phone="+19527373312",
        )

        assert result["action"] == "reschedule_alternatives_received"
        assert open_req.requested_alternatives is not None
        entries = open_req.requested_alternatives["entries"]
        assert entries[-1]["text"] == "How about Tuesday at 2pm?"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_keyword_reply_on_followup_thread_ignored_for_confirmation(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Y/R/C keywords must not reopen through the follow-up thread."""
        # Execute order (gap-03):
        #   1. find_confirmation_message → None (no active confirmation)
        #   2. _find_superseded_confirmation_for_thread → None (not a
        #      stale thread either)
        # Follow-up lookup is explicitly NOT consulted for keyword replies.
        mock_db.execute = _make_execute_side_effect(None, None)

        svc = JobConfirmationService(mock_db)
        result = await svc.handle_confirmation(
            thread_id="thread-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        assert result["action"] == "no_match"
        # Confirmation lookup + stale-thread lookup — no follow-up lookup.
        assert mock_db.execute.await_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_followup_replies_all_append(
        self,
        mock_db: AsyncMock,
    ) -> None:
        followup_msg = _make_sent_message(
            message_type=MessageType.RESCHEDULE_FOLLOWUP.value,
        )
        open_req = _make_open_request(appointment_id=followup_msg.appointment_id)

        svc = JobConfirmationService(mock_db)

        bodies = ["Tue 2pm", "or Wed morning", "or Fri 9am"]
        for body in bodies:
            # Three execute() calls per handle_confirmation:
            #   find_confirmation_message (None),
            #   find_reschedule_thread (followup_msg),
            #   open-request lookup in _handle_needs_review (open_req).
            mock_db.execute = _make_execute_side_effect(
                None,
                followup_msg,
                open_req,
            )
            await svc.handle_confirmation(
                thread_id="thread-123",
                keyword=None,
                raw_body=body,
                from_phone="+19527373312",
            )

        entries = open_req.requested_alternatives["entries"]
        assert [e["text"] for e in entries] == bodies


# ---------------------------------------------------------------------------
# Task 5 — late reschedule alert
# ---------------------------------------------------------------------------


class TestLateRescheduleAlert:
    """Coverage for ``NotificationService.send_admin_late_reschedule_alert``."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alert_row_persisted_with_correct_type_and_severity(
        self,
    ) -> None:
        from grins_platform.models.enums import AlertSeverity
        from grins_platform.services.notification_service import NotificationService

        db = AsyncMock()
        captured: list[Any] = []

        class _StubRepo:
            def __init__(self, _db: Any) -> None:
                pass

            async def create(self, alert: Any) -> Any:
                captured.append(alert)
                return alert

        import grins_platform.repositories.alert_repository as alert_repo_mod

        original_cls = alert_repo_mod.AlertRepository
        alert_repo_mod.AlertRepository = _StubRepo  # type: ignore[assignment,misc]
        try:
            svc = NotificationService(email_service=None)
            await svc.send_admin_late_reschedule_alert(
                db,
                appointment_id=uuid4(),
                customer_id=uuid4(),
                customer_name="Jane Doe",
                scheduled_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
                current_status=AppointmentStatus.EN_ROUTE.value,
            )
        finally:
            alert_repo_mod.AlertRepository = original_cls  # type: ignore[assignment,misc]

        assert len(captured) == 1
        alert = captured[0]
        assert alert.type == AlertType.LATE_RESCHEDULE_ATTEMPT.value
        assert alert.severity == AlertSeverity.WARNING.value
        assert alert.entity_type == "appointment"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alert_email_has_current_status_in_subject(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from grins_platform.services.notification_service import NotificationService

        # Force a configured admin recipient so the email path runs.
        monkeypatch.setenv("ADMIN_NOTIFICATION_EMAIL", "admin@example.com")

        email_service = Mock()
        email_service._send_email = Mock()

        svc = NotificationService(email_service=email_service)
        # Pre-seed the settings to bypass lazy pydantic lookup.
        svc.admin_settings = Mock()
        svc.admin_settings.admin_notification_email = "admin@example.com"

        db = AsyncMock()
        # Avoid exercising the Alert-row branch in this test.
        import grins_platform.repositories.alert_repository as alert_repo_mod

        class _StubRepo:
            def __init__(self, _db: Any) -> None:
                pass

            async def create(self, _alert: Any) -> Any:
                return None

        original_cls = alert_repo_mod.AlertRepository
        alert_repo_mod.AlertRepository = _StubRepo  # type: ignore[assignment,misc]
        try:
            await svc.send_admin_late_reschedule_alert(
                db,
                appointment_id=uuid4(),
                customer_id=uuid4(),
                customer_name="Jane Doe",
                scheduled_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
                current_status=AppointmentStatus.IN_PROGRESS.value,
            )
        finally:
            alert_repo_mod.AlertRepository = original_cls  # type: ignore[assignment,misc]

        email_service._send_email.assert_called_once()
        subject = email_service._send_email.call_args.kwargs["subject"]
        assert "Late reschedule attempt" in subject
        assert AppointmentStatus.IN_PROGRESS.value in subject

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alert_dispatch_never_raises(
        self,
    ) -> None:
        from grins_platform.services.notification_service import NotificationService

        db = AsyncMock()

        class _RaisingRepo:
            def __init__(self, _db: Any) -> None:
                pass

            async def create(self, _alert: Any) -> Any:
                msg = "db boom"
                raise RuntimeError(msg)

        import grins_platform.repositories.alert_repository as alert_repo_mod

        original_cls = alert_repo_mod.AlertRepository
        alert_repo_mod.AlertRepository = _RaisingRepo  # type: ignore[assignment,misc]
        try:
            svc = NotificationService(email_service=None)
            # Must NOT raise.
            result = await svc.send_admin_late_reschedule_alert(
                db,
                appointment_id=uuid4(),
                customer_id=uuid4(),
                customer_name="Jane Doe",
                scheduled_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
                current_status=AppointmentStatus.COMPLETED.value,
            )
        finally:
            alert_repo_mod.AlertRepository = original_cls  # type: ignore[assignment,misc]

        assert result is None
