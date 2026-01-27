"""Pydantic schemas for conflict resolution.

Validates: Requirements 10.1-10.7
"""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field


class WaitlistEntryCreate(BaseModel):
    """Create a waitlist entry."""

    job_id: UUID
    preferred_date: date
    preferred_time_start: time | None = None
    preferred_time_end: time | None = None
    priority: int = Field(default=0, ge=0, le=3)
    notes: str | None = None


class WaitlistEntryResponse(BaseModel):
    """Waitlist entry response."""

    id: UUID
    job_id: UUID
    preferred_date: date
    preferred_time_start: time | None = None
    preferred_time_end: time | None = None
    priority: int
    notes: str | None = None
    notified_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CancelAppointmentRequest(BaseModel):
    """Request to cancel an appointment."""

    reason: str = Field(..., min_length=1, max_length=500)
    add_to_waitlist: bool = False
    preferred_reschedule_date: date | None = None


class CancelAppointmentResponse(BaseModel):
    """Response from cancelling an appointment."""

    appointment_id: UUID
    cancelled_at: datetime
    reason: str
    waitlist_entry_id: UUID | None = None
    message: str


class RescheduleAppointmentRequest(BaseModel):
    """Request to reschedule an appointment."""

    new_date: date
    new_time_start: time
    new_time_end: time
    new_staff_id: UUID | None = None


class RescheduleAppointmentResponse(BaseModel):
    """Response from rescheduling an appointment."""

    original_appointment_id: UUID
    new_appointment_id: UUID
    new_date: date
    new_time_start: time
    new_time_end: time
    staff_id: UUID
    message: str


class FillGapRequest(BaseModel):
    """Request to fill a schedule gap."""

    target_date: date
    gap_start: time
    gap_end: time
    staff_id: UUID | None = None


class FillGapSuggestion(BaseModel):
    """A suggestion for filling a schedule gap."""

    job_id: UUID
    customer_name: str
    service_type: str
    duration_minutes: int
    priority: int
    from_waitlist: bool


class FillGapResponse(BaseModel):
    """Response with suggestions for filling a gap."""

    target_date: date
    gap_start: time
    gap_end: time
    gap_duration_minutes: int
    suggestions: list[FillGapSuggestion] = Field(default_factory=list)
