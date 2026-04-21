"""Integration tests for the thread-correlation hardening (gap-03).

Uses the same in-memory ``_StatefulDb`` pattern as
``test_reschedule_lifecycle_integration.py`` but teaches the execute
stub to distinguish ``superseded_at IS NULL`` from the inverted
predicate so the two classes of correlation lookup (active vs.
stale-thread-telemetry) return their correct rows.

Validates: gap-03 (3.A, 3.B).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any
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
)


class _StatefulDb:
    """In-memory session stub that routes queries by compiled SQL."""

    def __init__(
        self,
        *,
        sent_messages: list[Mock],
        appt: Mock,
    ) -> None:
        self.sent_messages = sent_messages
        self.appt = appt
        self.reschedule_rows: list[Any] = []
        self.response_rows: list[Any] = []
        self.flush = AsyncMock()
        self.begin_nested = MagicMock(return_value=AsyncMock())

    def add(self, obj: Any) -> None:
        cls_name = type(obj).__name__
        if cls_name == "RescheduleRequest":
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            self.reschedule_rows.append(obj)
        elif cls_name == "JobConfirmationResponse":
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            self.response_rows.append(obj)

    async def get(self, _model: Any, _pk: Any) -> Any:
        return self.appt

    async def execute(self, stmt: Any) -> Any:
        try:
            compiled = str(
                stmt.compile(compile_kwargs={"literal_binds": True}),
            ).lower()
        except Exception:
            compiled = str(stmt).lower()

        result = MagicMock()

        if "reschedule_requests" in compiled:
            open_rows = [
                r for r in self.reschedule_rows if getattr(r, "status", None) == "open"
            ]
            result.scalar_one_or_none.return_value = (
                sorted(open_rows, key=lambda r: getattr(r, "created_at", 0))[0]
                if open_rows
                else None
            )
            return result

        if "sent_messages" in compiled:
            # Filter candidate rows by the superseded_at predicate.
            want_active = (
                "superseded_at is null" in compiled and "is not null" not in compiled
            )
            want_stale = "superseded_at is not null" in compiled

            candidates = list(self.sent_messages)
            if want_active:
                candidates = [m for m in candidates if m.superseded_at is None]
            elif want_stale:
                candidates = [m for m in candidates if m.superseded_at is not None]

            # Filter by message_type using the compiled SQL hint.
            def _type_matches(msg: Mock) -> bool:
                mt = msg.message_type
                return mt in compiled

            typed = [m for m in candidates if _type_matches(m)]
            if typed:
                typed.sort(key=lambda m: m.created_at, reverse=True)
                result.scalar_one_or_none.return_value = typed[0]
            else:
                result.scalar_one_or_none.return_value = None
            return result

        result.scalar_one_or_none.return_value = None
        return result


def _make_sent_msg(
    *,
    message_type: str,
    superseded_at: datetime | None,
    appointment_id: Any,
    customer_id: Any,
    job_id: Any,
    created_at: datetime,
    thread_id: str = "thread-int",
) -> Mock:
    msg = Mock()
    msg.id = uuid4()
    msg.appointment_id = appointment_id
    msg.customer_id = customer_id
    msg.job_id = job_id
    msg.message_type = message_type
    msg.provider_thread_id = thread_id
    msg.recipient_phone = "+19527373312"
    msg.superseded_at = superseded_at
    msg.created_at = created_at
    return msg


def _make_appt(*, status: str) -> Mock:
    appt = Mock()
    appt.id = uuid4()
    appt.status = status
    appt.scheduled_date = date(2026, 5, 1)
    appt.time_window_start = time(9, 0)
    appt.time_window_end = time(11, 0)
    return appt


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reschedule_notification_reply_y_routes_through_widened_lookup() -> None:
    """Gap 3.A: a Y reply on a reschedule-notification SMS confirms the new date.

    Seed: superseded CONFIRMATION row + active RESCHEDULE row.
    Reply Y → handle_confirmation matches the RESCHEDULE row, transitions
    SCHEDULED → CONFIRMED, writes a ``confirmed`` response row.
    """
    appt_id = uuid4()
    cust_id = uuid4()
    job_id = uuid4()
    base = datetime.now(tz=timezone.utc)

    confirmation = _make_sent_msg(
        message_type=MessageType.APPOINTMENT_CONFIRMATION.value,
        superseded_at=base,  # tombstoned by the reschedule
        appointment_id=appt_id,
        customer_id=cust_id,
        job_id=job_id,
        created_at=base,
    )
    reschedule_notification = _make_sent_msg(
        message_type=MessageType.APPOINTMENT_RESCHEDULE.value,
        superseded_at=None,
        appointment_id=appt_id,
        customer_id=cust_id,
        job_id=job_id,
        created_at=base.replace(microsecond=base.microsecond + 1),
    )
    appt = _make_appt(status=AppointmentStatus.SCHEDULED.value)

    db = _StatefulDb(
        sent_messages=[confirmation, reschedule_notification],
        appt=appt,
    )
    svc = JobConfirmationService(db)  # type: ignore[arg-type]

    result = await svc.handle_confirmation(
        thread_id="thread-int",
        keyword=ConfirmationKeyword.CONFIRM,
        raw_body="Y",
        from_phone="+19527373312",
    )

    assert result["action"] == "confirmed"
    assert appt.status == AppointmentStatus.CONFIRMED.value
    # The response row references the active (reschedule) SentMessage.
    assert db.response_rows[0].sent_message_id == reschedule_notification.id
    assert db.response_rows[0].status == "confirmed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancellation_reply_r_opens_new_reschedule_request() -> None:
    """Gap 3.A post-cancel: R reply on a CANCELLATION thread opens a request."""
    appt_id = uuid4()
    cust_id = uuid4()
    job_id = uuid4()
    base = datetime.now(tz=timezone.utc)

    cancellation = _make_sent_msg(
        message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        superseded_at=None,
        appointment_id=appt_id,
        customer_id=cust_id,
        job_id=job_id,
        created_at=base,
    )
    appt = _make_appt(status=AppointmentStatus.CANCELLED.value)

    db = _StatefulDb(sent_messages=[cancellation], appt=appt)
    svc = JobConfirmationService(db)  # type: ignore[arg-type]

    result = await svc.handle_post_cancellation_reply(
        thread_id="thread-int",
        keyword=ConfirmationKeyword.RESCHEDULE,
        raw_body="R",
        from_phone="+19527373312",
    )

    assert result["action"] == "post_cancel_reschedule_requested"
    # A reschedule_requests row was created for the CANCELLED appointment.
    assert len(db.reschedule_rows) == 1
    assert db.reschedule_rows[0].status == "open"
    assert db.reschedule_rows[0].appointment_id == appt_id
    # The appointment status remains CANCELLED — reactivation is manual.
    assert appt.status == AppointmentStatus.CANCELLED.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancellation_reply_y_raises_reconsider_alert_no_status_change() -> None:
    """Gap 3.A: Y on a CANCELLATION thread raises alert, status stays CANCELLED."""
    appt_id = uuid4()
    cust_id = uuid4()
    job_id = uuid4()
    base = datetime.now(tz=timezone.utc)

    cancellation = _make_sent_msg(
        message_type=MessageType.APPOINTMENT_CANCELLATION.value,
        superseded_at=None,
        appointment_id=appt_id,
        customer_id=cust_id,
        job_id=job_id,
        created_at=base,
    )
    appt = _make_appt(status=AppointmentStatus.CANCELLED.value)

    db = _StatefulDb(sent_messages=[cancellation], appt=appt)
    svc = JobConfirmationService(db)  # type: ignore[arg-type]
    dispatch_spy = AsyncMock()
    svc._dispatch_reconsider_cancellation_alert = dispatch_spy  # type: ignore[method-assign]

    result = await svc.handle_post_cancellation_reply(
        thread_id="thread-int",
        keyword=ConfirmationKeyword.CONFIRM,
        raw_body="Y",
        from_phone="+19527373312",
    )

    assert result["action"] == "post_cancel_reconsider_pending"
    assert appt.status == AppointmentStatus.CANCELLED.value
    dispatch_spy.assert_awaited_once()
    assert db.response_rows[0].status == "cancel_reconsider_pending"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stale_confirmation_thread_y_writes_stale_reply_audit() -> None:
    """Gap 3.B: Y on a superseded-only thread → stale_thread_reply audit."""
    appt_id = uuid4()
    cust_id = uuid4()
    job_id = uuid4()
    base = datetime.now(tz=timezone.utc)

    # Only a superseded confirmation row — no active row at all for the
    # customer's (stale) thread.
    superseded = _make_sent_msg(
        message_type=MessageType.APPOINTMENT_CONFIRMATION.value,
        superseded_at=base,
        appointment_id=appt_id,
        customer_id=cust_id,
        job_id=job_id,
        created_at=base,
    )
    appt = _make_appt(status=AppointmentStatus.CONFIRMED.value)

    db = _StatefulDb(sent_messages=[superseded], appt=appt)
    svc = JobConfirmationService(db)  # type: ignore[arg-type]

    result = await svc.handle_confirmation(
        thread_id="thread-int",
        keyword=ConfirmationKeyword.CONFIRM,
        raw_body="Y",
        from_phone="+19527373312",
    )

    assert result["action"] == "stale_thread_reply"
    # No status mutation — the appointment wasn't touched.
    assert appt.status == AppointmentStatus.CONFIRMED.value
    # An audit row was written with the stale-reply status.
    stale_rows = [r for r in db.response_rows if r.status == "stale_thread_reply"]
    assert len(stale_rows) == 1
