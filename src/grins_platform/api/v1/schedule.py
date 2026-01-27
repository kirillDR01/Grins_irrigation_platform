"""
Schedule generation API endpoints.

Validates: Requirements 5.1, 5.6, 5.7, 5.8
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from grins_platform.database import get_sync_db
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.schedule_generation import (
    EmergencyInsertRequest,
    EmergencyInsertResponse,
    ReoptimizeRequest,
    ScheduleCapacityResponse,
    ScheduleGenerateRequest,
    ScheduleGenerateResponse,
)
from grins_platform.services.schedule_generation_service import (
    ScheduleGenerationService,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


class ScheduleEndpoints(LoggerMixin):
    """Schedule generation endpoints."""

    DOMAIN = "api"


endpoints = ScheduleEndpoints()


def get_schedule_service(
    db: Session = Depends(get_sync_db),
) -> ScheduleGenerationService:
    """Dependency to get ScheduleGenerationService."""
    return ScheduleGenerationService(db)


@router.post(  # type: ignore[misc,untyped-decorator]
    "/generate",
    response_model=ScheduleGenerateResponse,
)
def generate_schedule(
    request: ScheduleGenerateRequest,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleGenerateResponse:
    """Generate an optimized schedule for a date.

    POST /api/v1/schedule/generate
    """
    endpoints.log_started("generate_schedule", schedule_date=str(request.schedule_date))

    try:
        response = service.generate_schedule(
            schedule_date=request.schedule_date,
            timeout_seconds=request.timeout_seconds,
        )
    except Exception as e:
        endpoints.log_failed("generate_schedule", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule generation failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "generate_schedule",
            is_feasible=response.is_feasible,
            assigned=response.total_assigned,
        )
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/preview",
    response_model=ScheduleGenerateResponse,
)
def preview_schedule(
    request: ScheduleGenerateRequest,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleGenerateResponse:
    """Preview a schedule without persisting.

    POST /api/v1/schedule/preview
    """
    endpoints.log_started("preview_schedule", schedule_date=str(request.schedule_date))

    try:
        # Preview is same as generate but doesn't persist
        response = service.generate_schedule(
            schedule_date=request.schedule_date,
            timeout_seconds=request.timeout_seconds,
        )
    except Exception as e:
        endpoints.log_failed("preview_schedule", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule preview failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("preview_schedule", assigned=response.total_assigned)
        return response


@router.get(  # type: ignore[misc,untyped-decorator]
    "/capacity/{schedule_date}",
    response_model=ScheduleCapacityResponse,
)
def get_capacity(
    schedule_date: date,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleCapacityResponse:
    """Get scheduling capacity for a date.

    GET /api/v1/schedule/capacity/{date}
    """
    endpoints.log_started("get_capacity", schedule_date=str(schedule_date))

    try:
        response = service.get_capacity(schedule_date)
    except Exception as e:
        endpoints.log_failed("get_capacity", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Capacity check failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "get_capacity",
            available_staff=response.available_staff,
            remaining_minutes=response.remaining_capacity_minutes,
        )
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/insert-emergency",
    response_model=EmergencyInsertResponse,
)
def insert_emergency_job(
    request: EmergencyInsertRequest,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> EmergencyInsertResponse:
    """Insert an emergency job into existing schedule.

    POST /api/v1/schedule/insert-emergency

    Validates: Requirement 9.1
    """
    endpoints.log_started(
        "insert_emergency",
        job_id=str(request.job_id),
        target_date=str(request.target_date),
    )

    try:
        response = service.insert_emergency_job(
            job_id=request.job_id,
            target_date=request.target_date,
            priority_level=request.priority_level,
        )
    except Exception as e:
        endpoints.log_failed("insert_emergency", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency insertion failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("insert_emergency", success=response.success)
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/re-optimize/{target_date}",
    response_model=ScheduleGenerateResponse,
)
def reoptimize_schedule(
    target_date: date,
    request: ReoptimizeRequest | None = None,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleGenerateResponse:
    """Re-optimize an existing schedule for a date.

    POST /api/v1/schedule/re-optimize/{date}
    """
    timeout = request.timeout_seconds if request else 15
    endpoints.log_started("reoptimize", target_date=str(target_date))

    try:
        response = service.reoptimize_schedule(target_date, timeout)
    except Exception as e:
        endpoints.log_failed("reoptimize", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-optimization failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("reoptimize", assigned=response.total_assigned)
        return response
