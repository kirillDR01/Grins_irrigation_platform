"""
Staff Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for staff-related API operations,
including creation, updates, responses, and query parameters.

Validates: Requirements 8.1-8.10, 9.1-9.5
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from grins_platform.models.enums import SkillLevel, StaffRole
from grins_platform.schemas.customer import normalize_phone


class StaffCreate(BaseModel):
    """Schema for creating a new staff member.

    Validates: Requirements 8.1-8.3, 8.8-8.10, 2.1, 3.1 (Route Optimization)
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Full name of the staff member",
    )
    phone: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Phone number (10 digits, North American format)",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Email address (optional)",
    )
    role: StaffRole = Field(
        ...,
        description="Staff role (tech, sales, admin)",
    )
    skill_level: SkillLevel | None = Field(
        default=None,
        description="Skill level (junior, senior, lead)",
    )
    certifications: list[str] | None = Field(
        default=None,
        description="List of certifications",
    )
    assigned_equipment: list[str] | None = Field(
        default=None,
        description="List of assigned equipment (e.g., compressor, pipe_puller)",
    )
    default_start_address: str | None = Field(
        default=None,
        max_length=255,
        description="Default starting address for route optimization",
    )
    default_start_city: str | None = Field(
        default=None,
        max_length=100,
        description="Default starting city",
    )
    default_start_lat: Decimal | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Default starting latitude (-90 to 90)",
    )
    default_start_lng: Decimal | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Default starting longitude (-180 to 180)",
    )
    hourly_rate: Decimal | None = Field(
        default=None,
        ge=0,
        description="Hourly compensation rate (must be non-negative)",
    )
    is_available: bool = Field(
        default=True,
        description="Whether currently available for work",
    )
    availability_notes: str | None = Field(
        default=None,
        description="Notes about availability",
    )

    @field_validator("phone")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize phone number to 10 digits."""
        return normalize_phone(v)

    @field_validator("name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_name(cls, v: str) -> str:
        """Strip leading/trailing whitespace from name."""
        return v.strip()


class StaffUpdate(BaseModel):
    """Schema for updating an existing staff member.

    All fields are optional - only provided fields will be updated.

    Validates: Requirement 8.5, 2.1, 3.1 (Route Optimization)
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Full name of the staff member",
    )
    phone: str | None = Field(
        default=None,
        min_length=10,
        max_length=20,
        description="Phone number",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Email address",
    )
    role: StaffRole | None = Field(
        default=None,
        description="Staff role",
    )
    skill_level: SkillLevel | None = Field(
        default=None,
        description="Skill level",
    )
    certifications: list[str] | None = Field(
        default=None,
        description="List of certifications",
    )
    assigned_equipment: list[str] | None = Field(
        default=None,
        description="List of assigned equipment",
    )
    default_start_address: str | None = Field(
        default=None,
        max_length=255,
        description="Default starting address",
    )
    default_start_city: str | None = Field(
        default=None,
        max_length=100,
        description="Default starting city",
    )
    default_start_lat: Decimal | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Default starting latitude",
    )
    default_start_lng: Decimal | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Default starting longitude",
    )
    hourly_rate: Decimal | None = Field(
        default=None,
        ge=0,
        description="Hourly compensation rate",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether the staff member is active",
    )

    @field_validator("phone")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate and normalize phone number if provided."""
        if v is None:
            return None
        return normalize_phone(v)

    @field_validator("name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        """Strip leading/trailing whitespace from name if provided."""
        if v is None:
            return None
        return v.strip()


class StaffAvailabilityUpdate(BaseModel):
    """Schema for updating staff availability.

    Validates: Requirements 9.1, 9.2
    """

    is_available: bool = Field(
        ...,
        description="Whether currently available for work",
    )
    availability_notes: str | None = Field(
        default=None,
        description="Notes about availability (e.g., vacation dates)",
    )


class StaffResponse(BaseModel):
    """Schema for staff response data.

    Validates: Requirement 8.4, 2.1, 3.1 (Route Optimization)
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique staff identifier")
    name: str = Field(..., description="Full name of the staff member")
    phone: str = Field(..., description="Phone number (normalized)")
    email: str | None = Field(default=None, description="Email address")
    role: StaffRole = Field(..., description="Staff role")
    skill_level: SkillLevel | None = Field(
        default=None,
        description="Skill level",
    )
    certifications: list[str] | None = Field(
        default=None,
        description="List of certifications",
    )
    assigned_equipment: list[str] | None = Field(
        default=None,
        description="List of assigned equipment",
    )
    default_start_address: str | None = Field(
        default=None,
        description="Default starting address",
    )
    default_start_city: str | None = Field(
        default=None,
        description="Default starting city",
    )
    default_start_lat: Decimal | None = Field(
        default=None,
        description="Default starting latitude",
    )
    default_start_lng: Decimal | None = Field(
        default=None,
        description="Default starting longitude",
    )
    is_available: bool = Field(..., description="Whether currently available")
    availability_notes: str | None = Field(
        default=None,
        description="Notes about availability",
    )
    hourly_rate: Decimal | None = Field(
        default=None,
        description="Hourly compensation rate",
    )
    is_active: bool = Field(..., description="Whether the staff member is active")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    @field_validator("role", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_role(cls, v: str | StaffRole) -> StaffRole:
        """Convert string role to enum if needed."""
        if isinstance(v, str):
            return StaffRole(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("skill_level", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_skill_level(cls, v: str | SkillLevel | None) -> SkillLevel | None:
        """Convert string skill_level to enum if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            return SkillLevel(v)
        return v  # type: ignore[return-value,unreachable]


class StaffListParams(BaseModel):
    """Query parameters for listing staff members.

    Validates: Requirements 9.4, 9.5
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
    role: StaffRole | None = Field(
        default=None,
        description="Filter by staff role",
    )
    skill_level: SkillLevel | None = Field(
        default=None,
        description="Filter by skill level",
    )
    is_available: bool | None = Field(
        default=None,
        description="Filter by availability",
    )
    is_active: bool | None = Field(
        default=None,
        description="Filter by active status",
    )
    search: str | None = Field(
        default=None,
        description="Search by name (case-insensitive)",
    )
    sort_by: str = Field(
        default="name",
        description="Field to sort by",
    )
    sort_order: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    )


class PaginatedStaffResponse(BaseModel):
    """Paginated response for staff list.

    Validates: Requirement 9.4
    """

    items: list[StaffResponse] = Field(
        ...,
        description="List of staff members",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of staff matching filters",
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
