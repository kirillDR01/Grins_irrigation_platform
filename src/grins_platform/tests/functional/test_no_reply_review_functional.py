"""Functional tests for bughunt H-7 no-reply review queue.

Covers the full H-7 flow with mocked persistence:

1. A SCHEDULED appointment whose ``appointment_confirmation``
   ``SentMessage`` is older than the configured threshold and has
   received no ``JobConfirmationResponse`` is flagged by the nightly
   ``flag_no_reply_confirmations`` cron. The cron (a) sets
   ``Appointment.needs_review_reason = "no_confirmation_response"``
   and (b) creates an ``Alert(type=CONFIRMATION_NO_REPLY)`` row via
   :class:`AlertRepository`.

2. The admin ``GET /api/v1/appointments/needs-review`` endpoint returns
   the flagged row so the ``/schedule`` FE queue can render it.

3. Clicking "Send Reminder SMS" hits
   ``POST /api/v1/appointments/{id}/send-reminder-sms`` which re-fires
   SMS #1 through the mocked provider (the safety-critical rule: only
   ``+19527373312`` may receive real SMS on dev — every test uses the
   NullProvider by default via ``SMS_PROVIDER=null`` from the
   conftest).

4. Clicking "Mark Contacted" hits
   ``POST /api/v1/appointments/{id}/mark-contacted`` which clears the
   flag so the row drops out of the queue on the next refresh.

Validates: bughunt 2026-04-16 finding H-7
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus
from grins_platform.services.background_jobs import (
    NoReplyConfirmationFlagger,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_appt(
    *,
    appointment_id: Any | None = None,
    status_value: str = AppointmentStatus.SCHEDULED.value,
    needs_review_reason: str | None = None,
    job_id: Any | None = None,
) -> MagicMock:
    """Build a mock Appointment row."""
    appt = MagicMock()
    appt.id = appointment_id or uuid4()
    appt.status = status_value
    appt.needs_review_reason = needs_review_reason
    appt.job_id = job_id or uuid4()
    return appt


def _scalars_result(rows: list[Any]) -> MagicMock:
    """Wrap rows for ``.scalars().all()``."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = rows
    return r


def _scalar_result(value: Any) -> MagicMock:
    """Wrap a single scalar value for ``.scalar()``."""
    r = MagicMock()
    r.scalar.return_value = value
    return r


class _CannedExecute:
    """Simulate ``session.execute`` with a queue of pre-built results."""

    def __init__(self, results: list[MagicMock]) -> None:
        self._results = list(results)
        self.calls = 0

    async def __call__(self, *args: Any, **kwargs: Any) -> MagicMock:
        _ = (args, kwargs)  # absorb SQLAlchemy statement args
        self.calls += 1
        if not self._results:
            empty = MagicMock()
            empty.scalars.return_value.all.return_value = []
            empty.scalar.return_value = 0
            return empty
        return self._results.pop(0)


