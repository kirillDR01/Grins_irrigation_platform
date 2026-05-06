"""Unit tests for ``SalesPipelineService.send_estimate_visit_confirmation``.

The shim ``send_text_confirmation`` already has wide coverage in
``test_sales_pipeline_and_signwell.py`` (TestSendTextConfirmation). These
tests target the underlying primitive that the shim delegates to: copy
composition, status priming, the auto-advance-on-first-send rule, and
the error branches that protect against half-done sends.

Validates: sales-pipeline-estimate-visit-confirmation-lifecycle Task 18.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    CustomerHasNoPhoneError,
    CustomerNotFoundError,
    SalesCalendarEventNotFoundError,
)
from grins_platform.models.enums import MessageType, SalesEntryStatus
from grins_platform.services.sales_pipeline_service import SalesPipelineService


def _make_event(
    *,
    sales_entry_id: object | None = None,
    customer_id: object | None = None,
    confirmation_status: str = "pending",
    confirmation_status_at: datetime | None = None,
    scheduled_date: date | None = None,
    start_time: time | None = None,
) -> Mock:
    event = Mock()
    event.id = uuid4()
    event.sales_entry_id = sales_entry_id or uuid4()
    event.customer_id = customer_id or uuid4()
    event.scheduled_date = scheduled_date or date(2026, 5, 12)
    event.start_time = start_time
    event.confirmation_status = confirmation_status
    event.confirmation_status_at = confirmation_status_at
    return event


def _make_customer(
    *,
    customer_id: object | None = None,
    first_name: str = "Jane",
    phone: str | None = "+19527373312",
) -> Mock:
    customer = Mock()
    customer.id = customer_id or uuid4()
    customer.first_name = first_name
    customer.last_name = "Doe"
    customer.phone = phone
    customer.email = "kirillrakitinsecond@gmail.com"
    return customer


def _make_entry(
    *,
    customer_id: object | None = None,
    status: str = SalesEntryStatus.SCHEDULE_ESTIMATE.value,
) -> Mock:
    entry = Mock()
    entry.id = uuid4()
    entry.customer_id = customer_id or uuid4()
    entry.status = status
    entry.updated_at = datetime.now(tz=timezone.utc)
    return entry


@pytest.fixture()
def pipeline_service() -> SalesPipelineService:
    job_service = AsyncMock()
    audit_service = AsyncMock()
    audit_service.log_action = AsyncMock(return_value=Mock(id=uuid4()))
    return SalesPipelineService(
        job_service=job_service,
        audit_service=audit_service,
    )


@pytest.fixture()
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Copy composition
# ---------------------------------------------------------------------------


class TestEstimateVisitConfirmationBody:
    """``_build_estimate_visit_confirmation_body`` formats the customer-facing copy."""

    @pytest.mark.unit
    def test_includes_first_name_date_time_and_yrc_options(self) -> None:
        customer = _make_customer(first_name="Jane")
        event = _make_event(
            scheduled_date=date(2026, 5, 12),
            start_time=time(14, 0),
        )

        body = SalesPipelineService._build_estimate_visit_confirmation_body(
            customer=customer,
            event=event,
        )

        assert "Hi Jane" in body
        assert "May 12, 2026" in body
        assert "2:00 PM" in body
        assert "Reply Y to confirm" in body
        assert "R to" in body and "reschedule" in body
        assert "C to cancel" in body

    @pytest.mark.unit
    def test_falls_back_to_there_when_first_name_missing(self) -> None:
        customer = _make_customer(first_name=None)
        event = _make_event(
            scheduled_date=date(2026, 5, 12),
            start_time=time(9, 30),
        )

        body = SalesPipelineService._build_estimate_visit_confirmation_body(
            customer=customer,
            event=event,
        )

        assert body.startswith("Hi there,")

    @pytest.mark.unit
    def test_omits_time_when_event_has_no_start_time(self) -> None:
        customer = _make_customer()
        event = _make_event(
            scheduled_date=date(2026, 5, 12),
            start_time=None,
        )

        body = SalesPipelineService._build_estimate_visit_confirmation_body(
            customer=customer,
            event=event,
        )

        assert "May 12, 2026" in body
        assert " at " not in body


# ---------------------------------------------------------------------------
# send_estimate_visit_confirmation — happy path & error branches
# ---------------------------------------------------------------------------


class TestSendEstimateVisitConfirmation:
    """Direct tests for the primitive that ``send_text_confirmation`` delegates to."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatches_with_sales_calendar_event_id(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        """First-send path: SMSService.send_message is called with the
        estimate-tailored message_type and the event FK so inbound replies
        correlate.
        """
        entry = _make_entry()
        event = _make_event(
            sales_entry_id=entry.id,
            customer_id=entry.customer_id,
            confirmation_status="pending",
        )
        customer = _make_customer(customer_id=entry.customer_id)

        # execute() order inside send_estimate_visit_confirmation:
        # event lookup → customer lookup → entry lookup (auto-advance check).
        mock_db.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=event)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=customer)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=entry)),
            ],
        )
        sms_service = AsyncMock()
        sms_service.send_message = AsyncMock(
            return_value={"message_id": "m-est-1", "status": "sent"},
        )

        result = await pipeline_service.send_estimate_visit_confirmation(
            mock_db,
            event_id=event.id,
            sms_service=sms_service,
        )

        assert result == {"message_id": "m-est-1", "status": "sent"}
        sms_service.send_message.assert_awaited_once()
        args, kwargs = sms_service.send_message.call_args
        # Positional args: recipient, body, message_type
        assert args[2] == MessageType.ESTIMATE_VISIT_CONFIRMATION
        assert kwargs["sales_calendar_event_id"] == event.id
        assert kwargs["consent_type"] == "transactional"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_first_send_advances_entry_to_estimate_scheduled(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        """Per OQ-6: auto-advance fires on first successful SMS dispatch,
        never on bare event creation.
        """
        entry = _make_entry(status=SalesEntryStatus.SCHEDULE_ESTIMATE.value)
        event = _make_event(
            sales_entry_id=entry.id,
            customer_id=entry.customer_id,
        )
        customer = _make_customer(customer_id=entry.customer_id)
        mock_db.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=event)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=customer)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=entry)),
            ],
        )
        sms_service = AsyncMock()
        sms_service.send_message = AsyncMock(return_value={"message_id": "m-1"})

        await pipeline_service.send_estimate_visit_confirmation(
            mock_db,
            event_id=event.id,
            sms_service=sms_service,
        )

        assert entry.status == SalesEntryStatus.ESTIMATE_SCHEDULED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resend_does_not_re_advance_already_scheduled_entry(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        """Resend on an already-advanced entry leaves the status alone."""
        entry = _make_entry(status=SalesEntryStatus.ESTIMATE_SCHEDULED.value)
        event = _make_event(
            sales_entry_id=entry.id,
            customer_id=entry.customer_id,
            confirmation_status="pending",
        )
        customer = _make_customer(customer_id=entry.customer_id)
        mock_db.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=event)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=customer)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=entry)),
            ],
        )
        sms_service = AsyncMock()
        sms_service.send_message = AsyncMock(return_value={"message_id": "m-2"})

        await pipeline_service.send_estimate_visit_confirmation(
            mock_db,
            event_id=event.id,
            sms_service=sms_service,
            resend=True,
        )

        # Status pre-condition was already estimate_scheduled; resend
        # never demotes or re-advances.
        assert entry.status == SalesEntryStatus.ESTIMATE_SCHEDULED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_event_not_found_raises_typed_error(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=None),
            ),
        )
        sms_service = AsyncMock()

        with pytest.raises(SalesCalendarEventNotFoundError):
            await pipeline_service.send_estimate_visit_confirmation(
                mock_db,
                event_id=uuid4(),
                sms_service=sms_service,
            )
        sms_service.send_message.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_customer_not_found_raises_typed_error(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        event = _make_event()
        mock_db.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=event)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            ],
        )
        sms_service = AsyncMock()

        with pytest.raises(CustomerNotFoundError):
            await pipeline_service.send_estimate_visit_confirmation(
                mock_db,
                event_id=event.id,
                sms_service=sms_service,
            )
        sms_service.send_message.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_customer_with_no_phone_raises_typed_error(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
    ) -> None:
        event = _make_event()
        customer = _make_customer(customer_id=event.customer_id, phone=None)
        mock_db.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=event)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=customer)),
            ],
        )
        sms_service = AsyncMock()

        with pytest.raises(CustomerHasNoPhoneError):
            await pipeline_service.send_estimate_visit_confirmation(
                mock_db,
                event_id=event.id,
                sms_service=sms_service,
            )
        sms_service.send_message.assert_not_called()
