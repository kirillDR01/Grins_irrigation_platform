"""Pydantic schemas for the appointment communication timeline.

Validates: Gap 11 — AppointmentDetail communication timeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.schemas.job_confirmation import (
    RescheduleRequestResponse,  # noqa: TC001 - Pydantic field needs it at runtime
)


class TimelineEventKind(str, Enum):
    """Kinds of events that appear on the appointment communication timeline.

    Validates: Gap 11.
    """

    OUTBOUND_SMS = "outbound_sms"
    INBOUND_REPLY = "inbound_reply"
    RESCHEDULE_OPENED = "reschedule_opened"
    RESCHEDULE_RESOLVED = "reschedule_resolved"
    OPT_OUT = "opt_out"
    OPT_IN = "opt_in"


class TimelineEvent(BaseModel):
    """A single chronologically-sorted event on the timeline.

    Validates: Gap 11.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Stable event identifier")
    kind: TimelineEventKind = Field(..., description="Event kind discriminator")
    occurred_at: datetime = Field(..., description="When the event happened")
    summary: str = Field(..., description="Short one-line display string")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Kind-specific payload (raw body, message_type, etc.)",
    )
    source_id: UUID | None = Field(
        default=None,
        description="FK to the underlying row in the source table",
    )


class OptOutState(BaseModel):
    """Current SMS consent state for the appointment's customer.

    Validates: Gap 11.
    """

    model_config = ConfigDict(from_attributes=True)

    consent_given: bool = Field(
        ...,
        description="Most recent consent flag (False means opted out)",
    )
    recorded_at: datetime | None = Field(
        default=None,
        description="Timestamp of the latest consent record",
    )
    method: str | None = Field(
        default=None,
        description="consent_method or opt_out_method of the latest record",
    )


class AppointmentTimelineResponse(BaseModel):
    """Aggregated communication timeline for a single appointment.

    Validates: Gap 11.
    """

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID = Field(..., description="Appointment UUID")
    events: list[TimelineEvent] = Field(
        default_factory=list[TimelineEvent],
        description="Chronologically-sorted events (newest first)",
    )
    pending_reschedule_request: RescheduleRequestResponse | None = Field(
        default=None,
        description="The earliest-opened, still-open reschedule request if any",
    )
    needs_review_reason: str | None = Field(
        default=None,
        description="Appointment review-flag token (e.g. no_confirmation_response)",
    )
    opt_out: OptOutState | None = Field(
        default=None,
        description="Latest SMS consent state for the appointment's customer",
    )
    last_event_at: datetime | None = Field(
        default=None,
        description="occurred_at of the most recent event, if any",
    )
