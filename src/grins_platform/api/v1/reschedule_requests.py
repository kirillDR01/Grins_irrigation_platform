"""Reschedule requests API endpoints.

Provides admin queue for customer reschedule requests from Y/R/C flow.

Validates: CRM Changes Update 2 Req 25.1, 25.2, 25.3, 25.4
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from grins_platform.api.v1.auth_dependencies import CurrentActiveUser
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.job_confirmation import RescheduleRequest
from grins_platform.schemas.job_confirmation import (
    RescheduleRequestDetailResponse,
    RescheduleRequestResponse,
)

router = APIRouter(
    prefix="/schedule/reschedule-requests",
    tags=["reschedule-requests"],
)


class RescheduleEndpoints(LoggerMixin):
    """Reschedule request endpoints."""

    DOMAIN = "api"


endpoints = RescheduleEndpoints()


def _to_detail(
    req: RescheduleRequest,
) -> RescheduleRequestDetailResponse:
    """Map model to enriched detail response."""
    customer_name = ""
    if req.customer:
        first = req.customer.first_name or ""
        last = req.customer.last_name or ""
        customer_name = f"{first} {last}".strip()

    appt_date = None
    appt_staff = None
    if req.appointment:
        appt_date = req.appointment.scheduled_date
        if req.appointment.staff:
            appt_staff = req.appointment.staff.name or ""

    return RescheduleRequestDetailResponse(
        id=req.id,
        job_id=req.job_id,
        appointment_id=req.appointment_id,
        sales_calendar_event_id=req.sales_calendar_event_id,
        customer_id=req.customer_id,
        customer_name=customer_name,
        original_appointment_date=appt_date,
        original_appointment_staff=appt_staff,
        requested_alternatives=req.requested_alternatives,
        raw_alternatives_text=req.raw_alternatives_text,
        status=req.status,
        created_at=req.created_at,
        resolved_at=req.resolved_at,
    )


@router.get(
    "",
    response_model=list[RescheduleRequestDetailResponse],
    summary="List reschedule requests",
    description=("List reschedule requests grouped by status for admin queue."),
)
async def list_reschedule_requests(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (open/resolved)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[RescheduleRequestDetailResponse]:
    """List reschedule requests for admin queue.

    Returns requests sorted by created_at descending.
    Defaults to 'open' requests if no status filter.

    Validates: Req 25.1
    """
    endpoints.log_started(
        "list_reschedule_requests",
        status_filter=status_filter,
    )

    # Polymorphic FK guard (migration 20260509_120000): the schedule-tab
    # queue is appointment-scoped — sales-side rows live at
    # /api/v1/sales/calendar/events/reschedule-requests.
    query = (
        select(RescheduleRequest)
        .where(RescheduleRequest.appointment_id.is_not(None))
        .options(
            selectinload(RescheduleRequest.appointment).selectinload(  # type: ignore[arg-type]
                Appointment.staff,
            ),
        )
    )
    if status_filter:
        query = query.where(
            RescheduleRequest.status == status_filter,
        )
    else:
        query = query.where(
            RescheduleRequest.status == "open",
        )

    query = (
        query.order_by(RescheduleRequest.created_at.desc()).offset(skip).limit(limit)
    )
    result = await session.execute(query)
    requests = list(result.scalars().all())

    endpoints.log_completed(
        "list_reschedule_requests",
        count=len(requests),
    )
    return [_to_detail(r) for r in requests]


@router.put(
    "/{request_id}/resolve",
    response_model=RescheduleRequestResponse,
    summary="Resolve a reschedule request",
    description="Mark a reschedule request as resolved.",
)
async def resolve_reschedule_request(
    request_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RescheduleRequestResponse:
    """Mark a reschedule request as resolved.

    Validates: Req 25.4
    """
    endpoints.log_started(
        "resolve_reschedule_request",
        request_id=str(request_id),
    )

    result = await session.execute(
        select(RescheduleRequest).where(
            RescheduleRequest.id == request_id,
        ),
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reschedule request {request_id} not found",
        )

    if req.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request is already resolved",
        )

    req.status = "resolved"
    req.resolved_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(req)

    endpoints.log_completed(
        "resolve_reschedule_request",
        request_id=str(request_id),
    )
    resp: RescheduleRequestResponse = RescheduleRequestResponse.model_validate(req)
    return resp


__all__ = ["router"]