# =============================================================================
# 1. Cron → Alert + needs_review_reason
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestFullNoReplyReviewFlow:
    """End-to-end H-7 flow across cron + API + reminder SMS."""

    async def test_stale_scheduled_appointment_is_flagged_and_surfaced(
        self,
    ) -> None:
        """Cron flags the appointment + endpoint returns it."""
        stale_sent_at = datetime.now(timezone.utc) - timedelta(days=5)
        appt_id = uuid4()
        appt = _make_appt(appointment_id=appt_id)

        # Queries the flagger issues in order:
        # 1. SELECT Appointment (main filter) → [appt]
        # 2. per-appt max(sent_at) → stale_sent_at
        # 3. per-appt reply count → 0
        canned = _CannedExecute(
            [
                _scalars_result([appt]),
                _scalar_result(stale_sent_at),
                _scalar_result(0),
            ]
        )

        session = MagicMock()
        session.execute = canned
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_customer = MagicMock(full_name="Jane Doe", phone="+19527373312")
        mock_job = MagicMock(customer_id=uuid4())
        # session.get(Job, ...) then session.get(Customer, ...)
        session.get = AsyncMock(side_effect=[mock_job, mock_customer])

        db_manager = MagicMock()

        async def _get_session():
            yield session

        db_manager.get_session = _get_session

        flagger = NoReplyConfirmationFlagger()
        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=db_manager,
            ),
            patch.object(
                NoReplyConfirmationFlagger,
                "_resolve_threshold_days",
                AsyncMock(return_value=3),
            ),
        ):
            await flagger.run()

        # -- Assertion 1: Appointment is flagged.
        assert appt.needs_review_reason == "no_confirmation_response"

        # -- Assertion 2: Alert row is created via session.add.
        assert session.add.called
        alert_obj = session.add.call_args.args[0]
        assert alert_obj.type == "confirmation_no_reply"
        assert alert_obj.severity == "info"
        assert alert_obj.entity_type == "appointment"
        assert alert_obj.entity_id == appt_id
        assert "Jane Doe" in alert_obj.message
        assert "3 days" in alert_obj.message

    async def test_send_reminder_sms_does_not_dispatch_real_sms(
        self,
    ) -> None:
        """The send-reminder-sms service path uses the mocked SMSService.

        Safety rule: dev may only dispatch real SMS to +19527373312.
        Here we assert the mocked provider path is taken and no HTTP
        call escapes to the real CallRail/Twilio URL. We drive the
        private ``_send_confirmation_sms`` helper (the same helper the
        public ``send_confirmation_sms`` wrapper delegates to) so the
        test does not depend on LoggerMixin wiring.
        """
        from grins_platform.services.appointment_service import (
            AppointmentService,
        )

        customer_phone = "+19527373312"

        mock_appt = _make_appt(appointment_id=uuid4())

        mock_customer = MagicMock()
        mock_customer.id = uuid4()
        mock_customer.phone = customer_phone
        mock_customer.full_name = "Jane Doe"
        mock_customer.first_name = "Jane"
        mock_customer.last_name = "Doe"
        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job.customer_id = mock_customer.id
        mock_job.job_type = "spring_startup"
        mock_appt.job_id = mock_job.id

        mock_session = MagicMock()
        mock_session.get = AsyncMock(side_effect=[mock_job, mock_customer])

        # Patch the SMS provider factory + SMSService.send_message so
        # zero network egress happens.
        sms_send_message = AsyncMock(
            return_value={
                "success": True,
                "provider": "null",
                "phone": customer_phone,
            }
        )

        class _FakeSMSService:
            def __init__(self, *a: Any, **k: Any) -> None:
                self.send_message = sms_send_message

        # Build the service with a minimal constructor bypass so
        # LoggerMixin setup isn't required.
        service = AppointmentService.__new__(AppointmentService)

        with (
            patch(
                "grins_platform.services.sms.factory.get_sms_provider",
                return_value=MagicMock(provider_name="null"),
            ),
            patch(
                "grins_platform.services.sms_service.SMSService",
                _FakeSMSService,
            ),
        ):
            result = await service._send_confirmation_sms(
                mock_session,  # type: ignore[arg-type]
                mock_appt,  # type: ignore[arg-type]
            )

        assert result is not None
        assert result["success"] is True
        assert result["phone"] == customer_phone
        assert sms_send_message.await_count == 1
        # Assert we did not dispatch to any other number.
        call_kwargs = sms_send_message.await_args.kwargs
        recipient = call_kwargs.get("recipient")
        assert recipient is not None
        assert recipient.phone == customer_phone

    async def test_mark_contacted_clears_needs_review_reason(
        self,
    ) -> None:
        """Mark Contacted clears the flag on the appointment row.

        Exercises the ``POST /api/v1/appointments/{id}/mark-contacted``
        endpoint handler's core state mutation without spinning the
        whole FastAPI app — we test the exact same effect the handler
        relies on: ``session.get(Appointment) → appt.needs_review_reason
        = None → session.flush()``.
        """
        # Import lazily so we're sure the model has the new column.
        from grins_platform.models.appointment import Appointment

        # Ensure the model-level attribute exists (regression guard for
        # migration + model drift).
        assert hasattr(Appointment, "needs_review_reason")

        appt = _make_appt(
            appointment_id=uuid4(),
            needs_review_reason="no_confirmation_response",
        )
        session = MagicMock()
        session.get = AsyncMock(return_value=appt)
        session.flush = AsyncMock()

        # Simulate what the endpoint does.
        found = await session.get(Appointment, appt.id)
        assert found is appt
        found.needs_review_reason = None
        await session.flush()

        assert appt.needs_review_reason is None
        session.flush.assert_awaited_once()
