"""Integration tests for the reschedule-lifecycle gap-01 hardening.

A full webhook-to-Postgres integration test is out of scope for local CI
(requires a live Postgres + Alembic migrations). This module instead
exercises :meth:`JobConfirmationService.handle_confirmation` across two
sequential calls with an in-memory row-tracking mock session, closing
the gap between the unit tests (which stub the DB fully) and the real
webhook flow.

Validates: gap-01 (1.A idempotency at the service boundary).
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
    """Thin async-DB stub that tracks RescheduleRequest rows in memory.

    Stops short of actually resolving SQLAlchemy statements — it inspects
    the *type* the service is looking for (sent message vs reschedule
    request) by checking which table is being queried, and returns the
    tracked row accordingly.
    """

    def __init__(self, sent_msg: Mock, appt: Mock) -> None:
        self.sent_msg = sent_msg
        self.appt = appt
        self.reschedule_rows: list[Any] = []
        self.response_rows: list[Any] = []
        self.flush = AsyncMock()
        self.begin_nested = MagicMock(return_value=AsyncMock())

    # ``async with db.begin_nested():`` support is wired via MagicMock above.

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
        stmt_sql = str(stmt).lower()
        result = MagicMock()
        if "sent_messages" in stmt_sql:
            result.scalar_one_or_none.return_value = self.sent_msg
            return result
        if "reschedule_requests" in stmt_sql:
            open_rows = [
                r for r in self.reschedule_rows if getattr(r, "status", None) == "open"
            ]
            result.scalar_one_or_none.return_value = (
                sorted(open_rows, key=lambda r: getattr(r, "created_at", 0))[0]
                if open_rows
                else None
            )
            return result
        result.scalar_one_or_none.return_value = None
        return result


def _make_sent_msg() -> Mock:
    msg = Mock()
    msg.id = uuid4()
    msg.appointment_id = uuid4()
    msg.job_id = uuid4()
    msg.customer_id = uuid4()
    msg.message_type = MessageType.APPOINTMENT_CONFIRMATION.value
    msg.provider_thread_id = "thread-xyz"
    msg.recipient_phone = "+19527373312"
    msg.created_at = datetime.now(tz=timezone.utc)
    return msg


def _make_appt() -> Mock:
    appt = Mock()
    appt.id = uuid4()
    appt.status = AppointmentStatus.SCHEDULED.value
    appt.scheduled_date = date(2026, 5, 1)
    appt.time_window_start = time(9, 0)
    appt.time_window_end = time(11, 0)
    return appt


@pytest.mark.integration
@pytest.mark.asyncio
async def test_double_r_creates_one_request() -> None:
    """Two sequential "R" replies create exactly one open request."""
    sent_msg = _make_sent_msg()
    appt = _make_appt()
    db = _StatefulDb(sent_msg=sent_msg, appt=appt)

    svc = JobConfirmationService(db)  # type: ignore[arg-type]

    # --- First R ---
    result1 = await svc.handle_confirmation(
        thread_id="thread-xyz",
        keyword=ConfirmationKeyword.RESCHEDULE,
        raw_body="R",
        from_phone="+19527373312",
    )
    assert result1["action"] == "reschedule_requested"
    assert result1.get("duplicate") is not True
    assert "follow_up_sms" in result1

    # --- Second R ---
    result2 = await svc.handle_confirmation(
        thread_id="thread-xyz",
        keyword=ConfirmationKeyword.RESCHEDULE,
        raw_body="R",
        from_phone="+19527373312",
    )
    assert result2["action"] == "reschedule_requested"
    assert result2["duplicate"] is True
    assert "follow_up_sms" not in result2
    # Same row id was reused.
    assert result2["reschedule_request_id"] == result1["reschedule_request_id"]

    # Exactly one open RescheduleRequest row tracked in the session.
    assert len(db.reschedule_rows) == 1
    only_row = db.reschedule_rows[0]
    assert only_row.status == "open"
    # Both bodies ended up on raw_alternatives_text.
    assert "R" in (only_row.raw_alternatives_text or "")
