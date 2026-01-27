"""Pydantic schemas for staff reassignment.

Validates: Requirements 11.1-11.6
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MarkUnavailableRequest(BaseModel):
    """Request to mark staff as unavailable."""

    target_date: date
    reason: str = Field(..., min_length=1, max_length=500)


class MarkUnavailableResponse(BaseModel):
    """Response from marking staff unavailable."""

    staff_id: UUID
    target_date: date
    affected_appointments: int
    message: str


class ReassignStaffRequest(BaseModel):
    """Request to reassign jobs from one staff to another."""

    original_staff_id: UUID
    new_staff_id: UUID
    target_date: date
    reason: str = Field(..., min_length=1, max_length=500)


class ReassignStaffResponse(BaseModel):
    """Response from staff reassignment."""

    reassignment_id: UUID
    original_staff_id: UUID
    new_staff_id: UUID
    target_date: date
    jobs_reassigned: int
    message: str


class CoverageOption(BaseModel):
    """A coverage option for reassignment."""

    staff_id: UUID
    staff_name: str
    available_capacity_minutes: int
    current_jobs: int
    can_cover_all: bool


class CoverageOptionsResponse(BaseModel):
    """Response with coverage options."""

    target_date: date
    jobs_to_cover: int
    total_duration_minutes: int
    options: list[CoverageOption] = Field(default_factory=list)


class ReassignmentRecordResponse(BaseModel):
    """Response for a reassignment record."""

    id: UUID
    original_staff_id: UUID
    new_staff_id: UUID
    reassignment_date: date
    reason: str
    jobs_reassigned: int
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
