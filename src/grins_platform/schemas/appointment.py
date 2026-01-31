"""
Pydantic schemas for appointment management.

This module defines the Pydantic schemas for appointment-related
API requests and responses.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from datetime import date, datetime, time
from typing import Optional
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
    notes: Optional[str] = None
    route_order: Optional[int] = None
    estimated_arrival: Optional[time] = None
    created_at: datetime
    updated_at: datetime
    # Extended fields for display (populated from relationships)
    job_type: Optional[str] = None
    customer_name: Optional[str] = None
    staff_name: Optional[str] = None


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
