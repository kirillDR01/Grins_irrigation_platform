"""
Pydantic schemas for schedule generation API.

Validates: Requirements 5.1, 5.3, 5.4, 5.8
"""

from __future__ import annotations

from datetime import date, time  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field


class ScheduleGenerateRequest(BaseModel):
    """Request to generate a schedule for a date."""

    schedule_date: date
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class ScheduleJobAssignment(BaseModel):
    """A job assignment in the generated schedule."""

    job_id: UUID
    customer_name: str
    address: str | None = None
    city: str | None = None
    service_type: str
    start_time: time
    end_time: time
    duration_minutes: int
    travel_time_minutes: int
    sequence_index: int


class ScheduleStaffAssignment(BaseModel):
    """Staff assignment with their jobs for the day."""

    staff_id: UUID
    staff_name: str
    jobs: list[ScheduleJobAssignment] = Field(default_factory=list)
    total_jobs: int = 0
    total_travel_minutes: int = 0
    first_job_start: time | None = None
    last_job_end: time | None = None


class UnassignedJob(BaseModel):
    """A job that could not be assigned."""

    job_id: UUID
    customer_name: str
    service_type: str
    reason: str


class ScheduleGenerateResponse(BaseModel):
    """Response from schedule generation."""

    schedule_date: date
    is_feasible: bool
    hard_score: int
    soft_score: int
    assignments: list[ScheduleStaffAssignment] = Field(default_factory=list)
    unassigned_jobs: list[UnassignedJob] = Field(default_factory=list)
    total_jobs: int = 0
    total_assigned: int = 0
    total_travel_minutes: int = 0
    optimization_time_seconds: float = 0.0


class ScheduleCapacityResponse(BaseModel):
    """Response for schedule capacity check."""

    schedule_date: date
    total_staff: int
    available_staff: int
    total_capacity_minutes: int
    scheduled_minutes: int
    remaining_capacity_minutes: int
    can_accept_more: bool


class EmergencyInsertRequest(BaseModel):
    """Request to insert an emergency job into existing schedule.

    Validates: Requirements 9.1, 9.4
    """

    job_id: UUID
    target_date: date
    priority_level: int = Field(default=2, ge=0, le=3)  # 2=urgent, 3=emergency


class EmergencyInsertResponse(BaseModel):
    """Response from emergency job insertion."""

    success: bool
    job_id: UUID
    target_date: date
    assigned_staff_id: UUID | None = None
    assigned_staff_name: str | None = None
    scheduled_time: time | None = None
    bumped_jobs: list[UUID] = Field(default_factory=list)
    constraint_violations: list[str] = Field(default_factory=list)
    message: str


class ReoptimizeRequest(BaseModel):
    """Request to re-optimize an existing schedule."""

    target_date: date
    timeout_seconds: int = Field(default=15, ge=5, le=60)
