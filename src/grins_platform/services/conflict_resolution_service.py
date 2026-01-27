"""Conflict resolution service for schedule management.

Validates: Requirements 10.1-10.7
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.enums import AppointmentStatus
from grins_platform.models.job import Job
from grins_platform.models.schedule_waitlist import ScheduleWaitlist
from grins_platform.schemas.conflict_resolution import (
    CancelAppointmentResponse,
    FillGapResponse,
    FillGapSuggestion,
    RescheduleAppointmentResponse,
    WaitlistEntryResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ConflictResolutionService(LoggerMixin):
    """Service for handling schedule conflicts.

    Validates: Requirements 10.1-10.7
    """

    DOMAIN = "business"

    def __init__(self, db: Session) -> None:
        """Initialize the service."""
        super().__init__()
        self.db = db

    def cancel_appointment(
        self,
        appointment_id: UUID,
        reason: str,
        add_to_waitlist: bool = False,
        preferred_reschedule_date: date | None = None,
    ) -> CancelAppointmentResponse:
        """Cancel an appointment.

        Args:
            appointment_id: ID of appointment to cancel
            reason: Cancellation reason
            add_to_waitlist: Whether to add job to waitlist
            preferred_reschedule_date: Preferred date for rescheduling

        Returns:
            CancelAppointmentResponse with result

        Validates: Requirements 10.1, 10.2
        """
        self.log_started("cancel_appointment", appointment_id=str(appointment_id))

        appointment = (
            self.db.query(Appointment)
            .filter(Appointment.id == appointment_id)
            .first()
        )

        if not appointment:
            return CancelAppointmentResponse(
                appointment_id=appointment_id,
                cancelled_at=datetime.now(timezone.utc),
                reason=reason,
                message="Appointment not found",
            )

        # Update appointment
        now = datetime.now(timezone.utc)
        appointment.status = AppointmentStatus.CANCELLED.value
        appointment.cancellation_reason = reason
        appointment.cancelled_at = now

        waitlist_entry_id = None
        if add_to_waitlist and appointment.job_id:
            waitlist_entry = ScheduleWaitlist(
                job_id=appointment.job_id,
                preferred_date=preferred_reschedule_date or appointment.scheduled_date,
                preferred_time_start=appointment.time_window_start,
                preferred_time_end=appointment.time_window_end,
                priority=1,
                notes=f"Rescheduled from cancelled appointment: {reason}",
            )
            self.db.add(waitlist_entry)
            self.db.flush()
            waitlist_entry_id = waitlist_entry.id

        self.db.commit()

        self.log_completed(
            "cancel_appointment",
            appointment_id=str(appointment_id),
            added_to_waitlist=add_to_waitlist,
        )

        return CancelAppointmentResponse(
            appointment_id=appointment_id,
            cancelled_at=now,
            reason=reason,
            waitlist_entry_id=waitlist_entry_id,
            message="Appointment cancelled successfully",
        )

    def reschedule_appointment(
        self,
        appointment_id: UUID,
        new_date: date,
        new_time_start: time,
        new_time_end: time,
        new_staff_id: UUID | None = None,
    ) -> RescheduleAppointmentResponse:
        """Reschedule an appointment to a new time.

        Args:
            appointment_id: ID of appointment to reschedule
            new_date: New date
            new_time_start: New start time
            new_time_end: New end time
            new_staff_id: Optional new staff assignment

        Returns:
            RescheduleAppointmentResponse with result

        Validates: Requirement 10.3
        """
        self.log_started("reschedule_appointment", appointment_id=str(appointment_id))

        original = (
            self.db.query(Appointment)
            .filter(Appointment.id == appointment_id)
            .first()
        )

        if not original:
            msg = f"Appointment {appointment_id} not found"
            raise ValueError(msg)

        # Cancel original
        original.status = AppointmentStatus.CANCELLED.value
        original.cancellation_reason = "Rescheduled"
        original.cancelled_at = datetime.now(timezone.utc)

        # Create new appointment linked to original
        new_appointment = Appointment(
            job_id=original.job_id,
            staff_id=new_staff_id or original.staff_id,
            scheduled_date=new_date,
            time_window_start=new_time_start,
            time_window_end=new_time_end,
            status=AppointmentStatus.SCHEDULED.value,
            rescheduled_from_id=original.id,
            notes=f"Rescheduled from {original.scheduled_date}",
        )
        self.db.add(new_appointment)
        self.db.flush()

        self.db.commit()

        self.log_completed(
            "reschedule_appointment",
            original_id=str(appointment_id),
            new_id=str(new_appointment.id),
        )

        return RescheduleAppointmentResponse(
            original_appointment_id=appointment_id,
            new_appointment_id=new_appointment.id,
            new_date=new_date,
            new_time_start=new_time_start,
            new_time_end=new_time_end,
            staff_id=new_appointment.staff_id,
            message="Appointment rescheduled successfully",
        )

    def get_waitlist(
        self,
        target_date: date | None = None,
    ) -> list[WaitlistEntryResponse]:
        """Get waitlist entries.

        Args:
            target_date: Optional filter by preferred date

        Returns:
            List of waitlist entries

        Validates: Requirements 10.4, 10.5
        """
        query = self.db.query(ScheduleWaitlist)

        if target_date:
            query = query.filter(ScheduleWaitlist.preferred_date == target_date)

        entries = query.order_by(
            ScheduleWaitlist.priority.desc(),
            ScheduleWaitlist.created_at,
        ).all()

        return [
            WaitlistEntryResponse(
                id=e.id,
                job_id=e.job_id,
                preferred_date=e.preferred_date,
                preferred_time_start=e.preferred_time_start,
                preferred_time_end=e.preferred_time_end,
                priority=e.priority,
                notes=e.notes,
                notified_at=e.notified_at,
                created_at=e.created_at,
            )
            for e in entries
        ]

    def fill_gap_suggestions(
        self,
        target_date: date,
        gap_start: time,
        gap_end: time,
        staff_id: UUID | None = None,  # noqa: ARG002
    ) -> FillGapResponse:
        """Get suggestions for filling a schedule gap.

        Args:
            target_date: Date of the gap
            gap_start: Start time of gap
            gap_end: End time of gap
            staff_id: Optional staff filter

        Returns:
            FillGapResponse with suggestions

        Validates: Requirements 10.6, 10.7
        """
        self.log_started(
            "fill_gap_suggestions",
            target_date=str(target_date),
            gap_start=str(gap_start),
            gap_end=str(gap_end),
        )

        gap_minutes = (
            (gap_end.hour * 60 + gap_end.minute)
            - (gap_start.hour * 60 + gap_start.minute)
        )

        suggestions: list[FillGapSuggestion] = []

        # Check waitlist first
        waitlist_entries = (
            self.db.query(ScheduleWaitlist)
            .filter(ScheduleWaitlist.preferred_date == target_date)
            .order_by(ScheduleWaitlist.priority.desc())
            .limit(10)
            .all()
        )

        for entry in waitlist_entries:
            job = self.db.query(Job).filter(Job.id == entry.job_id).first()
            if (
                job
                and job.estimated_duration_minutes is not None
                and job.estimated_duration_minutes <= gap_minutes
            ):
                suggestions.append(
                    FillGapSuggestion(
                        job_id=job.id,
                        customer_name=self._get_customer_name(job),
                        service_type=job.job_type,
                        duration_minutes=job.estimated_duration_minutes or 30,
                        priority=entry.priority,
                        from_waitlist=True,
                    ),
                )

        self.log_completed("fill_gap_suggestions", count=len(suggestions))

        return FillGapResponse(
            target_date=target_date,
            gap_start=gap_start,
            gap_end=gap_end,
            gap_duration_minutes=gap_minutes,
            suggestions=suggestions,
        )

    def _get_customer_name(self, job: Job) -> str:
        """Get customer name for a job."""
        if job.customer:
            return f"{job.customer.first_name} {job.customer.last_name}"
        return "Unknown"
