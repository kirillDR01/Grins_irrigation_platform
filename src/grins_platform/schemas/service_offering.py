"""
ServiceOffering Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for service offering-related API
operations, including creation, updates, responses, and query parameters.

Validates: Requirements 1.1-1.13, 10.1-10.2, 10.6-10.7
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field, field_validator

from grins_platform.models.enums import PricingModel, ServiceCategory


class ServiceOfferingCreate(BaseModel):
    """Schema for creating a new service offering.

    Validates: Requirements 1.1-1.3, 10.6-10.7
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the service offering",
    )
    category: ServiceCategory = Field(
        ...,
        description="Service category (seasonal, repair, installation, etc.)",
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of the service",
    )
    base_price: Decimal | None = Field(
        default=None,
        ge=0,
        description="Base price for the service (must be non-negative)",
    )
    price_per_zone: Decimal | None = Field(
        default=None,
        ge=0,
        description="Additional price per zone for zone-based pricing",
    )
    pricing_model: PricingModel = Field(
        ...,
        description="Pricing model (flat, zone_based, hourly, custom)",
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        gt=0,
        description="Base estimated duration in minutes (must be positive)",
    )
    duration_per_zone_minutes: int | None = Field(
        default=None,
        gt=0,
        description="Additional minutes per zone (must be positive)",
    )
    staffing_required: int = Field(
        default=1,
        ge=1,
        description="Number of staff members required (minimum 1)",
    )
    equipment_required: list[str] | None = Field(
        default=None,
        description="List of equipment needed for the service",
    )
    lien_eligible: bool = Field(
        default=False,
        description="Whether service qualifies for mechanic's lien",
    )
    requires_prepay: bool = Field(
        default=False,
        description="Whether payment is required before work",
    )

    @field_validator("name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_name(cls, v: str) -> str:
        """Strip leading/trailing whitespace from name."""
        return v.strip()


class ServiceOfferingUpdate(BaseModel):
    """Schema for updating an existing service offering.

    All fields are optional - only provided fields will be updated.

    Validates: Requirement 1.5
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Name of the service offering",
    )
    category: ServiceCategory | None = Field(
        default=None,
        description="Service category",
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of the service",
    )
    base_price: Decimal | None = Field(
        default=None,
        ge=0,
        description="Base price for the service",
    )
    price_per_zone: Decimal | None = Field(
        default=None,
        ge=0,
        description="Additional price per zone",
    )
    pricing_model: PricingModel | None = Field(
        default=None,
        description="Pricing model",
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        gt=0,
        description="Base estimated duration in minutes",
    )
    duration_per_zone_minutes: int | None = Field(
        default=None,
        gt=0,
        description="Additional minutes per zone",
    )
    staffing_required: int | None = Field(
        default=None,
        ge=1,
        description="Number of staff members required",
    )
    equipment_required: list[str] | None = Field(
        default=None,
        description="List of equipment needed",
    )
    lien_eligible: bool | None = Field(
        default=None,
        description="Whether service qualifies for mechanic's lien",
    )
    requires_prepay: bool | None = Field(
        default=None,
        description="Whether payment is required before work",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether the service is currently offered",
    )

    @field_validator("name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        """Strip leading/trailing whitespace from name if provided."""
        if v is None:
            return None
        return v.strip()


class ServiceOfferingResponse(BaseModel):
    """Schema for service offering response data.

    Validates: Requirement 1.4
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique service offering identifier")
    name: str = Field(..., description="Name of the service offering")
    category: ServiceCategory = Field(..., description="Service category")
    description: str | None = Field(
        default=None,
        description="Detailed description",
    )
    base_price: Decimal | None = Field(
        default=None,
        description="Base price for the service",
    )
    price_per_zone: Decimal | None = Field(
        default=None,
        description="Additional price per zone",
    )
    pricing_model: PricingModel = Field(..., description="Pricing model")
    estimated_duration_minutes: int | None = Field(
        default=None,
        description="Base estimated duration in minutes",
    )
    duration_per_zone_minutes: int | None = Field(
        default=None,
        description="Additional minutes per zone",
    )
    staffing_required: int = Field(..., description="Number of staff required")
    equipment_required: list[str] | None = Field(
        default=None,
        description="List of equipment needed",
    )
    lien_eligible: bool = Field(
        ...,
        description="Whether service qualifies for mechanic's lien",
    )
    requires_prepay: bool = Field(
        ...,
        description="Whether payment is required before work",
    )
    is_active: bool = Field(..., description="Whether the service is active")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    @field_validator("category", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_category(cls, v: str | ServiceCategory) -> ServiceCategory:
        """Convert string category to enum if needed."""
        if isinstance(v, str):
            return ServiceCategory(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("pricing_model", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_pricing_model(cls, v: str | PricingModel) -> PricingModel:
        """Convert string pricing_model to enum if needed."""
        if isinstance(v, str):
            return PricingModel(v)
        return v  # type: ignore[return-value,unreachable]


class ServiceListParams(BaseModel):
    """Query parameters for listing service offerings.

    Validates: Requirement 1.11
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
    category: ServiceCategory | None = Field(
        default=None,
        description="Filter by service category",
    )
    pricing_model: PricingModel | None = Field(
        default=None,
        description="Filter by pricing model",
    )
    is_active: bool | None = Field(
        default=None,
        description="Filter by active status",
    )
    lien_eligible: bool | None = Field(
        default=None,
        description="Filter by lien eligibility",
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


class PaginatedServiceResponse(BaseModel):
    """Paginated response for service offering list.

    Validates: Requirement 1.11
    """

    items: list[ServiceOfferingResponse] = Field(
        ...,
        description="List of service offerings",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of services matching filters",
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
