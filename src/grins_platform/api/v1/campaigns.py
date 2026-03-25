"""Campaign API endpoints.

Provides CRUD for marketing campaigns, sending, and stats.

Validates: CRM Gap Closure Req 45.3, 45.4, 45.5
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    CampaignStatus,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.repositories.campaign_repository import CampaignRepository
from grins_platform.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignSendResult,
    CampaignStats,
)
from grins_platform.services.campaign_service import (
    CampaignAlreadySentError,
    CampaignNotFoundError,
    CampaignService,
    NoRecipientsError,
)

router = APIRouter()


class _CampaignEndpoints(LoggerMixin):
    """Campaign API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _CampaignEndpoints()


async def _get_campaign_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignService:
    """Get CampaignService dependency."""
    repo = CampaignRepository(session)
    return CampaignService(campaign_repository=repo)


# =============================================================================
# CRUD endpoints
# =============================================================================


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create campaign",
    description="Create a new marketing campaign.",
)
async def create_campaign(
    data: CampaignCreate,
    current_user: CurrentActiveUser,
    service: Annotated[CampaignService, Depends(_get_campaign_service)],
) -> CampaignResponse:
    """Create a new campaign.

    Validates: CRM Gap Closure Req 45.3
    """
    _endpoints.log_started("create_campaign", name=data.name)
    result = await service.create_campaign(data, created_by=current_user.id)
    _endpoints.log_completed("create_campaign", campaign_id=str(result.id))
    return result


@router.get(
    "",
    response_model=dict[str, Any],
    summary="List campaigns",
    description="List campaigns with pagination and optional status filter.",
)
async def list_campaigns(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: CampaignStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by status",
    ),
) -> dict[str, Any]:
    """List campaigns with pagination.

    Validates: CRM Gap Closure Req 45.3
    """
    _endpoints.log_started("list_campaigns", page=page)
    repo = CampaignRepository(session)
    campaigns, total = await repo.list_with_filters(
        page=page,
        page_size=page_size,
        status=status_filter.value if status_filter else None,
    )
    items = [CampaignResponse.model_validate(c) for c in campaigns]
    _endpoints.log_completed("list_campaigns", count=len(items), total=total)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign by ID",
)
async def get_campaign(
    campaign_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """Get a single campaign by ID."""
    _endpoints.log_started("get_campaign", campaign_id=str(campaign_id))
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign not found: {campaign_id}",
        )
    _endpoints.log_completed("get_campaign", campaign_id=str(campaign_id))
    return CampaignResponse.model_validate(campaign)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete campaign",
)
async def delete_campaign(
    campaign_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a campaign by ID."""
    _endpoints.log_started("delete_campaign", campaign_id=str(campaign_id))
    repo = CampaignRepository(session)
    deleted = await repo.delete(campaign_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign not found: {campaign_id}",
        )
    _endpoints.log_completed("delete_campaign", campaign_id=str(campaign_id))


# =============================================================================
# Campaign actions
# =============================================================================


@router.post(
    "/{campaign_id}/send",
    response_model=CampaignSendResult,
    summary="Send campaign",
    description="Send a campaign to its target audience.",
)
async def send_campaign(
    campaign_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[CampaignService, Depends(_get_campaign_service)],
) -> CampaignSendResult:
    """Send a campaign.

    Validates: CRM Gap Closure Req 45.4
    """
    _endpoints.log_started("send_campaign", campaign_id=str(campaign_id))
    try:
        result = await service.send_campaign(campaign_id)
    except CampaignNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except CampaignAlreadySentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except NoRecipientsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed(
            "send_campaign",
            campaign_id=str(campaign_id),
            sent=result.sent,
        )
        return result


@router.get(
    "/{campaign_id}/stats",
    response_model=CampaignStats,
    summary="Get campaign stats",
    description="Get delivery statistics for a campaign.",
)
async def get_campaign_stats(
    campaign_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[CampaignService, Depends(_get_campaign_service)],
) -> CampaignStats:
    """Get campaign delivery statistics.

    Validates: CRM Gap Closure Req 45.5
    """
    _endpoints.log_started("get_campaign_stats", campaign_id=str(campaign_id))
    try:
        result = await service.get_campaign_stats(campaign_id)
    except CampaignNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed(
            "get_campaign_stats",
            campaign_id=str(campaign_id),
        )
        return result
