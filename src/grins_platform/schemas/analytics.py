"""Pydantic schemas for staff time and lead time analytics.

Validates: CRM Gap Closure Req 25.2, 37.2
"""

from uuid import UUID

from pydantic import BaseModel, Field


class StaffTimeAnalyticsResponse(BaseModel):
    """Staff time analytics per staff/job type.

    Validates: CRM Gap Closure Req 37.2
    """

    staff_id: UUID | None = Field(default=None, description="Staff UUID")
    staff_name: str | None = Field(
        default=None,
        max_length=200,
        description="Staff display name",
    )
    job_type: str | None = Field(
        default=None,
        max_length=50,
        description="Job type",
    )
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
    flagged: bool = Field(
        default=False,
        description="Whether staff exceeds 1.5x average",
    )


class LeadTimeResponse(BaseModel):
    """Schedule booking lead time.

    Validates: CRM Gap Closure Req 25.2
    """

    days: int = Field(..., ge=0, description="Days until earliest available slot")
    display: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable display",
    )
