"""Schedule explanation schemas for AI-powered schedule insights.

This module defines schemas for:
- Schedule explanations (why jobs were assigned the way they were)
- Unassigned job explanations (why specific jobs couldn't be scheduled)
- Natural language constraint parsing
- Jobs ready to schedule preview

Validates: Schedule AI Updates Requirements 2.1, 3.1, 4.1, 6.1, 9.1
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

# =============================================================================
# Schedule Explanation Schemas (Requirement 2.1)
# =============================================================================


class StaffAssignmentSummary(BaseModel):
    """Summary of staff assignments for explanation."""

    staff_id: UUID
    staff_name: str
    job_count: int
    total_minutes: int
    cities: list[str]
    job_types: list[str]


class ScheduleExplanationRequest(BaseModel):
    """Request for schedule explanation."""

    schedule_date: date
    staff_assignments: list[StaffAssignmentSummary]
    unassigned_job_count: int


class ScheduleExplanationResponse(BaseModel):
    """Response with schedule explanation."""

    explanation: str = Field(
        ...,
        description="Natural language explanation of schedule",
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="Key points about the schedule",
    )


# =============================================================================
# Unassigned Job Explanation Schemas (Requirement 3.1)
# =============================================================================


class UnassignedJobExplanationRequest(BaseModel):
    """Request for unassigned job explanation."""

    job_id: UUID
    job_type: str
    customer_name: str
    city: str
    estimated_duration_minutes: int
    priority: str
    requires_equipment: list[str] = Field(default_factory=list)
    constraint_violations: list[str] = Field(
        default_factory=list,
        description="Constraint violations from solver",
    )


class UnassignedJobExplanationResponse(BaseModel):
    """Response with unassigned job explanation."""

    reason: str = Field(..., description="Why the job couldn't be scheduled")
    suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable suggestions to resolve",
    )
    alternative_dates: list[date] = Field(
        default_factory=list,
        description="Suggested alternative dates",
    )


# =============================================================================
# Natural Language Constraint Parsing (Requirement 4.1)
# =============================================================================


class ParsedConstraint(BaseModel):
    """A parsed scheduling constraint."""

    constraint_type: str = Field(
        ...,
        description="Type: staff_time, job_grouping, staff_restriction, geographic",
    )
    description: str = Field(..., description="Human-readable description")
    parameters: dict[str, str | int | list[str]] = Field(
        ...,
        description="Structured parameters for solver",
    )
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Validation errors if any",
    )


class ParseConstraintsRequest(BaseModel):
    """Request to parse natural language constraints."""

    constraint_text: str = Field(..., min_length=1, max_length=1000)


class ParseConstraintsResponse(BaseModel):
    """Response with parsed constraints."""

    constraints: list[ParsedConstraint]
    unparseable_text: str | None = Field(
        None,
        description="Text that couldn't be parsed",
    )


# =============================================================================
# Jobs Ready to Schedule (Requirement 9.1)
# =============================================================================


class JobReadyToSchedule(BaseModel):
    """A job ready to be scheduled."""

    job_id: UUID
    customer_id: UUID
    customer_name: str
    job_type: str
    city: str
    priority: str  # legacy label, kept for back-compat with older clients
    estimated_duration_minutes: int
    requires_equipment: list[str] = Field(default_factory=list)
    status: str
    # Extended fields consumed by the Pick-Jobs page (Requirements 4.1, 4.8-4.10)
    address: str | None = Field(
        default=None,
        description="Street address from Property.address",
    )
    customer_tags: list[str] = Field(
        default_factory=list,
        description="Lowercased CustomerTag.label values for the customer",
    )
    property_type: str | None = Field(
        default=None,
        description="Property.property_type ('residential' | 'commercial' | None)",
    )
    property_is_hoa: bool | None = Field(
        default=None,
        description="Property.is_hoa flag",
    )
    requested_week: str | None = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD, Monday) from Job.target_start_date",
    )
    notes: str | None = Field(
        default=None,
        description="Job.notes",
    )
    priority_level: int = Field(
        default=0,
        description="Raw Job.priority_level (0-2)",
    )
    effective_priority_level: int = Field(
        default=0,
        description=(
            "Display priority for the picker: max of base priority, "
            "'priority' tag (=>1), and active service agreement (=>1)."
        ),
    )
    has_active_agreement: bool = Field(
        default=False,
        description="True if customer has any ServiceAgreement with status='active'",
    )


class JobsReadyToScheduleResponse(BaseModel):
    """Response with jobs ready to schedule."""

    jobs: list[JobReadyToSchedule]
    total_count: int
    by_city: dict[str, int] = Field(
        default_factory=dict,
        description="Job count by city",
    )
    by_job_type: dict[str, int] = Field(
        default_factory=dict,
        description="Job count by job type",
    )
