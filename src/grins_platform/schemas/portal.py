"""Pydantic schemas for public portal endpoints.

Validates: CRM Gap Closure Req 16, 78, 84
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Estimate Portal (Req 16, 78)
# =============================================================================


class PortalEstimateResponse(BaseModel):
    """Public estimate view — no internal IDs exposed.

    Validates: CRM Gap Closure Req 78.6, 84.2
    """

    estimate_number: str | None = Field(
        default=None,
        max_length=50,
        description="Estimate reference number",
    )
    status: str = Field(..., max_length=20, description="Estimate status")
    line_items: list[dict[str, Any]] | None = Field(
        default=None,
        description="Estimate line items",
    )
    options: list[dict[str, Any]] | None = Field(
        default=None,
        description="Good/Better/Best tier options",
    )
    subtotal: Decimal = Field(..., description="Subtotal")
    tax_amount: Decimal = Field(..., description="Tax amount")
    discount_amount: Decimal = Field(..., description="Discount amount")
    total: Decimal = Field(..., description="Total amount")
    promotion_code: str | None = Field(
        default=None,
        max_length=50,
        description="Applied promotion code",
    )
    valid_until: datetime | None = Field(
        default=None,
        description="Estimate validity date",
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Estimate notes",
    )
    company_name: str | None = Field(
        default=None,
        max_length=200,
        description="Company name",
    )
    readonly: bool = Field(
        default=False,
        description="Whether estimate is read-only (already approved)",
    )


class PortalApproveRequest(BaseModel):
    """Request to approve an estimate via portal.

    Validates: CRM Gap Closure Req 16.2, 78.4
    """

    ip_address: str | None = Field(
        default=None,
        max_length=45,
        description="Client IP address",
    )
    user_agent: str | None = Field(
        default=None,
        max_length=500,
        description="Client user agent",
    )


class PortalRejectRequest(BaseModel):
    """Request to reject an estimate via portal.

    Validates: CRM Gap Closure Req 16.3
    """

    reason: str | None = Field(
        default=None,
        max_length=2000,
        description="Rejection reason",
    )


class PortalSignRequest(BaseModel):
    """Request to sign a contract via portal.

    Validates: CRM Gap Closure Req 16.4
    """

    signature_data: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Base64 signature data",
    )
    ip_address: str | None = Field(
        default=None,
        max_length=45,
        description="Client IP address",
    )
    user_agent: str | None = Field(
        default=None,
        max_length=500,
        description="Client user agent",
    )


# =============================================================================
# Invoice Portal (Req 84)
# =============================================================================


class PortalInvoiceResponse(BaseModel):
    """Public invoice view — no internal IDs exposed.

    Validates: CRM Gap Closure Req 84.2, 84.9
    """

    invoice_number: str = Field(
        ...,
        max_length=50,
        description="Invoice number",
    )
    invoice_date: str = Field(
        ...,
        max_length=20,
        description="Invoice date",
    )
    due_date: str = Field(..., max_length=20, description="Due date")
    line_items: list[dict[str, Any]] | None = Field(
        default=None,
        description="Invoice line items",
    )
    total: Decimal = Field(..., description="Total amount")
    paid: Decimal = Field(default=Decimal(0), description="Amount paid")
    balance: Decimal = Field(default=Decimal(0), description="Remaining balance")
    status: str = Field(..., max_length=20, description="Invoice status")
    payment_link: str | None = Field(
        default=None,
        max_length=2048,
        description="Stripe payment link",
    )
    company_name: str | None = Field(
        default=None,
        max_length=200,
        description="Company name",
    )
    company_address: str | None = Field(
        default=None,
        max_length=500,
        description="Company address",
    )
    company_phone: str | None = Field(
        default=None,
        max_length=20,
        description="Company phone",
    )
    company_logo_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Company logo URL",
    )
