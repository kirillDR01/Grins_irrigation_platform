"""
Job Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for job-related API operations,
including creation, updates, responses, status transitions, and query parameters.

Validates: Requirements 2.1-2.12, 4.1-4.10, 5.1-5.7, 6.1-6.9
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from typing import Any
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field, field_validator

from grins_platform.models.enums import (
    JobCategory,
    JobSource,
    JobStatus,
    PricingModel,
)


class JobCreate(BaseModel):
    """Schema for creating a new job request.

    Validates: Requirements 2.1-2.12, 3.1-3.5
    """

    customer_id: UUID = Field(
        ...,
        description="Reference to the customer",
    )
    property_id: UUID | None = Field(
        default=None,
        description="Reference to the property (optional)",
    )
    service_offering_id: UUID | None = Field(
        default=None,
        description="Reference to the service offering (optional)",
    )
    job_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of job (spring_startup, repair, etc.)",
    )
    description: str | None = Field(
        default=None,
        description="Job description and notes",
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        gt=0,
        description="Estimated time to complete (must be positive)",
    )
    priority_level: int = Field(
        default=0,
        ge=0,
        le=2,
        description="Priority (0=normal, 1=high, 2=urgent)",
    )
    weather_sensitive: bool = Field(
        default=False,
        description="Whether job depends on weather",
    )
    staffing_required: int = Field(
        default=1,
        ge=1,
        description="Number of staff needed (minimum 1)",
    )
    equipment_required: list[str] | None = Field(
        default=None,
        description="List of equipment needed",
    )
    materials_required: list[str] | None = Field(
        default=None,
        description="List of materials needed",
    )
    quoted_amount: Decimal | None = Field(
        default=None,
        ge=0,
        description="Quoted price for the job (must be non-negative)",
    )
    source: JobSource | None = Field(
        default=None,
        description="Lead source (website, google, referral, etc.)",
    )
    source_details: dict[str, Any] | None = Field(
        default=None,
        description="Additional source information",
    )

    @field_validator("job_type")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_job_type(cls, v: str) -> str:
        """Strip leading/trailing whitespace and lowercase job type."""
        return v.strip().lower()


class JobUpdate(BaseModel):
    """Schema for updating an existing job.

    All fields are optional - only provided fields will be updated.

    Validates: Requirements 3.6, 3.7
    """

    property_id: UUID | None = Field(
        default=None,
        description="Reference to the property",
    )
    service_offering_id: UUID | None = Field(
        default=None,
        description="Reference to the service offering",
    )
    job_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Type of job",
    )
    category: JobCategory | None = Field(
        default=None,
        description="Job category (manual override)",
    )
    description: str | None = Field(
        default=None,
        description="Job description and notes",
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        gt=0,
        description="Estimated time to complete",
    )
    priority_level: int | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Priority level",
    )
    weather_sensitive: bool | None = Field(
        default=None,
        description="Whether job depends on weather",
    )
    staffing_required: int | None = Field(
        default=None,
        ge=1,
        description="Number of staff needed",
    )
    equipment_required: list[str] | None = Field(
        default=None,
        description="List of equipment needed",
    )
    materials_required: list[str] | None = Field(
        default=None,
        description="List of materials needed",
    )
    quoted_amount: Decimal | None = Field(
        default=None,
        ge=0,
        description="Quoted price for the job",
    )
    final_amount: Decimal | None = Field(
        default=None,
        ge=0,
        description="Final price after completion",
    )
    source: JobSource | None = Field(
        default=None,
        description="Lead source",
    )
    source_details: dict[str, Any] | None = Field(
        default=None,
        description="Additional source information",
    )

    @field_validator("job_type")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_job_type(cls, v: str | None) -> str | None:
        """Strip leading/trailing whitespace and lowercase job type if provided."""
        if v is None:
            return None
        return v.strip().lower()


class JobStatusUpdate(BaseModel):
    """Schema for updating job status.

    Validates: Requirements 4.1-4.10
    """

    status: JobStatus = Field(
        ...,
        description="New status for the job",
    )
    notes: str | None = Field(
        default=None,
        description="Notes about the status change",
    )


class JobResponse(BaseModel):
    """Schema for job response data.

    Validates: Requirement 6.1
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique job identifier")
    customer_id: UUID = Field(..., description="Reference to the customer")
    property_id: UUID | None = Field(
        default=None,
        description="Reference to the property",
    )
    service_offering_id: UUID | None = Field(
        default=None,
        description="Reference to the service offering",
    )
    job_type: str = Field(..., description="Type of job")
    category: JobCategory = Field(..., description="Job category")
    status: JobStatus = Field(..., description="Current status")
    description: str | None = Field(default=None, description="Job description")
    estimated_duration_minutes: int | None = Field(
        default=None,
        description="Estimated time to complete",
    )
    priority_level: int = Field(..., description="Priority level")
    weather_sensitive: bool = Field(..., description="Weather dependency")
    staffing_required: int = Field(..., description="Number of staff needed")
    equipment_required: list[str] | None = Field(
        default=None,
        description="Equipment needed",
    )
    materials_required: list[str] | None = Field(
        default=None,
        description="Materials needed",
    )
    quoted_amount: Decimal | None = Field(
        default=None,
        description="Quoted price",
    )
    final_amount: Decimal | None = Field(
        default=None,
        description="Final price",
    )
    source: JobSource | None = Field(default=None, description="Lead source")
    source_details: dict[str, Any] | None = Field(
        default=None,
        description="Source details",
    )
    requested_at: datetime | None = Field(
        default=None,
        description="When the job was requested",
    )
    approved_at: datetime | None = Field(
        default=None,
        description="When the job was approved",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="When the job was scheduled",
    )
    started_at: datetime | None = Field(
        default=None,
        description="When work started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When work was completed",
    )
    closed_at: datetime | None = Field(
        default=None,
        description="When the job was closed",
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    @field_validator("category", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_category(cls, v: str | JobCategory) -> JobCategory:
        """Convert string category to enum if needed."""
        if isinstance(v, str):
            return JobCategory(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("status", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_status(cls, v: str | JobStatus) -> JobStatus:
        """Convert string status to enum if needed."""
        if isinstance(v, str):
            return JobStatus(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("source", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_source(cls, v: str | JobSource | None) -> JobSource | None:
        """Convert string source to enum if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            return JobSource(v)
        return v  # type: ignore[return-value,unreachable]


class JobStatusHistoryResponse(BaseModel):
    """Schema for job status history response.

    Validates: Requirements 7.1-7.4
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique history entry identifier")
    job_id: UUID = Field(..., description="Reference to the job")
    previous_status: JobStatus | None = Field(
        default=None,
        description="Previous status",
    )
    new_status: JobStatus = Field(..., description="New status")
    changed_at: datetime = Field(..., description="When the change occurred")
    changed_by: str | None = Field(
        default=None,
        description="Who made the change",
    )
    notes: str | None = Field(default=None, description="Notes about the change")

    @field_validator("previous_status", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_previous_status(cls, v: str | JobStatus | None) -> JobStatus | None:
        """Convert string previous_status to enum if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            return JobStatus(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("new_status", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_new_status(cls, v: str | JobStatus) -> JobStatus:
        """Convert string new_status to enum if needed."""
        if isinstance(v, str):
            return JobStatus(v)
        return v  # type: ignore[return-value,unreachable]


class JobDetailResponse(JobResponse):
    """Schema for detailed job response with related entities.

    Validates: Requirements 6.1, 7.2
    """

    # Forward references resolved at runtime
    customer: Any = Field(..., description="Customer details")
    job_property: Any | None = Field(default=None, description="Property details")
    service_offering: Any | None = Field(
        default=None,
        description="Service offering details",
    )
    status_history: list[JobStatusHistoryResponse] = Field(
        default_factory=list,
        description="Status change history",
    )


class PriceCalculationResponse(BaseModel):
    """Schema for price calculation response.

    Validates: Requirements 5.1-5.7
    """

    job_id: UUID = Field(..., description="Reference to the job")
    service_offering_id: UUID | None = Field(
        default=None,
        description="Reference to the service offering",
    )
    pricing_model: PricingModel | None = Field(
        default=None,
        description="Pricing model used",
    )
    base_price: Decimal | None = Field(
        default=None,
        description="Base price from service offering",
    )
    zone_count: int | None = Field(
        default=None,
        description="Number of zones from property",
    )
    calculated_price: Decimal | None = Field(
        default=None,
        description="Calculated price (null if requires manual quote)",
    )
    requires_manual_quote: bool = Field(
        ...,
        description="Whether manual quoting is required",
    )
    calculation_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Details about the calculation",
    )


class JobListParams(BaseModel):
    """Query parameters for listing jobs.

    Validates: Requirements 6.1-6.9
    """

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    )
    status: JobStatus | None = Field(
        default=None,
        description="Filter by job status",
    )
    category: JobCategory | None = Field(
        default=None,
        description="Filter by job category",
    )
    customer_id: UUID | None = Field(
        default=None,
        description="Filter by customer",
    )
    property_id: UUID | None = Field(
        default=None,
        description="Filter by property",
    )
    service_offering_id: UUID | None = Field(
        default=None,
        description="Filter by service offering",
    )
    priority_level: int | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Filter by priority level",
    )
    date_from: datetime | None = Field(
        default=None,
        description="Filter jobs created after this date",
    )
    date_to: datetime | None = Field(
        default=None,
        description="Filter jobs created before this date",
    )
    search: str | None = Field(
        default=None,
        description="Search by job type or description",
    )
    sort_by: str = Field(
        default="created_at",
        description="Field to sort by",
    )
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    )


class PaginatedJobResponse(BaseModel):
    """Paginated response for job list.

    Validates: Requirement 6.1
    """

    items: list[JobResponse] = Field(
        ...,
        description="List of jobs",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of jobs matching filters",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Number of items per page",
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
    )
