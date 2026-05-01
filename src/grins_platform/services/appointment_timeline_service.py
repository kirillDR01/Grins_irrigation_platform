"""AppointmentTimelineService — Gap 11 aggregator.

Assembles a chronologically-sorted communication timeline for a single
appointment from four existing sources: outbound ``SentMessage``, inbound
``JobConfirmationResponse``, ``RescheduleRequest`` rows, and the customer's
current ``SmsConsentRecord``. Read-only; no mutation or new business logic.

Validates: Gap 11.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from grins_platform.exceptions import AppointmentNotFoundError
from grins_platform.log_config import LoggerMixin
from grins_platform.models.invoice import Invoice
from grins_platform.models.job import Job
from grins_platform.repositories.appointment_repository import AppointmentRepository
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.repositories.sms_consent_repository import SmsConsentRepository
from grins_platform.schemas.appointment_timeline import (
    AppointmentTimelineResponse,
    OptOutState,
    TimelineEvent,
    TimelineEventKind,
)
from grins_platform.schemas.job_confirmation import (
    ConfirmationResponseSchema,
    RescheduleRequestResponse,
)
from grins_platform.schemas.sent_message import SentMessageResponse
from grins_platform.services.job_confirmation_service import JobConfirmationService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.job_confirmation import (
        JobConfirmationResponse,
        RescheduleRequest,
    )
    from grins_platform.models.sent_message import SentMessage
    from grins_platform.models.sms_consent_record import SmsConsentRecord


class AppointmentTimelineService(LoggerMixin):
    """Read-only aggregator for the AppointmentDetail communication timeline.

    Validates: Gap 11.
    """

    DOMAIN = "appointment_timeline"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session
        self.appointment_repo = AppointmentRepository(session=session)
        self.sent_message_repo = SentMessageRepository(session=session)
        self.consent_repo = SmsConsentRepository(session=session)
        self.confirmation_service = JobConfirmationService(session)

    async def get_timeline(
        self,
        appointment_id: UUID,
    ) -> AppointmentTimelineResponse:
        """Build a unified timeline for a single appointment.

        Raises:
            AppointmentNotFoundError: If the appointment does not exist.
        """
        self.log_started("build_timeline", appointment_id=str(appointment_id))

        appointment = await self.appointment_repo.get_by_id(appointment_id)
        if appointment is None:
            self.log_rejected("build_timeline", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        customer_id = await self._resolve_customer_id(appointment.job_id)

        outbound = await self.sent_message_repo.list_by_appointment(appointment_id)
        inbound = await self.confirmation_service.list_responses_by_appointment(
            appointment_id,
        )
        reschedule_rows = (
            await self.confirmation_service.list_reschedule_requests_by_appointment(
                appointment_id,
            )
        )
        consent = (
            await self.consent_repo.get_latest_for_customer(customer_id)
            if customer_id is not None
            else None
        )
        paid_invoices = await self._list_paid_invoices(appointment.job_id)

        events: list[TimelineEvent] = []
        events.extend(self._outbound_to_event(m) for m in outbound)
        events.extend(self._inbound_to_event(r) for r in inbound)
        for rr in reschedule_rows:
            events.extend(self._reschedule_to_events(rr))
        if consent is not None:
            events.append(self._consent_to_event(consent))
        events.extend(self._invoice_payment_to_event(inv) for inv in paid_invoices)

        events.sort(key=lambda e: e.occurred_at, reverse=True)

        pending_reschedule = next(
            (
                RescheduleRequestResponse.model_validate(rr)
                for rr in reschedule_rows
                if rr.status == "open"
            ),
            None,
        )

        opt_out_state: OptOutState | None = None
        if consent is not None:
            opt_out_state = OptOutState(
                consent_given=consent.consent_given,
                recorded_at=self._consent_recorded_at(consent),
                method=(
                    consent.opt_out_method
                    if not consent.consent_given
                    else consent.consent_method
                ),
            )

        response = AppointmentTimelineResponse(
            appointment_id=appointment_id,
            events=events,
            pending_reschedule_request=pending_reschedule,
            needs_review_reason=appointment.needs_review_reason,
            opt_out=opt_out_state,
            last_event_at=events[0].occurred_at if events else None,
        )

        self.log_completed(
            "build_timeline",
            appointment_id=str(appointment_id),
            event_count=len(events),
        )
        return response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_customer_id(self, job_id: UUID) -> UUID | None:
        """Look up ``Job.customer_id`` — Appointment has no direct FK."""
        result = await self.session.execute(
            select(Job.customer_id).where(Job.id == job_id),
        )
        value: UUID | None = result.scalar_one_or_none()
        return value

    async def _list_paid_invoices(self, job_id: UUID) -> list[Invoice]:
        """Fetch every invoice on this job with a recorded payment.

        A single appointment's job may have multiple invoices over time
        (e.g. deposit + final). Each paid invoice yields one timeline event.
        """
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.job_id == job_id)
            .where(Invoice.paid_at.is_not(None))
            .order_by(Invoice.paid_at.desc()),
        )
        return list(result.scalars().all())

    @staticmethod
    def _outbound_to_event(message: SentMessage) -> TimelineEvent:
        payload = SentMessageResponse.model_validate(message).model_dump(mode="json")
        occurred = message.sent_at or message.created_at
        summary = f"Sent {message.message_type.replace('_', ' ')}"
        return TimelineEvent(
            id=message.id,
            kind=TimelineEventKind.OUTBOUND_SMS,
            occurred_at=occurred,
            summary=summary,
            details=payload,
            source_id=message.id,
        )

    @staticmethod
    def _inbound_to_event(row: JobConfirmationResponse) -> TimelineEvent:
        payload = ConfirmationResponseSchema.model_validate(row).model_dump(mode="json")
        keyword = row.reply_keyword or "free-text"
        summary = f"Customer replied: {keyword}"
        return TimelineEvent(
            id=row.id,
            kind=TimelineEventKind.INBOUND_REPLY,
            occurred_at=row.received_at,
            summary=summary,
            details=payload,
            source_id=row.id,
        )

    @staticmethod
    def _reschedule_to_events(row: RescheduleRequest) -> list[TimelineEvent]:
        payload = RescheduleRequestResponse.model_validate(row).model_dump(mode="json")
        opened = TimelineEvent(
            id=row.id,
            kind=TimelineEventKind.RESCHEDULE_OPENED,
            occurred_at=row.created_at,
            summary="Reschedule request opened",
            details=payload,
            source_id=row.id,
        )
        if row.resolved_at is None:
            return [opened]
        resolved = TimelineEvent(
            id=row.id,
            kind=TimelineEventKind.RESCHEDULE_RESOLVED,
            occurred_at=row.resolved_at,
            summary="Reschedule request resolved",
            details=payload,
            source_id=row.id,
        )
        return [opened, resolved]

    @staticmethod
    def _invoice_payment_to_event(invoice: Invoice) -> TimelineEvent:
        method = (invoice.payment_method or "unknown").replace("_", " ")
        amount = (
            invoice.paid_amount
            if invoice.paid_amount is not None
            else invoice.total_amount
        )
        amount_display = f"${amount:.2f}" if amount is not None else "$0.00"
        summary = f"Payment received: {amount_display} via {method}"
        details: dict[str, Any] = {
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "payment_method": invoice.payment_method,
            "payment_reference": invoice.payment_reference,
            "paid_amount": str(amount) if amount is not None else None,
            "total_amount": str(invoice.total_amount),
            "status": invoice.status,
        }
        # paid_at is non-null by construction (filtered upstream)
        occurred = (
            invoice.paid_at if invoice.paid_at is not None else invoice.updated_at
        )
        return TimelineEvent(
            id=invoice.id,
            kind=TimelineEventKind.PAYMENT_RECEIVED,
            occurred_at=occurred,
            summary=summary,
            details=details,
            source_id=invoice.id,
        )

    @staticmethod
    def _consent_to_event(consent: SmsConsentRecord) -> TimelineEvent:
        occurred = (
            consent.opt_out_timestamp
            if not consent.consent_given and consent.opt_out_timestamp is not None
            else consent.consent_timestamp
        )
        kind = (
            TimelineEventKind.OPT_OUT
            if not consent.consent_given
            else TimelineEventKind.OPT_IN
        )
        method = (
            consent.opt_out_method
            if not consent.consent_given
            else consent.consent_method
        )
        summary = (
            f"Opted out via {method or 'unknown'}"
            if not consent.consent_given
            else f"Opted in via {method or 'unknown'}"
        )
        return TimelineEvent(
            id=consent.id,
            kind=kind,
            occurred_at=occurred,
            summary=summary,
            details={
                "consent_given": consent.consent_given,
                "method": method,
                "phone_number": consent.phone_number,
            },
            source_id=consent.id,
        )

    @staticmethod
    def _consent_recorded_at(consent: SmsConsentRecord) -> datetime | None:
        ts: datetime | None
        if not consent.consent_given and consent.opt_out_timestamp is not None:
            ts = consent.opt_out_timestamp
        else:
            ts = consent.consent_timestamp
        return ts
