"""Pydantic schemas for staff location and break operations.

Validates: CRM Gap Closure Req 41.1, 41.5, 42.2
"""

from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, Field


class StaffLocationRequest(BaseModel):
    """Request to update staff GPS location.

    Validates: CRM Gap Closure Req 41.1
    """

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="GPS latitude",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="GPS longitude",
    )
    appointment_id: UUID | None = Field(
        default=None,
        description="Current appointment UUID (optional)",
    )


class StaffLocationResponse(BaseModel):
    """Staff GPS location response.

    Validates: CRM Gap Closure Req 41.5
    """

    staff_id: UUID = Field(..., description="Staff UUID")
    latitude: float = Field(..., description="GPS latitude")
    longitude: float = Field(..., description="GPS longitude")
    timestamp: str = Field(..., description="ISO timestamp of location update")
    appointment_id: UUID | None = Field(
        default=None,
        description="Current appointment UUID",
    )


class StaffBreakCreateRequest(BaseModel):
    """Request to start a staff break.

    Validates: CRM Gap Closure Req 42.2
    """

    break_type: str = Field(
        ...,
        description="Break type: lunch, gas, personal, other",
    )
    appointment_id: UUID | None = Field(
        default=None,
        description="Appointment before the break (optional)",
    )


class StaffBreakResponse(BaseModel):
    """Staff break response.

    Validates: CRM Gap Closure Req 42.2
    """

    id: UUID = Field(..., description="Break UUID")
    staff_id: UUID = Field(..., description="Staff UUID")
    appointment_id: UUID | None = Field(
        default=None,
        description="Appointment before the break",
    )
    start_time: time = Field(..., description="Break start time")
    end_time: time | None = Field(default=None, description="Break end time")
    break_type: str = Field(..., description="Break type")
    created_at: datetime | None = Field(
        default=None,
        description="Record creation timestamp",
    )
