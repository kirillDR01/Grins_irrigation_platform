"""
Pydantic schemas for invoice management.

This module defines the Pydantic schemas for invoice-related
API requests and responses.

Validates: Schedule Workflow Improvements Requirements 7.1-7.10, 8.1-8.10,
           9.1-9.7, 10.1-10.7, 11.1-11.8, 12.1-12.5, 13.1-13.7
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from grins_platform.models.enums import InvoiceStatus, PaymentMethod

# Validation error messages
_ERR_QUANTITY_POSITIVE = "Quantity must be positive"
_ERR_AMOUNT_NON_NEGATIVE = "Amount must be non-negative"
_ERR_PAYMENT_AMOUNT_POSITIVE = "Payment amount must be positive"


class InvoiceLineItem(BaseModel):
    """Schema for invoice line item.

    Validates: Requirement 7.8
    """

    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Line item description",
    )
    quantity: Decimal = Field(
        ...,
        gt=0,
        description="Quantity (must be positive)",
    )
    unit_price: Decimal = Field(
        ...,
        ge=0,
        description="Unit price (must be non-negative)",
    )
    total: Decimal = Field(
        ...,
        ge=0,
        description="Line item total (must be non-negative)",
    )

    @field_validator("quantity")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        """Validate quantity is positive."""
        if v <= 0:
            raise ValueError(_ERR_QUANTITY_POSITIVE)
        return v

    @field_validator("unit_price", "total")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_positive_amounts(cls, v: Decimal) -> Decimal:
        """Validate amounts are non-negative."""
        if v < 0:
            raise ValueError(_ERR_AMOUNT_NON_NEGATIVE)
        return v


# =============================================================================
# Invoice Request Schemas
# =============================================================================


class InvoiceCreate(BaseModel):
    """Schema for creating a new invoice.

    Validates: Requirements 7.1-7.10
    """

    job_id: UUID = Field(
        ...,
        description="Reference to the job",
    )
    amount: Decimal = Field(
        ...,
        ge=0,
        description="Base invoice amount",
    )
    late_fee_amount: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Late fee amount",
    )
    due_date: date = Field(
        ...,
        description="Payment due date",
    )
    line_items: list[InvoiceLineItem] | None = Field(
        default=None,
        description="Invoice line items",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional notes",
    )

    @field_validator("amount", "late_fee_amount")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_amounts(cls, v: Decimal) -> Decimal:
        """Validate amounts are non-negative."""
        if v < 0:
            raise ValueError(_ERR_AMOUNT_NON_NEGATIVE)
        return v


class InvoiceUpdate(BaseModel):
    """Schema for updating an invoice (draft only).

    Validates: Requirements 7.1-7.10
    """

    amount: Decimal | None = Field(
        default=None,
        ge=0,
        description="Base invoice amount",
    )
    late_fee_amount: Decimal | None = Field(
        default=None,
        ge=0,
        description="Late fee amount",
    )
    due_date: date | None = Field(
        default=None,
        description="Payment due date",
    )
    line_items: list[InvoiceLineItem] | None = Field(
        default=None,
        description="Invoice line items",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional notes",
    )

    @field_validator("amount", "late_fee_amount")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_amounts(cls, v: Decimal | None) -> Decimal | None:
        """Validate amounts are non-negative."""
        if v is not None and v < 0:
            raise ValueError(_ERR_AMOUNT_NON_NEGATIVE)
        return v


# =============================================================================
# Invoice Response Schemas
# =============================================================================


class InvoiceResponse(BaseModel):
    """Schema for invoice response.

    Validates: Requirements 7.1-7.10, 13.1-13.7
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Invoice unique identifier")
    job_id: UUID = Field(description="Reference to the job")
    customer_id: UUID = Field(description="Reference to the customer")
    invoice_number: str = Field(description="Unique invoice number")
    amount: Decimal = Field(description="Base invoice amount")
    late_fee_amount: Decimal = Field(description="Late fee amount")
    total_amount: Decimal = Field(description="Total amount (amount + late_fee)")
    invoice_date: date = Field(description="Date invoice was created")
    due_date: date = Field(description="Payment due date")
    status: InvoiceStatus = Field(description="Invoice status")
    payment_method: PaymentMethod | None = Field(
        default=None, description="Method of payment",
    )
    payment_reference: str | None = Field(
        default=None, description="Payment reference/transaction ID",
    )
    paid_at: datetime | None = Field(
        default=None, description="Timestamp when payment was received",
    )
    paid_amount: Decimal | None = Field(default=None, description="Amount paid so far")
    reminder_count: int = Field(description="Number of reminders sent")
    last_reminder_sent: datetime | None = Field(
        default=None, description="Timestamp of last reminder",
    )
    lien_eligible: bool = Field(description="Whether job type is lien-eligible")
    lien_warning_sent: datetime | None = Field(
        default=None, description="Timestamp of 45-day lien warning",
    )
    lien_filed_date: date | None = Field(
        default=None, description="Date lien was filed",
    )
    line_items: list[InvoiceLineItem] | None = Field(
        default=None, description="Invoice line items",
    )
    notes: str | None = Field(default=None, description="Optional notes")
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Record update timestamp")


