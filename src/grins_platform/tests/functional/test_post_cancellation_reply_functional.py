"""Functional tests for the post-cancellation reply flow (gap-03 3.A).

Mirrors the mock-DB factory pattern from
``test_yrc_confirmation_functional.py`` — the DB is mocked but the
service method runs end-to-end including the internal dispatcher.

Validates: gap-03 (3.A post-cancellation reply).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    AppointmentStatus,
    ConfirmationKeyword,
    MessageType,
)
from grins_platform.models.job_confirmation import (
    JobConfirmationResponse,
    RescheduleRequest,
)
from grins_platform.services.job_confirmation_service import (
    JobConfirmationService,
)


def _make_cancellation_sent_message(**overrides: Any) -> MagicMock:
    msg = MagicMock()
    msg.id = overrides.get("id", uuid4())
    msg.customer_id = overrides.get("customer_id", uuid4())
    msg.job_id = overrides.get("job_id", uuid4())
    msg.appointment_id = overrides.get("appointment_id", uuid4())
    msg.message_type = MessageType.APPOINTMENT_CANCELLATION.value
    msg.provider_thread_id = overrides.get("provider_thread_id", "thread-pc")
    msg.recipient_phone = overrides.get("recipient_phone", "+19527373312")
    msg.superseded_at = None
    msg.created_at = datetime.now(tz=timezone.utc)
    return msg


def _build_mock_db(
    *,
    cancellation_msg: MagicMock,
    appointment: MagicMock | None = None,
    existing_open_request: MagicMock | None = None,
) -> AsyncMock:
    """Stateful-ish mock session.

    ``db.execute`` routes queries by compiled-SQL substrings:
    - ``reschedule_requests`` → returns ``existing_open_request`` (or None).
    - otherwise (sent_messages lookup) → returns ``cancellation_msg``.
    """
    db = AsyncMock()
    db._added_objects: list[Any] = []

    def _add_side_effect(obj: Any) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid4()
        db._added_objects.append(obj)

    db.add = MagicMock(side_effect=_add_side_effect)
    db.flush = AsyncMock()
    db.begin_nested = MagicMock(return_value=AsyncMock())

    async def _execute_side_effect(stmt: Any, *args: Any, **kwargs: Any) -> MagicMock:
        try:
            compiled = str(
                stmt.compile(compile_kwargs={"literal_binds": True}),
            ).lower()
        except Exception:
            compiled = str(stmt).lower()
        result = MagicMock()
        if "reschedule_requests" in compiled:
            result.scalar_one_or_none.return_value = existing_open_request
        else:
            result.scalar_one_or_none.return_value = cancellation_msg
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)

    async def _get_side_effect(model: Any, _pk: Any) -> Any:
        if model.__name__ == "Appointment":
            return appointment
        return None

    db.get = AsyncMock(side_effect=_get_side_effect)
    return db


@pytest.mark.functional
@pytest.mark.asyncio
class TestPostCancelRescheduleFlow:
    """R on a cancellation thread creates a RescheduleRequest."""

    async def test_creates_reschedule_request_and_returns_follow_up_sms(
        self,
    ) -> None:
        cancel_msg = _make_cancellation_sent_message()
        db = _build_mock_db(cancellation_msg=cancel_msg)

        svc = JobConfirmationService(db)
        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-pc",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        assert result["action"] == "post_cancel_reschedule_requested"
        assert "follow_up_sms" in result
        assert "auto_reply" in result

        responses = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        reschedules = [o for o in db._added_objects if isinstance(o, RescheduleRequest)]
        assert len(responses) == 1
        assert len(reschedules) == 1
        assert reschedules[0].status == "open"
        assert reschedules[0].raw_alternatives_text == "R"
        assert responses[0].status == "reschedule_requested"


@pytest.mark.functional
@pytest.mark.asyncio
class TestPostCancelReconsiderFlow:
    """Y on a cancellation thread dispatches the reconsider alert."""

    async def test_dispatches_admin_alert_and_no_status_change(self) -> None:
        cancel_msg = _make_cancellation_sent_message()
        appointment = MagicMock()
        appointment.id = cancel_msg.appointment_id
        appointment.status = AppointmentStatus.CANCELLED.value
        db = _build_mock_db(
            cancellation_msg=cancel_msg,
            appointment=appointment,
        )

        svc = JobConfirmationService(db)
        dispatch_spy = AsyncMock()
        svc._dispatch_reconsider_cancellation_alert = dispatch_spy  # type: ignore[method-assign]

        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-pc",
            keyword=ConfirmationKeyword.CONFIRM,
            raw_body="Y",
            from_phone="+19527373312",
        )

        assert result["action"] == "post_cancel_reconsider_pending"
        assert appointment.status == AppointmentStatus.CANCELLED.value
        dispatch_spy.assert_awaited_once()

        responses = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        reschedules = [o for o in db._added_objects if isinstance(o, RescheduleRequest)]
        assert len(responses) == 1
        assert responses[0].status == "cancel_reconsider_pending"
        assert len(reschedules) == 0


@pytest.mark.functional
@pytest.mark.asyncio
class TestPostCancelNeedsReview:
    """Unknown keyword / free text routes to needs_review."""

    async def test_unknown_reply_logs_needs_review(self) -> None:
        cancel_msg = _make_cancellation_sent_message()
        db = _build_mock_db(cancellation_msg=cancel_msg)

        svc = JobConfirmationService(db)
        result = await svc.handle_post_cancellation_reply(
            thread_id="thread-pc",
            keyword=None,
            raw_body="wait actually I still want it",
            from_phone="+19527373312",
        )

        assert result["action"] == "needs_review"

        responses = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        reschedules = [o for o in db._added_objects if isinstance(o, RescheduleRequest)]
        assert len(responses) == 1
        assert responses[0].status == "needs_review"
        assert len(reschedules) == 0
