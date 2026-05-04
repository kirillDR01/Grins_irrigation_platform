"""Functional tests for the full R-reply → admin-reschedule → new
confirmation-cycle flow.

Covers bughunt H-6: when a customer replies ``R`` (reschedule) and the
admin resolves the request via the Reschedule Requests queue, the
appointment must be moved to the new slot AND a fresh Y/R/C
confirmation SMS must be dispatched (SMS #1 again), not the one-way
"We moved your appointment to …" drag-drop notice.

Mocks the SMS provider so no real message is ever dispatched.

Validates: bughunt H-6
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus, ConfirmationKeyword
from grins_platform.models.job_confirmation import (
    JobConfirmationResponse,
    RescheduleRequest,
)
from grins_platform.services.appointment_service import AppointmentService
from grins_platform.services.job_confirmation_service import JobConfirmationService

# =============================================================================
# Helpers (mirrors test_yrc_confirmation_functional.py patterns)
# =============================================================================


def _make_sent_message(**overrides: Any) -> MagicMock:
    msg = MagicMock()
    msg.id = overrides.get("id", uuid4())
    msg.customer_id = overrides.get("customer_id", uuid4())
    msg.job_id = overrides.get("job_id", uuid4())
    msg.appointment_id = overrides.get("appointment_id", uuid4())
    msg.message_type = overrides.get("message_type", "appointment_confirmation")
    msg.provider_thread_id = overrides.get("provider_thread_id", "thread-abc-123")
    msg.recipient_phone = overrides.get("recipient_phone", "+19527373312")
    msg.delivery_status = overrides.get("delivery_status", "delivered")
    msg.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    return msg


def _make_appointment(**overrides: Any) -> MagicMock:
    appt = MagicMock()
    appt.id = overrides.get("id", uuid4())
    appt.job_id = overrides.get("job_id", uuid4())
    appt.staff_id = overrides.get("staff_id", uuid4())
    appt.scheduled_date = overrides.get("scheduled_date", date(2026, 4, 20))
    appt.time_window_start = overrides.get("time_window_start", time(9, 0))
    appt.time_window_end = overrides.get("time_window_end", time(11, 0))
    appt.status = overrides.get("status", AppointmentStatus.SCHEDULED.value)
    return appt


def _build_mock_db(
    *,
    sent_message: MagicMock | None = None,
    appointment: MagicMock | None = None,
) -> AsyncMock:
    db = AsyncMock()
    db._added_objects: list[Any] = []

    original_add = MagicMock()

    def _add_side_effect(obj: Any) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid4()
        db._added_objects.append(obj)
        original_add(obj)

    db.add = MagicMock(side_effect=_add_side_effect)

    async def _execute_side_effect(stmt: Any, params: Any = None) -> MagicMock:
        result = MagicMock()
        try:
            entity = stmt.column_descriptions[0].get("entity")
            entity_name = getattr(entity, "__name__", "")
        except (AttributeError, IndexError, KeyError):
            entity_name = ""

        # ``select(func.count())`` for invoice/appointment counts: default to 0.
        result.scalar_one.return_value = 0

        if entity_name == "Appointment":
            result.scalar_one_or_none.return_value = appointment
        elif entity_name == "RescheduleRequest":
            # No existing open RescheduleRequest — let _handle_reschedule
            # insert a fresh one rather than short-circuit on the seeded
            # sent_message row.
            result.scalar_one_or_none.return_value = None
        else:
            result.scalar_one_or_none.return_value = sent_message
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)

    async def _get_side_effect(model: Any, pk: Any) -> MagicMock | None:
        return appointment

    db.get = AsyncMock(side_effect=_get_side_effect)
    db.flush = AsyncMock()

    # ``async with db.begin_nested():`` is used by _handle_reschedule.
    nested_cm = AsyncMock()
    nested_cm.__aenter__ = AsyncMock(return_value=nested_cm)
    nested_cm.__aexit__ = AsyncMock(return_value=False)
    db.begin_nested = MagicMock(return_value=nested_cm)

    return db


# =============================================================================
# End-to-end: R reply → admin picks new date → new Y/R/C SMS fires
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestRescheduleFromRequestFlow:
    """H-6 functional coverage: the customer-requested reschedule path
    must produce at least two outbound SMS sends across the flow — one
    R-ack (from the initial R reply) and then a fresh SMS #1 when the
    admin picks the new date. The one-way ``_send_reschedule_sms`` must
    NOT fire on this path."""

    async def test_r_reply_then_admin_reschedule_triggers_new_y_r_c_prompt(
        self,
    ) -> None:
        """End-to-end H-6 coverage.

        1. Customer replies ``R`` → ``RescheduleRequest`` is created and
           the service returns a customer-facing ack (implicit: would be
           delivered as SMS; we assert on the persisted record + the
           auto_reply string since the reply itself is dispatched by the
           SMS service layer, which this test stubs).
        2. Admin resolves by calling ``reschedule_for_request`` with a
           new slot. That path must invoke ``_send_confirmation_sms``
           (Y/R/C again) and MUST NOT invoke ``_send_reschedule_sms``.

        Mocks the SMS provider — no real dispatch.
        """
        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=apt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(
            id=apt_id,
            job_id=job_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        # --- STEP 1: customer replies "R" -----------------------------
        jc_service = JobConfirmationService(db)
        r_result = await jc_service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        # A RescheduleRequest was persisted.
        reschedules = [o for o in db._added_objects if isinstance(o, RescheduleRequest)]
        assert len(reschedules) == 1
        assert reschedules[0].status == "open"

        # The customer receives an ack auto-reply (counted as "send #1"
        # below once the SMS service fires it). We assert the service
        # told the caller to dispatch one.
        assert r_result["action"] == "reschedule_requested"
        assert r_result.get("auto_reply")

        # And a JobConfirmationResponse with reschedule_requested status.
        confirmations = [
            o for o in db._added_objects if isinstance(o, JobConfirmationResponse)
        ]
        assert len(confirmations) == 1
        assert confirmations[0].status == "reschedule_requested"

        # --- STEP 2: admin resolves R-request via reschedule_for_request
        appt_repo = AsyncMock()
        # get_by_id returns the currently-scheduled appointment.
        current_appt = MagicMock()
        current_appt.id = apt_id
        current_appt.job_id = job_id
        current_appt.status = AppointmentStatus.SCHEDULED.value
        current_appt.scheduled_date = date(2026, 4, 20)
        current_appt.time_window_start = time(9, 0)
        current_appt.time_window_end = time(11, 0)
        appt_repo.get_by_id = AsyncMock(return_value=current_appt)

        updated_appt = MagicMock()
        updated_appt.id = apt_id
        updated_appt.job_id = job_id
        updated_appt.status = AppointmentStatus.SCHEDULED.value
        updated_appt.scheduled_date = date(2026, 4, 23)
        updated_appt.time_window_start = time(14, 0)
        updated_appt.time_window_end = time(16, 0)

        appt_repo.update = AsyncMock(return_value=updated_appt)
        appt_repo.session = AsyncMock()

        apt_svc = AppointmentService(
            appointment_repository=appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        # Stub both SMS helpers so we can count invocations.
        confirm_mock = AsyncMock(return_value={"success": True, "deferred": False})
        reschedule_mock = AsyncMock()
        audit_mock = AsyncMock()

        with (
            patch.object(apt_svc, "_send_confirmation_sms", confirm_mock),
            patch.object(apt_svc, "_send_reschedule_sms", reschedule_mock),
            patch.object(
                apt_svc,
                "_record_reschedule_reconfirmation_audit",
                audit_mock,
            ),
        ):
            new_slot = datetime(2026, 4, 23, 14, 0, tzinfo=timezone.utc)
            result = await apt_svc.reschedule_for_request(
                apt_id,
                new_slot,
                actor_id=uuid4(),
            )

        # Status is SCHEDULED — customer has NOT yet re-confirmed.
        assert result.status == AppointmentStatus.SCHEDULED.value
        # SMS #1 fires again (new Y/R/C prompt) — not the drag-drop notice.
        confirm_mock.assert_awaited_once()
        reschedule_mock.assert_not_awaited()
        # Audit row written.
        audit_mock.assert_awaited_once()

        # Combined outbound sends on this flow: 1x R-ack (from step 1)
        # + 1x new SMS #1 (from step 2) = at least two distinct
        # confirmation-related sends as the spec requires.
        assert r_result["auto_reply"]  # step-1 ack delivered
        # confirm_mock was awaited once in step 2 (new SMS #1)
        assert confirm_mock.await_count == 1

    async def test_r_reply_admin_reschedule_does_not_dispatch_real_sms(
        self,
    ) -> None:
        """Safety invariant: no real SMS provider call on either leg —
        both the R-ack and the new SMS #1 path go through mocks."""
        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        sent_msg = _make_sent_message(
            appointment_id=apt_id,
            job_id=job_id,
            customer_id=customer_id,
        )
        appointment = _make_appointment(id=apt_id, job_id=job_id)
        db = _build_mock_db(sent_message=sent_msg, appointment=appointment)

        jc_service = JobConfirmationService(db)
        await jc_service.handle_confirmation(
            thread_id="thread-abc-123",
            keyword=ConfirmationKeyword.RESCHEDULE,
            raw_body="R",
            from_phone="+19527373312",
        )

        # Admin path with mocked SMS helpers (no provider reached).
        appt_repo = AsyncMock()
        current_appt = MagicMock()
        current_appt.id = apt_id
        current_appt.job_id = job_id
        current_appt.status = AppointmentStatus.SCHEDULED.value
        current_appt.scheduled_date = date(2026, 4, 20)
        current_appt.time_window_start = time(9, 0)
        current_appt.time_window_end = time(11, 0)
        appt_repo.get_by_id = AsyncMock(return_value=current_appt)

        updated_appt = MagicMock()
        updated_appt.status = AppointmentStatus.SCHEDULED.value
        appt_repo.update = AsyncMock(return_value=updated_appt)
        appt_repo.session = AsyncMock()

        apt_svc = AppointmentService(
            appointment_repository=appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with (
            patch.object(apt_svc, "_send_confirmation_sms", AsyncMock()) as cm,
            patch.object(apt_svc, "_send_reschedule_sms", AsyncMock()) as rm,
            patch.object(
                apt_svc,
                "_record_reschedule_reconfirmation_audit",
                AsyncMock(),
            ),
        ):
            await apt_svc.reschedule_for_request(
                apt_id,
                datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc),
            )

            # Confirmation-SMS path invoked exactly once; one-way
            # reschedule-SMS path never invoked.
            assert cm.await_count == 1
            assert rm.await_count == 0
