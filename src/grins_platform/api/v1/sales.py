"""Sales API endpoints.

Provides sales pipeline metrics for the Sales Dashboard.

Validates: CRM Gap Closure Req 47.3
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import (
    func as sa_func,
    select as sa_select,
)
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import EstimateStatus
from grins_platform.models.estimate import Estimate
from grins_platform.models.estimate_follow_up import EstimateFollowUp
from grins_platform.schemas.sales import SalesMetricsResponse

router = APIRouter()


class _SalesEndpoints(LoggerMixin):
    """Sales API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _SalesEndpoints()


@router.get(
    "/metrics",
    response_model=SalesMetricsResponse,
    summary="Get sales pipeline metrics",
    description="Returns estimate pipeline counts and revenue metrics.",
)
async def get_sales_metrics(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SalesMetricsResponse:
    """Get sales pipeline metrics.

    Validates: CRM Gap Closure Req 47.3
    """
    _endpoints.log_started("get_sales_metrics")

    # Estimates needing writeup (DRAFT)
    draft_q = (
        sa_select(sa_func.count())
        .select_from(Estimate)
        .where(
            Estimate.status == EstimateStatus.DRAFT.value,
        )
    )
    draft_result = await session.execute(draft_q)
    draft_count: int = draft_result.scalar() or 0

    # Pending approval (SENT or VIEWED)
    pending_q = (
        sa_select(sa_func.count())
        .select_from(Estimate)
        .where(
            Estimate.status.in_(
                [
                    EstimateStatus.SENT.value,
                    EstimateStatus.VIEWED.value,
                ],
            ),
        )
    )
    pending_result = await session.execute(pending_q)
    pending_count: int = pending_result.scalar() or 0

    # Needs follow-up: estimates with pending follow-ups
    followup_q = (
        sa_select(sa_func.count(sa_func.distinct(EstimateFollowUp.estimate_id)))
        .select_from(EstimateFollowUp)
        .where(EstimateFollowUp.status == "PENDING")
    )
    followup_result = await session.execute(followup_q)
    followup_count: int = followup_result.scalar() or 0

    # Total pipeline revenue (sum of totals for non-terminal estimates)
    revenue_q = sa_select(sa_func.coalesce(sa_func.sum(Estimate.total), 0)).where(
        Estimate.status.in_(
            [
                EstimateStatus.DRAFT.value,
                EstimateStatus.SENT.value,
                EstimateStatus.VIEWED.value,
            ],
        ),
    )
    revenue_result = await session.execute(revenue_q)
    pipeline_revenue = revenue_result.scalar() or 0

    # Conversion rate
    total_q = sa_select(sa_func.count()).select_from(Estimate)
    total_result = await session.execute(total_q)
    total_estimates: int = total_result.scalar() or 0

    approved_q = (
        sa_select(sa_func.count())
        .select_from(Estimate)
        .where(
            Estimate.status == EstimateStatus.APPROVED.value,
        )
    )
    approved_result = await session.execute(approved_q)
    approved_count: int = approved_result.scalar() or 0

    conversion_rate = (
        round((approved_count / total_estimates) * 100, 1)
        if total_estimates > 0
        else 0.0
    )

    _endpoints.log_completed(
        "get_sales_metrics",
        draft=draft_count,
        pending=pending_count,
        followup=followup_count,
    )

    return SalesMetricsResponse(
        estimates_needing_writeup_count=draft_count,
        pending_approval_count=pending_count,
        needs_followup_count=followup_count,
        total_pipeline_revenue=pipeline_revenue,
        conversion_rate=conversion_rate,
    )
