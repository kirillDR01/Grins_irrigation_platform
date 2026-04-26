"""Sales Pipeline API endpoints.

CRUD and workflow endpoints for the sales pipeline.

Validates: CRM Changes Update 2 Req 14.1, 14.2, 14.4, 14.5, 14.8, 14.10,
           15.1, 15.2, 15.3, 16.1, 16.2, 16.3, 16.4, 18.1, 18.2, 18.3
"""

import datetime as _dt
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.auth_dependencies import CurrentActiveUser
from grins_platform.api.v1.dependencies import get_db_session, get_job_service
from grins_platform.exceptions import (
    InvalidSalesTransitionError,
    SalesEntryNotFoundError,
    SignatureRequiredError,
)
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.customer_document import CustomerDocument
from grins_platform.models.enums import SalesEntryStatus
from grins_platform.models.sales import SalesCalendarEvent, SalesEntry
from grins_platform.schemas.sales_pipeline import (
    SalesCalendarEventCreate,
    SalesCalendarEventResponse,
    SalesCalendarEventUpdate,
    SalesEntryResponse,
    SalesEntryStatusUpdate,
)
from grins_platform.services.audit_service import AuditService
from grins_platform.services.job_service import JobService
from grins_platform.services.photo_service import PhotoService
from grins_platform.services.sales_pipeline_service import SalesPipelineService

router = APIRouter()
logger = get_logger(__name__)


class _SalesPipelineEndpoints(LoggerMixin):
    DOMAIN = "api"


_ep = _SalesPipelineEndpoints()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_signing_document(
    session: AsyncSession,
    customer_id: UUID,
    sales_entry_id: UUID | None = None,
    *,
    include_legacy: bool = False,
) -> CustomerDocument | None:
    """Find the most recent estimate/contract document for a pipeline entry.

    By default (``include_legacy=False``) the query is **strictly** scoped
    to the supplied ``sales_entry_id`` — an unscoped/legacy row never
    leaks across to a different entry's signing flow. This is the
    behavior wanted by every active pipeline operation (bughunt M-11):
    a customer with two open entries where only the older one ever
    uploaded a doc must not be allowed to sign that doc against the
    newer entry. The admin gets a 422 ("Upload an estimate document
    first") and is prompted to upload a properly-scoped document.

    Reporting reads that need to surface every historical document
    (including the pre-migration ``sales_entry_id IS NULL`` rows) can
    opt back into the old behavior with ``include_legacy=True``.

    Validates: Req 9.1, 9.2; bughunt H-7, M-11.
    """
    from sqlalchemy import case  # noqa: PLC0415

    conditions = [
        CustomerDocument.customer_id == customer_id,
        CustomerDocument.document_type.in_(("estimate", "contract")),
    ]
    if sales_entry_id is not None:
        if include_legacy:
            # Legacy/reporting path: prefer entry-scoped rows (priority 0),
            # fall back to unscoped/legacy rows (priority 1). Rows scoped
            # to a *different* entry are excluded entirely.
            conditions.append(
                (CustomerDocument.sales_entry_id == sales_entry_id)
                | (CustomerDocument.sales_entry_id.is_(None)),
            )
            priority = case(
                (CustomerDocument.sales_entry_id == sales_entry_id, 0),
                else_=1,
            )
            stmt = (
                select(CustomerDocument)
                .where(*conditions)
                .order_by(priority, CustomerDocument.uploaded_at.desc())
                .limit(1)
            )
        else:
            # Strict scope (default): only entry-scoped rows count. The
            # legacy ``sales_entry_id IS NULL`` fallback is dropped so
            # multi-entry customers can't accidentally sign the wrong
            # entry's doc.
            conditions.append(
                CustomerDocument.sales_entry_id == sales_entry_id,
            )
            stmt = (
                select(CustomerDocument)
                .where(*conditions)
                .order_by(CustomerDocument.uploaded_at.desc())
                .limit(1)
            )
    else:
        stmt = (
            select(CustomerDocument)
            .where(*conditions)
            .order_by(CustomerDocument.uploaded_at.desc())
            .limit(1)
        )
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if (
        include_legacy
        and sales_entry_id is not None
        and doc is not None
        and doc.sales_entry_id is None
    ):
        _ep.log_started(
            "signing_document.ambiguous_scope",
            customer_id=str(customer_id),
            sales_entry_id=str(sales_entry_id),
        )
    return doc


