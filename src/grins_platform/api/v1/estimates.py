"""
Estimate API endpoints.

This module provides REST API endpoints for estimate CRUD operations
and sending estimates to customers.

Validates: CRM Gap Closure Req 17.3, 17.4, 48.2, 48.3
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_estimate_service
from grins_platform.exceptions import (
    EstimateNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import EstimateStatus
from grins_platform.schemas.estimate import (
    EstimateCreate,
    EstimateResponse,
    EstimateSendResponse,
    EstimateUpdate,
)
from grins_platform.services.estimate_service import (
    EstimateService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class EstimateEndpoints(LoggerMixin):
    """Estimate API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = EstimateEndpoints()


# =============================================================================
# Estimate CRUD — Req 48.2, 48.3
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=EstimateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new estimate",
    description="Create a new estimate with line items and optional tiers.",
)
async def create_estimate(
    data: EstimateCreate,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> EstimateResponse:
    """Create a new estimate.

    Args:
        data: Estimate creation data.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Created estimate response.

    Validates: CRM Gap Closure Req 48.2
    """
    _endpoints.log_started(
        "create_estimate",
        user_id=str(current_user.id),
    )
    result = await service.create_estimate(data, created_by=current_user.id)
    _endpoints.log_completed(
        "create_estimate",
        estimate_id=str(result.id),
    )
    return result


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=dict[str, Any],
    summary="List estimates with filters",
    description="List estimates with optional filtering by status, lead, or customer.",
)
async def list_estimates(
    _current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: EstimateStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by estimate status",
    ),
    lead_id: UUID | None = Query(default=None, description="Filter by lead"),
    customer_id: UUID | None = Query(default=None, description="Filter by customer"),
) -> dict[str, Any]:
    """List estimates with pagination and filters.

    Args:
        current_user: Authenticated active user.
        service: EstimateService instance.
        page: Page number (1-based).
        page_size: Items per page.
        status_filter: Optional status filter.
        lead_id: Optional lead filter.
        customer_id: Optional customer filter.

    Returns:
        Paginated estimate list.

    Validates: CRM Gap Closure Req 48.2
    """
    _endpoints.log_started("list_estimates", page=page, page_size=page_size)

    status_value = status_filter.value if status_filter else None
    estimates, total = await service.repo.list_with_filters(
        page=page,
        page_size=page_size,
        status=status_value,
        lead_id=lead_id,
        customer_id=customer_id,
    )

    items = [EstimateResponse.model_validate(e) for e in estimates]
    _endpoints.log_completed("list_estimates", count=len(items), total=total)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(  # type: ignore[untyped-decorator]
    "/{estimate_id}",
    response_model=EstimateResponse,
    summary="Get estimate by ID",
    description="Retrieve a single estimate by its UUID.",
)
async def get_estimate(
    estimate_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> EstimateResponse:
    """Get a single estimate by ID.

    Args:
        estimate_id: Estimate UUID.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Estimate response.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 48.2
    """
    _endpoints.log_started("get_estimate", estimate_id=str(estimate_id))

    estimate = await service.repo.get_by_id(estimate_id)
    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate not found: {estimate_id}",
        )

    _endpoints.log_completed("get_estimate", estimate_id=str(estimate_id))
    return EstimateResponse.model_validate(estimate)


@router.patch(  # type: ignore[untyped-decorator]
    "/{estimate_id}",
    response_model=EstimateResponse,
    summary="Update an estimate",
    description="Update estimate fields. Only DRAFT estimates can be updated.",
)
async def update_estimate(
    estimate_id: UUID,
    data: EstimateUpdate,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> EstimateResponse:
    """Update an estimate.

    Args:
        estimate_id: Estimate UUID.
        data: Fields to update.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Updated estimate response.

    Raises:
        HTTPException: 404 if not found, 400 if not in DRAFT status.

    Validates: CRM Gap Closure Req 48.2
    """
    _endpoints.log_started(
        "update_estimate",
        estimate_id=str(estimate_id),
        user_id=str(current_user.id),
    )

    existing = await service.repo.get_by_id(estimate_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate not found: {estimate_id}",
        )

    if existing.status != EstimateStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT estimates can be updated",
        )

    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        return EstimateResponse.model_validate(existing)

    updated = await service.repo.update(estimate_id, **update_fields)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate not found: {estimate_id}",
        )

    _endpoints.log_completed("update_estimate", estimate_id=str(estimate_id))
    return EstimateResponse.model_validate(updated)


@router.delete(  # type: ignore[untyped-decorator]
    "/{estimate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an estimate",
    description="Delete an estimate by ID.",
)
async def delete_estimate(
    estimate_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> None:
    """Delete an estimate.

    Args:
        estimate_id: Estimate UUID.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 48.2
    """
    _endpoints.log_started(
        "delete_estimate",
        estimate_id=str(estimate_id),
        user_id=str(current_user.id),
    )

    deleted = await service.repo.delete(estimate_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate not found: {estimate_id}",
        )

    _endpoints.log_completed("delete_estimate", estimate_id=str(estimate_id))


# =============================================================================
# Send Estimate — Req 48.3
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{estimate_id}/send",
    response_model=EstimateSendResponse,
    summary="Send estimate to customer",
    description="Send an estimate to the customer via SMS and email portal link.",
)
async def send_estimate(
    estimate_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> EstimateSendResponse:
    """Send an estimate to the customer.

    Args:
        estimate_id: Estimate UUID.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Send response with portal URL and channels used.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 48.3
    """
    _endpoints.log_started(
        "send_estimate",
        estimate_id=str(estimate_id),
        user_id=str(current_user.id),
    )

    try:
        result = await service.send_estimate(estimate_id)
    except EstimateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    _endpoints.log_completed(
        "send_estimate",
        estimate_id=str(estimate_id),
        sent_via=result.sent_via,
    )
    return result
