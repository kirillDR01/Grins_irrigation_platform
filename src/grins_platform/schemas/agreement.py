"""Pydantic schemas for agreement API endpoints.

Request/response schemas for agreements, tiers, metrics, compliance,
and dashboard extension.

Validates: Requirements 19.1-19.7, 20.1-20.3, 38.1-38.3
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Agreement Tier schemas
# ---------------------------------------------------------------------------


class AgreementTierResponse(BaseModel):
    """Response schema for a service agreement tier."""

    id: UUID
    name: str
    slug: str
    description: str | None = None
    package_type: str
    annual_price: Decimal
    billing_frequency: str
    included_services: list[dict[str, Any]]
    perks: list[str] | None = None
    is_active: bool
    display_order: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Agreement Status Log schemas
# ---------------------------------------------------------------------------


class AgreementStatusLogResponse(BaseModel):
    """Response schema for an agreement status log entry."""

    id: UUID
    old_status: str | None = None
    new_status: str
    changed_by: UUID | None = None
    changed_by_name: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] | None = Field(None, alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ---------------------------------------------------------------------------
# Agreement schemas
# ---------------------------------------------------------------------------


class AgreementJobSummary(BaseModel):
    """Summary of a job linked to an agreement."""

    id: UUID
    job_type: str | None = None
    status: str
    target_start_date: date | None = None
    target_end_date: date | None = None

    model_config = {"from_attributes": True}


class AgreementResponse(BaseModel):
    """Response schema for a service agreement (list view)."""

    id: UUID
    agreement_number: str
    customer_id: UUID
    customer_name: str | None = None
    tier_id: UUID
    tier_name: str | None = None
    package_type: str | None = None
    property_id: UUID | None = None
    status: str
    annual_price: Decimal
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    auto_renew: bool
    payment_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgreementDetailResponse(AgreementResponse):
    """Detailed response for a single agreement."""

    stripe_subscription_id: str | None = None
    stripe_customer_id: str | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    cancellation_refund_amount: Decimal | None = None
    pause_reason: str | None = None
    last_payment_date: datetime | None = None
    last_payment_amount: Decimal | None = None
    renewal_approved_by: UUID | None = None
    renewal_approved_at: datetime | None = None
    consent_recorded_at: datetime | None = None
    consent_method: str | None = None
    last_annual_notice_sent: datetime | None = None
    last_renewal_notice_sent: datetime | None = None
    notes: str | None = None
    jobs: list[AgreementJobSummary] = Field(default_factory=list)
    status_logs: list[AgreementStatusLogResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedAgreementResponse(BaseModel):
    """Paginated list of agreements."""

    items: list[AgreementResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Agreement request schemas
# ---------------------------------------------------------------------------


class AgreementStatusUpdateRequest(BaseModel):
    """Request to update agreement status."""

    status: str = Field(..., description="New status value")
    reason: str | None = Field(None, description="Reason for status change")


class AgreementRenewalRejectRequest(BaseModel):
    """Request to reject a renewal (optional reason)."""

    reason: str | None = Field(None, description="Reason for rejection")


class AgreementNotesUpdateRequest(BaseModel):
    """Request to update agreement admin notes."""

    notes: str | None = Field(None, description="Admin notes text")


# ---------------------------------------------------------------------------
# Metrics schemas
# ---------------------------------------------------------------------------


class AgreementMetricsResponse(BaseModel):
    """Response schema for agreement business metrics."""

    active_count: int
    mrr: Decimal
    arpa: Decimal
    renewal_rate: Decimal
    churn_rate: Decimal
    past_due_amount: Decimal


class MrrDataPointResponse(BaseModel):
    """Single month MRR data point."""

    month: str
    mrr: Decimal


class MrrHistoryResponse(BaseModel):
    """MRR over trailing 12 months."""

    data_points: list[MrrDataPointResponse]


class TierDistributionItemResponse(BaseModel):
    """Active agreement count for a single tier."""

    tier_id: str
    tier_name: str
    package_type: str
    active_count: int


class TierDistributionResponse(BaseModel):
    """Active agreement counts grouped by tier."""

    items: list[TierDistributionItemResponse]


# ---------------------------------------------------------------------------
# Compliance schemas
# ---------------------------------------------------------------------------


class DisclosureRecordResponse(BaseModel):
    """Response schema for a disclosure record."""

    id: UUID
    agreement_id: UUID | None = None
    customer_id: UUID | None = None
    disclosure_type: str
    sent_at: datetime
    sent_via: str
    recipient_email: str | None = None
    recipient_phone: str | None = None
    delivery_confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dashboard extension schemas
# ---------------------------------------------------------------------------


class DashboardSummaryExtension(BaseModel):
    """Extended dashboard summary with agreement and lead metrics."""

    active_agreement_count: int = 0
    mrr: Decimal = Decimal("0.00")
    renewal_pipeline_count: int = 0
    failed_payment_count: int = 0
    failed_payment_amount: Decimal = Decimal("0.00")
    new_leads_count: int = 0
    follow_up_queue_count: int = 0
    leads_awaiting_contact_oldest_age_hours: float | None = None
