"""
Staff Availability API endpoints.

This module provides REST API endpoints for staff availability management
including CRUD operations and availability queries.

Validates: Requirements 1.1-1.5 (Route Optimization)
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from grins_platform.api.v1.dependencies import get_staff_availability_service
from grins_platform.exceptions import (
    StaffAvailabilityNotFoundError,
    StaffNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.staff_availability import (
    AvailableStaffOnDateResponse,
    StaffAvailabilityCreate,
    StaffAvailabilityResponse,
    StaffAvailabilityUpdate,
)
from grins_platform.services.staff_availability_service import (
    StaffAvailabilityService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class StaffAvailabilityEndpoints(LoggerMixin):
    """Staff Availability API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = StaffAvailabilityEndpoints()


# =============================================================================
# POST /api/v1/staff/{staff_id}/availability - Create Availability
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{staff_id}/availability",
    response_model=StaffAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create staff availability",
    description="Create a new availability entry for a staff member.",
)
async def create_availability(
    staff_id: UUID,
    data: StaffAvailabilityCreate,
    service: Annotated[
        StaffAvailabilityService,
        Depends(get_staff_availability_service),
    ],
) -> StaffAvailabilityResponse:
    """Create a new staff availability entry.

    Validates: Requirement 1.1
    """
    _endpoints.log_started(
        "create_availability",
        staff_id=str(staff_id),
        date=str(data.date),
    )

    try:
        result = await service.create_availability(staff_id, data)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("create_availability", reason="staff_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    except ValueError as e:
        _endpoints.log_rejected("create_availability", reason="already_exists")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed(
            "create_availability",
            availability_id=str(result.id),
        )
        return result


# =============================================================================
# GET /api/v1/staff/{staff_id}/availability - List Availability
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{staff_id}/availability",
    response_model=list[StaffAvailabilityResponse],
    summary="List staff availability",
    description="List availability entries for a staff member.",
)
async def list_availability(
    staff_id: UUID,
    service: Annotated[
        StaffAvailabilityService,
        Depends(get_staff_availability_service),
    ],
    start_date: date | None = Query(
        default=None,
        description="Start date filter (inclusive)",
    ),
    end_date: date | None = Query(
        default=None,
        description="End date filter (inclusive)",
    ),
) -> list[StaffAvailabilityResponse]:
    """List availability entries for a staff member.

    Validates: Requirement 1.2
    """
    _endpoints.log_started(
        "list_availability",
        staff_id=str(staff_id),
        start_date=str(start_date) if start_date else None,
        end_date=str(end_date) if end_date else None,
    )

    try:
        result = await service.list_availability(staff_id, start_date, end_date)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("list_availability", reason="staff_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    else:
        _endpoints.log_completed(
            "list_availability",
            staff_id=str(staff_id),
            count=len(result),
        )
        return result


# =============================================================================
# GET /api/v1/staff/{staff_id}/availability/{date} - Get Availability by Date
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{staff_id}/availability/{target_date}",
    response_model=StaffAvailabilityResponse,
    summary="Get staff availability by date",
    description="Get availability entry for a staff member on a specific date.",
)
async def get_availability_by_date(
    staff_id: UUID,
    target_date: date,
    service: Annotated[
        StaffAvailabilityService,
        Depends(get_staff_availability_service),
    ],
) -> StaffAvailabilityResponse:
    """Get availability for a specific staff member and date.

    Validates: Requirement 1.2
    """
    _endpoints.log_started(
        "get_availability_by_date",
        staff_id=str(staff_id),
        date=str(target_date),
    )

    try:
        result = await service.get_availability_by_date(staff_id, target_date)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("get_availability_by_date", reason="staff_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    except StaffAvailabilityNotFoundError:
        _endpoints.log_rejected("get_availability_by_date", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No availability for staff {staff_id} on {target_date}",
        ) from None
    else:
        _endpoints.log_completed(
            "get_availability_by_date",
            staff_id=str(staff_id),
            date=str(target_date),
        )
        return result


# =============================================================================
# PUT /api/v1/staff/{staff_id}/availability/{date} - Update Availability
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{staff_id}/availability/{target_date}",
    response_model=StaffAvailabilityResponse,
    summary="Update staff availability",
    description="Update availability entry for a staff member on a date.",
)
async def update_availability(
    staff_id: UUID,
    target_date: date,
    data: StaffAvailabilityUpdate,
    service: Annotated[
        StaffAvailabilityService,
        Depends(get_staff_availability_service),
    ],
) -> StaffAvailabilityResponse:
    """Update a staff availability entry.

    Validates: Requirement 1.3
    """
    _endpoints.log_started(
        "update_availability",
        staff_id=str(staff_id),
        date=str(target_date),
    )

    try:
        result = await service.update_availability(staff_id, target_date, data)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("update_availability", reason="staff_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    except StaffAvailabilityNotFoundError:
        _endpoints.log_rejected("update_availability", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No availability for staff {staff_id} on {target_date}",
        ) from None
    else:
        _endpoints.log_completed(
            "update_availability",
            staff_id=str(staff_id),
            date=str(target_date),
        )
        return result


# =============================================================================
# DELETE /api/v1/staff/{staff_id}/availability/{date} - Delete Availability
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{staff_id}/availability/{target_date}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete staff availability",
    description="Delete availability entry for a staff member on a date.",
)
async def delete_availability(
    staff_id: UUID,
    target_date: date,
    service: Annotated[
        StaffAvailabilityService,
        Depends(get_staff_availability_service),
    ],
) -> None:
    """Delete a staff availability entry.

    Validates: Requirement 1.4
    """
    _endpoints.log_started(
        "delete_availability",
        staff_id=str(staff_id),
        date=str(target_date),
    )

    try:
        await service.delete_availability(staff_id, target_date)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("delete_availability", reason="staff_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    except StaffAvailabilityNotFoundError:
        _endpoints.log_rejected("delete_availability", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No availability for staff {staff_id} on {target_date}",
        ) from None
    else:
        _endpoints.log_completed(
            "delete_availability",
            staff_id=str(staff_id),
            date=str(target_date),
        )


# =============================================================================
# GET /api/v1/staff/availability/date/{date} - Get Available Staff on Date
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/availability/date/{target_date}",
    response_model=AvailableStaffOnDateResponse,
    summary="Get available staff on date",
    description="Get all staff members available on a specific date.",
)
async def get_available_staff_on_date(
    target_date: date,
    service: Annotated[
        StaffAvailabilityService,
        Depends(get_staff_availability_service),
    ],
) -> AvailableStaffOnDateResponse:
    """Get all available staff members for a specific date.

    Validates: Requirement 1.5
    """
    _endpoints.log_started("get_available_staff_on_date", date=str(target_date))

    result = await service.get_available_staff_on_date(target_date)

    _endpoints.log_completed(
        "get_available_staff_on_date",
        date=str(target_date),
        count=result.total_available,
    )
    return result
