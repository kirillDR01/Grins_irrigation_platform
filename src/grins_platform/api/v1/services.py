"""
Service Offering API endpoints.

This module provides REST API endpoints for service offering management including
CRUD operations, category filtering, and listing with pagination.

Validates: Requirement 1.1-1.13, 12.1-12.7
"""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from grins_platform.api.v1.dependencies import get_service_offering_service
from grins_platform.exceptions import ServiceOfferingNotFoundError
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    ServiceCategory,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.schemas.service_offering import (
    PaginatedServiceResponse,
    ServiceOfferingCreate,
    ServiceOfferingResponse,
    ServiceOfferingUpdate,
)
from grins_platform.services.service_offering_service import (
    ServiceOfferingService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class ServiceOfferingEndpoints(LoggerMixin):
    """Service Offering API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = ServiceOfferingEndpoints()


# =============================================================================
# Task 11.2: GET /api/v1/services - List Services
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=PaginatedServiceResponse,
    summary="List service offerings",
    description="List service offerings with filtering, sorting, and pagination.",
)
async def list_services(
    service: Annotated[ServiceOfferingService, Depends(get_service_offering_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
    category: ServiceCategory | None = Query(
        default=None,
        description="Filter by service category",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status",
    ),
    sort_by: str = Query(
        default="name",
        description="Field to sort by",
    ),
    sort_order: str = Query(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
) -> PaginatedServiceResponse:
    """List service offerings with filtering and pagination.

    Args:
        service: Injected ServiceOfferingService
        page: Page number (1-indexed)
        page_size: Number of items per page
        category: Filter by service category
        is_active: Filter by active status
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)

    Returns:
        PaginatedServiceResponse with services and pagination info

    Validates: Requirement 1.11, 12.1, 12.5
    """
    _endpoints.log_started(
        "list_services",
        page=page,
        page_size=page_size,
        filters={
            "category": category.value if category else None,
            "is_active": is_active,
        },
    )

    services, total = await service.list_services(
        page=page,
        page_size=page_size,
        category=category,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    _endpoints.log_completed(
        "list_services",
        count=len(services),
        total=total,
    )

    return PaginatedServiceResponse(
        items=[ServiceOfferingResponse.model_validate(s) for s in services],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# Task 11.3: GET /api/v1/services/{id} - Get Service by ID
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{service_id}",
    response_model=ServiceOfferingResponse,
    summary="Get service offering by ID",
    description="Retrieve a service offering by its unique identifier.",
)
async def get_service(
    service_id: UUID,
    service: Annotated[ServiceOfferingService, Depends(get_service_offering_service)],
) -> ServiceOfferingResponse:
    """Get service offering by ID.

    Args:
        service_id: UUID of the service offering to retrieve
        service: Injected ServiceOfferingService

    Returns:
        ServiceOfferingResponse with service data

    Raises:
        HTTPException: 404 if service not found

    Validates: Requirement 1.4, 12.1, 12.3
    """
    _endpoints.log_started("get_service", service_id=str(service_id))

    try:
        result = await service.get_service(service_id)
    except ServiceOfferingNotFoundError as e:
        _endpoints.log_rejected("get_service", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service offering not found: {e.service_id}",
        ) from e
    else:
        _endpoints.log_completed("get_service", service_id=str(service_id))
        return ServiceOfferingResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 11.4: GET /api/v1/services/category/{category} - Get by Category
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/category/{category}",
    response_model=list[ServiceOfferingResponse],
    summary="Get services by category",
    description="Retrieve all active service offerings in a specific category.",
)
async def get_services_by_category(
    category: ServiceCategory,
    service: Annotated[ServiceOfferingService, Depends(get_service_offering_service)],
) -> list[ServiceOfferingResponse]:
    """Get all active services in a category.

    Args:
        category: Service category to filter by
        service: Injected ServiceOfferingService

    Returns:
        List of ServiceOfferingResponse objects (active only)

    Validates: Requirement 1.11, 12.1
    """
    _endpoints.log_started("get_services_by_category", category=category.value)

    services = await service.get_by_category(category)

    _endpoints.log_completed("get_services_by_category", count=len(services))
    return [ServiceOfferingResponse.model_validate(s) for s in services]


# =============================================================================
# Task 11.5: POST /api/v1/services - Create Service
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=ServiceOfferingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new service offering",
    description="Create a new service offering with the provided information.",
)
async def create_service(
    data: ServiceOfferingCreate,
    service: Annotated[ServiceOfferingService, Depends(get_service_offering_service)],
) -> ServiceOfferingResponse:
    """Create a new service offering.

    Args:
        data: ServiceOfferingCreate schema with service information
        service: Injected ServiceOfferingService

    Returns:
        ServiceOfferingResponse with created service data

    Validates: Requirement 1.1-1.3, 12.1
    """
    _endpoints.log_started(
        "create_service",
        name=data.name,
        category=data.category.value,
    )

    result = await service.create_service(data)

    _endpoints.log_completed("create_service", service_id=str(result.id))
    return ServiceOfferingResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 11.6: PUT /api/v1/services/{id} - Update Service
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{service_id}",
    response_model=ServiceOfferingResponse,
    summary="Update service offering",
    description="Update service offering. Only provided fields will be updated.",
)
async def update_service(
    service_id: UUID,
    data: ServiceOfferingUpdate,
    service: Annotated[ServiceOfferingService, Depends(get_service_offering_service)],
) -> ServiceOfferingResponse:
    """Update service offering information.

    Args:
        service_id: UUID of the service offering to update
        data: ServiceOfferingUpdate schema with fields to update
        service: Injected ServiceOfferingService

    Returns:
        ServiceOfferingResponse with updated service data

    Raises:
        HTTPException: 404 if service not found

    Validates: Requirement 1.5, 12.1, 12.3
    """
    _endpoints.log_started("update_service", service_id=str(service_id))

    try:
        result = await service.update_service(service_id, data)
    except ServiceOfferingNotFoundError as e:
        _endpoints.log_rejected("update_service", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service offering not found: {e.service_id}",
        ) from e
    else:
        _endpoints.log_completed("update_service", service_id=str(service_id))
        return ServiceOfferingResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 11.7: DELETE /api/v1/services/{id} - Deactivate Service
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate service offering",
    description="Deactivate a service offering (soft delete). The record is preserved.",
)
async def delete_service(
    service_id: UUID,
    service: Annotated[ServiceOfferingService, Depends(get_service_offering_service)],
) -> None:
    """Deactivate a service offering (soft delete).

    Args:
        service_id: UUID of the service offering to deactivate
        service: Injected ServiceOfferingService

    Raises:
        HTTPException: 404 if service not found

    Validates: Requirement 1.6, 12.1, 12.3
    """
    _endpoints.log_started("delete_service", service_id=str(service_id))

    try:
        await service.deactivate_service(service_id)
    except ServiceOfferingNotFoundError as e:
        _endpoints.log_rejected("delete_service", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service offering not found: {e.service_id}",
        ) from e
    else:
        _endpoints.log_completed("delete_service", service_id=str(service_id))
