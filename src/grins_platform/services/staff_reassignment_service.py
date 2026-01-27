"""Staff reassignment service.

Validates: Requirements 11.1-11.6
"""

from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.enums import AppointmentStatus
from grins_platform.models.schedule_reassignment import ScheduleReassignment
from grins_platform.models.staff import Staff
from grins_platform.models.staff_availability import StaffAvailability
from grins_platform.schemas.staff_reassignment import (
    CoverageOption,
    CoverageOptionsResponse,
    MarkUnavailableResponse,
    ReassignStaffResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class StaffReassignmentService(LoggerMixin):
    """Service for handling staff reassignment.

    Validates: Requirements 11.1-11.6
    """

    DOMAIN = "business"

    def __init__(self, db: Session) -> None:
        """Initialize the service."""
        super().__init__()
        self.db = db

    def mark_staff_unavailable(
        self,
        staff_id: UUID,
        target_date: date,
        reason: str,
    ) -> MarkUnavailableResponse:
        """Mark a staff member as unavailable for a date.

        Args:
            staff_id: ID of staff to mark unavailable
            target_date: Date to mark unavailable
            reason: Reason for unavailability

        Returns:
            MarkUnavailableResponse with affected appointments

        Validates: Requirement 11.1
        """
        self.log_started(
            "mark_staff_unavailable",
            staff_id=str(staff_id),
            target_date=str(target_date),
        )

        # Update or create availability record
        availability = (
            self.db.query(StaffAvailability)
            .filter(
                StaffAvailability.staff_id == staff_id,
                StaffAvailability.date == target_date,
            )
            .first()
        )

        if availability:
            availability.is_available = False
            availability.notes = reason
        else:
            availability = StaffAvailability(
                staff_id=staff_id,
                date=target_date,
                is_available=False,
                start_time=time(8, 0),
                end_time=time(17, 0),
                notes=reason,
            )
            self.db.add(availability)

        # Count affected appointments
        affected = (
            self.db.query(Appointment)
            .filter(
                Appointment.staff_id == staff_id,
                Appointment.scheduled_date == target_date,
                Appointment.status.notin_([
                    AppointmentStatus.CANCELLED.value,
                    AppointmentStatus.COMPLETED.value,
                ]),
            )
            .count()
        )

        self.db.commit()

        self.log_completed(
            "mark_staff_unavailable",
            staff_id=str(staff_id),
            affected=affected,
        )

        return MarkUnavailableResponse(
            staff_id=staff_id,
            target_date=target_date,
            affected_appointments=affected,
            message=f"Staff marked unavailable. {affected} appointments affected.",
        )

    def reassign_jobs(
        self,
        original_staff_id: UUID,
        new_staff_id: UUID,
        target_date: date,
        reason: str,
    ) -> ReassignStaffResponse:
        """Reassign jobs from one staff to another.

        Args:
            original_staff_id: Staff to reassign from
            new_staff_id: Staff to reassign to
            target_date: Date of reassignment
            reason: Reason for reassignment

        Returns:
            ReassignStaffResponse with result

        Validates: Requirements 11.2, 11.3
        """
        self.log_started(
            "reassign_jobs",
            original_staff_id=str(original_staff_id),
            new_staff_id=str(new_staff_id),
        )

        # Get appointments to reassign
        appointments = (
            self.db.query(Appointment)
            .filter(
                Appointment.staff_id == original_staff_id,
                Appointment.scheduled_date == target_date,
                Appointment.status.notin_([
                    AppointmentStatus.CANCELLED.value,
                    AppointmentStatus.COMPLETED.value,
                ]),
            )
            .all()
        )

        # Reassign appointments
        for apt in appointments:
            apt.staff_id = new_staff_id

        # Create reassignment record
        reassignment = ScheduleReassignment(
            original_staff_id=original_staff_id,
            new_staff_id=new_staff_id,
            reassignment_date=target_date,
            reason=reason,
            jobs_reassigned=len(appointments),
        )
        self.db.add(reassignment)
        self.db.flush()

        self.db.commit()

        self.log_completed(
            "reassign_jobs",
            reassignment_id=str(reassignment.id),
            jobs_reassigned=len(appointments),
        )

        return ReassignStaffResponse(
            reassignment_id=reassignment.id,
            original_staff_id=original_staff_id,
            new_staff_id=new_staff_id,
            target_date=target_date,
            jobs_reassigned=len(appointments),
            message=f"Reassigned {len(appointments)} jobs successfully.",
        )

    def get_coverage_options(
        self,
        target_date: date,
        exclude_staff_id: UUID | None = None,
    ) -> CoverageOptionsResponse:
        """Get coverage options for a date.

        Args:
            target_date: Date to find coverage for
            exclude_staff_id: Staff to exclude (the unavailable one)

        Returns:
            CoverageOptionsResponse with options

        Validates: Requirement 11.6
        """
        self.log_started("get_coverage_options", target_date=str(target_date))

        # Get jobs that need coverage
        jobs_query = self.db.query(Appointment).filter(
            Appointment.scheduled_date == target_date,
            Appointment.status.notin_([
                AppointmentStatus.CANCELLED.value,
                AppointmentStatus.COMPLETED.value,
            ]),
        )
        if exclude_staff_id:
            jobs_query = jobs_query.filter(Appointment.staff_id == exclude_staff_id)

        jobs_to_cover = jobs_query.all()
        total_duration = sum(apt.get_duration_minutes() for apt in jobs_to_cover)

        # Get available staff
        available_staff = (
            self.db.query(Staff)
            .join(StaffAvailability)
            .filter(
                StaffAvailability.date == target_date,
                StaffAvailability.is_available == True,  # noqa: E712
                Staff.is_active == True,  # noqa: E712
            )
        )
        if exclude_staff_id:
            available_staff = available_staff.filter(Staff.id != exclude_staff_id)

        options: list[CoverageOption] = []
        for staff in available_staff.all():
            # Get staff's current load
            current_appointments = (
                self.db.query(Appointment)
                .filter(
                    Appointment.staff_id == staff.id,
                    Appointment.scheduled_date == target_date,
                    Appointment.status.notin_([
                        AppointmentStatus.CANCELLED.value,
                        AppointmentStatus.COMPLETED.value,
                    ]),
                )
                .all()
            )
            current_duration = sum(
                apt.get_duration_minutes() for apt in current_appointments
            )

            # Get availability
            availability = (
                self.db.query(StaffAvailability)
                .filter(
                    StaffAvailability.staff_id == staff.id,
                    StaffAvailability.date == target_date,
                )
                .first()
            )

            if availability:
                start_mins = (
                    availability.start_time.hour * 60
                    + availability.start_time.minute
                )
                end_mins = (
                    availability.end_time.hour * 60
                    + availability.end_time.minute
                )
                total_capacity = end_mins - start_mins
                available_capacity = total_capacity - current_duration

                options.append(
                    CoverageOption(
                        staff_id=staff.id,
                        staff_name=staff.name,
                        available_capacity_minutes=max(0, available_capacity),
                        current_jobs=len(current_appointments),
                        can_cover_all=available_capacity >= total_duration,
                    ),
                )

        self.log_completed("get_coverage_options", options_count=len(options))

        return CoverageOptionsResponse(
            target_date=target_date,
            jobs_to_cover=len(jobs_to_cover),
            total_duration_minutes=total_duration,
            options=options,
        )
