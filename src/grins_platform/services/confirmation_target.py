"""ConfirmationTarget: polymorphic adapter for the Y/R/C lifecycle.

The Y/R/C SMS confirmation infrastructure (parser, throttle, dispatcher,
``RescheduleRequest`` queue, audit-log writes) was built around
``Appointment`` but the same machinery now also drives the sales-pipeline
``SalesCalendarEvent`` (estimate visit) lifecycle. ``ConfirmationTarget``
is the small adapter that lets the dispatcher branch on which entity a
given inbound reply pertains to without forking the call site.

PR A (this revision) introduces the dataclass and a factory keyed off
``SentMessage`` FKs. PR B wires it into ``JobConfirmationService`` and
``SMSService._try_confirmation_reply`` so estimate-visit replies route
through the same code path as appointment replies, branching only on
``target.kind`` where copy or status transitions diverge.

Validates: sales-pipeline-estimate-visit-confirmation-lifecycle (OQ-1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.sent_message import SentMessage


ConfirmationTargetKind = Literal["appointment", "estimate_visit"]


@dataclass(frozen=True, slots=True)
class ConfirmationTarget:
    """Identifies the entity an inbound Y/R/C reply pertains to.

    Carries only IDs (not loaded ORM objects) so it stays cheap to
    construct and pass around. Handlers that need the full
    ``Appointment`` or ``SalesCalendarEvent`` row resolve it from these
    IDs at the point of use.

    Exactly one of ``appointment_id`` / ``sales_calendar_event_id`` is
    non-null; ``kind`` discriminates between them.

    ``job_id`` is only meaningful for ``kind="appointment"`` —
    ``SalesCalendarEvent`` has no associated job.
    """

    kind: ConfirmationTargetKind
    customer_id: UUID
    appointment_id: UUID | None
    sales_calendar_event_id: UUID | None
    job_id: UUID | None

    @classmethod
    def from_sent_message(cls, sent_message: SentMessage) -> ConfirmationTarget:
        """Build a target from the FK pattern on a correlated ``SentMessage``.

        Raises ``ValueError`` if the message has neither an
        ``appointment_id`` nor a ``sales_calendar_event_id`` (e.g.
        legacy campaign rows or lead-confirmation rows that cannot
        anchor a Y/R/C lifecycle).
        """
        if sent_message.appointment_id is not None:
            customer_id = sent_message.customer_id
            if customer_id is None:
                msg = "SentMessage with appointment_id has no customer_id"
                raise ValueError(msg)
            return cls(
                kind="appointment",
                customer_id=customer_id,
                appointment_id=sent_message.appointment_id,
                sales_calendar_event_id=None,
                job_id=sent_message.job_id,
            )
        if sent_message.sales_calendar_event_id is not None:
            customer_id = sent_message.customer_id
            if customer_id is None:
                msg = "SentMessage with sales_calendar_event_id has no customer_id"
                raise ValueError(msg)
            return cls(
                kind="estimate_visit",
                customer_id=customer_id,
                appointment_id=None,
                sales_calendar_event_id=sent_message.sales_calendar_event_id,
                job_id=None,
            )
        msg = (
            "SentMessage has neither appointment_id nor sales_calendar_event_id; "
            "cannot anchor a confirmation target."
        )
        raise ValueError(msg)
