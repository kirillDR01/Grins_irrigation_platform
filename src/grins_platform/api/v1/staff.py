"""
Staff API endpoints.

This module provides REST API endpoints for staff management including
CRUD operations, availability management, and role filtering.

Validates: Requirement 8.1-8.10, 9.1-9.5, 12.1-12.7
"""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session, get_staff_service
from grins_platform.exceptions import StaffNotFoundError
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    SkillLevel,  # noqa: TC001 - Required at runtime for FastAPI query params
    StaffRole,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.schemas.staff import (
    PaginatedStaffResponse,
    StaffAvailabilityUpdate,
    StaffCreate,
    StaffResponse,
    StaffUpdate,
)
from grins_platform.schemas.staff_ops import (
    StaffBreakCreateRequest,
    StaffBreakResponse,
    StaffLocationRequest,
    StaffLocationResponse,
)
from grins_platform.services.staff_service import (
    StaffService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class StaffEndpoints(LoggerMixin):
    """Staff API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = StaffEndpoints()


# =============================================================================
# Task 13.6: GET /api/v1/staff - List Staff
# NOTE: Static routes must come BEFORE dynamic routes like /{staff_id}
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=PaginatedStaffResponse,
    summary="List staff members",
    description="List staff members with filtering, sorting, and pagination.",
)
async def list_staff(
    service: Annotated[StaffService, Depends(get_staff_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
    role: StaffRole | None = Query(
        default=None,
        description="Filter by staff role",
    ),
    skill_level: SkillLevel | None = Query(
        default=None,
        description="Filter by skill level",
    ),
    is_available: bool | None = Query(
        default=None,
        description="Filter by availability",
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
) -> PaginatedStaffResponse:
    """List staff members with filtering and pagination.

    Validates: Requirement 9.4, 9.5, 12.1
    """
    _endpoints.log_started(
        "list_staff",
        page=page,
        page_size=page_size,
        filters={
            "role": role.value if role else None,
            "skill_level": skill_level.value if skill_level else None,
            "is_available": is_available,
            "is_active": is_active,
        },
    )

    staff, total = await service.list_staff(
        page=page,
        page_size=page_size,
        role=role,
        skill_level=skill_level,
        is_available=is_available,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    _endpoints.log_completed("list_staff", count=len(staff), total=total)

    return PaginatedStaffResponse(
        items=[StaffResponse.model_validate(s) for s in staff],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# Task 13.7: GET /api/v1/staff/available - Get Available Staff
# NOTE: Must come BEFORE /{staff_id} route
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/available",
    response_model=list[StaffResponse],
    summary="Get available staff",
    description="Retrieve all staff members who are available and active.",
)
async def get_available_staff(
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> list[StaffResponse]:
    """Get all available and active staff members.

    Validates: Requirement 9.3, 12.1
    """
    _endpoints.log_started("get_available_staff")

    staff = await service.get_available_staff()

    _endpoints.log_completed("get_available_staff", count=len(staff))
    return [StaffResponse.model_validate(s) for s in staff]


# =============================================================================
# Task 13.8: GET /api/v1/staff/by-role/{role} - Get Staff by Role
# NOTE: Must come BEFORE /{staff_id} route
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/by-role/{role}",
    response_model=list[StaffResponse],
    summary="Get staff by role",
    description="Retrieve all active staff members with a specific role.",
)
async def get_staff_by_role(
    role: StaffRole,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> list[StaffResponse]:
    """Get all active staff members by role.

    Validates: Requirement 9.4, 12.1
    """
    _endpoints.log_started("get_staff_by_role", role=role.value)

    staff = await service.get_by_role(role)

    _endpoints.log_completed("get_staff_by_role", count=len(staff))
    return [StaffResponse.model_validate(s) for s in staff]


# =============================================================================
# GET /api/v1/staff/locations - All staff locations (Req 41)
# NOTE: Static route must come BEFORE dynamic /{staff_id} routes
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/locations",
    response_model=list[StaffLocationResponse],
    summary="Get all staff locations",
    description="Get the latest GPS location for all active staff members.",
)
async def get_all_staff_locations(
    _current_user: CurrentActiveUser,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> list[StaffLocationResponse]:
    """Get all active staff locations from Redis.

    Validates: Requirement 41.5
    """
    _endpoints.log_started("get_all_staff_locations")

    from grins_platform.services.staff_location_service import (  # noqa: PLC0415
        StaffLocationService,
    )

    # Get all active staff IDs
    staff_list = await service.get_available_staff()
    staff_ids = [s.id for s in staff_list]

    location_service = StaffLocationService()
    locations = await location_service.get_all_locations(staff_ids)

    result = [
        StaffLocationResponse(
            staff_id=loc.staff_id,
            latitude=loc.latitude,
            longitude=loc.longitude,
            timestamp=loc.timestamp,
            appointment_id=loc.appointment_id,
        )
        for loc in locations
    ]

    _endpoints.log_completed("get_all_staff_locations", count=len(result))
    return result


# =============================================================================
# PATCH /api/v1/staff/me — current-user self-update (umbrella plan §Phase 5.2)
# Static route must come BEFORE dynamic /{staff_id} routes.
# =============================================================================


@router.patch(  # type: ignore[untyped-decorator]
    "/me",
    response_model=StaffResponse,
    summary="Update the current staff user's preferences",
    description=(
        "Patch self-update for tech-personalization fields like "
        "preferred_maps_app. Authenticated; only the current user's "
        "own record is mutated."
    ),
)
async def update_current_staff(
    data: StaffUpdate,
    current_user: CurrentActiveUser,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> StaffResponse:
    """Patch the current staff user (umbrella plan §Phase 5.2)."""
    _endpoints.log_started("update_current_staff", staff_id=str(current_user.id))

    try:
        result = await service.update_staff(current_user.id, data)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("update_current_staff", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    else:
        _endpoints.log_completed(
            "update_current_staff",
            staff_id=str(current_user.id),
        )
        return StaffResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 13.2: POST /api/v1/staff - Create Staff
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new staff member",
    description="Create a new staff member with the provided information. "
    "Phone number will be normalized to 10 digits.",
)
async def create_staff(
    data: StaffCreate,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> StaffResponse:
    """Create a new staff member.

    Validates: Requirement 8.1-8.10, 12.1
    """
    _endpoints.log_started("create_staff", name=data.name, role=data.role.value)

    result = await service.create_staff(data)

    _endpoints.log_completed("create_staff", staff_id=str(result.id))
    return StaffResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 13.3: GET /api/v1/staff/{id} - Get Staff by ID
# NOTE: Dynamic routes must come AFTER static routes like /available
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{staff_id}",
    response_model=StaffResponse,
    summary="Get staff member by ID",
    description="Retrieve a staff member by their unique identifier.",
)
async def get_staff(
    staff_id: UUID,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> StaffResponse:
    """Get staff member by ID.

    Validates: Requirement 8.4, 12.1, 12.3
    """
    _endpoints.log_started("get_staff", staff_id=str(staff_id))

    try:
        result = await service.get_staff(staff_id)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("get_staff", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    else:
        _endpoints.log_completed("get_staff", staff_id=str(staff_id))
        return StaffResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 13.4: PUT /api/v1/staff/{id} - Update Staff
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{staff_id}",
    response_model=StaffResponse,
    summary="Update staff member",
    description="Update staff member. Only provided fields will be updated.",
)
async def update_staff(
    staff_id: UUID,
    data: StaffUpdate,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> StaffResponse:
    """Update staff member information.

    Validates: Requirement 8.5, 12.1, 12.3
    """
    _endpoints.log_started("update_staff", staff_id=str(staff_id))

    try:
        result = await service.update_staff(staff_id, data)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("update_staff", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    else:
        _endpoints.log_completed("update_staff", staff_id=str(staff_id))
        return StaffResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 13.5: DELETE /api/v1/staff/{id} - Deactivate Staff
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate staff member",
    description="Deactivate a staff member (soft delete). The record is preserved.",
)
async def delete_staff(
    staff_id: UUID,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> None:
    """Deactivate a staff member (soft delete).

    Validates: Requirement 8.6, 12.1, 12.3
    """
    _endpoints.log_started("delete_staff", staff_id=str(staff_id))

    try:
        await service.deactivate_staff(staff_id)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("delete_staff", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    else:
        _endpoints.log_completed("delete_staff", staff_id=str(staff_id))


# =============================================================================
# Task 13.9: PUT /api/v1/staff/{id}/availability - Update Availability
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{staff_id}/availability",
    response_model=StaffResponse,
    summary="Update staff availability",
    description="Update a staff member's availability status and notes.",
)
async def update_staff_availability(
    staff_id: UUID,
    data: StaffAvailabilityUpdate,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> StaffResponse:
    """Update staff member availability.

    Validates: Requirement 9.1, 9.2, 12.1, 12.3
    """
    _endpoints.log_started(
        "update_availability",
        staff_id=str(staff_id),
        is_available=data.is_available,
    )

    try:
        result = await service.update_availability(
            staff_id=staff_id,
            is_available=data.is_available,
            availability_notes=data.availability_notes,
        )
    except StaffNotFoundError as e:
        _endpoints.log_rejected("update_availability", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e
    else:
        _endpoints.log_completed("update_availability", staff_id=str(staff_id))
        return StaffResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# POST /api/v1/staff/{id}/location - GPS location update (Req 41)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{staff_id}/location",
    response_model=dict[str, bool],
    summary="Update staff GPS location",
    description="Store a staff member's GPS location in Redis with 5-minute TTL.",
)
async def update_staff_location(
    staff_id: UUID,
    data: StaffLocationRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[StaffService, Depends(get_staff_service)],
) -> dict[str, bool]:
    """Update a staff member's GPS location.

    Validates: Requirement 41.1
    """
    _endpoints.log_started(
        "update_staff_location",
        staff_id=str(staff_id),
    )

    # Verify staff exists
    try:
        await service.get_staff(staff_id)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("update_staff_location", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e

    from grins_platform.services.staff_location_service import (  # noqa: PLC0415
        StaffLocationService,
    )

    location_service = StaffLocationService()
    stored = await location_service.store_location(
        staff_id=staff_id,
        latitude=data.latitude,
        longitude=data.longitude,
        appointment_id=data.appointment_id,
    )

    _endpoints.log_completed(
        "update_staff_location",
        staff_id=str(staff_id),
        stored=stored,
    )
    return {"stored": stored}


# =============================================================================
# POST /api/v1/staff/{id}/breaks - Start break (Req 42)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{staff_id}/breaks",
    response_model=StaffBreakResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a staff break",
    description="Create a break record for a staff member.",
)
async def start_staff_break(
    staff_id: UUID,
    data: StaffBreakCreateRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[StaffService, Depends(get_staff_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffBreakResponse:
    """Start a break for a staff member.

    Validates: Requirement 42.2
    """
    _endpoints.log_started(
        "start_staff_break",
        staff_id=str(staff_id),
        break_type=data.break_type,
    )

    # Verify staff exists
    try:
        await service.get_staff(staff_id)
    except StaffNotFoundError as e:
        _endpoints.log_rejected("start_staff_break", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member not found: {e.staff_id}",
        ) from e

    from grins_platform.services.staff_break_service import (  # noqa: PLC0415
        StaffBreakService,
    )

    break_service = StaffBreakService()
    try:
        staff_break = await break_service.create_break(
            session,
            staff_id=staff_id,
            break_type=data.break_type,
            appointment_id=data.appointment_id,
        )
    except ValueError as e:
        _endpoints.log_rejected("start_staff_break", reason=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    await session.commit()

    _endpoints.log_completed(
        "start_staff_break",
        staff_id=str(staff_id),
        break_id=str(staff_break.id),
    )
    return StaffBreakResponse(
        id=staff_break.id,
        staff_id=staff_break.staff_id,
        appointment_id=staff_break.appointment_id,
        start_time=staff_break.start_time,
        end_time=staff_break.end_time,
        break_type=staff_break.break_type,
        created_at=staff_break.created_at,
    )


# =============================================================================
# PATCH /api/v1/staff/{id}/breaks/{break_id} - End break (Req 42)
# =============================================================================


@router.patch(  # type: ignore[untyped-decorator]
    "/{staff_id}/breaks/{break_id}",
    response_model=StaffBreakResponse,
    summary="End a staff break",
    description="End a staff break and adjust subsequent appointment ETAs.",
)
async def end_staff_break(
    staff_id: UUID,
    break_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffBreakResponse:
    """End a staff break.

    Validates: Requirement 42.2
    """
    _endpoints.log_started(
        "end_staff_break",
        staff_id=str(staff_id),
        break_id=str(break_id),
    )

    from grins_platform.services.staff_break_service import (  # noqa: PLC0415
        BreakAlreadyEndedError,
        BreakNotFoundError,
        StaffBreakService,
    )

    break_service = StaffBreakService()
    try:
        staff_break = await break_service.end_break(session, break_id=break_id)
    except BreakNotFoundError as e:
        _endpoints.log_rejected("end_staff_break", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except BreakAlreadyEndedError as e:
        _endpoints.log_rejected("end_staff_break", reason="already_ended")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    await session.commit()

    _endpoints.log_completed(
        "end_staff_break",
        staff_id=str(staff_id),
        break_id=str(break_id),
    )
    return StaffBreakResponse(
        id=staff_break.id,
        staff_id=staff_break.staff_id,
        appointment_id=staff_break.appointment_id,
        start_time=staff_break.start_time,
        end_time=staff_break.end_time,
        break_type=staff_break.break_type,
        created_at=staff_break.created_at,
    )
