"""
Appointment API endpoints.

This module provides REST API endpoints for appointment management including
CRUD operations, status transitions, and schedule queries.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Annotated
from uuid import UUID  # noqa: TC003 - Required at runtime for FastAPI query params

from fastapi import APIRouter, Depends, HTTPException, Query, status

from grins_platform.api.v1.dependencies import get_appointment_service
from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    StaffNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    AppointmentStatus,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.schemas.appointment import (
    AppointmentCreate,
    AppointmentPaginatedResponse,
    AppointmentResponse,
    AppointmentUpdate,
    DailyScheduleResponse,
    StaffDailyScheduleResponse,
    WeeklyScheduleResponse,
)
from grins_platform.services.appointment_service import (
    AppointmentService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class AppointmentEndpoints(LoggerMixin):
    """Appointment API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = AppointmentEndpoints()


# =============================================================================
# GET /api/v1/appointments - List Appointments
# NOTE: Static routes must come BEFORE dynamic routes like /{appointment_id}
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=AppointmentPaginatedResponse,
    summary="List appointments",
    description="List appointments with filtering, sorting, and pagination.",
)
async def list_appointments(
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
    status_filter: AppointmentStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by appointment status",
    ),
    staff_id: UUID | None = Query(
        default=None,
        description="Filter by staff member ID",
    ),
    job_id: UUID | None = Query(
        default=None,
        description="Filter by job ID",
    ),
    date_from: date | None = Query(
        default=None,
        description="Filter appointments from this date",
    ),
    date_to: date | None = Query(
        default=None,
        description="Filter appointments until this date",
    ),
    sort_by: str = Query(
        default="scheduled_date",
        description="Field to sort by",
    ),
    sort_order: str = Query(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
) -> AppointmentPaginatedResponse:
    """List appointments with filtering and pagination.

    Validates: Admin Dashboard Requirement 1.4
    """
    _endpoints.log_started(
        "list_appointments",
        page=page,
        page_size=page_size,
        filters={
            "status": status_filter.value if status_filter else None,
            "staff_id": str(staff_id) if staff_id else None,
            "job_id": str(job_id) if job_id else None,
        },
    )

    appointments, total = await service.list_appointments(
        page=page,
        page_size=page_size,
        status=status_filter,
        staff_id=staff_id,
        job_id=job_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    _endpoints.log_completed("list_appointments", count=len(appointments), total=total)

    return AppointmentPaginatedResponse(
        items=[AppointmentResponse.model_validate(a) for a in appointments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# GET /api/v1/appointments/daily/{date} - Get Daily Schedule
# NOTE: Must come BEFORE /{appointment_id} route
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/daily/{schedule_date}",
    response_model=DailyScheduleResponse,
    summary="Get daily schedule",
    description="Get all appointments for a specific date.",
)
async def get_daily_schedule(
    schedule_date: date,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> DailyScheduleResponse:
    """Get all appointments for a specific date.

    Validates: Admin Dashboard Requirement 1.5
    """
    _endpoints.log_started("get_daily_schedule", date=str(schedule_date))

    appointments, total = await service.get_daily_schedule(
        schedule_date,
        include_relationships=True,
    )

    _endpoints.log_completed("get_daily_schedule", count=total)

    return DailyScheduleResponse(
        date=schedule_date,
        appointments=[AppointmentResponse.model_validate(a) for a in appointments],
        total_count=total,
    )


# =============================================================================
# GET /api/v1/appointments/staff/{staff_id}/daily/{date} - Get Staff Daily Schedule
# NOTE: Must come BEFORE /{appointment_id} route
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/staff/{staff_id}/daily/{schedule_date}",
    response_model=StaffDailyScheduleResponse,
    summary="Get staff daily schedule",
    description="Get all appointments for a specific staff member on a specific date.",
)
async def get_staff_daily_schedule(
    staff_id: UUID,
    schedule_date: date,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> StaffDailyScheduleResponse:
    """Get all appointments for a specific staff member on a specific date.

    Validates: Admin Dashboard Requirement 1.5
    """
    _endpoints.log_started(
        "get_staff_daily_schedule",
        staff_id=str(staff_id),
        date=str(schedule_date),
    )

    try:
        appointments, total, total_minutes = await service.get_staff_daily_schedule(
            staff_id,
            schedule_date,
            include_relationships=True,
        )
    except StaffNotFoundError as e:
        _endpoints.log_rejected("get_staff_daily_schedule", reason="staff_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff not found: {e.staff_id}",
        ) from e

    _endpoints.log_completed(
        "get_staff_daily_schedule",
        count=total,
        total_minutes=total_minutes,
    )

    return StaffDailyScheduleResponse(
        staff_id=staff_id,
        staff_name="",  # Would need to fetch from staff service
        date=schedule_date,
        appointments=[AppointmentResponse.model_validate(a) for a in appointments],
        total_scheduled_minutes=total_minutes,
    )


# =============================================================================
# GET /api/v1/appointments/weekly - Get Weekly Schedule
# NOTE: Must come BEFORE /{appointment_id} route
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/weekly",
    response_model=WeeklyScheduleResponse,
    summary="Get weekly schedule",
    description="Get all appointments for a week starting from the specified date.",
)
async def get_weekly_schedule(
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    start_date: date = Query(
        ...,
        description="First day of the week to retrieve",
    ),
) -> WeeklyScheduleResponse:
    """Get all appointments for a week starting from start_date.

    Validates: Admin Dashboard Requirement 1.5
    """
    _endpoints.log_started("get_weekly_schedule", start_date=str(start_date))

    schedule, total = await service.get_weekly_schedule(
        start_date,
        include_relationships=True,
    )

    # Build daily schedule responses
    days: list[DailyScheduleResponse] = []
    for i in range(7):
        day_date = start_date + timedelta(days=i)
        day_appointments = schedule.get(day_date, [])
        days.append(
            DailyScheduleResponse(
                date=day_date,
                appointments=[
                    AppointmentResponse.model_validate(a) for a in day_appointments
                ],
                total_count=len(day_appointments),
            ),
        )

    end_date = start_date + timedelta(days=6)

    _endpoints.log_completed("get_weekly_schedule", total_appointments=total)

    return WeeklyScheduleResponse(
        start_date=start_date,
        end_date=end_date,
        days=days,
        total_appointments=total,
    )


# =============================================================================
# POST /api/v1/appointments - Create Appointment
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new appointment",
    description="Create a new appointment for a job.",
)
async def create_appointment(
    data: AppointmentCreate,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentResponse:
    """Create a new appointment.

    Validates: Admin Dashboard Requirement 1.1
    """
    _endpoints.log_started(
        "create_appointment",
        job_id=str(data.job_id),
        staff_id=str(data.staff_id),
        scheduled_date=str(data.scheduled_date),
    )

    try:
        result = await service.create_appointment(data)
    except JobNotFoundError as e:
        _endpoints.log_rejected("create_appointment", reason="job_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    except StaffNotFoundError as e:
        _endpoints.log_rejected("create_appointment", reason="staff_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff not found: {e.staff_id}",
        ) from e

    _endpoints.log_completed("create_appointment", appointment_id=str(result.id))
    return AppointmentResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# GET /api/v1/appointments/{id} - Get Appointment by ID
# NOTE: Dynamic routes must come AFTER static routes
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get appointment by ID",
    description="Retrieve an appointment by its unique identifier.",
)
async def get_appointment(
    appointment_id: UUID,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentResponse:
    """Get appointment by ID.

    Validates: Admin Dashboard Requirement 1.3
    """
    _endpoints.log_started("get_appointment", appointment_id=str(appointment_id))

    try:
        result = await service.get_appointment(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("get_appointment", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e

    _endpoints.log_completed("get_appointment", appointment_id=str(appointment_id))
    return AppointmentResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# PUT /api/v1/appointments/{id} - Update Appointment
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Update appointment",
    description="Update appointment details. Only provided fields will be updated.",
)
async def update_appointment(
    appointment_id: UUID,
    data: AppointmentUpdate,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentResponse:
    """Update appointment information.

    Validates: Admin Dashboard Requirement 1.2
    """
    _endpoints.log_started("update_appointment", appointment_id=str(appointment_id))

    try:
        result = await service.update_appointment(appointment_id, data)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("update_appointment", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except InvalidStatusTransitionError as e:
        _endpoints.log_rejected(
            "update_appointment",
            reason="invalid_transition",
            current=e.current_status.value,
            requested=e.requested_status.value,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {e.current_status.value} "
            f"to {e.requested_status.value}",
        ) from e

    _endpoints.log_completed("update_appointment", appointment_id=str(appointment_id))
    return AppointmentResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# DELETE /api/v1/appointments/{id} - Cancel Appointment
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel appointment",
    description="Cancel an appointment. Record is preserved but marked cancelled.",
)
async def cancel_appointment(
    appointment_id: UUID,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> None:
    """Cancel an appointment.

    Validates: Admin Dashboard Requirement 1.2
    """
    _endpoints.log_started("cancel_appointment", appointment_id=str(appointment_id))

    try:
        await service.cancel_appointment(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("cancel_appointment", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except InvalidStatusTransitionError as e:
        _endpoints.log_rejected(
            "cancel_appointment",
            reason="invalid_transition",
            current=e.current_status.value,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel appointment in status {e.current_status.value}",
        ) from e

    _endpoints.log_completed("cancel_appointment", appointment_id=str(appointment_id))
