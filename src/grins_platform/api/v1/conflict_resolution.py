"""Conflict resolution API endpoints.

Validates: Requirements 10.1, 10.3, 10.4, 10.6
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from grins_platform.database import get_sync_db
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.conflict_resolution import (
    CancelAppointmentRequest,
    CancelAppointmentResponse,
    FillGapRequest,
    FillGapResponse,
    RescheduleAppointmentRequest,
    RescheduleAppointmentResponse,
    WaitlistEntryResponse,
)
from grins_platform.services.conflict_resolution_service import (
    ConflictResolutionService,
)

router = APIRouter(tags=["conflict-resolution"])


class ConflictEndpoints(LoggerMixin):
    """Conflict resolution endpoints."""

    DOMAIN = "api"


endpoints = ConflictEndpoints()


def get_conflict_service(
    db: Session = Depends(get_sync_db),
) -> ConflictResolutionService:
    """Dependency to get ConflictResolutionService."""
    return ConflictResolutionService(db)


@router.post(  # type: ignore[misc,untyped-decorator]
    "/appointments/{appointment_id}/cancel",
    response_model=CancelAppointmentResponse,
)
def cancel_appointment(
    appointment_id: UUID,
    request: CancelAppointmentRequest,
    service: ConflictResolutionService = Depends(get_conflict_service),
) -> CancelAppointmentResponse:
    """Cancel an appointment.

    POST /api/v1/appointments/{id}/cancel

    Validates: Requirements 10.1, 10.2
    """
    endpoints.log_started("cancel_appointment", appointment_id=str(appointment_id))

    try:
        response = service.cancel_appointment(
            appointment_id=appointment_id,
            reason=request.reason,
            add_to_waitlist=request.add_to_waitlist,
            preferred_reschedule_date=request.preferred_reschedule_date,
        )
    except Exception as e:
        endpoints.log_failed("cancel_appointment", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cancellation failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("cancel_appointment", success=True)
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/appointments/{appointment_id}/reschedule",
    response_model=RescheduleAppointmentResponse,
)
def reschedule_appointment(
    appointment_id: UUID,
    request: RescheduleAppointmentRequest,
    service: ConflictResolutionService = Depends(get_conflict_service),
) -> RescheduleAppointmentResponse:
    """Reschedule an appointment.

    POST /api/v1/appointments/{id}/reschedule

    Validates: Requirement 10.3
    """
    endpoints.log_started("reschedule_appointment", appointment_id=str(appointment_id))

    try:
        response = service.reschedule_appointment(
            appointment_id=appointment_id,
            new_date=request.new_date,
            new_time_start=request.new_time_start,
            new_time_end=request.new_time_end,
            new_staff_id=request.new_staff_id,
        )
    except ValueError as e:
        endpoints.log_failed("reschedule_appointment", error=e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        endpoints.log_failed("reschedule_appointment", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reschedule failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("reschedule_appointment", success=True)
        return response


@router.get(  # type: ignore[misc,untyped-decorator]
    "/schedule/waitlist",
    response_model=list[WaitlistEntryResponse],
)
def get_waitlist(
    target_date: date | None = None,
    service: ConflictResolutionService = Depends(get_conflict_service),
) -> list[WaitlistEntryResponse]:
    """Get schedule waitlist.

    GET /api/v1/schedule/waitlist

    Validates: Requirements 10.4, 10.5
    """
    endpoints.log_started(
        "get_waitlist",
        target_date=str(target_date) if target_date else None,
    )

    try:
        response = service.get_waitlist(target_date)
    except Exception as e:
        endpoints.log_failed("get_waitlist", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get waitlist: {e!s}",
        ) from e
    else:
        endpoints.log_completed("get_waitlist", count=len(response))
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/schedule/fill-gap",
    response_model=FillGapResponse,
)
def fill_gap(
    request: FillGapRequest,
    service: ConflictResolutionService = Depends(get_conflict_service),
) -> FillGapResponse:
    """Get suggestions for filling a schedule gap.

    POST /api/v1/schedule/fill-gap

    Validates: Requirements 10.6, 10.7
    """
    endpoints.log_started(
        "fill_gap",
        target_date=str(request.target_date),
    )

    try:
        response = service.fill_gap_suggestions(
            target_date=request.target_date,
            gap_start=request.gap_start,
            gap_end=request.gap_end,
            staff_id=request.staff_id,
        )
    except Exception as e:
        endpoints.log_failed("fill_gap", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fill gap failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("fill_gap", suggestions=len(response.suggestions))
        return response
