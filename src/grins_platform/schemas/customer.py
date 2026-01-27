"""
Customer Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for customer-related API operations,
including creation, updates, responses, and query parameters.

Validates: Requirement 1.2, 1.3, 1.4, 3.1-3.4, 4.1-4.7, 7.2, 12.3-12.4
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from grins_platform.models.enums import CustomerStatus, LeadSource

if TYPE_CHECKING:
    from grins_platform.schemas.property import PropertyResponse


def normalize_phone(phone: str) -> str:
    """Normalize phone number to 10 digits.

    Removes all non-digit characters and validates North American format.

    Args:
        phone: Phone number string in any format

    Returns:
        Normalized 10-digit phone string

    Raises:
        ValueError: If phone doesn't contain exactly 10 digits

    Validates: Requirement 6.10
    """
    digits = "".join(filter(str.isdigit, phone))
    # Handle 11-digit numbers starting with 1 (country code)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        msg = "Phone must be 10 digits (North American format)"
        raise ValueError(msg)
    return digits


class CustomerCreate(BaseModel):
    """Schema for creating a new customer.

    Validates: Requirement 1.2, 1.3
    """

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Customer's first name",
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Customer's last name",
    )
    phone: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Customer's phone number (10 digits, North American format)",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Customer's email address (RFC 5322 format)",
    )
    lead_source: LeadSource | None = Field(
        default=None,
        description="How the customer found the business",
    )
    lead_source_details: dict[str, Any] | None = Field(
        default=None,
        description="Additional lead source information",
    )
    sms_opt_in: bool = Field(
        default=False,
        description="SMS communication opt-in status",
    )
    email_opt_in: bool = Field(
        default=False,
        description="Email communication opt-in status",
    )

    @field_validator("phone")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize phone number to 10 digits.

        Validates: Requirement 1.3, 6.10
        """
        return normalize_phone(v)

    @field_validator("first_name", "last_name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace from names."""
        return v.strip()


class CustomerUpdate(BaseModel):
    """Schema for updating an existing customer.

    All fields are optional - only provided fields will be updated.

    Validates: Requirement 1.5
    """

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Customer's first name",
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Customer's last name",
    )
    phone: str | None = Field(
        default=None,
        min_length=10,
        max_length=20,
        description="Customer's phone number (10 digits, North American format)",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Customer's email address (RFC 5322 format)",
    )
    status: CustomerStatus | None = Field(
        default=None,
        description="Customer status (active/inactive)",
    )
    lead_source: LeadSource | None = Field(
        default=None,
        description="How the customer found the business",
    )
    lead_source_details: dict[str, Any] | None = Field(
        default=None,
        description="Additional lead source information",
    )
    sms_opt_in: bool | None = Field(
        default=None,
        description="SMS communication opt-in status",
    )
    email_opt_in: bool | None = Field(
        default=None,
        description="Email communication opt-in status",
    )

    @field_validator("phone")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate and normalize phone number if provided."""
        if v is None:
            return None
        return normalize_phone(v)

    @field_validator("first_name", "last_name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        """Strip leading/trailing whitespace from names if provided."""
        if v is None:
            return None
        return v.strip()


class CustomerFlagsUpdate(BaseModel):
    """Schema for updating customer flags.

    Validates: Requirement 3.1-3.4
    """

    is_priority: bool | None = Field(
        default=None,
        description="Priority customer flag for expedited service",
    )
    is_red_flag: bool | None = Field(
        default=None,
        description="Red flag for behavioral or access concerns",
    )
    is_slow_payer: bool | None = Field(
        default=None,
        description="Slow payer flag for payment history issues",
    )
    is_new_customer: bool | None = Field(
        default=None,
        description="New customer flag (vs returning customer)",
    )


class ServiceHistorySummary(BaseModel):
    """Summary of customer service history.

    Validates: Requirement 7.2
    """

    total_jobs: int = Field(
        ...,
        ge=0,
        description="Total number of jobs completed for customer",
    )
    last_service_date: datetime | None = Field(
        default=None,
        description="Date of most recent service",
    )
    total_revenue: float = Field(
        ...,
        ge=0,
        description="Total revenue from customer across all services",
    )


class CustomerResponse(BaseModel):
    """Schema for customer response data.

    Validates: Requirement 1.4
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique customer identifier")
    first_name: str = Field(..., description="Customer's first name")
    last_name: str = Field(..., description="Customer's last name")
    phone: str = Field(..., description="Customer's phone number (normalized)")
    email: str | None = Field(default=None, description="Customer's email address")
    status: CustomerStatus = Field(..., description="Customer status")
    is_priority: bool = Field(..., description="Priority customer flag")
    is_red_flag: bool = Field(..., description="Red flag indicator")
    is_slow_payer: bool = Field(..., description="Slow payer flag")
    is_new_customer: bool = Field(..., description="New customer flag")
    sms_opt_in: bool = Field(..., description="SMS opt-in status")
    email_opt_in: bool = Field(..., description="Email opt-in status")
    lead_source: LeadSource | None = Field(
        default=None,
        description="Lead source",
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    @field_validator("status", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_status(cls, v: str | CustomerStatus) -> CustomerStatus:
        """Convert string status to enum if needed."""
        if isinstance(v, str):
            return CustomerStatus(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("lead_source", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_lead_source(
        cls,
        v: str | LeadSource | None,
    ) -> LeadSource | None:
        """Convert string lead_source to enum if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            return LeadSource(v)
        return v  # type: ignore[return-value,unreachable]


class CustomerDetailResponse(CustomerResponse):
    """Detailed customer response including properties and service history.

    Validates: Requirement 1.4, 7.2
    """

    # Import PropertyResponse here to avoid circular imports
    properties: list[PropertyResponse] = Field(
        default_factory=list,
        description="Customer's properties",
    )
    service_history_summary: ServiceHistorySummary | None = Field(
        default=None,
        description="Summary of service history",
    )


class CustomerListParams(BaseModel):
    """Query parameters for listing customers.

    Validates: Requirement 4.1-4.7
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
    city: str | None = Field(
        default=None,
        description="Filter by city (customers with properties in this city)",
    )
    status: CustomerStatus | None = Field(
        default=None,
        description="Filter by customer status",
    )
    is_priority: bool | None = Field(
        default=None,
        description="Filter by priority flag",
    )
    is_red_flag: bool | None = Field(
        default=None,
        description="Filter by red flag",
    )
    is_slow_payer: bool | None = Field(
        default=None,
        description="Filter by slow payer flag",
    )
    search: str | None = Field(
        default=None,
        description="Search by name or email (case-insensitive)",
    )
    sort_by: str = Field(
        default="last_name",
        description="Field to sort by",
    )
    sort_order: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    )


class PaginatedCustomerResponse(BaseModel):
    """Paginated response for customer list.

    Validates: Requirement 4.1
    """

    items: list[CustomerResponse] = Field(
        ...,
        description="List of customers",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of customers matching filters",
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


class BulkPreferencesUpdate(BaseModel):
    """Schema for bulk updating communication preferences.

    Validates: Requirement 12.3-12.4
    """

    customer_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of customer IDs to update (max 1000)",
    )
    sms_opt_in: bool | None = Field(
        default=None,
        description="New SMS opt-in status",
    )
    email_opt_in: bool | None = Field(
        default=None,
        description="New email opt-in status",
    )


class BulkUpdateResponse(BaseModel):
    """Response for bulk update operations.

    Validates: Requirement 12.5
    """

    updated_count: int = Field(
        ...,
        ge=0,
        description="Number of records successfully updated",
    )
    failed_count: int = Field(
        ...,
        ge=0,
        description="Number of records that failed to update",
    )
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of errors for failed updates",
    )


def _rebuild_models() -> None:
    """Rebuild models to resolve forward references.

    This function is called at module load time to resolve the forward
    reference to PropertyResponse in CustomerDetailResponse.
    """
    # Import here to avoid circular import at module level
    from grins_platform.schemas import property as property_schemas  # noqa: PLC0415

    # Update the forward reference
    CustomerDetailResponse.model_rebuild(
        _types_namespace={"PropertyResponse": property_schemas.PropertyResponse},
    )


_rebuild_models()
