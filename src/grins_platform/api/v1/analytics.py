"""
Analytics API endpoints.

Provides staff time analytics for schedule management.

Validates: CRM Gap Closure Req 37.2
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_appointment_service
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.analytics import StaffTimeAnalyticsResponse
from grins_platform.schemas.appointment_ops import DateRange
from grins_platform.services.appointment_service import (
    AppointmentService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class AnalyticsEndpoints(LoggerMixin):
    """Analytics API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = AnalyticsEndpoints()


# =============================================================================
# GET /api/v1/analytics/staff-time - Staff time analytics (Req 37)
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/staff-time",
    response_model=list[StaffTimeAnalyticsResponse],
    summary="Get staff time analytics",
    description=(
        "Calculate average travel time, job duration, and total time "
        "grouped by staff and job type. Flags staff exceeding 1.5x average."
    ),
)
async def get_staff_time_analytics(
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    start_date: date = Query(
        ...,
        description="Start date for analysis period",
    ),
    end_date: date = Query(
        ...,
        description="End date for analysis period",
    ),
) -> list[StaffTimeAnalyticsResponse]:
    """Get staff time analytics.

    Validates: Requirement 37.2
    """
    _endpoints.log_started(
        "get_staff_time_analytics",
        start_date=str(start_date),
        end_date=str(end_date),
    )

    date_range = DateRange(start_date=start_date, end_date=end_date)
    entries = await service.get_staff_time_analytics(date_range)

    result = [
        StaffTimeAnalyticsResponse(
            staff_id=e.staff_id,
            staff_name=e.staff_name,
            job_type=e.job_type,
            avg_travel_minutes=e.avg_travel_minutes,
            avg_job_minutes=e.avg_job_minutes,
            avg_total_minutes=e.avg_total_minutes,
            flagged=e.flagged,
        )
        for e in entries
    ]

    _endpoints.log_completed(
        "get_staff_time_analytics",
        entry_count=len(result),
    )
    return result
