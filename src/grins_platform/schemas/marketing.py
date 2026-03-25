"""Pydantic schemas for marketing analytics.

Validates: CRM Gap Closure Req 58.2, 63.5, 64.2, 65.1
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LeadSourceAnalytics(BaseModel):
    """Analytics for a single lead source.

    Validates: CRM Gap Closure Req 63.5
    """

    source: str = Field(..., max_length=50, description="Lead source name")
    count: int = Field(..., ge=0, description="Total leads from source")
    converted: int = Field(..., ge=0, description="Converted leads")
    conversion_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Conversion rate percentage",
    )


class FunnelStage(BaseModel):
    """Conversion funnel stage.

    Validates: CRM Gap Closure Req 63.5
    """

    stage: str = Field(..., max_length=50, description="Funnel stage name")
    count: int = Field(..., ge=0, description="Count at this stage")


class LeadAnalyticsResponse(BaseModel):
    """Lead source analytics.

    Validates: CRM Gap Closure Req 63.5
    """

    total_leads: int = Field(..., ge=0, description="Total leads in period")
    conversion_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall conversion rate",
    )
    avg_time_to_conversion_hours: float | None = Field(
        default=None,
        description="Average hours to conversion",
    )
    top_source: str | None = Field(
        default=None,
        max_length=50,
        description="Top performing source",
    )
    sources: list[LeadSourceAnalytics] = Field(
        default_factory=list,
        description="Per-source analytics",
    )
    funnel: list[FunnelStage] = Field(
        default_factory=list,
        description="Conversion funnel stages",
    )


class CACBySourceResponse(BaseModel):
    """Customer acquisition cost by source.

    Validates: CRM Gap Closure Req 58.2
    """

    source: str = Field(..., max_length=50, description="Lead source name")
    total_spend: Decimal = Field(
        default=Decimal(0),
        description="Total marketing spend",
    )
    customers_acquired: int = Field(
        ...,
        ge=0,
        description="Customers acquired from source",
    )
    cac: Decimal = Field(
        default=Decimal(0),
        description="Customer acquisition cost",
    )


class MarketingBudgetCreate(BaseModel):
    """Schema for creating a marketing budget.

    Validates: CRM Gap Closure Req 64.2
    """

    channel: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Marketing channel",
    )
    budget_amount: Decimal = Field(
        ...,
        gt=0,
        description="Budget amount",
    )
    period_start: date = Field(..., description="Budget period start")
    period_end: date = Field(..., description="Budget period end")
    actual_spend: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Actual spend to date",
    )


class MarketingBudgetResponse(BaseModel):
    """Schema for marketing budget response.

    Validates: CRM Gap Closure Req 64.2
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Budget UUID")
    channel: str = Field(..., description="Marketing channel")
    budget_amount: Decimal = Field(..., description="Budget amount")
    period_start: date = Field(..., description="Budget period start")
    period_end: date = Field(..., description="Budget period end")
    actual_spend: Decimal = Field(..., description="Actual spend to date")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")


class QRCodeRequest(BaseModel):
    """Schema for QR code generation.

    Validates: CRM Gap Closure Req 65.1
    """

    target_url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Target URL for QR code",
    )
    campaign_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Campaign name for tracking",
    )
