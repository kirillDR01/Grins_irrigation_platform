"""Pydantic schemas for estimates, estimate templates, and contract templates.

Validates: CRM Gap Closure Req 16, 17, 48, 51, 78, 83
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from grins_platform.models.enums import EstimateStatus, FollowUpStatus

# =============================================================================
# Estimate Template Schemas
# =============================================================================


class EstimateTemplateCreate(BaseModel):
    """Schema for creating an estimate template.

    Validates: CRM Gap Closure Req 17.1, 17.2, 75.1, 75.2
    """

    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Template description",
    )
    line_items: list[dict[str, Any]] | None = Field(
        default=None,
        description="Default line items",
    )
    terms: str | None = Field(
        default=None,
        max_length=5000,
        description="Default terms",
    )


class EstimateTemplateResponse(BaseModel):
    """Schema for estimate template response.

    Validates: CRM Gap Closure Req 17.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Template UUID")
    name: str = Field(..., description="Template name")
    description: str | None = Field(default=None, description="Template description")
    line_items: list[dict[str, Any]] | None = Field(
        default=None,
        description="Default line items",
    )
    terms: str | None = Field(default=None, description="Default terms")
    is_active: bool = Field(..., description="Whether template is active")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")


class EstimateTemplateUpdate(BaseModel):
    """Schema for updating an estimate template.

    Validates: CRM Gap Closure Req 17.3
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    line_items: list[dict[str, Any]] | None = Field(default=None)
    terms: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = Field(default=None)


# =============================================================================
# Contract Template Schemas
# =============================================================================


class ContractTemplateCreate(BaseModel):
    """Schema for creating a contract template.

    Validates: CRM Gap Closure Req 17.1, 17.2, 75.1, 75.2
    """

    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    body: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Contract body text",
    )
    terms_and_conditions: str | None = Field(
        default=None,
        max_length=50000,
        description="Terms and conditions",
    )


class ContractTemplateResponse(BaseModel):
    """Schema for contract template response.

    Validates: CRM Gap Closure Req 17.4
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Template UUID")
    name: str = Field(..., description="Template name")
    body: str = Field(..., description="Contract body text")
    terms_and_conditions: str | None = Field(
        default=None,
        description="Terms and conditions",
    )
    is_active: bool = Field(..., description="Whether template is active")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")


class ContractTemplateUpdate(BaseModel):
    """Schema for updating a contract template.

    Validates: CRM Gap Closure Req 17.4
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=50000)
    terms_and_conditions: str | None = Field(default=None, max_length=50000)
    is_active: bool | None = Field(default=None)


# =============================================================================
# Estimate line-item shape (umbrella plan Phase 3 / Task 3.1).
# =============================================================================


class EstimateLineItem(BaseModel):
    """Shape of one entry in ``Estimate.line_items`` (JSONB).

    The column stays ``list[dict[str, Any]]`` for backwards-compat — every
    estimate ever written predates this schema. New consumers should
    validate dicts through this model on read so the new fields are
    surfaced consistently. Older rows simply have the new keys absent.

    Phase 3 additions (umbrella plan E2 / P5 / N3 seam):
      * ``service_offering_id`` — pin the line to the live pricelist row
        the tech picked from. Lets us keep historic estimates rendering
        their original prices via the immutable archive chain.
      * ``unit_cost`` — staff-only internal cost per unit, hidden from
        the customer-facing PDF/portal. Drives the margin readout in
        the staff edit drawer.
      * ``material_markup_pct`` — 0 by default (the markup math is
        deferred per N3, but the column is here so future activation
        is a UI/config change rather than a migration).
    """

    model_config = ConfigDict(extra="allow")

    item: str | None = Field(
        default=None,
        description="Free-form item label rendered to the customer",
    )
    description: str | None = Field(
        default=None,
        description="Optional sub-description rendered below ``item``",
    )
    quantity: Decimal = Field(
        default=Decimal(1),
        ge=0,
        description="Number of units / zones / hours",
    )
    unit_price: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Customer-facing per-unit price (the committed number)",
    )
    # Phase 3 additions ---------------------------------------------------
    service_offering_id: UUID | None = Field(
        default=None,
        description=(
            "FK to the ``service_offerings`` row the tech picked. "
            "Null for legacy / template-derived items."
        ),
    )
    unit_cost: Decimal | None = Field(
        default=None,
        ge=0,
        description=(
            "Internal cost-per-unit (staff-only). MUST NOT render on "
            "customer-facing PDF or portal. Drives the margin readout in "
            "the staff edit drawer."
        ),
    )
    material_markup_pct: Decimal = Field(
        default=Decimal(0),
        ge=0,
        le=Decimal(500),
        description=(
            "Material markup percentage applied on top of ``unit_cost``. "
            "Default 0 — the markup math is deferred (umbrella plan N3); "
            "the field is here as a future-proofing seam."
        ),
    )
    # Tier metadata (Phase 3 / N4 schema seam — Good/Better/Best).
    selected_tier: str | None = Field(
        default=None,
        description=(
            "Picked range_anchors tier label ('low' | 'mid' | 'high') "
            "when the offering exposes range_anchors. Free-form for "
            "future tier names."
        ),
    )


# =============================================================================
# Estimate Schemas
# =============================================================================


class EstimateCreate(BaseModel):
    """Schema for creating an estimate.

    Validates: CRM Gap Closure Req 48.1, 75.1, 75.2, 75.4
    """

    lead_id: UUID | None = Field(default=None, description="Lead UUID")
    customer_id: UUID | None = Field(default=None, description="Customer UUID")
    job_id: UUID | None = Field(default=None, description="Job UUID")
    template_id: UUID | None = Field(default=None, description="Template UUID")
    line_items: list[dict[str, Any]] | None = Field(
        default=None,
        description="Estimate line items",
    )
    options: list[dict[str, Any]] | None = Field(
        default=None,
        description="Good/Better/Best tier options",
    )
    subtotal: Decimal = Field(default=Decimal(0), ge=0, description="Subtotal")
    tax_amount: Decimal = Field(default=Decimal(0), ge=0, description="Tax amount")
    discount_amount: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Discount amount",
    )
    total: Decimal = Field(default=Decimal(0), ge=0, description="Total amount")
    promotion_code: str | None = Field(
        default=None,
        max_length=50,
        description="Promotion code",
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


class EstimateResponse(BaseModel):
    """Schema for estimate response.

    Validates: CRM Gap Closure Req 48.1, 83.2
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(..., description="Estimate UUID")
    lead_id: UUID | None = Field(default=None, description="Lead UUID")
    customer_id: UUID | None = Field(default=None, description="Customer UUID")
    job_id: UUID | None = Field(default=None, description="Job UUID")
    template_id: UUID | None = Field(default=None, description="Template UUID")
    status: EstimateStatus = Field(..., description="Estimate status")
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
        description="Promotion code",
    )
    valid_until: datetime | None = Field(
        default=None,
        description="Estimate validity date",
    )
    notes: str | None = Field(default=None, description="Estimate notes")
    customer_token: UUID | None = Field(
        default=None,
        description="Portal access token",
    )
    token_expires_at: datetime | None = Field(
        default=None,
        description="Token expiry",
    )
    token_readonly: bool = Field(
        default=False,
        description="Whether token is read-only after approval",
    )
    approved_at: datetime | None = Field(
        default=None,
        description="Approval timestamp",
    )
    rejected_at: datetime | None = Field(
        default=None,
        description="Rejection timestamp",
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Rejection reason",
        validation_alias=AliasChoices("rejection_reason", "rejected_reason"),
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")


class EstimateUpdate(BaseModel):
    """Schema for updating an estimate.

    Validates: CRM Gap Closure Req 48.2
    """

    lead_id: UUID | None = Field(default=None)
    customer_id: UUID | None = Field(default=None)
    job_id: UUID | None = Field(default=None)
    line_items: list[dict[str, Any]] | None = Field(default=None)
    options: list[dict[str, Any]] | None = Field(default=None)
    subtotal: Decimal | None = Field(default=None, ge=0)
    tax_amount: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal | None = Field(default=None, ge=0)
    total: Decimal | None = Field(default=None, ge=0)
    promotion_code: str | None = Field(default=None, max_length=50)
    valid_until: datetime | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=5000)


