"""
Staff Availability Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for staff availability API operations,
including creation, updates, responses, and query parameters.

Validates: Requirements 1.1, 1.6, 1.7 (Route Optimization)
"""

from __future__ import annotations

from datetime import (
    date as date_type,
    datetime,
    time,
)
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StaffAvailabilityCreate(BaseModel):
    """Schema for creating a staff availability entry.

    Validates: Requirements 1.1, 1.6, 1.7
    """

    date: date_type = Field(
        ...,
        description="Date of availability",
    )
    start_time: time = Field(
        default=time(7, 0),
        description="Start time of availability window",
    )
    end_time: time = Field(
        default=time(17, 0),
        description="End time of availability window",
    )
    is_available: bool = Field(
        default=True,
        description="Whether the staff member is available",
    )
    lunch_start: time | None = Field(
        default=time(12, 0),
        description="Start time of lunch break (optional)",
    )
    lunch_duration_minutes: int = Field(
        default=30,
        ge=0,
        le=120,
        description="Duration of lunch break in minutes (0-120)",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Additional notes about availability",
    )

    @model_validator(mode="after")  # type: ignore[misc,untyped-decorator]
    def validate_time_ranges(self) -> StaffAvailabilityCreate:
        """Validate time range constraints.

        Requirement 1.6: Start time must be before end time.
        Requirement 1.7: Lunch time must be within availability window.
        """
        # Validate start_time < end_time
        if self.start_time >= self.end_time:
            msg = "start_time must be before end_time"
            raise ValueError(msg)

        # Validate lunch_start within window if specified
        if self.lunch_start is not None:
            if self.lunch_start < self.start_time:
                msg = "lunch_start must be at or after start_time"
                raise ValueError(msg)
            if self.lunch_start >= self.end_time:
                msg = "lunch_start must be before end_time"
                raise ValueError(msg)

            # Validate lunch doesn't extend past end_time
            lunch_start_minutes = self.lunch_start.hour * 60 + self.lunch_start.minute
            lunch_end_minutes = lunch_start_minutes + self.lunch_duration_minutes
            end_minutes = self.end_time.hour * 60 + self.end_time.minute

            if lunch_end_minutes > end_minutes:
                msg = "lunch break must end before end_time"
                raise ValueError(msg)

        return self


class StaffAvailabilityUpdate(BaseModel):
    """Schema for updating a staff availability entry.

    All fields are optional - only provided fields will be updated.

    Validates: Requirements 1.3, 1.6, 1.7
    """

    start_time: time | None = Field(
        default=None,
        description="Start time of availability window",
    )
    end_time: time | None = Field(
        default=None,
        description="End time of availability window",
    )
    is_available: bool | None = Field(
        default=None,
        description="Whether the staff member is available",
    )
    lunch_start: time | None = Field(
        default=None,
        description="Start time of lunch break",
    )
    lunch_duration_minutes: int | None = Field(
        default=None,
        ge=0,
        le=120,
        description="Duration of lunch break in minutes (0-120)",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Additional notes about availability",
    )

    @model_validator(mode="after")  # type: ignore[misc,untyped-decorator]
    def validate_time_ranges(self) -> StaffAvailabilityUpdate:
        """Validate time range constraints when both times are provided.

        Requirement 1.6: Start time must be before end time.
        """
        # Only validate if both times are provided
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)

        return self


class StaffAvailabilityResponse(BaseModel):
    """Schema for staff availability response data.

    Validates: Requirement 1.2
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique availability entry identifier")
    staff_id: UUID = Field(..., description="Staff member identifier")
    date: date_type = Field(..., description="Date of availability")
    start_time: time = Field(..., description="Start time of availability window")
    end_time: time = Field(..., description="End time of availability window")
    is_available: bool = Field(..., description="Whether the staff member is available")
    lunch_start: time | None = Field(
        default=None,
        description="Start time of lunch break",
    )
    lunch_duration_minutes: int = Field(
        ...,
        description="Duration of lunch break in minutes",
    )
    notes: str | None = Field(default=None, description="Additional notes")
    available_minutes: int = Field(
        ...,
        description="Total available minutes excluding lunch",
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")


class StaffAvailabilityListParams(BaseModel):
    """Query parameters for listing staff availability entries.

    Validates: Requirement 1.2
    """

    start_date: date_type | None = Field(
        default=None,
        description="Start date for filtering (inclusive)",
    )
    end_date: date_type | None = Field(
        default=None,
        description="End date for filtering (inclusive)",
    )
    is_available: bool | None = Field(
        default=None,
        description="Filter by availability status",
    )

    @model_validator(mode="after")  # type: ignore[misc,untyped-decorator]
    def validate_date_range(self) -> StaffAvailabilityListParams:
        """Validate that start_date is before or equal to end_date."""
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            msg = "start_date must be before or equal to end_date"
            raise ValueError(msg)
        return self


class StaffWithAvailability(BaseModel):
    """Schema for staff member with their availability for a specific date.

    Validates: Requirement 1.5
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Staff member identifier")
    name: str = Field(..., description="Staff member name")
    availability: StaffAvailabilityResponse = Field(
        ...,
        description="Availability entry for the requested date",
    )


class AvailableStaffOnDateResponse(BaseModel):
    """Response schema for available staff on a specific date.

    Validates: Requirement 1.5
    """

    date: date_type = Field(..., description="The queried date")
    available_staff: list[StaffWithAvailability] = Field(
        ...,
        description="List of available staff members with their availability",
    )
    total_available: int = Field(
        ...,
        ge=0,
        description="Total number of available staff",
    )