def _entry_to_response(entry: SalesEntry) -> SalesEntryResponse:
    """Build response with denormalized customer/property fields."""
    from grins_platform.models.enums import job_type_display  # noqa: PLC0415

    customer = entry.customer
    prop = entry.property
    customer_name = f"{customer.first_name} {customer.last_name}" if customer else None
    customer_phone = customer.phone if customer else None
    property_address: str | None = None
    if prop:
        parts = [p for p in [prop.address, prop.city, prop.state, prop.zip_code] if p]
        property_address = ", ".join(parts) if parts else None
    resp = SalesEntryResponse.model_validate(entry)
    resp.customer_name = customer_name
    resp.customer_phone = customer_phone
    resp.customer_email = customer.email if customer else None
    resp.customer_internal_notes = customer.internal_notes if customer else None
    resp.property_address = property_address
    resp.job_type_display = job_type_display(entry.job_type) or None
    return resp  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


async def _get_pipeline_service(
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> SalesPipelineService:
    return SalesPipelineService(
        job_service=job_service,
        audit_service=AuditService(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/pipeline",
    response_model=dict[str, Any],
    summary="List sales pipeline entries with summary boxes",
)
async def list_sales_entries(
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
) -> dict[str, Any]:
    """Return paginated pipeline entries plus status summary counts.

    Validates: Req 14.1, 14.2
    """
    _ep.log_started("list_sales_entries")

    # Summary counts per status
    count_q = select(
        SalesEntry.status,
        func.count().label("cnt"),
    ).group_by(SalesEntry.status)
    rows = (await session.execute(count_q)).all()
    summary: dict[str, int] = {r.status: r.cnt for r in rows}

    # Filtered list
    q = select(SalesEntry).order_by(SalesEntry.created_at.desc())
    if status is not None:
        q = q.where(SalesEntry.status == status)
    q = q.offset(skip).limit(limit)
    entries = (await session.execute(q)).scalars().all()

    # Total for pagination
    total_q = select(func.count()).select_from(SalesEntry)
    if status is not None:
        total_q = total_q.where(SalesEntry.status == status)
    total: int = (await session.execute(total_q)).scalar() or 0

    _ep.log_completed("list_sales_entries", count=len(entries))
    return {
        "items": [_entry_to_response(e) for e in entries],
        "total": total,
        "summary": summary,
    }


@router.get(
    "/pipeline/{entry_id}",
    response_model=SalesEntryResponse,
    summary="Get sales entry detail",
)
async def get_sales_entry(
    entry_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SalesEntryResponse:
    """Validates: Req 14.10"""
    result = await session.execute(
        select(SalesEntry).where(SalesEntry.id == entry_id),
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Sales entry not found")
    return _entry_to_response(entry)


@router.post(
    "/pipeline/{entry_id}/advance",
    response_model=SalesEntryResponse,
    summary="Advance sales entry one step forward",
)
async def advance_sales_entry(
    entry_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[SalesPipelineService, Depends(_get_pipeline_service)],
) -> SalesEntryResponse:
    """Validates: Req 14.4, 14.5"""
    try:
        entry = await service.advance_status(session, entry_id)
        await session.commit()
    except SalesEntryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Sales entry not found",
        ) from exc
    except InvalidSalesTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        return SalesEntryResponse.model_validate(entry)  # type: ignore[no-any-return]


@router.put(
    "/pipeline/{entry_id}/status",
    response_model=SalesEntryResponse,
    summary="Manual status override (admin escape hatch)",
)
async def override_sales_status(
    entry_id: UUID,
    body: SalesEntryStatusUpdate,
    user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[SalesPipelineService, Depends(_get_pipeline_service)],
) -> SalesEntryResponse:
    """Validates: Req 14.8"""
    try:
        entry = await service.manual_override_status(
            session,
            entry_id,
            body.status,
            closed_reason=body.closed_reason,
            actor_id=user.id,
        )
        await session.commit()
    except SalesEntryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Sales entry not found",
        ) from exc
    else:
        return SalesEntryResponse.model_validate(entry)  # type: ignore[no-any-return]


@router.post(
    "/pipeline/{entry_id}/sign/email",
    summary="Trigger email signing via SignWell",
)
async def trigger_email_signing(
    entry_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Validates: Req 18.1, 18.2"""
    from grins_platform.services.signwell.client import SignWellClient  # noqa: PLC0415

    result = await session.execute(
        select(SalesEntry).where(SalesEntry.id == entry_id),
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Sales entry not found")

    customer = entry.customer
    if not customer or not customer.email:
        raise HTTPException(
            status_code=422,
            detail="Customer has no email address on file",
        )

    # Look up the most recent estimate/contract document — Validates: Req 9.1, 9.2, 9.4
    # Strict entry-scope: bughunt M-11 removed the legacy customer-scoped
    # fallback so a multi-entry customer can't sign the wrong entry's
    # doc. Admins prompted to upload a properly-scoped doc on miss.
    signing_doc = await _get_signing_document(
        session,
        entry.customer_id,
        sales_entry_id=entry.id,
    )
    if not signing_doc:
        raise HTTPException(
            status_code=422,
            detail="Upload an estimate document first",
        )

    photo_service = PhotoService()
    pdf_url = photo_service.generate_presigned_url(signing_doc.file_key)

    client = SignWellClient()
    doc = await client.create_document_for_email(
        pdf_url=pdf_url,
        email=customer.email,
        name=f"{customer.first_name} {customer.last_name}",
    )

    entry.signwell_document_id = doc.get("id")
    await session.commit()

    return {"document_id": doc.get("id"), "status": "sent"}


@router.post(
    "/pipeline/{entry_id}/sign/embedded",
    summary="Get embedded signing URL for on-site signing",
)
async def get_embedded_signing(
    entry_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Validates: Req 18.3"""
    from grins_platform.services.signwell.client import SignWellClient  # noqa: PLC0415

    result = await session.execute(
        select(SalesEntry).where(SalesEntry.id == entry_id),
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Sales entry not found")

    customer = entry.customer
    signer_name = (
        f"{customer.first_name} {customer.last_name}" if customer else "Customer"
    )

    # Look up the most recent estimate/contract document — Validates: Req 9.1, 9.2, 9.4
    # Strict entry-scope: bughunt M-11 removed the legacy customer-scoped
    # fallback so a multi-entry customer can't sign the wrong entry's
    # doc. Admins prompted to upload a properly-scoped doc on miss.
    signing_doc = await _get_signing_document(
        session,
        entry.customer_id,
        sales_entry_id=entry.id,
    )
    if not signing_doc:
        raise HTTPException(
            status_code=422,
            detail="Upload an estimate document first",
        )

    photo_service = PhotoService()
    pdf_url = photo_service.generate_presigned_url(signing_doc.file_key)

    client = SignWellClient()

    if entry.signwell_document_id:
        url = await client.get_embedded_url(entry.signwell_document_id)
    else:
        doc = await client.create_document_for_embedded(
            pdf_url=pdf_url,
            signer_name=signer_name,
        )
        entry.signwell_document_id = doc.get("id")
        await session.flush()
        url = await client.get_embedded_url(doc["id"])

    await session.commit()
    return {"signing_url": url}


@router.post(
    "/pipeline/{entry_id}/convert",
    summary="Convert sales entry to job (signature gated)",
)
async def convert_to_job(
    entry_id: UUID,
    user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[SalesPipelineService, Depends(_get_pipeline_service)],
) -> dict[str, Any]:
    """Validates: Req 16.1, 16.2"""
    try:
        job = await service.convert_to_job(
            session,
            entry_id,
            force=False,
            actor_id=user.id,
        )
        await session.commit()
    except SalesEntryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Sales entry not found",
        ) from exc
    except SignatureRequiredError as exc:
        raise HTTPException(
            status_code=422,
            detail="Waiting for customer signature",
        ) from exc
    except InvalidSalesTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        return {"job_id": str(job.id), "status": "closed_won"}


@router.post(
    "/pipeline/{entry_id}/force-convert",
    summary="Force convert to job without signature",
)
async def force_convert_to_job(
    entry_id: UUID,
    user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[SalesPipelineService, Depends(_get_pipeline_service)],
) -> dict[str, Any]:
    """Validates: Req 16.3, 16.4"""
    try:
        job = await service.convert_to_job(
            session,
            entry_id,
            force=True,
            actor_id=user.id,
        )
        await session.commit()
    except SalesEntryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Sales entry not found",
        ) from exc
    except InvalidSalesTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        return {"job_id": str(job.id), "status": "closed_won", "forced": True}


@router.delete(
    "/pipeline/{entry_id}",
    response_model=SalesEntryResponse,
    summary="Mark sales entry as lost",
)
async def mark_sales_entry_lost(
    entry_id: UUID,
    user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[SalesPipelineService, Depends(_get_pipeline_service)],
    closed_reason: str | None = Query(None),
) -> SalesEntryResponse:
    """Validates: Req 14.7, 14.9"""
    try:
        entry = await service.mark_lost(
            session,
            entry_id,
            closed_reason=closed_reason,
            actor_id=user.id,
        )
        await session.commit()
    except SalesEntryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Sales entry not found",
        ) from exc
    except InvalidSalesTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        return SalesEntryResponse.model_validate(entry)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Sales Calendar Event endpoints — Req 15.1, 15.2, 15.3
# ---------------------------------------------------------------------------


@router.get(
    "/calendar/events",
    response_model=list[SalesCalendarEventResponse],
    summary="List estimate appointments",
)
async def list_calendar_events(
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    start_date: _dt.date | None = Query(None),
    end_date: _dt.date | None = Query(None),
    sales_entry_id: UUID | None = Query(None),
) -> list[SalesCalendarEventResponse]:
    """Return sales calendar events, optionally filtered by date range.

    Validates: Req 15.1
    """
    _ep.log_started("list_calendar_events")
    q = select(SalesCalendarEvent).order_by(SalesCalendarEvent.scheduled_date)
    if start_date is not None:
        q = q.where(SalesCalendarEvent.scheduled_date >= start_date)
    if end_date is not None:
        q = q.where(SalesCalendarEvent.scheduled_date <= end_date)
    if sales_entry_id is not None:
        q = q.where(SalesCalendarEvent.sales_entry_id == sales_entry_id)
    events = (await session.execute(q)).scalars().all()
    _ep.log_completed("list_calendar_events", count=len(events))
    return [SalesCalendarEventResponse.model_validate(e) for e in events]


@router.post(
    "/calendar/events",
    response_model=SalesCalendarEventResponse,
    status_code=201,
    summary="Create estimate appointment",
)
async def create_calendar_event(
    body: SalesCalendarEventCreate,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SalesCalendarEventResponse:
    """Validates: Req 15.2"""
    _ep.log_started("create_calendar_event", sales_entry_id=str(body.sales_entry_id))
    event = SalesCalendarEvent(
        sales_entry_id=body.sales_entry_id,
        customer_id=body.customer_id,
        title=body.title,
        scheduled_date=body.scheduled_date,
        start_time=body.start_time,
        end_time=body.end_time,
        notes=body.notes,
        assigned_to_user_id=body.assigned_to_user_id,
    )
    session.add(event)

    # Auto-advance sales entry from schedule_estimate → estimate_scheduled
    # Validates: Req 10.1, 10.4
    result = await session.execute(
        select(SalesEntry).where(SalesEntry.id == body.sales_entry_id),
    )
    sales_entry = result.scalar_one_or_none()
    if (
        sales_entry is not None
        and sales_entry.status == SalesEntryStatus.SCHEDULE_ESTIMATE.value
    ):
        sales_entry.status = SalesEntryStatus.ESTIMATE_SCHEDULED.value
        logger.info(
            "sales.calendar_event.auto_advance",
            sales_entry_id=str(body.sales_entry_id),
            from_status=SalesEntryStatus.SCHEDULE_ESTIMATE.value,
            to_status=SalesEntryStatus.ESTIMATE_SCHEDULED.value,
        )

    await session.commit()
    await session.refresh(event)
    _ep.log_completed(
        "create_calendar_event",
        event_id=str(event.id),
        assigned_to_user_id=str(body.assigned_to_user_id)
        if body.assigned_to_user_id
        else None,
    )
    return SalesCalendarEventResponse.model_validate(event)  # type: ignore[no-any-return]


@router.put(
    "/calendar/events/{event_id}",
    response_model=SalesCalendarEventResponse,
    summary="Update estimate appointment",
)
async def update_calendar_event(
    event_id: UUID,
    body: SalesCalendarEventUpdate,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SalesCalendarEventResponse:
    """Validates: Req 15.2"""
    _ep.log_started("update_calendar_event", event_id=str(event_id))
    result = await session.execute(
        select(SalesCalendarEvent).where(SalesCalendarEvent.id == event_id),
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    await session.commit()
    await session.refresh(event)
    _ep.log_completed("update_calendar_event", event_id=str(event_id))
    return SalesCalendarEventResponse.model_validate(event)  # type: ignore[no-any-return]


@router.delete(
    "/calendar/events/{event_id}",
    status_code=204,
    summary="Delete estimate appointment",
)
async def delete_calendar_event(
    event_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Validates: Req 15.3"""
    _ep.log_started("delete_calendar_event", event_id=str(event_id))
    result = await session.execute(
        select(SalesCalendarEvent).where(SalesCalendarEvent.id == event_id),
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    await session.delete(event)
    await session.commit()
    _ep.log_completed("delete_calendar_event", event_id=str(event_id))
