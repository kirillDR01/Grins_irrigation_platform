"""
Dashboard Pydantic schemas for the Admin Dashboard (Phase 3).

This module defines schemas for dashboard metrics, request volume,
schedule overview, and payment status endpoints.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardMetrics(BaseModel):
    """Overall dashboard metrics response."""

    total_customers: int = Field(..., description="Total number of customers")
    active_customers: int = Field(
        ...,
        description="Customers with recent activity (last 90 days)",
    )
    jobs_by_status: dict[str, int] = Field(
        ...,
        description="Count of jobs grouped by status",
    )
    today_appointments: int = Field(
        ...,
        description="Number of appointments scheduled for today",
    )
    available_staff: int = Field(
        ...,
        description="Number of staff members currently available",
    )
    total_staff: int = Field(..., description="Total number of active staff members")
    new_leads_today: int = Field(
        default=0,
        description="Number of new leads submitted today",
    )
    uncontacted_leads: int = Field(
        default=0,
        description="Number of leads with status 'new' (not yet contacted)",
    )

    model_config = {"from_attributes": True}


class RequestVolumeMetrics(BaseModel):
    """Request volume metrics for tracking job requests over time."""

    period_start: date = Field(..., description="Start date of the period")
    period_end: date = Field(..., description="End date of the period")
    total_requests: int = Field(..., description="Total job requests in period")
    requests_by_day: dict[str, int] = Field(
        ...,
        description="Job requests grouped by day (ISO date string -> count)",
    )
    requests_by_category: dict[str, int] = Field(
        ...,
        description="Job requests grouped by category",
    )
    requests_by_source: dict[str, int] = Field(
        ...,
        description="Job requests grouped by source",
    )
    average_daily_requests: float = Field(
        ...,
        description="Average number of requests per day",
    )

    model_config = {"from_attributes": True}


class ScheduleOverview(BaseModel):
    """Schedule overview for the dashboard."""

    schedule_date: date = Field(..., description="Date of the schedule overview")
    total_appointments: int = Field(
        ...,
        description="Total appointments for the date",
    )
    appointments_by_status: dict[str, int] = Field(
        ...,
        description="Appointments grouped by status",
    )
    appointments_by_staff: dict[str, int] = Field(
        ...,
        description="Appointments grouped by staff member name",
    )
    total_scheduled_minutes: int = Field(
        ...,
        description="Total scheduled time in minutes",
    )
    staff_utilization: dict[str, float] = Field(
        ...,
        description="Staff utilization percentage (staff name -> percentage)",
    )

    model_config = {"from_attributes": True}


class PaymentStatusOverview(BaseModel):
    """Payment status overview for the dashboard."""

    total_invoices: int = Field(..., description="Total number of invoices")
    pending_invoices: int = Field(..., description="Number of pending invoices")
    paid_invoices: int = Field(..., description="Number of paid invoices")
    overdue_invoices: int = Field(..., description="Number of overdue invoices")
    total_pending_amount: float = Field(
        ...,
        description="Total amount pending payment",
    )
    total_overdue_amount: float = Field(..., description="Total overdue amount")
    average_days_to_payment: float = Field(
        ...,
        description="Average days from invoice to payment",
    )

    model_config = {"from_attributes": True}


class RecentActivityItem(BaseModel):
    """Single item in the recent activity feed."""

    id: UUID = Field(..., description="Unique identifier for the activity")
    activity_type: str = Field(
        ...,
        description="Type of activity (job_created, status_changed, etc.)",
    )
    description: str = Field(..., description="Human-readable description")
    job_id: Optional[UUID] = Field(None, description="Related job ID if applicable")
    customer_name: str = Field(
        ...,
        description="Customer name associated with activity",
    )
    timestamp: datetime = Field(..., description="When the activity occurred")

    model_config = {"from_attributes": True}


class RecentActivityResponse(BaseModel):
    """Response containing recent activity items."""

    items: list[RecentActivityItem] = Field(..., description="List of activity items")
    total: int = Field(..., description="Total number of activity items")

    model_config = {"from_attributes": True}


class JobsByStatusResponse(BaseModel):
    """Jobs count grouped by status."""

    requested: int = Field(default=0, description="Jobs in requested status")
    approved: int = Field(default=0, description="Jobs in approved status")
    scheduled: int = Field(default=0, description="Jobs in scheduled status")
    in_progress: int = Field(default=0, description="Jobs in progress")
    completed: int = Field(default=0, description="Completed jobs")
    closed: int = Field(default=0, description="Closed jobs")
    cancelled: int = Field(default=0, description="Cancelled jobs")

    model_config = {"from_attributes": True}


class TodayScheduleResponse(BaseModel):
    """Today's schedule summary."""

    schedule_date: date = Field(..., description="Today's date")
    total_appointments: int = Field(
        ...,
        description="Total appointments for today",
    )
    completed_appointments: int = Field(
        ...,
        description="Completed appointments today",
    )
    in_progress_appointments: int = Field(
        ...,
        description="Appointments currently in progress",
    )
    upcoming_appointments: int = Field(
        ...,
        description="Upcoming appointments today",
    )
    cancelled_appointments: int = Field(
        ...,
        description="Cancelled appointments today",
    )

    model_config = {"from_attributes": True}
