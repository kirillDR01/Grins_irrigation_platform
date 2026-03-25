"""Marketing API endpoints.

Provides lead analytics, CAC, budget management, and QR code generation.

Validates: CRM Gap Closure Req 58.2, 63.5, 64.2, 65.1
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.marketing_budget_repository import (
    MarketingBudgetRepository,
)
from grins_platform.schemas.marketing import (
    CACBySourceResponse,
    LeadAnalyticsResponse,
    MarketingBudgetCreate,
    MarketingBudgetResponse,
    QRCodeRequest,
)
from grins_platform.services.marketing_service import (
    MarketingService,
    QRCodeGenerationError,
)

router = APIRouter()


class _MarketingEndpoints(LoggerMixin):
    """Marketing API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _MarketingEndpoints()


async def _get_marketing_service() -> MarketingService:
    """Get MarketingService dependency."""
    return MarketingService()


# =============================================================================
# Analytics endpoints
# =============================================================================


@router.get(
    "/lead-analytics",
    response_model=LeadAnalyticsResponse,
    summary="Get lead source analytics",
    description="Returns lead source breakdown, conversion funnel, and metrics.",
)
async def get_lead_analytics(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LeadAnalyticsResponse:
    """Get lead source analytics.

    Validates: CRM Gap Closure Req 63.5
    """
    _endpoints.log_started("get_lead_analytics")
    svc = MarketingService()
    result = await svc.get_lead_analytics(session)
    _endpoints.log_completed("get_lead_analytics")
    return result


@router.get(
    "/cac",
    response_model=list[CACBySourceResponse],
    summary="Get customer acquisition cost",
    description="Returns CAC per lead source.",
)
async def get_cac(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CACBySourceResponse]:
    """Get customer acquisition cost by source.

    Validates: CRM Gap Closure Req 58.2
    """
    _endpoints.log_started("get_cac")
    svc = MarketingService()
    result = await svc.get_cac(session)
    _endpoints.log_completed("get_cac", count=len(result))
    return result


# =============================================================================
# Budget CRUD
# =============================================================================


@router.post(
    "/budgets",
    response_model=MarketingBudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create marketing budget",
)
async def create_budget(
    data: MarketingBudgetCreate,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MarketingBudgetResponse:
    """Create a marketing budget entry.

    Validates: CRM Gap Closure Req 64.2
    """
    _endpoints.log_started("create_budget", channel=data.channel)
    repo = MarketingBudgetRepository(session)
    budget = await repo.create(
        channel=data.channel,
        budget_amount=data.budget_amount,
        period_start=data.period_start,
        period_end=data.period_end,
        actual_spend=data.actual_spend,
    )
    _endpoints.log_completed("create_budget", budget_id=str(budget.id))
    return MarketingBudgetResponse.model_validate(budget)


@router.get(
    "/budgets",
    response_model=dict[str, Any],
    summary="List marketing budgets",
)
async def list_budgets(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """List marketing budgets with pagination.

    Validates: CRM Gap Closure Req 64.2
    """
    _endpoints.log_started("list_budgets", page=page)
    repo = MarketingBudgetRepository(session)
    budgets, total = await repo.list_with_filters(
        page=page,
        page_size=page_size,
    )
    items = [MarketingBudgetResponse.model_validate(b) for b in budgets]
    _endpoints.log_completed("list_budgets", count=len(items))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/budgets/{budget_id}",
    response_model=MarketingBudgetResponse,
    summary="Get marketing budget by ID",
)
async def get_budget(
    budget_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MarketingBudgetResponse:
    """Get a single marketing budget by ID."""
    _endpoints.log_started("get_budget", budget_id=str(budget_id))
    repo = MarketingBudgetRepository(session)
    budget = await repo.get_by_id(budget_id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketing budget not found: {budget_id}",
        )
    _endpoints.log_completed("get_budget", budget_id=str(budget_id))
    return MarketingBudgetResponse.model_validate(budget)


@router.delete(
    "/budgets/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete marketing budget",
)
async def delete_budget(
    budget_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a marketing budget by ID."""
    _endpoints.log_started("delete_budget", budget_id=str(budget_id))
    repo = MarketingBudgetRepository(session)
    deleted = await repo.delete(budget_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketing budget not found: {budget_id}",
        )
    _endpoints.log_completed("delete_budget", budget_id=str(budget_id))


# =============================================================================
# QR Code generation
# =============================================================================


@router.post(
    "/qr-codes",
    summary="Generate QR code",
    description="Generate a QR code PNG for a campaign URL.",
)
async def generate_qr_code(
    data: QRCodeRequest,
    _current_user: CurrentActiveUser,
) -> Response:
    """Generate a QR code image.

    Validates: CRM Gap Closure Req 65.1
    """
    _endpoints.log_started("generate_qr_code", campaign=data.campaign_name)
    try:
        svc = MarketingService()
        png_bytes = svc.generate_qr_code(data)
        _endpoints.log_completed("generate_qr_code")
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="qr-{data.campaign_name}.png"'
                ),
            },
        )
    except QRCodeGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
