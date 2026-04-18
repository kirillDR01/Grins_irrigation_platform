"""
Pydantic schemas for appointment management.

This module defines the Pydantic schemas for appointment-related
API requests and responses.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from datetime import date, datetime, time
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grins_platform.models.enums import AppointmentStatus


class AppointmentCreate(BaseModel):
    """Schema for creating a new appointment.

    Validates: Admin Dashboard Requirement 1.1
    """

    job_id: UUID = Field(..., description="ID of the job to schedule")
    staff_id: UUID = Field(..., description="ID of the assigned staff member")
    scheduled_date: date = Field(..., description="Date of the appointment")
    time_window_start: time = Field(..., description="Start of the time window")
    time_window_end: time = Field(..., description="End of the time window")
    notes: Optional[str] = Field(None, description="Additional notes")
    status: Optional[AppointmentStatus] = Field(
        default=None,
        description=(
            "Initial appointment status. Defaults to DRAFT for the standard "
            "UX flow; bulk-import paths (seed data, admin CSV imports) may "
            "pass SCHEDULED or CONFIRMED to bypass the draft-mode prompt. "
            "(bughunt M-6)"
        ),
    )

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def validate_time_window(self) -> "AppointmentCreate":
        """Validate that end time is after start time."""
        if self.time_window_end <= self.time_window_start:
            msg = "End time must be after start time"
            raise ValueError(msg)
        return self


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment.

    Validates: Admin Dashboard Requirement 1.2
    """

    staff_id: Optional[UUID] = Field(None, description="Assigned staff member ID")
    scheduled_date: Optional[date] = Field(None, description="Appointment date")
    time_window_start: Optional[time] = Field(None, description="Time window start")
    time_window_end: Optional[time] = Field(None, description="Time window end")
    notes: Optional[str] = Field(None, description="Additional notes")
    status: Optional[AppointmentStatus] = Field(None, description="Appointment status")
    route_order: Optional[int] = Field(None, ge=0, description="Route order")
    estimated_arrival: Optional[time] = Field(None, description="Estimated arrival")


class AppointmentResponse(BaseModel):
    """Schema for appointment response.

    Validates: Admin Dashboard Requirement 1.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    staff_id: UUID
    scheduled_date: date
    time_window_start: time
    time_window_end: time
    status: AppointmentStatus
    arrived_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    en_route_at: Optional[datetime] = None
    materials_needed: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    route_order: Optional[int] = None
    estimated_arrival: Optional[time] = None
    created_at: datetime
    updated_at: datetime
    # Extended fields for display (populated from relationships)
    job_type: Optional[str] = None
    customer_name: Optional[str] = None
    customer_internal_notes: Optional[str] = None
    staff_name: Optional[str] = None
    # Service agreement indicator for calendar display (Smoothing Req 7.5)
    service_agreement_id: Optional[UUID] = None


class AppointmentListParams(BaseModel):
    """Schema for appointment list query parameters.

    Validates: Admin Dashboard Requirement 1.4
    """

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    status: Optional[AppointmentStatus] = Field(None, description="Filter by status")
    staff_id: Optional[UUID] = Field(None, description="Filter by staff member")
    job_id: Optional[UUID] = Field(None, description="Filter by job")
    date_from: Optional[date] = Field(None, description="Filter by date from")
    date_to: Optional[date] = Field(None, description="Filter by date to")
    sort_by: str = Field("scheduled_date", description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")


class DailyScheduleResponse(BaseModel):
    """Schema for daily schedule response.

    Validates: Admin Dashboard Requirement 1.5
    """

    date: date
    appointments: list[AppointmentResponse]
    total_count: int


class StaffDailyScheduleResponse(BaseModel):
    """Schema for staff daily schedule response.

    Validates: Admin Dashboard Requirement 1.5
    """

    staff_id: UUID
    staff_name: str
    date: date
    appointments: list[AppointmentResponse]
    total_scheduled_minutes: int


class WeeklyScheduleResponse(BaseModel):
    """Schema for weekly schedule response.

    Validates: Admin Dashboard Requirement 1.5
    """

    start_date: date
    end_date: date
    days: list[DailyScheduleResponse]
    total_appointments: int


class AppointmentPaginatedResponse(BaseModel):
    """Schema for paginated appointment response."""

    items: list[AppointmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Draft Mode Schemas (Req 8)
# =============================================================================


class SendConfirmationResponse(BaseModel):
    """Response for single send-confirmation endpoint.

    Validates: Req 8.4, 8.12
    """

    appointment_id: UUID
    status: str
    sms_sent: bool


class BulkSendConfirmationsRequest(BaseModel):
    """Request for bulk send-confirmations endpoint.

    Validates: Req 8.6, 8.13
    """

    appointment_ids: Optional[list[UUID]] = Field(
        None, description="Specific appointment IDs to send confirmations for"
    )
    date_from: Optional[date] = Field(
        None, description="Start date for date range filter"
    )
    date_to: Optional[date] = Field(None, description="End date for date range filter")


class BulkSendConfirmationItemResult(BaseModel):
    """Per-appointment outcome row for bulk send-confirmations.

    Validates: Req 8.6, 8.13; bughunt M-8, M-9
    """

    appointment_id: UUID
    # ``sent`` = delivery handed to provider; ``deferred`` = rate-limited
    # and scheduled; ``skipped`` = no phone / missing customer / consent;
    # ``failed`` = unexpected error.
    status: Literal["sent", "deferred", "skipped", "failed"]
    reason: Optional[str] = None


class BulkSendConfirmationsResponse(BaseModel):
    """Response for bulk send-confirmations endpoint.

    Validates: Req 8.6, 8.13; bughunt M-8, M-9
    """

    sent_count: int
    deferred_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_draft: int
    results: list[BulkSendConfirmationItemResult] = Field(default_factory=list)


# =============================================================================
# Needs-Review Queue schemas (bughunt H-7)
# =============================================================================


class NeedsReviewAppointmentResponse(BaseModel):
    """Row returned by ``GET /appointments/needs-review``.

    Bundles the minimum appointment + customer fields required by the
    ``/schedule`` admin review queue so the FE does not have to round-trip
    the customer endpoint to render the row.

    Validates: bughunt 2026-04-16 finding H-7
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    staff_id: UUID
    scheduled_date: date
    time_window_start: time
    time_window_end: time
    status: AppointmentStatus
    needs_review_reason: Optional[str] = None
    # ISO-8601 timestamp of the most recent
    # ``appointment_confirmation`` SMS, so the FE can render
    # "N days since confirmation sent".
    confirmation_sent_at: Optional[datetime] = None
    customer_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None


class MarkContactedResponse(BaseModel):
    """Response for ``POST /appointments/{id}/mark-contacted``.

    Validates: bughunt 2026-04-16 finding H-7
    """

    appointment_id: UUID
    needs_review_reason: Optional[str] = None
