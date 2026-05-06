"""Sales-side reschedule queue endpoints.

Mirror of :mod:`grins_platform.api.v1.reschedule_requests` for the
estimate-visit lifecycle. Surfaces ``RescheduleRequest`` rows whose
``sales_calendar_event_id`` is non-null (per migration
``20260509_120000``) so the sales pipeline gets its own queue without
mixing in appointment-side rows.

Validates: sales-pipeline-estimate-visit-confirmation-lifecycle (OQ-2).
"""

from datetime import (
    date as _date,
    datetime,
    time as _time,
    timezone,
)
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from grins_platform.api.v1.auth_dependencies import CurrentActiveUser
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.job_confirmation import RescheduleRequest
from grins_platform.models.sales import SalesCalendarEvent
from grins_platform.schemas.job_confirmation import (
    RescheduleRequestDetailResponse,
    RescheduleRequestResponse,
)

router = APIRouter(
    prefix="/sales/calendar/events/reschedule-requests",
    tags=["sales-reschedule-requests"],
)


class _Endpoints(LoggerMixin):
    DOMAIN = "api"


_ep = _Endpoints()


def _to_detail(req: RescheduleRequest) -> RescheduleRequestDetailResponse:
    """Map a sales-side RescheduleRequest to the detail response."""
    customer_name = ""
    if req.customer:
        first = req.customer.first_name or ""
        last = req.customer.last_name or ""
        customer_name = f"{first} {last}".strip()

    event_date = None
    if req.sales_calendar_event:
        event_date = req.sales_calendar_event.scheduled_date

    return RescheduleRequestDetailResponse(
        id=req.id,
        job_id=req.job_id,
        appointment_id=req.appointment_id,
        sales_calendar_event_id=req.sales_calendar_event_id,
        customer_id=req.customer_id,
        customer_name=customer_name,
        original_appointment_date=event_date,
        original_appointment_staff=None,
        requested_alternatives=req.requested_alternatives,
        raw_alternatives_text=req.raw_alternatives_text,
        status=req.status,
        created_at=req.created_at,
        resolved_at=req.resolved_at,
    )


@router.get(
    "",
    response_model=list[RescheduleRequestDetailResponse],
    summary="List sales-pipeline reschedule requests",
)
async def list_sales_reschedule_requests(
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (open/resolved). Defaults to open.",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[RescheduleRequestDetailResponse]:
    """List open reschedule requests for estimate visits."""
    _ep.log_started("list_sales_reschedule_requests", status=status_filter)

    query = (
        select(RescheduleRequest)
        .where(RescheduleRequest.sales_calendar_event_id.is_not(None))
        .options(
            selectinload(RescheduleRequest.sales_calendar_event),  # type: ignore[arg-type]
        )
    )
    if status_filter:
        query = query.where(RescheduleRequest.status == status_filter)
    else:
        query = query.where(RescheduleRequest.status == "open")

    query = (
        query.order_by(RescheduleRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(query)
    rows = list(result.scalars().all())

    _ep.log_completed("list_sales_reschedule_requests", count=len(rows))
    return [_to_detail(r) for r in rows]


@router.put(
    "/{request_id}/resolve",
    response_model=RescheduleRequestResponse,
    summary="Resolve a sales-pipeline reschedule request",
)
async def resolve_sales_reschedule_request(
    request_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RescheduleRequestResponse:
    """Mark a sales-side reschedule request as resolved (idempotent)."""
    _ep.log_started(
        "resolve_sales_reschedule_request",
        request_id=str(request_id),
    )
    result = await session.execute(
        select(RescheduleRequest).where(
            RescheduleRequest.id == request_id,
            RescheduleRequest.sales_calendar_event_id.is_not(None),
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

    _ep.log_completed(
        "resolve_sales_reschedule_request",
        request_id=str(request_id),
    )
    return RescheduleRequestResponse.model_validate(req)  # type: ignore[no-any-return]


@router.post(
    "/{request_id}/reschedule",
    summary=(
        "Reschedule the underlying estimate visit and resolve the request"
    ),
)
async def reschedule_sales_calendar_event_from_request(
    request_id: UUID,
    body: dict[str, Any],
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Update the originating SalesCalendarEvent's slot in place + resolve.

    Body shape: ``{"scheduled_date": "YYYY-MM-DD", "start_time":
    "HH:MM:SS" | null, "end_time": "HH:MM:SS" | null}``. The new slot
    primes the event's ``confirmation_status='pending'`` so a fresh
    Y/R/C SMS can be triggered next (clients call the
    ``send-confirmation`` endpoint after this returns).

    Per OQ-10 we update the existing event in place rather than create
    a sibling so the FK fan-out from messages / responses / requests
    keeps a single anchor.
    """
    _ep.log_started(
        "reschedule_sales_calendar_event_from_request",
        request_id=str(request_id),
    )

    request_result = await session.execute(
        select(RescheduleRequest).where(
            RescheduleRequest.id == request_id,
            RescheduleRequest.sales_calendar_event_id.is_not(None),
        ),
    )
    req: RescheduleRequest | None = request_result.scalar_one_or_none()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reschedule request {request_id} not found",
        )
    if req.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reschedule request is no longer open",
        )

    event_result = await session.execute(
        select(SalesCalendarEvent).where(
            SalesCalendarEvent.id == req.sales_calendar_event_id,
        ),
    )
    event: SalesCalendarEvent | None = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Underlying sales calendar event not found",
        )

    scheduled_date = body.get("scheduled_date")
    if not scheduled_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scheduled_date is required",
        )

    try:
        new_date = _date.fromisoformat(scheduled_date)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scheduled_date must be ISO date (YYYY-MM-DD)",
        ) from exc

    new_start_time: _time | None = None
    new_end_time: _time | None = None
    raw_start = body.get("start_time")
    raw_end = body.get("end_time")
    if raw_start:
        try:
            new_start_time = _time.fromisoformat(raw_start)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_time must be ISO time (HH:MM:SS)",
            ) from exc
    if raw_end:
        try:
            new_end_time = _time.fromisoformat(raw_end)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="end_time must be ISO time (HH:MM:SS)",
            ) from exc

    event.scheduled_date = new_date
    event.start_time = new_start_time
    event.end_time = new_end_time
    event.confirmation_status = "pending"
    event.confirmation_status_at = datetime.now(timezone.utc)

    req.status = "resolved"
    req.resolved_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(event)

    _ep.log_completed(
        "reschedule_sales_calendar_event_from_request",
        request_id=str(request_id),
        event_id=str(event.id),
    )
    return {
        "event_id": str(event.id),
        "request_id": str(req.id),
        "scheduled_date": event.scheduled_date.isoformat(),
        "confirmation_status": event.confirmation_status,
    }


__all__ = ["router"]