class InvoiceDetailResponse(InvoiceResponse):
    """Schema for invoice detail response with job and customer info.

    Validates: Requirements 7.1-7.10, 13.1
    """

    job_description: str | None = Field(
        default=None, description="Job description",
    )
    customer_name: str | None = Field(
        default=None, description="Customer full name",
    )
    customer_phone: str | None = Field(
        default=None, description="Customer phone number",
    )
    customer_email: str | None = Field(
        default=None, description="Customer email address",
    )


# =============================================================================
# Payment and Lien Schemas
# =============================================================================


class PaymentRecord(BaseModel):
    """Schema for recording a payment on an invoice.

    Validates: Requirements 9.1-9.7
    """

    amount: Decimal = Field(
        ...,
        gt=0,
        description="Payment amount (must be positive)",
    )
    payment_method: PaymentMethod = Field(
        ...,
        description="Method of payment",
    )
    payment_reference: str | None = Field(
        default=None,
        max_length=255,
        description="Payment reference/transaction ID (optional)",
    )

    @field_validator("amount")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate payment amount is positive."""
        if v <= 0:
            raise ValueError(_ERR_PAYMENT_AMOUNT_POSITIVE)
        return v


class LienFiledRequest(BaseModel):
    """Schema for marking a lien as filed.

    Validates: Requirements 11.1-11.8
    """

    filing_date: date = Field(
        ...,
        description="Date the lien was filed",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional notes about the lien filing",
    )


class LienDeadlineInvoice(BaseModel):
    """Schema for an invoice approaching a lien deadline."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Invoice unique identifier")
    invoice_number: str = Field(description="Unique invoice number")
    customer_id: UUID = Field(description="Reference to the customer")
    customer_name: str | None = Field(
        default=None, description="Customer full name",
    )
    amount: Decimal = Field(description="Invoice amount")
    total_amount: Decimal = Field(description="Total amount due")
    due_date: date = Field(description="Payment due date")
    days_overdue: int = Field(description="Number of days overdue")


class LienDeadlineResponse(BaseModel):
    """Schema for invoices approaching lien deadlines.

    Validates: Requirements 11.4-11.5
    """

    approaching_45_day: list[LienDeadlineInvoice] = Field(
        default_factory=list,
        description="Invoices approaching 45-day lien warning deadline",
    )
    approaching_120_day: list[LienDeadlineInvoice] = Field(
        default_factory=list,
        description="Invoices approaching 120-day lien filing deadline",
    )


# =============================================================================
# Invoice List Schemas
# =============================================================================


class InvoiceListParams(BaseModel):
    """Query parameters for listing invoices.

    Validates: Requirements 13.1-13.7
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
    status: InvoiceStatus | None = Field(
        default=None,
        description="Filter by invoice status",
    )
    customer_id: UUID | None = Field(
        default=None,
        description="Filter by customer",
    )
    date_from: date | None = Field(
        default=None,
        description="Filter invoices created on or after this date",
    )
    date_to: date | None = Field(
        default=None,
        description="Filter invoices created on or before this date",
    )
    lien_eligible: bool | None = Field(
        default=None,
        description="Filter by lien eligibility",
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


class PaginatedInvoiceResponse(BaseModel):
    """Paginated response for invoice list.

    Validates: Requirements 13.1-13.7
    """

    items: list[InvoiceResponse] = Field(
        ...,
        description="List of invoices",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of invoices matching filters",
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
