"""Pydantic schemas for sales pipeline metrics.

Validates: CRM Gap Closure Req 47.3
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class SalesMetricsResponse(BaseModel):
    """Sales pipeline metrics.

    Validates: CRM Gap Closure Req 47.3
    """

    estimates_needing_writeup_count: int = Field(
        ...,
        ge=0,
        description="Estimates needing writeup",
    )
    pending_approval_count: int = Field(
        ...,
        ge=0,
        description="Estimates pending customer approval",
    )
    needs_followup_count: int = Field(
        ...,
        ge=0,
        description="Estimates needing follow-up",
    )
    total_pipeline_revenue: Decimal = Field(
        default=Decimal(0),
        description="Total pipeline revenue",
    )
    conversion_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Estimate-to-job conversion rate",
    )