class EstimateSendResponse(BaseModel):
    """Response after sending an estimate to customer.

    Validates: CRM Gap Closure Req 48.5
    """

    estimate_id: UUID = Field(..., description="Estimate UUID")
    portal_url: str = Field(..., max_length=2048, description="Portal URL")
    sent_via: list[str] = Field(
        ...,
        description="Channels used (sms, email)",
    )


# =============================================================================
# Follow-Up Schemas
# =============================================================================


class FollowUpResponse(BaseModel):
    """Schema for estimate follow-up response.

    Validates: CRM Gap Closure Req 51.2
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Follow-up UUID")
    estimate_id: UUID = Field(..., description="Estimate UUID")
    follow_up_number: int = Field(..., ge=1, description="Follow-up sequence number")
    scheduled_at: datetime = Field(..., description="Scheduled send time")
    sent_at: datetime | None = Field(default=None, description="Actual send time")
    channel: str = Field(..., max_length=20, description="SMS or EMAIL")
    message: str | None = Field(default=None, description="Follow-up message")
    promotion_code: str | None = Field(
        default=None,
        description="Promotion code for this follow-up",
    )
    status: FollowUpStatus = Field(..., description="Follow-up status")
    created_at: datetime = Field(..., description="Record creation timestamp")


# =============================================================================
# Activity Timeline (Req 83)
# =============================================================================


class EstimateActivityEvent(BaseModel):
    """Single event in estimate activity timeline.

    Validates: CRM Gap Closure Req 83.2, 83.3
    """

    event_type: str = Field(
        ...,
        max_length=50,
        description="Event type (created, sent, viewed, etc.)",
    )
    timestamp: datetime = Field(..., description="When the event occurred")
    actor: str | None = Field(
        default=None,
        max_length=200,
        description="Who performed the action",
    )
    details: str | None = Field(
        default=None,
        max_length=2000,
        description="Event details",
    )


class EstimateDetailResponse(EstimateResponse):
    """Estimate detail with activity timeline.

    Validates: CRM Gap Closure Req 83.2, 83.3
    """

    activity_timeline: list[EstimateActivityEvent] = Field(
        default_factory=list,
        description="Chronological activity events",
    )
    follow_ups: list[FollowUpResponse] = Field(
        default_factory=list,
        description="Scheduled follow-ups",
    )
