"""Staff reassignment API endpoints.

Validates: Requirements 11.1, 11.2, 11.6
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from grins_platform.database import get_sync_db
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.staff_reassignment import (
    CoverageOptionsResponse,
    MarkUnavailableRequest,
    MarkUnavailableResponse,
    ReassignStaffRequest,
    ReassignStaffResponse,
)
from grins_platform.services.staff_reassignment_service import (
    StaffReassignmentService,
)

router = APIRouter(tags=["staff-reassignment"])


class ReassignmentEndpoints(LoggerMixin):
    """Staff reassignment endpoints."""

    DOMAIN = "api"


endpoints = ReassignmentEndpoints()


def get_reassignment_service(
    db: Session = Depends(get_sync_db),
) -> StaffReassignmentService:
    """Dependency to get StaffReassignmentService."""
    return StaffReassignmentService(db)


@router.post(  # type: ignore[misc,untyped-decorator]
    "/staff/{staff_id}/mark-unavailable",
    response_model=MarkUnavailableResponse,
)
def mark_staff_unavailable(
    staff_id: UUID,
    request: MarkUnavailableRequest,
    service: StaffReassignmentService = Depends(get_reassignment_service),
) -> MarkUnavailableResponse:
    """Mark a staff member as unavailable.

    POST /api/v1/staff/{id}/mark-unavailable

    Validates: Requirement 11.1
    """
    endpoints.log_started("mark_unavailable", staff_id=str(staff_id))

    try:
        response = service.mark_staff_unavailable(
            staff_id=staff_id,
            target_date=request.target_date,
            reason=request.reason,
        )
    except Exception as e:
        endpoints.log_failed("mark_unavailable", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark unavailable: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "mark_unavailable",
            affected=response.affected_appointments,
        )
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/schedule/reassign-staff",
    response_model=ReassignStaffResponse,
)
def reassign_staff(
    request: ReassignStaffRequest,
    service: StaffReassignmentService = Depends(get_reassignment_service),
) -> ReassignStaffResponse:
    """Reassign jobs from one staff to another.

    POST /api/v1/schedule/reassign-staff

    Validates: Requirements 11.2, 11.3
    """
    endpoints.log_started(
        "reassign_staff",
        original=str(request.original_staff_id),
        new=str(request.new_staff_id),
    )

    try:
        response = service.reassign_jobs(
            original_staff_id=request.original_staff_id,
            new_staff_id=request.new_staff_id,
            target_date=request.target_date,
            reason=request.reason,
        )
    except Exception as e:
        endpoints.log_failed("reassign_staff", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reassignment failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("reassign_staff", jobs=response.jobs_reassigned)
        return response


@router.get(  # type: ignore[misc,untyped-decorator]
    "/schedule/coverage-options/{target_date}",
    response_model=CoverageOptionsResponse,
)
def get_coverage_options(
    target_date: date,
    exclude_staff_id: UUID | None = None,
    service: StaffReassignmentService = Depends(get_reassignment_service),
) -> CoverageOptionsResponse:
    """Get coverage options for a date.

    GET /api/v1/schedule/coverage-options/{date}

    Validates: Requirement 11.6
    """
    endpoints.log_started("coverage_options", target_date=str(target_date))

    try:
        response = service.get_coverage_options(target_date, exclude_staff_id)
    except Exception as e:
        endpoints.log_failed("coverage_options", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get coverage options: {e!s}",
        ) from e
    else:
        endpoints.log_completed("coverage_options", options=len(response.options))
        return response
