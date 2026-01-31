"""
Appointment service for business logic operations.

This module provides the AppointmentService class for all appointment-related
business operations including scheduling, status transitions, and schedule queries.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    StaffNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import AppointmentStatus

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.appointment import Appointment
    from grins_platform.repositories.appointment_repository import (
        AppointmentRepository,
    )
    from grins_platform.repositories.job_repository import JobRepository
    from grins_platform.repositories.staff_repository import StaffRepository
    from grins_platform.schemas.appointment import (
        AppointmentCreate,
        AppointmentUpdate,
    )


class AppointmentService(LoggerMixin):
    """Service for appointment management operations.

    This class handles all business logic for appointments including
    scheduling, status transitions, and schedule queries.

    Attributes:
        appointment_repository: AppointmentRepository for database operations
        job_repository: JobRepository for job validation
        staff_repository: StaffRepository for staff validation

    Validates: Admin Dashboard Requirements 1.1-1.5
    """

    DOMAIN = "appointment"

    def __init__(
        self,
        appointment_repository: AppointmentRepository,
        job_repository: JobRepository,
        staff_repository: StaffRepository,
    ) -> None:
        """Initialize service with repositories.

        Args:
            appointment_repository: AppointmentRepository for database operations
            job_repository: JobRepository for job validation
            staff_repository: StaffRepository for staff validation
        """
        super().__init__()
        self.appointment_repository = appointment_repository
        self.job_repository = job_repository
        self.staff_repository = staff_repository

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

        # Validate staff exists
        staff = await self.staff_repository.get_by_id(data.staff_id)
        if not staff:
            self.log_rejected("create_appointment", reason="staff_not_found")
            raise StaffNotFoundError(data.staff_id)

        # Create the appointment
        appointment = await self.appointment_repository.create(
            job_id=data.job_id,
            staff_id=data.staff_id,
            scheduled_date=data.scheduled_date,
            time_window_start=data.time_window_start,
            time_window_end=data.time_window_end,
            status=AppointmentStatus.SCHEDULED.value,
            notes=data.notes,
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

        # Check if appointment exists
        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("update_appointment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        # Build update dict
        update_data = data.model_dump(exclude_unset=True)

        # If rescheduling a cancelled appointment (date/time changed), reactivate it
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

        updated = await self.appointment_repository.update(appointment_id, update_data)

        self.log_completed("update_appointment", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    async def cancel_appointment(self, appointment_id: UUID) -> Appointment:
        """Cancel an appointment.

        Args:
            appointment_id: UUID of the appointment to cancel

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            InvalidStatusTransitionError: If appointment cannot be cancelled

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("cancel_appointment", appointment_id=str(appointment_id))

        # Check if appointment exists
        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("cancel_appointment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        # Check if can be cancelled
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

        updated = await self.appointment_repository.update_status(
            appointment_id,
            AppointmentStatus.CANCELLED,
        )

        self.log_completed("cancel_appointment", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

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

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status
            staff_id: Filter by staff member
            job_id: Filter by job
            date_from: Filter by scheduled_date >= date_from
            date_to: Filter by scheduled_date <= date_to
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            include_relationships: Whether to load related entities (job, staff)

        Returns:
            Tuple of (list of appointments, total count)

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

        Args:
            schedule_date: Date to get appointments for
            include_relationships: Whether to load related entities

        Returns:
            Tuple of (list of appointments, total count)

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

        Args:
            staff_id: UUID of the staff member
            schedule_date: Date to get appointments for
            include_relationships: Whether to load related entities

        Returns:
            Tuple of (list of appointments, total count, total scheduled minutes)

        Raises:
            StaffNotFoundError: If staff not found

        Validates: Admin Dashboard Requirement 1.5
        """
        self.log_started(
            "get_staff_daily_schedule",
            staff_id=str(staff_id),
            date=str(schedule_date),
        )

        # Validate staff exists
        staff = await self.staff_repository.get_by_id(staff_id)
        if not staff:
            self.log_rejected("get_staff_daily_schedule", reason="staff_not_found")
            raise StaffNotFoundError(staff_id)

        appointments = await self.appointment_repository.get_staff_daily_schedule(
            staff_id,
            schedule_date,
            include_relationships=include_relationships,
        )

        # Calculate total scheduled minutes
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

        Args:
            start_date: First day of the week
            include_relationships: Whether to load related entities

        Returns:
            Tuple of (dict mapping dates to appointments, total count)

        Validates: Admin Dashboard Requirement 1.5
        """
        self.log_started("get_weekly_schedule", start_date=str(start_date))

        schedule = await self.appointment_repository.get_weekly_schedule(
            start_date,
            include_relationships=include_relationships,
        )

        # Count total appointments
        total = sum(len(appointments) for appointments in schedule.values())

        self.log_completed("get_weekly_schedule", total_appointments=total)
        return schedule, total

    async def mark_arrived(self, appointment_id: UUID) -> Appointment:
        """Mark an appointment as arrived (in progress).

        Args:
            appointment_id: UUID of the appointment

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            InvalidStatusTransitionError: If cannot transition to in_progress

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("mark_arrived", appointment_id=str(appointment_id))

        # Check if appointment exists
        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("mark_arrived", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        # Check if can transition to in_progress
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
            arrived_at=datetime.now(),
        )

        self.log_completed("mark_arrived", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    async def mark_completed(self, appointment_id: UUID) -> Appointment:
        """Mark an appointment as completed.

        Args:
            appointment_id: UUID of the appointment

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            InvalidStatusTransitionError: If appointment cannot transition to completed

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("mark_completed", appointment_id=str(appointment_id))

        # Check if appointment exists
        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("mark_completed", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        # Check if can transition to completed
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
            completed_at=datetime.now(),
        )

        self.log_completed("mark_completed", appointment_id=str(appointment_id))
        return updated  # type: ignore[return-value]

    async def confirm_appointment(self, appointment_id: UUID) -> Appointment:
        """Confirm an appointment.

        Args:
            appointment_id: UUID of the appointment

        Returns:
            Updated Appointment instance

        Raises:
            AppointmentNotFoundError: If appointment not found
            InvalidStatusTransitionError: If appointment cannot be confirmed

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("confirm_appointment", appointment_id=str(appointment_id))

        # Check if appointment exists
        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("confirm_appointment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)

        # Check if can transition to confirmed
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
