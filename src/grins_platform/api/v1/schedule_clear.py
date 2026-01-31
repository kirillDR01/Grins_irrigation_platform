"""
Schedule Clear API endpoints.

This module provides FastAPI endpoints for schedule clear operations,
including clearing schedules, viewing audit logs, and recent clears.

Validates: Requirements 3.1-3.7, 5.1-5.6, 6.1-6.5, 17.5-17.6
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.auth_dependencies import ManagerOrAdminUser
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.exceptions import ScheduleClearAuditNotFoundError
from grins_platform.repositories.appointment_repository import AppointmentRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.schedule_clear_audit_repository import (
    ScheduleClearAuditRepository,
)
from grins_platform.schemas.schedule_clear import (
    ScheduleClearAuditDetailResponse,
    ScheduleClearAuditResponse,
    ScheduleClearRequest,
    ScheduleClearResponse,
    ScheduleRestoreResponse,
)
from grins_platform.services.schedule_clear_service import ScheduleClearService

router = APIRouter(prefix="/schedule/clear", tags=["schedule-clear"])


async def get_schedule_clear_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScheduleClearService:
    """Get ScheduleClearService dependency.

    Args:
        session: Database session from dependency injection

    Returns:
        ScheduleClearService instance
    """
    appointment_repository = AppointmentRepository(session=session)
    job_repository = JobRepository(session=session)
    audit_repository = ScheduleClearAuditRepository(session=session)
    return ScheduleClearService(
        appointment_repository=appointment_repository,
        job_repository=job_repository,
        audit_repository=audit_repository,
    )


@router.post(
    "",
    response_model=ScheduleClearResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear schedule for a date",
    description="Clear all appointments for a date, reset job statuses, create audit.",
)
async def clear_schedule(
    request: ScheduleClearRequest,
    current_user: ManagerOrAdminUser,
    service: Annotated[ScheduleClearService, Depends(get_schedule_clear_service)],
) -> ScheduleClearResponse:
    """Clear appointments for specified date.

    This endpoint:
    - Deletes all appointments for the specified date
    - Resets job statuses from 'scheduled' to 'approved'
    - Creates an audit log of the operation

    Requires manager or admin role.

    Args:
        request: Schedule clear request with date and optional notes
        current_user: Authenticated manager or admin user
        service: ScheduleClearService instance

    Returns:
        ScheduleClearResponse with audit ID and counts

    Validates: Requirements 3.1-3.7, 17.5-17.6, 21.1
    """
    return await service.clear_schedule(
        schedule_date=request.schedule_date,
        cleared_by=current_user.id,
        notes=request.notes,
    )


@router.get(
    "/recent",
    response_model=list[ScheduleClearAuditResponse],
    summary="Get recently cleared schedules",
    description="Get schedules cleared in the last 24 hours.",
)
async def get_recent_clears(
    _current_user: ManagerOrAdminUser,
    service: Annotated[ScheduleClearService, Depends(get_schedule_clear_service)],
    hours: int = 24,
) -> list[ScheduleClearAuditResponse]:
    """Get recently cleared schedules.

    Returns audit records for schedules cleared within the specified time window.

    Requires manager or admin role.

    Args:
        current_user: Authenticated manager or admin user
        service: ScheduleClearService instance
        hours: Number of hours to look back (default 24)

    Returns:
        List of ScheduleClearAuditResponse

    Validates: Requirements 6.1-6.2, 17.5-17.6, 21.4
    """
    return await service.get_recent_clears(hours=hours)


@router.get(
    "/{audit_id}",
    response_model=ScheduleClearAuditDetailResponse,
    summary="Get schedule clear audit details",
    description="Get detailed audit log for a specific schedule clear operation.",
)
async def get_clear_details(
    audit_id: UUID,
    _current_user: ManagerOrAdminUser,
    service: Annotated[ScheduleClearService, Depends(get_schedule_clear_service)],
) -> ScheduleClearAuditDetailResponse:
    """Get detailed audit log.

    Returns full audit record including serialized appointment data
    and list of reset job IDs.

    Requires manager or admin role.

    Args:
        audit_id: UUID of the audit record
        current_user: Authenticated manager or admin user
        service: ScheduleClearService instance

    Returns:
        ScheduleClearAuditDetailResponse with full details

    Raises:
        HTTPException: 404 if audit record not found

    Validates: Requirements 6.3, 17.5-17.6, 22.3
    """
    try:
        return await service.get_clear_details(audit_id=audit_id)
    except ScheduleClearAuditNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{audit_id}/restore",
    response_model=ScheduleRestoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore a cleared schedule",
    description="Restore appointments from a cleared schedule audit record.",
)
async def restore_schedule(
    audit_id: UUID,
    current_user: ManagerOrAdminUser,
    service: Annotated[ScheduleClearService, Depends(get_schedule_clear_service)],
) -> ScheduleRestoreResponse:
    """Restore a previously cleared schedule.

    This endpoint:
    - Recreates all appointments from the audit record
    - Updates job statuses back to 'scheduled'
    - Deletes the audit record after successful restore

    Requires manager or admin role.

    Args:
        audit_id: UUID of the audit record to restore from
        current_user: Authenticated manager or admin user
        service: ScheduleClearService instance

    Returns:
        ScheduleRestoreResponse with counts of restored items

    Raises:
        HTTPException: 404 if audit record not found

    Validates: Requirements 6.4-6.5
    """
    try:
        return await service.restore_schedule(
            audit_id=audit_id,
            restored_by=current_user.id,
        )
    except ScheduleClearAuditNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


__all__ = ["router"]
