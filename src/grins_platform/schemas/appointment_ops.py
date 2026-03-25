"""Pydantic schemas for appointment service operations.

Covers payment collection, invoice creation, notes/photos,
review requests, and staff time analytics.

Validates: CRM Gap Closure Req 24, 25, 29, 30, 31, 32, 33, 34, 35, 36, 37
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from grins_platform.models.enums import AppointmentStatus, PaymentMethod  # noqa: TC001


class RescheduleRequest(BaseModel):
    """Request to reschedule an appointment via drag-drop.

    Validates: CRM Gap Closure Req 24.2
    """

    new_date: date = Field(..., description="New scheduled date")
    new_start: str = Field(
        ...,
        pattern=r"^\d{2}:\d{2}$",
        description="New start time HH:MM",
    )
    new_end: str = Field(
        ...,
        pattern=r"^\d{2}:\d{2}$",
        description="New end time HH:MM",
    )


class StatusTransitionRequest(BaseModel):
    """Request to transition appointment status.

    Validates: CRM Gap Closure Req 35.4, 35.5, 35.6
    """

    new_status: AppointmentStatus = Field(
        ...,
        description="Target status",
    )
    actor_id: UUID = Field(..., description="Staff/admin performing the action")
    admin_override: bool = Field(
        default=False,
        description="Admin override for payment gate",
    )


class PaymentCollectionRequest(BaseModel):
    """Request to collect payment on-site.

    Validates: CRM Gap Closure Req 30.3, 30.4, 30.5
    """

    payment_method: PaymentMethod = Field(
        ...,
        description="Payment method used",
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Payment amount",
    )
    reference_number: str | None = Field(
        default=None,
        max_length=255,
        description="Check number, Venmo/Zelle reference, etc.",
    )


class PaymentResult(BaseModel):
    """Result of payment collection.

    Validates: CRM Gap Closure Req 30.3
    """

    invoice_id: UUID = Field(..., description="Invoice UUID")
    invoice_number: str = Field(..., description="Invoice number")
    amount_paid: Decimal = Field(..., description="Amount collected")
    payment_method: str = Field(..., description="Payment method used")
    status: str = Field(..., description="Invoice status after payment")


class NotesAndPhotosRequest(BaseModel):
    """Request to add notes and photos to an appointment.

    Validates: CRM Gap Closure Req 33.2, 33.3
    """

    notes: str | None = Field(
        default=None,
        max_length=10000,
        description="Appointment notes",
    )
    # Photos are handled via multipart upload, not in this schema


class DateRange(BaseModel):
    """Date range filter for analytics queries."""

    start_date: date = Field(..., description="Start date")
    end_date: date = Field(..., description="End date")


class StaffTimeEntry(BaseModel):
    """Individual staff time analytics entry.

    Validates: CRM Gap Closure Req 37.1, 37.2
    """

    staff_id: UUID | None = Field(default=None, description="Staff UUID")
    staff_name: str | None = Field(default=None, description="Staff name")
    job_type: str | None = Field(default=None, description="Job type")
    avg_travel_minutes: float = Field(
        default=0.0,
        ge=0.0,
        description="Average travel time in minutes",
    )
    avg_job_minutes: float = Field(
        default=0.0,
        ge=0.0,
        description="Average job duration in minutes",
    )
    avg_total_minutes: float = Field(
        default=0.0,
        ge=0.0,
        description="Average total time in minutes",
    )
    appointment_count: int = Field(
        default=0,
        ge=0,
        description="Number of appointments in sample",
    )
    flagged: bool = Field(
        default=False,
        description="Whether staff exceeds 1.5x average for job type",
    )


class LeadTimeResult(BaseModel):
    """Result of lead time calculation.

    Validates: CRM Gap Closure Req 25.2, 25.3
    """

    days: int = Field(..., ge=0, description="Days until earliest slot")
    earliest_date: date | None = Field(
        default=None,
        description="Earliest available date",
    )
    display: str = Field(
        ...,
        description="Human-readable display string",
    )


class ReviewRequestResult(BaseModel):
    """Result of Google review request.

    Validates: CRM Gap Closure Req 34.2
    """

    sent: bool = Field(..., description="Whether the review request was sent")
    channel: str | None = Field(
        default=None,
        description="Channel used (sms, email)",
    )
    message: str = Field(..., description="Status message")
