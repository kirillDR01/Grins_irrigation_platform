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
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
    ManagerOrAdminUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import (
    get_appointment_note_service,
    get_appointment_service,
    get_appointment_timeline_service,
    get_db_session,
    get_full_appointment_service,
)
from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    ReviewAlreadyRequestedError,
    StaffConflictError,
    StaffNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    AppointmentStatus,
)
from grins_platform.schemas.appointment import (
    AppointmentCreate,
    AppointmentPaginatedResponse,
    AppointmentResponse,
    AppointmentUpdate,
    BulkSendConfirmationsRequest,
    BulkSendConfirmationsResponse,
    DailyScheduleResponse,
    MarkContactedResponse,
    NeedsReviewAppointmentResponse,
    ReplyState,
    SendConfirmationResponse,
    StaffDailyScheduleResponse,
    WeeklyScheduleResponse,
)
from grins_platform.schemas.appointment_note import (
    AppointmentNotesResponse,
    AppointmentNotesSaveRequest,
)
from grins_platform.schemas.appointment_ops import (
    PaymentCollectionRequest,
    PaymentResult,
    RescheduleFromRequest,
    RescheduleRequest,
    ReviewRequestResult,
)
from grins_platform.schemas.appointment_timeline import AppointmentTimelineResponse
from grins_platform.schemas.estimate import (
    EstimateCreate,
    EstimateResponse,
)
from grins_platform.schemas.invoice import (
    InvoiceResponse,
)
from grins_platform.services.appointment_note_service import (
    AppointmentNoteService,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.services.appointment_service import (
    AppointmentService,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.services.appointment_timeline_service import (
    AppointmentTimelineService,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.services.photo_service import PhotoService, UploadContext

router = APIRouter()


class AppointmentEndpoints(LoggerMixin):
    """Appointment API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = AppointmentEndpoints()


def _populate_appointment_extended_fields(
    response: AppointmentResponse,
    appointment: object,
) -> None:
    """Populate extended display fields on an AppointmentResponse.

    Reads job_type, customer_name, staff_name, and service_agreement_id
    from the appointment's relationships.
    """
    job = getattr(appointment, "job", None)
    if job:
        response.job_type = job.job_type
        response.service_agreement_id = getattr(job, "service_agreement_id", None)
        response.priority_level = getattr(job, "priority_level", None)
        customer = getattr(job, "customer", None)
        if customer:
            response.customer_name = f"{customer.first_name} {customer.last_name}"
            response.customer_internal_notes = customer.internal_notes
    staff = getattr(appointment, "staff", None)
    if staff:
        response.staff_name = staff.name


def _enrich_appointment_response(
    appointment: object,
    reply_state: ReplyState | None = None,
) -> AppointmentResponse:
    """Create an AppointmentResponse with extended fields populated.

    Optional ``reply_state`` is attached for the weekly-schedule path
    (gap-12). Daily / list endpoints leave it ``None`` to keep their
    query plans unchanged.
    """
    response: AppointmentResponse = AppointmentResponse.model_validate(appointment)
    _populate_appointment_extended_fields(response, appointment)
    if reply_state is not None:
        response.reply_state = reply_state
    return response


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
        include_relationships=True,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    _endpoints.log_completed("list_appointments", count=len(appointments), total=total)

    # Build response with extended fields from relationships
    items: list[AppointmentResponse] = []
    for a in appointments:
        response = AppointmentResponse.model_validate(a)
        _populate_appointment_extended_fields(response, a)
        items.append(response)

    return AppointmentPaginatedResponse(
        items=items,
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
        appointments=[_enrich_appointment_response(a) for a in appointments],
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
        appointments=[_enrich_appointment_response(a) for a in appointments],
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

    Validates: Admin Dashboard Requirement 1.5;
               scheduling-gaps gap-12 (per-appointment reply_state).
    """
    _endpoints.log_started("get_weekly_schedule", start_date=str(start_date))

    (
        schedule,
        total,
        reply_state_map,
    ) = await service.get_weekly_schedule_with_reply_state(start_date)

    def _reply_state_for(appt: object) -> ReplyState | None:
        appt_id = getattr(appt, "id", None)
        if appt_id is None:
            return None
        raw = reply_state_map.get(appt_id)
        if raw is None:
            return None
        return ReplyState(**raw)

    # Build daily schedule responses
    days: list[DailyScheduleResponse] = []
    for i in range(7):
        day_date = start_date + timedelta(days=i)
        day_appointments = schedule.get(day_date, [])
        days.append(
            DailyScheduleResponse(
                date=day_date,
                appointments=[
                    _enrich_appointment_response(a, reply_state=_reply_state_for(a))
                    for a in day_appointments
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


async def _send_appointment_confirmation_sms(
    db: AsyncSession,
    appointment: object,
) -> None:
    """Send APPOINTMENT_CONFIRMATION SMS after creating an appointment.

    Fire-and-forget: failures are logged but do not block appointment creation.

    Validates: CRM Changes Update 2 Req 24.1
    """
    from grins_platform.log_config import get_logger as _get_logger  # noqa: PLC0415
    from grins_platform.models.customer import Customer  # noqa: PLC0415
    from grins_platform.models.job import Job  # noqa: PLC0415
    from grins_platform.schemas.ai import MessageType  # noqa: PLC0415
    from grins_platform.services.sms.factory import (  # noqa: PLC0415
        get_sms_provider,
    )
    from grins_platform.services.sms.recipient import Recipient  # noqa: PLC0415
    from grins_platform.services.sms_service import SMSService  # noqa: PLC0415

    _log = _get_logger(__name__)
    try:
        job = await db.get(Job, appointment.job_id)  # type: ignore[union-attr]
        if job is None:
            return
        customer = await db.get(Customer, job.customer_id)
        if customer is None or not customer.phone:
            return

        sms_service = SMSService(db, provider=get_sms_provider())
        recipient = Recipient.from_customer(customer)

        date_str = str(appointment.scheduled_date)  # type: ignore[union-attr]
        window_start = getattr(appointment, "time_window_start", None)
        window_end = getattr(appointment, "time_window_end", None)

        def _fmt_time_12h(t: object) -> str:
            """Format a time string like '09:00:00' to '9:00 AM'."""
            s = str(t)[:5]  # "09:00"
            h, m = int(s[:2]), int(s[3:5])
            suffix = "AM" if h < 12 else "PM"
            h = h % 12 or 12
            return f"{h}:{m:02d} {suffix}"

        if window_start and window_end:
            time_part = f" between {_fmt_time_12h(window_start)} and {_fmt_time_12h(window_end)}"
        elif window_start:
            time_part = f" at {_fmt_time_12h(window_start)}"
        else:
            time_part = ""
        msg = (
            f"Your appointment on {date_str}{time_part} has been scheduled. "
            "Reply Y to confirm, R to reschedule, or C to cancel."
        )

        await sms_service.send_message(
            recipient=recipient,
            message=msg,
            message_type=MessageType.APPOINTMENT_CONFIRMATION,
            consent_type="transactional",
            job_id=job.id,
            appointment_id=appointment.id,  # type: ignore[union-attr]
        )
    except Exception:
        _log.warning(
            "appointment.confirmation_sms.failed",
            appointment_id=str(getattr(appointment, "id", None)),
            exc_info=True,
        )


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new appointment",
    description="Create a new appointment for a job.",
)
async def create_appointment(
    data: AppointmentCreate,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AppointmentResponse:
    """Create a new appointment.

    Validates: Admin Dashboard Requirement 1.1
    Validates: CRM Changes Update 2 Req 24.1 (send confirmation SMS)
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

    # Draft mode (Req 8.2): No SMS on creation — appointment starts as DRAFT

    _endpoints.log_completed("create_appointment", appointment_id=str(result.id))
    return AppointmentResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# POST /api/v1/appointments/send-confirmations - Bulk send (Req 8)
# NOTE: Static routes must come BEFORE dynamic /{appointment_id} routes
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/send-confirmations",
    response_model=BulkSendConfirmationsResponse,
    summary="Bulk send confirmation SMS for draft appointments",
    description=(
        "Sends Y/R/C confirmation SMS for all DRAFT appointments matching the filter. "
        "Accepts appointment IDs or a date range."
    ),
)
async def bulk_send_confirmations(
    data: BulkSendConfirmationsRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_full_appointment_service)],
) -> BulkSendConfirmationsResponse:
    """Bulk send confirmation SMS for draft appointments.

    Validates: Req 8.6, 8.13
    """
    _endpoints.log_started(
        "bulk_send_confirmations",
        ids_count=len(data.appointment_ids) if data.appointment_ids else 0,
    )

    result = await service.bulk_send_confirmations(
        appointment_ids=data.appointment_ids,
        date_from=data.date_from,
        date_to=data.date_to,
    )

    _endpoints.log_completed(
        "bulk_send_confirmations",
        sent_count=result["sent_count"],
        deferred_count=result.get("deferred_count", 0),
        skipped_count=result.get("skipped_count", 0),
        failed_count=result["failed_count"],
    )
    return BulkSendConfirmationsResponse(
        sent_count=result["sent_count"],
        deferred_count=result.get("deferred_count", 0),
        skipped_count=result.get("skipped_count", 0),
        failed_count=result["failed_count"],
        total_draft=result["total_draft"],
        results=result.get("results", []),
    )


# =============================================================================
# GET /api/v1/appointments/needs-review - Admin review queue (bughunt H-7)
# NOTE: Static routes must come BEFORE dynamic /{appointment_id} routes
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/needs-review",
    response_model=list[NeedsReviewAppointmentResponse],
    summary="List appointments flagged for admin review",
    description=(
        "Return every appointment whose ``needs_review_reason`` is populated "
        "and matches the optional ``reason`` filter — used by the "
        "/schedule no-reply-confirmation queue."
    ),
)
async def list_needs_review_appointments(
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    reason: str | None = Query(
        default=None,
        description=(
            "Optional filter on the review reason token (for example "
            "``no_confirmation_response``). If omitted, every flagged "
            "appointment is returned."
        ),
    ),
) -> list[NeedsReviewAppointmentResponse]:
    """List flagged appointments for the admin review queue.

    Validates: bughunt 2026-04-16 finding H-7
    """
    _endpoints.log_started(
        "list_needs_review_appointments",
        reason=reason,
    )

    from sqlalchemy import (  # noqa: PLC0415
        func as _sa_func,
        select as _select,
    )
    from sqlalchemy.orm import selectinload as _selectinload  # noqa: PLC0415

    from grins_platform.models.appointment import (  # noqa: PLC0415
        Appointment as _Appointment,
    )
    from grins_platform.models.job import Job as _Job  # noqa: PLC0415
    from grins_platform.models.sent_message import (  # noqa: PLC0415
        SentMessage as _SentMessage,
    )
    from grins_platform.schemas.ai import (  # noqa: PLC0415
        MessageType as _MessageType,
    )

    stmt = (
        _select(_Appointment)
        .options(
            _selectinload(_Appointment.job).selectinload(_Job.customer),
        )
        .where(_Appointment.needs_review_reason.is_not(None))
    )
    if reason is not None:
        stmt = stmt.where(_Appointment.needs_review_reason == reason)
    stmt = stmt.order_by(_Appointment.scheduled_date.asc())

    result = await session.execute(stmt)
    appointments = list(result.scalars().unique().all())

    items: list[NeedsReviewAppointmentResponse] = []
    for appt in appointments:
        # Resolve the most-recent confirmation SMS sent_at so the FE can
        # render "N days since confirmation sent".
        sent_at_stmt = _select(_sa_func.max(_SentMessage.sent_at)).where(
            _SentMessage.appointment_id == appt.id,
            _SentMessage.message_type == _MessageType.APPOINTMENT_CONFIRMATION.value,
            _SentMessage.sent_at.is_not(None),
        )
        sent_at_result = await session.execute(sent_at_stmt)
        confirmation_sent_at = sent_at_result.scalar()

        customer = getattr(getattr(appt, "job", None), "customer", None)
        customer_name = None
        customer_phone = None
        customer_id = None
        if customer is not None:
            customer_id = customer.id
            customer_name = customer.full_name
            customer_phone = customer.phone

        items.append(
            NeedsReviewAppointmentResponse(
                id=appt.id,
                job_id=appt.job_id,
                staff_id=appt.staff_id,
                scheduled_date=appt.scheduled_date,
                time_window_start=appt.time_window_start,
                time_window_end=appt.time_window_end,
                status=AppointmentStatus(appt.status),
                needs_review_reason=appt.needs_review_reason,
                confirmation_sent_at=confirmation_sent_at,
                customer_id=customer_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
            )
        )

    _endpoints.log_completed(
        "list_needs_review_appointments",
        count=len(items),
    )
    return items


# =============================================================================
# POST /api/v1/appointments/{id}/mark-contacted (bughunt H-7)
# Clears needs_review_reason on an admin-reviewed appointment.
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/mark-contacted",
    response_model=MarkContactedResponse,
    summary="Mark a needs-review appointment as contacted",
    description=(
        "Clears ``needs_review_reason`` so the appointment no longer shows "
        "in the /schedule admin review queue. Used once admin has called "
        "the customer to confirm."
    ),
)
async def mark_appointment_contacted(
    appointment_id: UUID,
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MarkContactedResponse:
    """Clear the review flag on an appointment.

    Validates: bughunt 2026-04-16 finding H-7
    """
    _endpoints.log_started(
        "mark_appointment_contacted",
        appointment_id=str(appointment_id),
    )

    from grins_platform.models.appointment import (  # noqa: PLC0415
        Appointment as _Appointment,
    )

    appt = await session.get(_Appointment, appointment_id)
    if appt is None:
        _endpoints.log_rejected("mark_appointment_contacted", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {appointment_id}",
        )

    prior_reason = appt.needs_review_reason
    appt.needs_review_reason = None
    await session.flush()

    # gap-05: audit who cleared the review flag and what it used to say.
    try:
        from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
            AuditLogRepository,
        )

        audit_repo = AuditLogRepository(session)
        _ = await audit_repo.create(
            action="appointment.mark_contacted",
            resource_type="appointment",
            resource_id=appointment_id,
            actor_id=_current_user.id,
            details={
                "actor_type": "staff",
                "source": "admin_ui",
                "prior_reason": prior_reason,
            },
        )
    except Exception:
        _endpoints.log_failed(
            "mark_appointment_contacted.audit",
            appointment_id=str(appointment_id),
        )

    _endpoints.log_completed(
        "mark_appointment_contacted",
        appointment_id=str(appointment_id),
    )
    return MarkContactedResponse(
        appointment_id=appointment_id,
        needs_review_reason=None,
    )


# =============================================================================
# POST /api/v1/appointments/{id}/send-reminder-sms (bughunt H-7)
# Re-fires the Y/R/C confirmation SMS without resetting appointment status.
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/send-reminder-sms",
    response_model=SendConfirmationResponse,
    summary="Re-fire the Y/R/C confirmation SMS as a reminder",
    description=(
        "Re-sends SMS #1 (Y/R/C prompt) for a SCHEDULED appointment that "
        "never received a customer reply. Unlike ``send-confirmation``, "
        "this endpoint does not require DRAFT status — it is intended "
        "for the needs-review queue where the appointment is already "
        "SCHEDULED."
    ),
)
async def send_reminder_sms(
    appointment_id: UUID,
    _current_user: ManagerOrAdminUser,
    service: Annotated[AppointmentService, Depends(get_full_appointment_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SendConfirmationResponse:
    """Send a confirmation-SMS reminder for a flagged appointment.

    Validates: bughunt 2026-04-16 finding H-7
    """
    _endpoints.log_started(
        "send_reminder_sms",
        appointment_id=str(appointment_id),
    )

    try:
        result = await service.send_confirmation_sms(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("send_reminder_sms", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e

    sms_sent = bool(result and result.get("success"))

    # gap-05: audit the manual reminder send. Audit failures are logged
    # but never block the customer-facing reminder.
    try:
        from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
            AuditLogRepository,
        )

        sent_message_id: str | None = None
        if isinstance(result, dict):
            raw_id = result.get("sent_message_id") or result.get("message_id")
            if raw_id is not None:
                sent_message_id = str(raw_id)

        audit_repo = AuditLogRepository(session)
        _ = await audit_repo.create(
            action="appointment.reminder_sent",
            resource_type="appointment",
            resource_id=appointment_id,
            actor_id=_current_user.id,
            details={
                "actor_type": "staff",
                "source": "admin_ui",
                "stage": "manual",
                "sms_sent": sms_sent,
                "sent_message_id": sent_message_id,
            },
        )
    except Exception:
        _endpoints.log_failed(
            "send_reminder_sms.audit",
            appointment_id=str(appointment_id),
        )

    _endpoints.log_completed(
        "send_reminder_sms",
        appointment_id=str(appointment_id),
        sms_sent=sms_sent,
    )
    return SendConfirmationResponse(
        appointment_id=appointment_id,
        status=AppointmentStatus.SCHEDULED.value,
        sms_sent=sms_sent,
    )


# =============================================================================
# GET /api/v1/appointments/{id}/notes - Get appointment notes (V2)
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{appointment_id}/notes",
    response_model=AppointmentNotesResponse,
    summary="Get appointment internal notes",
    description=(
        "Returns the centralized internal notes for an appointment. "
        "If no notes record exists, returns an empty body with null updated_by."
    ),
)
async def get_appointment_notes(
    appointment_id: UUID,
    _current_user: CurrentActiveUser,
    note_service: Annotated[
        AppointmentNoteService,
        Depends(get_appointment_note_service),
    ],
) -> AppointmentNotesResponse:
    """Get internal notes for an appointment.

    Validates: Appointment Modal V2 Req 10.1, 10.2, 10.4
    """
    _endpoints.log_started(
        "get_appointment_notes",
        appointment_id=str(appointment_id),
    )

    try:
        result = await note_service.get_notes(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("get_appointment_notes", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e

    _endpoints.log_completed(
        "get_appointment_notes",
        appointment_id=str(appointment_id),
    )
    return result


# =============================================================================
# PATCH /api/v1/appointments/{id}/notes - Save appointment notes (V2)
# =============================================================================


@router.patch(  # type: ignore[untyped-decorator]
    "/{appointment_id}/notes",
    response_model=AppointmentNotesResponse,
    summary="Save appointment internal notes",
    description=(
        "Upserts the centralized internal notes for an appointment. "
        "Creates the record if it doesn't exist, updates if it does. "
        "Sets updated_by to the current authenticated user."
    ),
)
async def save_appointment_notes(
    appointment_id: UUID,
    data: AppointmentNotesSaveRequest,
    current_user: CurrentActiveUser,
    note_service: Annotated[
        AppointmentNoteService,
        Depends(get_appointment_note_service),
    ],
) -> AppointmentNotesResponse:
    """Save internal notes for an appointment.

    Validates: Appointment Modal V2 Req 10.3, 10.4, 10.5, 10.6
    """
    _endpoints.log_started(
        "save_appointment_notes",
        appointment_id=str(appointment_id),
        body_len=len(data.body),
    )

    try:
        result = await note_service.save_notes(
            appointment_id=appointment_id,
            body=data.body,
            updated_by_id=current_user.id,
        )
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("save_appointment_notes", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e

    _endpoints.log_completed(
        "save_appointment_notes",
        appointment_id=str(appointment_id),
    )
    return result


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
# GET /api/v1/appointments/{id}/timeline - Communication Timeline (Gap 11)
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{appointment_id}/timeline",
    response_model=AppointmentTimelineResponse,
    summary="Get appointment communication timeline",
    description=(
        "Returns a chronologically-sorted communication timeline for an "
        "appointment: outbound SMS, inbound replies, reschedule requests, "
        "and opt-out state. Backs Gap 11 AppointmentDetail enhancement."
    ),
)
async def get_appointment_timeline(
    appointment_id: UUID,
    service: Annotated[
        AppointmentTimelineService,
        Depends(get_appointment_timeline_service),
    ],
) -> AppointmentTimelineResponse:
    """Get appointment communication timeline.

    Validates: Gap 11.
    """
    _endpoints.log_started(
        "get_appointment_timeline",
        appointment_id=str(appointment_id),
    )

    try:
        result = await service.get_timeline(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("get_appointment_timeline", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e

    _endpoints.log_completed(
        "get_appointment_timeline",
        appointment_id=str(appointment_id),
        event_count=len(result.events),
    )
    return result


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
    current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentResponse:
    """Update appointment information.

    Validates: Admin Dashboard Requirement 1.2; bughunt M-7
    """
    _endpoints.log_started("update_appointment", appointment_id=str(appointment_id))

    try:
        # bughunt M-7: surface the actor so the audit log row can attribute
        # the update to the admin who clicked Save.
        result = await service.update_appointment(
            appointment_id,
            data,
            actor_id=current_user.id,
        )
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
    description=(
        "Cancel an appointment. Record is preserved but marked cancelled. "
        "Pass ``notify_customer=false`` to suppress the cancellation SMS "
        "(admin opt-out)."
    ),
)
async def cancel_appointment(
    appointment_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    notify_customer: bool = True,
) -> None:
    """Cancel an appointment.

    Validates: Admin Dashboard Requirement 1.2, CR-2 (notify_customer opt-out)
    """
    _endpoints.log_started(
        "cancel_appointment",
        appointment_id=str(appointment_id),
        notify_customer=notify_customer,
    )

    try:
        await service.cancel_appointment(
            appointment_id,
            notify_customer=notify_customer,
            actor_id=current_user.id,
        )
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


# =============================================================================
# POST /api/v1/appointments/{id}/send-confirmation - Draft → Scheduled (Req 8)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/send-confirmation",
    response_model=SendConfirmationResponse,
    summary="Send confirmation SMS for a draft appointment",
    description=(
        "Sends Y/R/C confirmation SMS and transitions appointment from DRAFT to SCHEDULED. "
        "Returns 422 if appointment is not in DRAFT status."
    ),
)
async def send_confirmation(
    appointment_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_full_appointment_service)],
) -> SendConfirmationResponse:
    """Send confirmation SMS for a draft appointment.

    Validates: Req 8.4, 8.12
    """
    _endpoints.log_started("send_confirmation", appointment_id=str(appointment_id))

    try:
        result = await service.send_confirmation(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("send_confirmation", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except InvalidStatusTransitionError as e:
        _endpoints.log_rejected(
            "send_confirmation",
            reason="not_draft",
            current=e.current_status.value,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Appointment must be in DRAFT status to send confirmation. "
            f"Current status: {e.current_status.value}",
        ) from e

    _endpoints.log_completed("send_confirmation", appointment_id=str(appointment_id))
    return SendConfirmationResponse(
        appointment_id=result.id,
        status=result.status,
        sms_sent=True,
    )


# =============================================================================
# PATCH /api/v1/appointments/{id}/reschedule - Reschedule via drag-drop (Req 24)
# =============================================================================


@router.patch(  # type: ignore[untyped-decorator]
    "/{appointment_id}/reschedule",
    response_model=AppointmentResponse,
    summary="Reschedule appointment via drag-drop",
    description=(
        "Reschedule an appointment to a new date/time. Validates no staff conflict."
    ),
)
async def reschedule_appointment(
    appointment_id: UUID,
    data: RescheduleRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentResponse:
    """Reschedule an appointment via drag-drop.

    Validates: Requirement 24.2
    """
    _endpoints.log_started(
        "reschedule_appointment",
        appointment_id=str(appointment_id),
        new_date=str(data.new_date),
    )

    from datetime import time as _time  # noqa: PLC0415

    new_start = _time.fromisoformat(data.new_start)
    new_end = _time.fromisoformat(data.new_end)

    try:
        result = await service.reschedule(
            appointment_id=appointment_id,
            new_date=data.new_date,
            new_start=new_start,
            new_end=new_end,
        )
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("reschedule_appointment", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except StaffConflictError as e:
        _endpoints.log_rejected("reschedule_appointment", reason="staff_conflict")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    _endpoints.log_completed(
        "reschedule_appointment",
        appointment_id=str(appointment_id),
    )
    return AppointmentResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# POST /api/v1/appointments/{id}/reschedule-from-request -
#   Admin resolves a customer R-request, triggers new Y/R/C cycle (H-6)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/reschedule-from-request",
    response_model=AppointmentResponse,
    summary="Reschedule from a customer R-request (re-fire Y/R/C SMS)",
    description=(
        "Admin picks a new date from the Reschedule Requests queue. "
        "Moves the appointment to the new slot, resets status to SCHEDULED, "
        "and sends SMS #1 (Y/R/C prompt) so the customer must re-confirm. "
        "Replaces the drag-drop one-way 'We moved your appointment to …' SMS "
        "on the customer-requested-reschedule path only."
    ),
)
async def reschedule_from_request(
    appointment_id: UUID,
    data: RescheduleFromRequest,
    _current_user: ManagerOrAdminUser,
    service: Annotated[
        AppointmentService,
        Depends(get_full_appointment_service),
    ],
) -> AppointmentResponse:
    """Reschedule an appointment in response to a customer R-request.

    Validates: bughunt H-6
    """
    _endpoints.log_started(
        "reschedule_from_request",
        appointment_id=str(appointment_id),
        new_scheduled_at=data.new_scheduled_at.isoformat(),
    )

    try:
        result = await service.reschedule_for_request(
            appointment_id=appointment_id,
            new_scheduled_at=data.new_scheduled_at,
            actor_id=_current_user.id,
        )
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("reschedule_from_request", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except InvalidStatusTransitionError as e:
        _endpoints.log_rejected(
            "reschedule_from_request",
            reason="invalid_state",
            current=e.current_status.value,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Appointment cannot be rescheduled-from-request in its current "
                f"state. Current status: {e.current_status.value}"
            ),
        ) from e
    except Exception as exc:
        _endpoints.log_failed(
            "reschedule_from_request",
            appointment_id=str(appointment_id),
            error=exc,
        )
        raise

    _endpoints.log_completed(
        "reschedule_from_request",
        appointment_id=str(appointment_id),
    )
    return AppointmentResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# POST /api/v1/appointments/{id}/collect-payment - On-site payment (Req 30)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/collect-payment",
    response_model=PaymentResult,
    summary="Collect on-site payment",
    description="Collect payment on-site for an appointment. Creates/updates invoice.",
)
async def collect_payment(
    appointment_id: UUID,
    data: PaymentCollectionRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_full_appointment_service)],
) -> PaymentResult:
    """Collect payment on-site for an appointment.

    Validates: Requirement 30.5
    """
    _endpoints.log_started(
        "collect_payment",
        appointment_id=str(appointment_id),
        payment_method=data.payment_method.value,
        amount=str(data.amount),
    )

    try:
        result = await service.collect_payment(appointment_id, data)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("collect_payment", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except JobNotFoundError as e:
        _endpoints.log_rejected("collect_payment", reason="job_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e

    _endpoints.log_completed(
        "collect_payment",
        appointment_id=str(appointment_id),
        invoice_id=str(result.invoice_id),
    )
    return result


# =============================================================================
# POST /api/v1/appointments/{id}/create-invoice - On-site invoice (Req 31)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/create-invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create invoice from appointment",
    description="Create an invoice pre-populated from appointment/job/customer data.",
)
async def create_invoice_from_appointment(
    appointment_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_full_appointment_service)],
) -> InvoiceResponse:
    """Create an invoice from an appointment.

    Validates: Requirement 31.4
    """
    _endpoints.log_started(
        "create_invoice_from_appointment",
        appointment_id=str(appointment_id),
    )

    try:
        invoice = await service.create_invoice_from_appointment(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected(
            "create_invoice_from_appointment",
            reason="not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except JobNotFoundError as e:
        _endpoints.log_rejected(
            "create_invoice_from_appointment",
            reason="job_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e

    _endpoints.log_completed(
        "create_invoice_from_appointment",
        appointment_id=str(appointment_id),
        invoice_id=str(invoice.id),
    )
    return InvoiceResponse.model_validate(invoice)  # type: ignore[no-any-return]


# =============================================================================
# POST /api/v1/appointments/{id}/create-estimate - On-site estimate (Req 32)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/create-estimate",
    status_code=status.HTTP_201_CREATED,
    summary="Create estimate from appointment",
    description=(
        "Create an estimate from an appointment using templates and price lists."
    ),
)
async def create_estimate_from_appointment(
    appointment_id: UUID,
    data: EstimateCreate,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_full_appointment_service)],
) -> EstimateResponse:
    """Create an estimate from an appointment.

    Validates: Requirement 32.6
    """
    _endpoints.log_started(
        "create_estimate_from_appointment",
        appointment_id=str(appointment_id),
    )

    try:
        estimate = await service.create_estimate_from_appointment(
            appointment_id,
            data,
        )
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected(
            "create_estimate_from_appointment",
            reason="not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except JobNotFoundError as e:
        _endpoints.log_rejected(
            "create_estimate_from_appointment",
            reason="job_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e

    _endpoints.log_completed(
        "create_estimate_from_appointment",
        appointment_id=str(appointment_id),
    )
    return EstimateResponse.model_validate(estimate)  # type: ignore[no-any-return]


# =============================================================================
# POST /api/v1/appointments/{id}/photos - Staff photo upload (Req 33)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/photos",
    status_code=status.HTTP_201_CREATED,
    summary="Upload photos from appointment",
    description=(
        "Upload photos during an appointment, linked to both appointment and customer."
    ),
)
async def upload_appointment_photos(
    appointment_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File(description="Photo file to upload")],
    notes: Annotated[
        str | None,
        Form(description="Optional notes to save with the photo"),
    ] = None,
) -> dict[str, object]:
    """Upload photos from an appointment context.

    Validates: Requirement 33.4
    """
    _endpoints.log_started(
        "upload_appointment_photos",
        appointment_id=str(appointment_id),
    )

    # Verify appointment exists
    try:
        appointment = await service.get_appointment(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("upload_appointment_photos", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e

    # Read file data
    file_data = await file.read()
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty file",
        )

    # Upload via PhotoService
    photo_service = PhotoService()
    try:
        upload_result = photo_service.upload_file(
            data=file_data,
            file_name=file.filename or "photo",
            context=UploadContext.CUSTOMER_PHOTO,
        )
    except ValueError as e:
        # bughunt M-16: size cap exceeded → 413 Payload Too Large.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        ) from e
    except TypeError as e:
        # bughunt M-16: MIME not in allow-list → 415 Unsupported Media Type.
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        ) from e

    # Get customer_id from the job
    customer_id = None  # Will be resolved below

    from grins_platform.models.customer_photo import CustomerPhoto  # noqa: PLC0415

    # Look up the job to get customer_id
    job_obj = await service.job_repository.get_by_id(appointment.job_id)
    if job_obj:
        customer_id = job_obj.customer_id

        photo = CustomerPhoto(
            customer_id=customer_id,
            file_key=upload_result.file_key,
            file_name=upload_result.file_name,
            file_size=upload_result.file_size,
            content_type=upload_result.content_type,
            caption=notes,
            uploaded_by=current_user.id,
            appointment_id=appointment_id,
        )
        session.add(photo)
        await session.commit()
        await session.refresh(photo)

    # Also save notes to appointment if provided
    if notes:
        await service.add_notes_and_photos(
            appointment_id=appointment_id,
            notes=notes,
        )

    download_url = photo_service.generate_presigned_url(upload_result.file_key)

    _endpoints.log_completed(
        "upload_appointment_photos",
        appointment_id=str(appointment_id),
        file_key=upload_result.file_key,
    )

    return {
        "file_key": upload_result.file_key,
        "file_name": upload_result.file_name,
        "file_size": upload_result.file_size,
        "content_type": upload_result.content_type,
        "download_url": download_url,
        "appointment_id": str(appointment_id),
    }


# =============================================================================
# POST /api/v1/appointments/{id}/request-review - Google review SMS (Req 34)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{appointment_id}/request-review",
    response_model=ReviewRequestResult,
    summary="Request Google review via SMS",
    description="Send a Google review request to the customer after job completion.",
)
async def request_google_review(
    appointment_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> ReviewRequestResult:
    """Request a Google review from the customer.

    Validates: Requirement 34.3
    """
    _endpoints.log_started(
        "request_google_review",
        appointment_id=str(appointment_id),
    )

    try:
        result = await service.request_google_review(appointment_id)
    except AppointmentNotFoundError as e:
        _endpoints.log_rejected("request_google_review", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment not found: {e.appointment_id}",
        ) from e
    except ReviewAlreadyRequestedError as e:
        _endpoints.log_rejected("request_google_review", reason="dedup_30_day")
        # E-BUG-F: structured detail so the UI can render
        # "Already sent within last 30 days (sent {date})"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REVIEW_ALREADY_SENT",
                "message": str(e),
                "last_sent_at": e.last_requested_at,
            },
        ) from e

    _endpoints.log_completed(
        "request_google_review",
        appointment_id=str(appointment_id),
        sent=result.sent,
    )
    return result
