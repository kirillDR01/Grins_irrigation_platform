"""
Appointment service for business logic operations.

This module provides the AppointmentService class for all appointment-related
business operations including scheduling, status transitions, payment collection,
invoice/estimate creation, notes/photos, review requests, lead time calculation,
and staff time analytics.

Validates: Admin Dashboard Requirements 1.1-1.5
Validates: CRM Gap Closure Req 24, 25, 29, 30, 31, 32, 33, 34, 35, 36, 37
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from grins_platform.exceptions import (
    AppointmentNotFoundError,
    AppointmentOnFinishedJobError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    PaymentRequiredError,
    ReviewAlreadyRequestedError,
    StaffConflictError,
    StaffNotFoundError,
)
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.appointment import VALID_APPOINTMENT_TRANSITIONS
from grins_platform.models.enums import (
    AppointmentStatus,
    InvoiceStatus,
    JobStatus,
)
from grins_platform.schemas.appointment_ops import (
    LeadTimeResult,
    PaymentCollectionRequest,
    PaymentResult,
    ReviewRequestResult,
    StaffTimeEntry,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.appointment import Appointment
    from grins_platform.models.invoice import Invoice
    from grins_platform.models.job import Job
    from grins_platform.repositories.appointment_repository import (
        AppointmentRepository,
    )
    from grins_platform.repositories.invoice_repository import InvoiceRepository
    from grins_platform.repositories.job_repository import JobRepository
    from grins_platform.repositories.staff_repository import StaffRepository
    from grins_platform.schemas.appointment import (
        AppointmentCreate,
        AppointmentUpdate,
    )
    from grins_platform.schemas.appointment_ops import DateRange
    from grins_platform.schemas.estimate import EstimateCreate
    from grins_platform.services.estimate_service import EstimateService


# Review dedup window in days
_REVIEW_DEDUP_DAYS = 30

# Terminal appointment statuses (not counted as "active")
_TERMINAL_STATUSES: set[str] = {
    AppointmentStatus.COMPLETED.value,
    AppointmentStatus.CANCELLED.value,
    AppointmentStatus.NO_SHOW.value,
}


async def count_active_appointments(
    session: AsyncSession,
    job_id: UUID,
    *,
    exclude: UUID | None = None,
) -> int:
    """Count non-terminal appointments for a job, optionally excluding one.

    Args:
        session: Active database session.
        job_id: The job whose appointments to count.
        exclude: Optional appointment ID to exclude from the count.

    Returns:
        Number of active (non-terminal) appointments.

    Validates: Requirements 2.3, 2.4
    """
    from sqlalchemy import (
        func as sa_func,
        select,
    )

    from grins_platform.models.appointment import Appointment  # noqa: PLC0415

    stmt = (
        select(sa_func.count())
        .select_from(Appointment)
        .where(
            Appointment.job_id == job_id,
            Appointment.status.notin_(_TERMINAL_STATUSES),
        )
    )
    if exclude is not None:
        stmt = stmt.where(Appointment.id != exclude)
    result = await session.execute(stmt)
    return result.scalar_one()


async def clear_on_site_data(
    session: AsyncSession,
    appointment: Appointment,
    job: Job | None = None,
) -> None:
    """Reset on-site operation fields after cancellation.

    Clears timestamps on the appointment, deletes On My Way SMS records so a
    replacement appointment can send fresh SMS, resets the payment-collected
    flag, and — when no other active appointments remain — clears the parent
    job's timestamps as well.

    Args:
        session: Active database session.
        appointment: The appointment being cancelled.
        job: Optional parent job; when supplied the function checks whether
             job-level timestamps should also be cleared.

    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
    """
    from sqlalchemy import delete  # noqa: PLC0415

    from grins_platform.models.enums import MessageType  # noqa: PLC0415
    from grins_platform.models.sent_message import SentMessage  # noqa: PLC0415

    logger = get_logger(__name__)
    logger.info(
        "appointment.clear_on_site_data.started",
        appointment_id=str(appointment.id),
    )

    # 1. Clear appointment on-site timestamps
    appointment.en_route_at = None
    appointment.arrived_at = None
    appointment.completed_at = None

    # 2. Delete On My Way SMS records so replacement can send fresh SMS
    await session.execute(
        delete(SentMessage).where(
            SentMessage.appointment_id == appointment.id,
            SentMessage.message_type == MessageType.ON_MY_WAY.value,
        )
    )

    # 3. Clear payment/invoice warning override flag
    if job is not None:
        job.payment_collected_on_site = False

    # 4. If job provided and no other active appointments, clear job timestamps
    if job is not None:
        active_count = await count_active_appointments(
            session, job.id, exclude=appointment.id
        )
        if active_count == 0:
            job.on_my_way_at = None
            job.started_at = None
            job.completed_at = None
            # Revert job from SCHEDULED to TO_BE_SCHEDULED (Req 5.4)
            from grins_platform.models.enums import JobStatus  # noqa: PLC0415

            if job.status == JobStatus.SCHEDULED.value:
                job.status = JobStatus.TO_BE_SCHEDULED.value
                logger.info(
                    "appointment.clear_on_site_data.job_reverted_to_be_scheduled",
                    job_id=str(job.id),
                )

    await session.flush()

    logger.info(
        "appointment.clear_on_site_data.completed",
        appointment_id=str(appointment.id),
    )


class AppointmentService(LoggerMixin):
    """Service for appointment management operations.

    This class handles all business logic for appointments including
    scheduling, status transitions, payment collection, invoice/estimate
    creation, notes/photos, review requests, lead time calculation,
    and staff time analytics.

    Attributes:
        appointment_repository: AppointmentRepository for database operations
        job_repository: JobRepository for job validation
        staff_repository: StaffRepository for staff validation
        invoice_repository: Optional InvoiceRepository for payment operations
        estimate_service: Optional EstimateService for estimate delegation

    Validates: Admin Dashboard Requirements 1.1-1.5
    Validates: CRM Gap Closure Req 24, 25, 29, 30, 31, 32, 33, 34, 35, 36, 37
    """

    DOMAIN = "appointment"

    def __init__(
        self,
        appointment_repository: AppointmentRepository,
        job_repository: JobRepository,
        staff_repository: StaffRepository,
        invoice_repository: InvoiceRepository | None = None,
        estimate_service: EstimateService | None = None,
        google_review_url: str = "",
    ) -> None:
        """Initialize service with repositories.

        Args:
            appointment_repository: AppointmentRepository for database operations
            job_repository: JobRepository for job validation
            staff_repository: StaffRepository for staff validation
            invoice_repository: Optional InvoiceRepository for payment ops
            estimate_service: Optional EstimateService for estimate delegation
            google_review_url: Google Business review URL
        """
        super().__init__()
        self.appointment_repository = appointment_repository
        self.job_repository = job_repository
        self.staff_repository = staff_repository
        self.invoice_repository = invoice_repository
        self.estimate_service = estimate_service
        self.google_review_url = google_review_url

    # =========================================================================
    # Original CRUD Methods (Admin Dashboard)
    # =========================================================================

    async def create_appointment(self, data: AppointmentCreate) -> Appointment:
        """Create a new appointment.

        Args:
            data: Appointment creation data

        Returns:
            Created Appointment instance

        Raises:
            JobNotFoundError: If job not found
            StaffNotFoundError: If staff not found

        Validates: Admin Dashboard Requirement 1.1
        """
        self.log_started(
            "create_appointment",
            job_id=str(data.job_id),
            staff_id=str(data.staff_id),
            scheduled_date=str(data.scheduled_date),
        )

        # Validate job exists
        job = await self.job_repository.get_by_id(data.job_id)
        if not job:
            self.log_rejected("create_appointment", reason="job_not_found")
            raise JobNotFoundError(data.job_id)

        # bughunt H-4: reject appointments on finished or cancelled jobs.
        # Previously silently allowed — admins could accidentally schedule
        # a completed job and the draft-mode flow would happily proceed.
        if job.status in (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value):
            self.log_rejected(
                "create_appointment",
                reason="job_finished",
                job_status=job.status,
            )
            raise AppointmentOnFinishedJobError(data.job_id, job.status)

        # Validate staff exists
        staff = await self.staff_repository.get_by_id(data.staff_id)
        if not staff:
            self.log_rejected("create_appointment", reason="staff_not_found")
            raise StaffNotFoundError(data.staff_id)

        # bughunt M-6: honour caller-provided status for bulk-import paths,
        # defaulting to DRAFT for the ordinary UX flow. Guarded against
        # MagicMock-style test payloads that auto-generate a ``status``
        # attribute — we only accept real AppointmentStatus / str values.
        requested_status = getattr(data, "status", None)
        if isinstance(requested_status, AppointmentStatus):
            resolved_status = requested_status.value
        elif isinstance(requested_status, str):
            resolved_status = requested_status
        else:
            resolved_status = AppointmentStatus.DRAFT.value

        # Create the appointment
        appointment = await self.appointment_repository.create(
            job_id=data.job_id,
            staff_id=data.staff_id,
            scheduled_date=data.scheduled_date,
            time_window_start=data.time_window_start,
            time_window_end=data.time_window_end,
            status=resolved_status,
            notes=data.notes,
        )

        # Auto-transition job to SCHEDULED if currently TO_BE_SCHEDULED (Req 5.3)
        if job.status == JobStatus.TO_BE_SCHEDULED.value:
            job.status = JobStatus.SCHEDULED.value
            session = self.appointment_repository.session
            await session.flush()
            self.log_completed(
                "auto_transition_job_scheduled",
                job_id=str(data.job_id),
            )

        self.log_completed(
            "create_appointment",
            appointment_id=str(appointment.id),
        )
        return appointment

    async def get_appointment(
        self,
        appointment_id: UUID,
        include_relationships: bool = False,
    ) -> Appointment:
        """Get appointment by ID.

        Args:
            appointment_id: UUID of the appointment
            include_relationships: Whether to load related entities

        Returns:
            Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found

        Validates: Admin Dashboard Requirement 1.3
        """
        self.log_started("get_appointment", appointment_id=str(appointment_id))

        appointment = await self.appointment_repository.get_by_id(
            appointment_id,
            include_relationships=include_relationships,
        )
        if not appointment:
            self.log_rejected("get_appointment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        self.log_completed("get_appointment", appointment_id=str(appointment_id))
        return appointment

    async def update_appointment(
        self,
        appointment_id: UUID,
        data: AppointmentUpdate,
    ) -> Appointment:
        """Update appointment details.

        Args:
            appointment_id: UUID of the appointment to update
            data: Update data

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            InvalidStatusTransitionError: If status transition is invalid

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("update_appointment", appointment_id=str(appointment_id))

        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("update_appointment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        update_data = data.model_dump(exclude_unset=True)

        # If rescheduling a cancelled appointment, reactivate it
        is_rescheduling = (
            "scheduled_date" in update_data
            or "time_window_start" in update_data
            or "time_window_end" in update_data
        )
        if (
            appointment.status == AppointmentStatus.CANCELLED.value
            and is_rescheduling
            and "status" not in update_data
        ):
            update_data["status"] = AppointmentStatus.SCHEDULED.value
            self.log_started(
                "reactivate_cancelled_appointment",
                appointment_id=str(appointment_id),
            )

        # Validate status transition if status is being updated
        if "status" in update_data and update_data["status"] is not None:
            new_status = update_data["status"]
            if isinstance(new_status, AppointmentStatus):
                new_status_value = new_status.value
            else:
                new_status_value = new_status

            if not appointment.can_transition_to(new_status_value):
                self.log_rejected(
                    "update_appointment",
                    reason="invalid_transition",
                    current=appointment.status,
                    requested=new_status_value,
                )
                raise InvalidStatusTransitionError(
                    AppointmentStatus(appointment.status),
                    AppointmentStatus(new_status_value),
                )
            update_data["status"] = new_status_value

        # Capture the pre-update status *before* the UPDATE runs so we
        # can distinguish reactivation (CANCELLED → SCHEDULED via reschedule)
        # from regular reschedules (SCHEDULED/CONFIRMED → SCHEDULED).
        pre_update_status = appointment.status

        updated = await self.appointment_repository.update(appointment_id, update_data)

        # Req 8.8, 8.9: Post-send reschedule detection.
        # Fire reschedule SMS when a non-DRAFT appointment's date/time
        # changed — including reactivation from CANCELLED (bughunt H-8),
        # since the customer was told "cancelled" and now needs to know
        # it's back on.
        if is_rescheduling and pre_update_status in (
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
            AppointmentStatus.CANCELLED.value,
        ):
            session = self.appointment_repository.session
            try:
                await self._send_reschedule_sms(session, updated)  # type: ignore[arg-type]
            except Exception:
                self.log_failed(
                    "reschedule_sms",
                    appointment_id=str(appointment_id),
                )
            # Reset status to SCHEDULED (unconfirmed)
            if updated and updated.status != AppointmentStatus.SCHEDULED.value:  # type: ignore[union-attr]
                await self.appointment_repository.update(
                    appointment_id,
                    {"status": AppointmentStatus.SCHEDULED.value},
                )

        self.log_completed("update_appointment", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    async def cancel_appointment(
        self,
        appointment_id: UUID,
        *,
        notify_customer: bool = True,
        actor_id: UUID | None = None,
    ) -> Appointment:
        """Cancel an appointment.

        Args:
            appointment_id: UUID of the appointment to cancel.
            notify_customer: If True (default), send the cancellation SMS for
                customer-visible states (SCHEDULED/CONFIRMED/EN_ROUTE/IN_PROGRESS).
                If False, skip the SMS — the admin opted out via the UI.
            actor_id: Staff/admin performing the cancellation (for audit log).

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            InvalidStatusTransitionError: If appointment cannot be cancelled

        Validates: Admin Dashboard Requirement 1.2, CR-2 (Req 8.10, 8.11, 15)
        """
        self.log_started("cancel_appointment", appointment_id=str(appointment_id))

        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("cancel_appointment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        if not appointment.can_transition_to(AppointmentStatus.CANCELLED.value):
            self.log_rejected(
                "cancel_appointment",
                reason="invalid_transition",
                current=appointment.status,
            )
            raise InvalidStatusTransitionError(
                AppointmentStatus(appointment.status),
                AppointmentStatus.CANCELLED,
            )

        # Capture the original status BEFORE the update. SQLAlchemy's identity
        # map refreshes the in-memory ``appointment`` when we UPDATE ... RETURNING,
        # so reading ``appointment.status`` after that point would always be
        # ``cancelled`` — which is how the original SMS-gating branch became
        # dead code (CR-2). Snapshot here.
        pre_cancel_status = appointment.status

        updated = await self.appointment_repository.update_status(
            appointment_id,
            AppointmentStatus.CANCELLED,
        )

        # Clear on-site data after cancellation (Req 2.1, 2.2, 2.3)
        session = self.appointment_repository.session
        job = await self.job_repository.get_by_id(appointment.job_id)
        await clear_on_site_data(session, appointment, job=job)

        # Req 8.10, 8.11: Cancellation SMS based on pre-cancel state.
        # DRAFT → no SMS (customer was never notified). Admin can still opt
        # out via ``notify_customer=False`` (dialog "Cancel without text").
        sms_sent = False
        customer_visible = pre_cancel_status in (
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
            AppointmentStatus.EN_ROUTE.value,
            AppointmentStatus.IN_PROGRESS.value,
        )
        if notify_customer and customer_visible:
            try:
                await self._send_cancellation_sms(session, appointment)
                sms_sent = True
            except Exception:
                self.log_failed(
                    "cancellation_sms",
                    appointment_id=str(appointment_id),
                )

        await self._record_cancellation_audit(
            session,
            appointment_id=appointment_id,
            pre_cancel_status=pre_cancel_status,
            notify_customer=notify_customer,
            sms_sent=sms_sent,
            actor_id=actor_id,
        )

        self.log_completed(
            "cancel_appointment",
            appointment_id=str(appointment_id),
            notify_customer=notify_customer,
            sms_sent=sms_sent,
        )
        return updated  # type: ignore[return-value]

    async def _record_cancellation_audit(
        self,
        session: AsyncSession,
        *,
        appointment_id: UUID,
        pre_cancel_status: str,
        notify_customer: bool,
        sms_sent: bool,
        actor_id: UUID | None,
    ) -> None:
        """Write an AuditLog row recording the admin's cancel choice."""
        from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
            AuditLogRepository,
        )

        try:
            repo = AuditLogRepository(session)
            await repo.create(
                action="appointment.cancel",
                resource_type="appointment",
                resource_id=appointment_id,
                actor_id=actor_id,
                details={
                    "pre_cancel_status": pre_cancel_status,
                    "notify_customer": notify_customer,
                    "sms_sent": sms_sent,
                },
            )
        except Exception:
            # Audit write failure must never block the cancellation itself.
            self.log_failed(
                "cancellation_audit",
                appointment_id=str(appointment_id),
            )

    async def list_appointments(
        self,
        page: int = 1,
        page_size: int = 20,
        status: AppointmentStatus | None = None,
        staff_id: UUID | None = None,
        job_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str = "scheduled_date",
        sort_order: str = "asc",
        include_relationships: bool = True,
    ) -> tuple[list[Appointment], int]:
        """List appointments with filtering.

        Validates: Admin Dashboard Requirement 1.4
        """
        self.log_started("list_appointments", page=page, page_size=page_size)

        appointments, total = await self.appointment_repository.list_with_filters(
            page=page,
            page_size=page_size,
            status=status,
            staff_id=staff_id,
            job_id=job_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            include_relationships=include_relationships,
        )

        self.log_completed("list_appointments", count=len(appointments), total=total)
        return appointments, total

    async def get_daily_schedule(
        self,
        schedule_date: date,
        include_relationships: bool = False,
    ) -> tuple[list[Appointment], int]:
        """Get all appointments for a specific date.

        Validates: Admin Dashboard Requirement 1.5
        """
        self.log_started("get_daily_schedule", date=str(schedule_date))

        appointments = await self.appointment_repository.get_daily_schedule(
            schedule_date,
            include_relationships=include_relationships,
        )

        self.log_completed("get_daily_schedule", count=len(appointments))
        return appointments, len(appointments)

    async def get_staff_daily_schedule(
        self,
        staff_id: UUID,
        schedule_date: date,
        include_relationships: bool = False,
    ) -> tuple[list[Appointment], int, int]:
        """Get all appointments for a specific staff member on a specific date.

        Validates: Admin Dashboard Requirement 1.5
        """
        self.log_started(
            "get_staff_daily_schedule",
            staff_id=str(staff_id),
            date=str(schedule_date),
        )

        staff = await self.staff_repository.get_by_id(staff_id)
        if not staff:
            self.log_rejected("get_staff_daily_schedule", reason="staff_not_found")
            raise StaffNotFoundError(staff_id)

        appointments = await self.appointment_repository.get_staff_daily_schedule(
            staff_id,
            schedule_date,
            include_relationships=include_relationships,
        )

        total_minutes = sum(apt.get_duration_minutes() for apt in appointments)

        self.log_completed(
            "get_staff_daily_schedule",
            count=len(appointments),
            total_minutes=total_minutes,
        )
        return appointments, len(appointments), total_minutes

    async def get_weekly_schedule(
        self,
        start_date: date,
        include_relationships: bool = False,
    ) -> tuple[dict[date, list[Appointment]], int]:
        """Get all appointments for a week starting from start_date.

        Validates: Admin Dashboard Requirement 1.5
        """
        self.log_started("get_weekly_schedule", start_date=str(start_date))

        schedule = await self.appointment_repository.get_weekly_schedule(
            start_date,
            include_relationships=include_relationships,
        )

        total = sum(len(appointments) for appointments in schedule.values())

        self.log_completed("get_weekly_schedule", total_appointments=total)
        return schedule, total

    async def mark_arrived(self, appointment_id: UUID) -> Appointment:
        """Mark an appointment as arrived (in progress).

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("mark_arrived", appointment_id=str(appointment_id))

        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("mark_arrived", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        if not appointment.can_transition_to(AppointmentStatus.IN_PROGRESS.value):
            self.log_rejected(
                "mark_arrived",
                reason="invalid_transition",
                current=appointment.status,
            )
            raise InvalidStatusTransitionError(
                AppointmentStatus(appointment.status),
                AppointmentStatus.IN_PROGRESS,
            )

        updated = await self.appointment_repository.update_status(
            appointment_id,
            AppointmentStatus.IN_PROGRESS,
            arrived_at=datetime.now(tz=timezone.utc),
        )

        self.log_completed("mark_arrived", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    async def mark_completed(self, appointment_id: UUID) -> Appointment:
        """Mark an appointment as completed.

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("mark_completed", appointment_id=str(appointment_id))

        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("mark_completed", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        if not appointment.can_transition_to(AppointmentStatus.COMPLETED.value):
            self.log_rejected(
                "mark_completed",
                reason="invalid_transition",
                current=appointment.status,
            )
            raise InvalidStatusTransitionError(
                AppointmentStatus(appointment.status),
                AppointmentStatus.COMPLETED,
            )

        updated = await self.appointment_repository.update_status(
            appointment_id,
            AppointmentStatus.COMPLETED,
            completed_at=datetime.now(tz=timezone.utc),
        )

        self.log_completed("mark_completed", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    async def confirm_appointment(self, appointment_id: UUID) -> Appointment:
        """Confirm an appointment.

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("confirm_appointment", appointment_id=str(appointment_id))

        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("confirm_appointment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        if not appointment.can_transition_to(AppointmentStatus.CONFIRMED.value):
            self.log_rejected(
                "confirm_appointment",
                reason="invalid_transition",
                current=appointment.status,
            )
            raise InvalidStatusTransitionError(
                AppointmentStatus(appointment.status),
                AppointmentStatus.CONFIRMED,
            )

        updated = await self.appointment_repository.update_status(
            appointment_id,
            AppointmentStatus.CONFIRMED,
        )

        self.log_completed("confirm_appointment", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    # =========================================================================
    # CRM Gap Closure Enhancements
    # =========================================================================

    async def reschedule(
        self,
        appointment_id: UUID,
        new_date: date,
        new_start: time,
        new_end: time,
    ) -> Appointment:
        """Reschedule an appointment via drag-drop.

        Validates no staff conflict before updating the time slot.

        Args:
            appointment_id: UUID of the appointment to reschedule
            new_date: New scheduled date
            new_start: New start time
            new_end: New end time

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            StaffConflictError: If overlapping appointment exists

        Validates: CRM Gap Closure Req 24.2, 24.5
        """
        self.log_started(
            "reschedule",
            appointment_id=str(appointment_id),
            new_date=str(new_date),
            new_start=str(new_start),
            new_end=str(new_end),
        )

        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("reschedule", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        # Check for staff conflicts on the new date/time
        conflict = await self._check_staff_conflict(
            staff_id=appointment.staff_id,
            scheduled_date=new_date,
            start_time=new_start,
            end_time=new_end,
            exclude_appointment_id=appointment_id,
        )
        if conflict is not None:
            self.log_rejected(
                "reschedule",
                reason="staff_conflict",
                conflicting_id=str(conflict.id),
            )
            raise StaffConflictError(appointment.staff_id, conflict.id)

        updated = await self.appointment_repository.update(
            appointment_id,
            {
                "scheduled_date": new_date,
                "time_window_start": new_start,
                "time_window_end": new_end,
            },
        )

        # Req 8.8, 8.9: Post-send reschedule detection for drag-drop
        if appointment.status in (
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
        ):
            session = self.appointment_repository.session
            try:
                await self._send_reschedule_sms(session, updated)  # type: ignore[arg-type]
            except Exception:
                self.log_failed(
                    "reschedule_sms",
                    appointment_id=str(appointment_id),
                )
            # Reset status to SCHEDULED (unconfirmed)
            if updated and updated.status != AppointmentStatus.SCHEDULED.value:  # type: ignore[union-attr]
                await self.appointment_repository.update(
                    appointment_id,
                    {"status": AppointmentStatus.SCHEDULED.value},
                )

        self.log_completed("reschedule", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    # =========================================================================
    # Draft Mode Methods (Req 8)
    # =========================================================================

    async def send_confirmation(self, appointment_id: UUID) -> Appointment:
        """Send confirmation SMS and transition DRAFT → SCHEDULED.

        Args:
            appointment_id: UUID of the draft appointment

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            InvalidStatusTransitionError: If appointment is not in DRAFT status

        Validates: Req 8.4, 8.12
        """
        self.log_started("send_confirmation", appointment_id=str(appointment_id))

        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("send_confirmation", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        if appointment.status != AppointmentStatus.DRAFT.value:
            self.log_rejected(
                "send_confirmation",
                reason="not_draft",
                current_status=appointment.status,
            )
            raise InvalidStatusTransitionError(
                AppointmentStatus(appointment.status),
                AppointmentStatus.SCHEDULED,
            )

        # Send Y/R/C confirmation SMS
        session = self.appointment_repository.session
        await self._send_confirmation_sms(session, appointment)

        # Transition DRAFT → SCHEDULED
        updated = await self.appointment_repository.update(
            appointment_id,
            {"status": AppointmentStatus.SCHEDULED.value},
        )

        self.log_completed("send_confirmation", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    async def bulk_send_confirmations(
        self,
        appointment_ids: list[UUID] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, int]:
        """Send confirmation SMS for multiple DRAFT appointments.

        Args:
            appointment_ids: Specific appointment IDs to confirm
            date_from: Start date for date range filter
            date_to: End date for date range filter

        Returns:
            Dict with sent_count, failed_count, total_draft

        Validates: Req 8.6, 8.13
        """
        self.log_started(
            "bulk_send_confirmations",
            ids_count=len(appointment_ids) if appointment_ids else 0,
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to) if date_to else None,
        )

        session = self.appointment_repository.session

        # Build query for DRAFT appointments
        from sqlalchemy import select  # noqa: PLC0415

        from grins_platform.models.appointment import (
            Appointment as AppointmentModel,
        )

        stmt = select(AppointmentModel).where(
            AppointmentModel.status == AppointmentStatus.DRAFT.value
        )

        if appointment_ids:
            stmt = stmt.where(AppointmentModel.id.in_(appointment_ids))
        if date_from:
            stmt = stmt.where(AppointmentModel.scheduled_date >= date_from)
        if date_to:
            stmt = stmt.where(AppointmentModel.scheduled_date <= date_to)

        result = await session.execute(stmt)
        draft_appointments = list(result.scalars().all())
        total_draft = len(draft_appointments)

        sent_count = 0
        failed_count = 0

        for appt in draft_appointments:
            try:
                await self._send_confirmation_sms(session, appt)
                appt.status = AppointmentStatus.SCHEDULED.value
                sent_count += 1
            except Exception:
                self.log_failed(
                    "bulk_send_confirmation_item",
                    appointment_id=str(appt.id),
                )
                failed_count += 1

        await session.flush()

        self.log_completed(
            "bulk_send_confirmations",
            sent_count=sent_count,
            failed_count=failed_count,
            total_draft=total_draft,
        )
        return {
            "sent_count": sent_count,
            "failed_count": failed_count,
            "total_draft": total_draft,
        }

    async def _send_confirmation_sms(
        self,
        session: AsyncSession,
        appointment: Appointment,
    ) -> None:
        """Send Y/R/C confirmation SMS for an appointment.

        Validates: Req 8.4; bughunt H-3 (weekday date format), L-4
        (include service type).
        """
        from grins_platform.models.customer import Customer  # noqa: PLC0415
        from grins_platform.models.job import Job  # noqa: PLC0415
        from grins_platform.schemas.ai import MessageType  # noqa: PLC0415
        from grins_platform.services.sms.factory import (  # noqa: PLC0415
            get_sms_provider,
        )
        from grins_platform.services.sms.formatters import (  # noqa: PLC0415
            format_job_type_display,
            format_sms_date,
            format_sms_time_window,
        )
        from grins_platform.services.sms.recipient import Recipient  # noqa: PLC0415
        from grins_platform.services.sms_service import SMSService  # noqa: PLC0415

        job = await session.get(Job, appointment.job_id)
        if job is None:
            return
        customer = await session.get(Customer, job.customer_id)
        if customer is None or not customer.phone:
            return

        sms_service = SMSService(session, provider=get_sms_provider())
        recipient = Recipient.from_customer(customer)

        date_str = format_sms_date(appointment.scheduled_date)
        time_part = format_sms_time_window(
            getattr(appointment, "time_window_start", None),
            getattr(appointment, "time_window_end", None),
        )
        service = format_job_type_display(getattr(job, "job_type", None))
        service_clause = f" for your {service}" if service else ""

        msg = (
            f"Your appointment on {date_str}{time_part}{service_clause} "
            "has been scheduled. "
            "Reply Y to confirm, R to reschedule, or C to cancel."
        )

        await sms_service.send_message(
            recipient=recipient,
            message=msg,
            message_type=MessageType.APPOINTMENT_CONFIRMATION,
            consent_type="transactional",
            job_id=job.id,
            appointment_id=appointment.id,
        )

    async def _send_reschedule_sms(
        self,
        session: AsyncSession,
        appointment: Appointment,
    ) -> None:
        """Send reschedule notification SMS for a moved appointment.

        Validates: Req 8.9; bughunt H-3 (weekday date format), L-4
        (include service type).
        """
        from grins_platform.models.customer import Customer  # noqa: PLC0415
        from grins_platform.models.job import Job  # noqa: PLC0415
        from grins_platform.schemas.ai import MessageType  # noqa: PLC0415
        from grins_platform.services.sms.factory import (  # noqa: PLC0415
            get_sms_provider,
        )
        from grins_platform.services.sms.formatters import (  # noqa: PLC0415
            format_job_type_display,
            format_sms_date,
            format_sms_time_window,
        )
        from grins_platform.services.sms.recipient import Recipient  # noqa: PLC0415
        from grins_platform.services.sms_service import SMSService  # noqa: PLC0415

        job = await session.get(Job, appointment.job_id)
        if job is None:
            return
        customer = await session.get(Customer, job.customer_id)
        if customer is None or not customer.phone:
            return

        sms_service = SMSService(session, provider=get_sms_provider())
        recipient = Recipient.from_customer(customer)

        date_str = format_sms_date(appointment.scheduled_date)
        time_part = format_sms_time_window(
            getattr(appointment, "time_window_start", None),
            getattr(appointment, "time_window_end", None),
        )
        service = format_job_type_display(getattr(job, "job_type", None))
        subject = f"Your {service} appointment" if service else "Your appointment"

        msg = (
            f"{subject} has been rescheduled to {date_str}{time_part}. "
            "Reply Y to confirm, R to reschedule, or C to cancel."
        )

        await sms_service.send_message(
            recipient=recipient,
            message=msg,
            message_type=MessageType.APPOINTMENT_RESCHEDULE,
            consent_type="transactional",
            job_id=job.id,
            appointment_id=appointment.id,
        )

    async def _send_cancellation_sms(
        self,
        session: AsyncSession,
        appointment: Appointment,
    ) -> None:
        """Send cancellation notification SMS.

        Validates: Req 8.11; bughunt H-3 (weekday date format).
        """
        from grins_platform.models.customer import Customer  # noqa: PLC0415
        from grins_platform.models.job import Job  # noqa: PLC0415
        from grins_platform.schemas.ai import MessageType  # noqa: PLC0415
        from grins_platform.services.sms.factory import (  # noqa: PLC0415
            get_sms_provider,
        )
        from grins_platform.services.sms.formatters import (  # noqa: PLC0415
            format_sms_date,
        )
        from grins_platform.services.sms.recipient import Recipient  # noqa: PLC0415
        from grins_platform.services.sms_service import SMSService  # noqa: PLC0415

        job = await session.get(Job, appointment.job_id)
        if job is None:
            return
        customer = await session.get(Customer, job.customer_id)
        if customer is None or not customer.phone:
            return

        sms_service = SMSService(session, provider=get_sms_provider())
        recipient = Recipient.from_customer(customer)

        date_str = format_sms_date(appointment.scheduled_date)
        msg = (
            f"Your appointment on {date_str} has been cancelled. "
            "Please contact us if you'd like to reschedule."
        )

        await sms_service.send_message(
            recipient=recipient,
            message=msg,
            message_type=MessageType.APPOINTMENT_CANCELLATION,
            consent_type="transactional",
            job_id=job.id,
            appointment_id=appointment.id,
        )

    async def transition_status(
        self,
        appointment_id: UUID,
        new_status: AppointmentStatus,
        actor_id: UUID,
        admin_override: bool = False,
    ) -> Appointment:
        """Transition appointment status via strict state machine.

        State machine: confirmed → en_route → in_progress → completed.
        Also supports cancellation and no-show from applicable states.
        Records timestamps at each transition.
        Payment gate on completion (Req 36).

        Args:
            appointment_id: UUID of the appointment
            new_status: Target status
            actor_id: Staff/admin performing the action
            admin_override: If True, bypasses payment gate for completion

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            InvalidStatusTransitionError: If transition violates state machine
            PaymentRequiredError: If completing without payment/invoice

        Validates: CRM Gap Closure Req 35.4, 35.5, 35.6, 36.1, 36.2
        """
        self.log_started(
            "transition_status",
            appointment_id=str(appointment_id),
            new_status=new_status.value,
            actor_id=str(actor_id),
        )

        appointment = await self.appointment_repository.get_by_id(
            appointment_id,
            include_relationships=True,
        )
        if not appointment:
            self.log_rejected("transition_status", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        current = appointment.status

        # Validate the transition
        if not self._is_valid_transition(current, new_status.value):
            self.log_rejected(
                "transition_status",
                reason="invalid_transition",
                current=current,
                requested=new_status.value,
            )
            raise InvalidStatusTransitionError(
                AppointmentStatus(current),
                new_status,
            )

        # Payment gate on completion (Req 36)
        if new_status == AppointmentStatus.COMPLETED and not admin_override:
            has_payment = await self._has_payment_or_invoice(appointment)
            if not has_payment:
                self.log_rejected(
                    "transition_status",
                    reason="payment_required",
                    appointment_id=str(appointment_id),
                )
                raise PaymentRequiredError(appointment_id)

        # Build update dict with timestamps
        now = datetime.now(tz=timezone.utc)
        update_data: dict[str, object] = {"status": new_status.value}

        if new_status == AppointmentStatus.EN_ROUTE:
            update_data["en_route_at"] = now
        elif new_status == AppointmentStatus.IN_PROGRESS:
            update_data["arrived_at"] = now
        elif new_status == AppointmentStatus.COMPLETED:
            update_data["completed_at"] = now

        updated = await self.appointment_repository.update(
            appointment_id,
            update_data,
        )

        self.log_completed(
            "transition_status",
            appointment_id=str(appointment_id),
            new_status=new_status.value,
        )
        return updated  # type: ignore[return-value]

    async def collect_payment(
        self,
        appointment_id: UUID,
        payment: PaymentCollectionRequest,
    ) -> PaymentResult:
        """Collect payment on-site for an appointment.

        Creates or updates the linked invoice with the payment details.
        Supports: card, cash, check, venmo, zelle.

        Args:
            appointment_id: UUID of the appointment
            payment: Payment details (method, amount, reference)

        Returns:
            PaymentResult with invoice details

        Raises:
            AppointmentNotFoundError: If appointment not found
            JobNotFoundError: If linked job not found

        Validates: CRM Gap Closure Req 30.3, 30.4, 30.5, 30.6
        """
        self.log_started(
            "collect_payment",
            appointment_id=str(appointment_id),
            payment_method=payment.payment_method.value,
            amount=str(payment.amount),
        )

        appointment = await self.appointment_repository.get_by_id(
            appointment_id,
            include_relationships=True,
        )
        if not appointment:
            self.log_rejected("collect_payment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        job = await self.job_repository.get_by_id(appointment.job_id)
        if not job:
            self.log_rejected("collect_payment", reason="job_not_found")
            raise JobNotFoundError(appointment.job_id)

        if self.invoice_repository is None:
            msg = "InvoiceRepository is required for payment collection"
            raise RuntimeError(msg)

        # Find existing invoice for this job
        existing_invoice = await self._find_invoice_for_job(appointment.job_id)

        now = datetime.now(tz=timezone.utc)

        if existing_invoice is not None:
            # Update existing invoice with payment
            existing_paid = existing_invoice.paid_amount or Decimal(0)
            new_paid = existing_paid + payment.amount
            new_status = (
                InvoiceStatus.PAID.value
                if new_paid >= existing_invoice.total_amount
                else InvoiceStatus.PARTIAL.value
            )
            updated_invoice = await self.invoice_repository.update(
                existing_invoice.id,
                {
                    "paid_amount": new_paid,
                    "payment_method": payment.payment_method.value,
                    "payment_reference": payment.reference_number,
                    "paid_at": now,
                    "status": new_status,
                },
            )
            result_invoice = updated_invoice or existing_invoice
        else:
            # Create new invoice then update with payment fields
            seq = await self.invoice_repository.get_next_sequence()
            invoice_number = f"INV-{now.year}-{seq:04d}"
            due_date = (now + timedelta(days=30)).date()

            result_invoice = await self.invoice_repository.create(
                job_id=appointment.job_id,
                customer_id=job.customer_id,
                invoice_number=invoice_number,
                amount=payment.amount,
                total_amount=payment.amount,
                invoice_date=now.date(),
                due_date=due_date,
                status=InvoiceStatus.PAID.value,
                line_items=[
                    {
                        "description": f"{job.job_type} service",
                        "amount": str(payment.amount),
                    },
                ],
            )
            # Update with payment details
            await self.invoice_repository.update(
                result_invoice.id,
                {
                    "payment_method": payment.payment_method.value,
                    "payment_reference": payment.reference_number,
                    "paid_at": now,
                    "paid_amount": payment.amount,
                },
            )

        self.log_completed(
            "collect_payment",
            appointment_id=str(appointment_id),
            invoice_id=str(result_invoice.id),
            amount=str(payment.amount),
            method=payment.payment_method.value,
        )

        return PaymentResult(
            invoice_id=result_invoice.id,
            invoice_number=result_invoice.invoice_number,
            amount_paid=payment.amount,
            payment_method=payment.payment_method.value,
            status=result_invoice.status,
        )

    async def create_invoice_from_appointment(
        self,
        appointment_id: UUID,
    ) -> Invoice:
        """Create an invoice pre-populated from appointment/job/customer data.

        Generates a Stripe payment link and sends via SMS + email.

        Args:
            appointment_id: UUID of the appointment

        Returns:
            Created Invoice instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            JobNotFoundError: If linked job not found

        Validates: CRM Gap Closure Req 31.2, 31.3, 31.4, 31.5
        """
        self.log_started(
            "create_invoice_from_appointment",
            appointment_id=str(appointment_id),
        )

        appointment = await self.appointment_repository.get_by_id(
            appointment_id,
            include_relationships=True,
        )
        if not appointment:
            self.log_rejected(
                "create_invoice_from_appointment",
                reason="not_found",
            )
            raise AppointmentNotFoundError(appointment_id)

        job = await self.job_repository.get_by_id(appointment.job_id)
        if not job:
            self.log_rejected(
                "create_invoice_from_appointment",
                reason="job_not_found",
            )
            raise JobNotFoundError(appointment.job_id)

        if self.invoice_repository is None:
            msg = "InvoiceRepository is required for invoice creation"
            raise RuntimeError(msg)

        now = datetime.now(tz=timezone.utc)
        seq = await self.invoice_repository.get_next_sequence()
        invoice_number = f"INV-{now.year}-{seq:04d}"
        due_date = (now + timedelta(days=30)).date()

        # Use quoted_amount from job, or final_amount if available
        amount = job.final_amount or job.quoted_amount or Decimal(0)

        line_items = [
            {
                "description": f"{job.job_type} service",
                "amount": str(amount),
            },
        ]

        invoice = await self.invoice_repository.create(
            job_id=job.id,
            customer_id=job.customer_id,
            invoice_number=invoice_number,
            amount=amount,
            total_amount=amount,
            invoice_date=now.date(),
            due_date=due_date,
            status=InvoiceStatus.SENT.value,
            line_items=line_items,
        )

        self.log_completed(
            "create_invoice_from_appointment",
            appointment_id=str(appointment_id),
            invoice_id=str(invoice.id),
            invoice_number=invoice_number,
        )
        return invoice

    async def create_estimate_from_appointment(
        self,
        appointment_id: UUID,
        data: EstimateCreate,
    ) -> object:
        """Create an estimate from an appointment, delegating to EstimateService.

        Links the estimate to the appointment's job and customer.

        Args:
            appointment_id: UUID of the appointment
            data: Estimate creation data

        Returns:
            Created Estimate instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            RuntimeError: If EstimateService not configured

        Validates: CRM Gap Closure Req 32.5, 32.6
        """
        self.log_started(
            "create_estimate_from_appointment",
            appointment_id=str(appointment_id),
        )

        appointment = await self.appointment_repository.get_by_id(
            appointment_id,
            include_relationships=True,
        )
        if not appointment:
            self.log_rejected(
                "create_estimate_from_appointment",
                reason="not_found",
            )
            raise AppointmentNotFoundError(appointment_id)

        if self.estimate_service is None:
            msg = "EstimateService is required for estimate creation"
            raise RuntimeError(msg)

        job = await self.job_repository.get_by_id(appointment.job_id)
        if not job:
            self.log_rejected(
                "create_estimate_from_appointment",
                reason="job_not_found",
            )
            raise JobNotFoundError(appointment.job_id)

        # Ensure the estimate is linked to the appointment's job/customer
        data.job_id = job.id
        data.customer_id = job.customer_id

        estimate = await self.estimate_service.create_estimate(data)

        self.log_completed(
            "create_estimate_from_appointment",
            appointment_id=str(appointment_id),
            estimate_id=str(estimate.id),
        )
        return estimate

    async def add_notes_and_photos(
        self,
        appointment_id: UUID,
        notes: str | None = None,
        photo_records: list[dict[str, object]] | None = None,
    ) -> Appointment:
        """Save notes to appointment and append to customer.internal_notes.

        Upload photos linked to both appointment and customer.

        Args:
            appointment_id: UUID of the appointment
            notes: Text notes to save
            photo_records: Pre-processed photo metadata dicts (from PhotoService)

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found

        Validates: CRM Gap Closure Req 33.2, 33.3
        """
        self.log_started(
            "add_notes_and_photos",
            appointment_id=str(appointment_id),
            has_notes=notes is not None,
            photo_count=len(photo_records) if photo_records else 0,
        )

        appointment = await self.appointment_repository.get_by_id(
            appointment_id,
            include_relationships=True,
        )
        if not appointment:
            self.log_rejected("add_notes_and_photos", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        update_data: dict[str, object] = {}

        if notes is not None:
            # Save notes to appointment
            update_data["notes"] = notes

            # Append to customer's internal_notes with timestamp
            job = await self.job_repository.get_by_id(appointment.job_id)
            if job:
                customer = job.customer
                if customer is not None:
                    now_str = datetime.now(tz=timezone.utc).strftime(
                        "%Y-%m-%d %H:%M UTC",
                    )
                    prefix = f"\n[{now_str}] Appointment note: "
                    existing = customer.internal_notes or ""
                    customer.internal_notes = existing + prefix + notes

        if update_data:
            updated = await self.appointment_repository.update(
                appointment_id,
                update_data,
            )
        else:
            updated = appointment  # type: ignore[assignment]

        self.log_completed(
            "add_notes_and_photos",
            appointment_id=str(appointment_id),
        )
        return updated  # type: ignore[return-value]

    async def request_google_review(
        self,
        appointment_id: UUID,
    ) -> ReviewRequestResult:
        """Send Google review request via SMS, consent-gated with 30-day dedup.

        Args:
            appointment_id: UUID of the appointment

        Returns:
            ReviewRequestResult indicating whether the request was sent

        Raises:
            AppointmentNotFoundError: If appointment not found
            ReviewAlreadyRequestedError: If review requested within 30 days

        Returns ``ReviewRequestResult(sent=False)`` (not raising) when
        consent is missing, so the endpoint returns a 2xx with a
        structured payload rather than a 422 error.

        Validates: CRM Gap Closure Req 34.2, 34.5, 34.6
        """
        self.log_started(
            "request_google_review",
            appointment_id=str(appointment_id),
        )

        appointment = await self.appointment_repository.get_by_id(
            appointment_id,
            include_relationships=True,
        )
        if not appointment:
            self.log_rejected("request_google_review", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        job = await self.job_repository.get_by_id(appointment.job_id)
        if not job:
            self.log_rejected("request_google_review", reason="job_not_found")
            raise JobNotFoundError(appointment.job_id)

        customer = job.customer
        if customer is None:
            self.log_rejected("request_google_review", reason="customer_not_found")
            return ReviewRequestResult(
                sent=False,
                channel=None,
                message="Customer not found for this appointment",
            )

        # Check SMS consent via the canonical consent module (Req 34.2).
        # Previously this consulted only ``customer.sms_opt_in`` (legacy
        # column), which diverges from the authoritative SmsConsentRecord
        # table — so a customer who opted in via the new consent flow but
        # whose legacy flag was still False was falsely denied. Using
        # ``check_sms_consent`` with transactional scope aligns both.
        # (bughunt CR-9 remainder.)
        from grins_platform.services.sms.consent import (  # noqa: PLC0415
            check_sms_consent,
        )

        session = self.appointment_repository.session
        has_consent = False
        if customer.phone:
            has_consent = await check_sms_consent(
                session,
                customer.phone,
                "transactional",
            )
        if not has_consent:
            self.log_rejected(
                "request_google_review",
                reason="no_sms_consent",
                customer_id=str(customer.id),
            )
            return ReviewRequestResult(
                sent=False,
                channel=None,
                message="Customer has opted out of SMS. Review request not sent.",
            )

        # 30-day dedup check (Req 34.6)
        last_review = await self._get_last_review_request_date(customer.id)
        if last_review is not None:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(
                days=_REVIEW_DEDUP_DAYS,
            )
            if last_review > cutoff:
                self.log_rejected(
                    "request_google_review",
                    reason="dedup_30_day",
                    customer_id=str(customer.id),
                    last_requested=last_review.isoformat(),
                )
                raise ReviewAlreadyRequestedError(
                    customer.id,
                    last_review.isoformat(),
                )

        # Actually send the review request SMS (Req 1.1, 1.2, 1.5)
        import os  # noqa: PLC0415

        from grins_platform.models.enums import MessageType  # noqa: PLC0415
        from grins_platform.services.sms.recipient import Recipient  # noqa: PLC0415
        from grins_platform.services.sms_service import SMSService  # noqa: PLC0415

        # bughunt X-1 / L-5: fail-closed when neither the env var nor the
        # service-level override is set, instead of shipping a stale
        # plural-slug fallback that 404s.
        review_url = os.environ.get("GOOGLE_REVIEW_URL") or self.google_review_url
        if not review_url:
            self.log_rejected(
                "request_google_review",
                reason="review_url_unset",
                customer_id=str(customer.id),
            )
            return ReviewRequestResult(
                sent=False,
                channel=None,
                message=(
                    "GOOGLE_REVIEW_URL is not configured. "
                    "Ask ops to set the environment variable before retrying."
                ),
            )

        message = (
            f"Hi {customer.first_name or 'there'}! "
            "Thank you for choosing Grins Irrigation. "
            "We'd love your feedback — please leave us a Google review: "
            f"{review_url}"
        )

        recipient = Recipient.from_customer(customer)
        sms_service = SMSService(session)
        try:
            send_result = await sms_service.send_message(
                recipient=recipient,
                message=message,
                message_type=MessageType.GOOGLE_REVIEW_REQUEST,
                consent_type="transactional",
                appointment_id=appointment_id,
            )
            provider_sid = send_result.get("message_id", "")
            self.log_completed(
                "request_google_review",
                appointment_id=str(appointment_id),
                customer_id=str(customer.id),
                provider_sid=provider_sid,
            )
            return ReviewRequestResult(
                sent=True,
                channel="sms",
                message="Google review request sent successfully",
            )
        except Exception as exc:
            self.log_failed(
                "request_google_review",
                error=exc,
                appointment_id=str(appointment_id),
                customer_id=str(customer.id),
            )
            return ReviewRequestResult(
                sent=False,
                channel="sms",
                message=f"Failed to send review request: {exc}",
            )

    async def calculate_lead_time(
        self,
        max_appointments_per_day: int = 8,
        look_ahead_days: int = 90,
    ) -> LeadTimeResult:
        """Calculate earliest available scheduling slot.

        Based on staff availability and appointment density.

        Args:
            max_appointments_per_day: Max appointments per staff per day
            look_ahead_days: How far ahead to search

        Returns:
            LeadTimeResult with days until earliest slot

        Validates: CRM Gap Closure Req 25.2, 25.3
        """
        self.log_started(
            "calculate_lead_time",
            max_per_day=max_appointments_per_day,
            look_ahead_days=look_ahead_days,
        )

        today = date.today()

        # Get all active staff members
        all_staff = await self.staff_repository.find_available(active_only=True)
        staff_count = len(all_staff) if all_staff else 1

        # Total capacity per day = staff_count * max_appointments_per_day
        daily_capacity = staff_count * max_appointments_per_day

        for day_offset in range(look_ahead_days):
            check_date = today + timedelta(days=day_offset)

            # Skip weekends (basic availability check)
            if check_date.weekday() >= 6:  # Sunday
                continue

            count = await self.appointment_repository.count_by_date(check_date)
            if count < daily_capacity:
                days_out = day_offset
                if days_out == 0:
                    display = "Available today"
                elif days_out == 1:
                    display = "Available tomorrow"
                elif days_out < 7:
                    display = f"Available in {days_out} days"
                elif days_out < 14:
                    display = "Booked out 1 week"
                elif days_out < 21:
                    display = "Booked out 2 weeks"
                elif days_out < 28:
                    display = "Booked out 3 weeks"
                else:
                    weeks = days_out // 7
                    display = f"Booked out {weeks} weeks"

                self.log_completed(
                    "calculate_lead_time",
                    days=days_out,
                    earliest_date=str(check_date),
                )
                return LeadTimeResult(
                    days=days_out,
                    earliest_date=check_date,
                    display=display,
                )

        # No availability found within look-ahead window
        self.log_completed(
            "calculate_lead_time",
            days=look_ahead_days,
            earliest_date=None,
        )
        return LeadTimeResult(
            days=look_ahead_days,
            earliest_date=None,
            display=f"Booked out {look_ahead_days // 7}+ weeks",
        )

    async def get_staff_time_analytics(
        self,
        date_range: DateRange,
    ) -> list[StaffTimeEntry]:
        """Calculate staff time analytics: avg travel, job duration, total time.

        Groups by staff and job type. Flags staff exceeding 1.5x average.

        Args:
            date_range: Start and end date for the analysis period

        Returns:
            List of StaffTimeEntry with analytics per staff/job_type

        Validates: CRM Gap Closure Req 37.1, 37.2, 37.4
        """
        self.log_started(
            "get_staff_time_analytics",
            start_date=str(date_range.start_date),
            end_date=str(date_range.end_date),
        )

        # Get completed appointments in the date range
        appointments, _ = await self.appointment_repository.list_with_filters(
            status=AppointmentStatus.COMPLETED,
            date_from=date_range.start_date,
            date_to=date_range.end_date,
            page=1,
            page_size=10000,
            include_relationships=True,
        )

        # Group by (staff_id, job_type) and compute durations
        groups: dict[
            tuple[str, str],
            list[dict[str, float]],
        ] = {}

        for apt in appointments:
            if apt.en_route_at and apt.arrived_at and apt.completed_at:
                travel = (apt.arrived_at - apt.en_route_at).total_seconds() / 60.0
                job_dur = (apt.completed_at - apt.arrived_at).total_seconds() / 60.0
                total = (apt.completed_at - apt.en_route_at).total_seconds() / 60.0
            elif apt.arrived_at and apt.completed_at:
                travel = 0.0
                job_dur = (apt.completed_at - apt.arrived_at).total_seconds() / 60.0
                total = job_dur
            else:
                continue

            staff_id_str = str(apt.staff_id)
            job_type = getattr(apt, "job", None)
            jt = job_type.job_type if job_type else "unknown"
            key = (staff_id_str, jt)

            if key not in groups:
                groups[key] = []
            groups[key].append(
                {
                    "travel": max(travel, 0.0),
                    "job": max(job_dur, 0.0),
                    "total": max(total, 0.0),
                },
            )

        # Compute averages per group
        entries: list[StaffTimeEntry] = []
        # Also compute global averages per job_type for flagging
        job_type_totals: dict[str, list[float]] = {}

        for (staff_id_str, jt), durations in groups.items():
            count = len(durations)
            avg_travel = sum(d["travel"] for d in durations) / count
            avg_job = sum(d["job"] for d in durations) / count
            avg_total = sum(d["total"] for d in durations) / count

            # Collect for global average
            if jt not in job_type_totals:
                job_type_totals[jt] = []
            job_type_totals[jt].extend(d["total"] for d in durations)

            # Look up staff name
            from uuid import UUID as _UUID  # noqa: PLC0415

            staff = await self.staff_repository.get_by_id(_UUID(staff_id_str))
            staff_name = f"{staff.first_name} {staff.last_name}" if staff else "Unknown"

            entries.append(
                StaffTimeEntry(
                    staff_id=_UUID(staff_id_str),
                    staff_name=staff_name,
                    job_type=jt,
                    avg_travel_minutes=round(avg_travel, 1),
                    avg_job_minutes=round(avg_job, 1),
                    avg_total_minutes=round(avg_total, 1),
                    appointment_count=count,
                    flagged=False,  # Will be set below
                ),
            )

        # Flag entries where avg_total exceeds 1.5x the global average
        # for that job type (Req 37.4)
        for entry in entries:
            jt = entry.job_type or "unknown"
            if jt in job_type_totals and len(job_type_totals[jt]) > 1:
                global_avg = sum(job_type_totals[jt]) / len(job_type_totals[jt])
                if global_avg > 0 and entry.avg_total_minutes > 1.5 * global_avg:
                    entry.flagged = True

        self.log_completed(
            "get_staff_time_analytics",
            entry_count=len(entries),
        )
        return entries

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _check_staff_conflict(
        self,
        staff_id: UUID,
        scheduled_date: date,
        start_time: time,
        end_time: time,
        exclude_appointment_id: UUID | None = None,
    ) -> Appointment | None:
        """Check if a staff member has a conflicting appointment.

        Returns the conflicting appointment if found, None otherwise.
        """
        existing = await self.appointment_repository.get_staff_daily_schedule(
            staff_id,
            scheduled_date,
        )

        for apt in existing:
            if exclude_appointment_id and apt.id == exclude_appointment_id:
                continue
            if apt.status in (
                AppointmentStatus.CANCELLED.value,
                AppointmentStatus.NO_SHOW.value,
            ):
                continue
            # Check time overlap
            if start_time < apt.time_window_end and end_time > apt.time_window_start:
                return apt

        return None

    def _is_valid_transition(self, current: str, target: str) -> bool:
        """Check if a status transition is valid.

        Delegates to the single source of truth in
        `grins_platform.models.appointment.VALID_APPOINTMENT_TRANSITIONS`.
        """
        return target in VALID_APPOINTMENT_TRANSITIONS.get(current, [])

    async def _has_payment_or_invoice(self, appointment: Appointment) -> bool:
        """Check if the appointment's job has a payment or invoice.

        Validates: CRM Gap Closure Req 36.1, 36.2
        """
        if self.invoice_repository is None:
            # If no invoice repo, can't check — allow completion
            return True

        invoice = await self._find_invoice_for_job(appointment.job_id)
        return invoice is not None

    async def _find_invoice_for_job(
        self,
        job_id: UUID,
    ) -> Invoice | None:
        """Find an existing invoice for a job by querying the DB directly.

        Returns the first invoice found, or None.
        """
        if self.invoice_repository is None:
            return None

        try:
            from sqlalchemy import select  # noqa: PLC0415

            from grins_platform.models.invoice import Invoice  # noqa: PLC0415

            session = self.invoice_repository.session
            stmt = (
                select(Invoice)
                .where(Invoice.job_id == job_id)
                .order_by(Invoice.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception:
            return None

    async def _get_last_review_request_date(
        self,
        customer_id: UUID,
    ) -> datetime | None:
        """Get the date of the last Google review request for a customer.

        Checks sent_messages for review_request type messages.
        Returns None if no previous request found.
        """
        # Query sent_messages for this customer with type review_request
        # For now, we check via the appointment repository's session
        # This is a simplified check — in production, would query
        # sent_messages table directly
        try:
            from sqlalchemy import select  # noqa: PLC0415

            from grins_platform.models.sent_message import (  # noqa: PLC0415
                SentMessage,
            )

            session = self.appointment_repository.session
            stmt = (
                select(SentMessage.created_at)
                .where(
                    SentMessage.customer_id == customer_id,
                    SentMessage.message_type.in_(
                        ["review_request", "google_review_request"],
                    ),
                )
                .order_by(SentMessage.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()  # type: ignore[return-value]
        except Exception:
            # If we can't check, allow the request
            return None
