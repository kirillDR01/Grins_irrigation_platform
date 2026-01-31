"""
Appointment repository for database operations.

This module provides the AppointmentRepository class for all appointment-related
database operations using SQLAlchemy 2.0 async patterns.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.enums import AppointmentStatus  # noqa: TC001
from grins_platform.models.job import Job

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class AppointmentRepository(LoggerMixin):
    """Repository for appointment database operations.

    This class handles all database operations for appointments including
    CRUD operations, queries, and schedule management.

    Attributes:
        session: AsyncSession for database operations

    Validates: Admin Dashboard Requirements 1.1-1.5
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__()
        self.session = session

    async def create(
        self,
        job_id: UUID,
        staff_id: UUID,
        scheduled_date: date,
        time_window_start: time,
        time_window_end: time,
        status: str = "scheduled",
        notes: str | None = None,
        route_order: int | None = None,
        estimated_arrival: time | None = None,
    ) -> Appointment:
        """Create a new appointment record.

        Args:
            job_id: Job UUID
            staff_id: Staff UUID
            scheduled_date: Date of the appointment
            time_window_start: Start of the time window
            time_window_end: End of the time window
            status: Initial appointment status
            notes: Additional notes
            route_order: Order in the daily route
            estimated_arrival: Estimated arrival time

        Returns:
            Created Appointment instance

        Validates: Admin Dashboard Requirement 1.1
        """
        self.log_started(
            "create",
            job_id=str(job_id),
            staff_id=str(staff_id),
            scheduled_date=str(scheduled_date),
        )

        appointment = Appointment(
            job_id=job_id,
            staff_id=staff_id,
            scheduled_date=scheduled_date,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            status=status,
            notes=notes,
            route_order=route_order,
            estimated_arrival=estimated_arrival,
        )

        self.session.add(appointment)
        await self.session.flush()
        await self.session.refresh(appointment)

        self.log_completed("create", appointment_id=str(appointment.id))
        return appointment

    async def get_by_id(
        self,
        appointment_id: UUID,
        include_relationships: bool = False,
    ) -> Appointment | None:
        """Get an appointment by ID.

        Args:
            appointment_id: UUID of the appointment
            include_relationships: Whether to load related entities

        Returns:
            Appointment instance or None if not found

        Validates: Admin Dashboard Requirement 1.3
        """
        self.log_started("get_by_id", appointment_id=str(appointment_id))

        stmt = select(Appointment).where(Appointment.id == appointment_id)

        if include_relationships:
            stmt = stmt.options(
                selectinload(Appointment.job),
                selectinload(Appointment.staff),
            )

        result = await self.session.execute(stmt)
        appointment: Appointment | None = result.scalar_one_or_none()

        if appointment:
            self.log_completed("get_by_id", appointment_id=str(appointment_id))
        else:
            self.log_completed(
                "get_by_id",
                appointment_id=str(appointment_id),
                found=False,
            )

        return appointment

    async def update(
        self,
        appointment_id: UUID,
        data: dict[str, Any],
    ) -> Appointment | None:
        """Update an appointment record.

        Args:
            appointment_id: UUID of the appointment to update
            data: Dictionary of fields to update

        Returns:
            Updated Appointment instance or None if not found

        Validates: Admin Dashboard Requirement 1.2
        """
        self.log_started("update", appointment_id=str(appointment_id))

        # Remove None values
        update_data = {k: v for k, v in data.items() if v is not None}

        if not update_data:
            return await self.get_by_id(appointment_id)

        update_data["updated_at"] = datetime.now()

        stmt = (
            update(Appointment)
            .where(Appointment.id == appointment_id)
            .values(**update_data)
            .returning(Appointment)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        appointment: Appointment | None = result.scalar_one_or_none()

        if appointment:
            self.log_completed("update", appointment_id=str(appointment_id))
        else:
            self.log_completed(
                "update",
                appointment_id=str(appointment_id),
                found=False,
            )

        return appointment

    async def delete(self, appointment_id: UUID) -> bool:
        """Delete an appointment (hard delete).

        Args:
            appointment_id: UUID of the appointment to delete

        Returns:
            True if appointment was deleted, False if not found
        """
        self.log_started("delete", appointment_id=str(appointment_id))

        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            self.log_completed(
                "delete",
                appointment_id=str(appointment_id),
                found=False,
            )
            return False

        await self.session.delete(appointment)
        await self.session.flush()

        self.log_completed("delete", appointment_id=str(appointment_id))
        return True

    async def list_with_filters(
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
        include_relationships: bool = False,
    ) -> tuple[list[Appointment], int]:
        """List appointments with filtering and pagination.

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
        self.log_started("list_with_filters", page=page, page_size=page_size)

        # Base query
        base_query = select(Appointment)

        # Apply filters
        if status is not None:
            base_query = base_query.where(Appointment.status == status.value)

        if staff_id is not None:
            base_query = base_query.where(Appointment.staff_id == staff_id)

        if job_id is not None:
            base_query = base_query.where(Appointment.job_id == job_id)

        if date_from is not None:
            base_query = base_query.where(Appointment.scheduled_date >= date_from)

        if date_to is not None:
            base_query = base_query.where(Appointment.scheduled_date <= date_to)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Appointment, sort_by, Appointment.scheduled_date)
        sort_column = sort_column.desc() if sort_order == "desc" else sort_column.asc()

        # Apply pagination
        offset = (page - 1) * page_size
        paginated_query = (
            base_query.order_by(sort_column).offset(offset).limit(page_size)
        )

        # Include relationships if requested
        if include_relationships:
            paginated_query = paginated_query.options(
                selectinload(Appointment.job).selectinload(Job.customer),
                selectinload(Appointment.staff),
            )

        result = await self.session.execute(paginated_query)
        appointments = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(appointments), total=total)
        return appointments, total

    async def get_daily_schedule(
        self,
        schedule_date: date,
        include_relationships: bool = False,
    ) -> list[Appointment]:
        """Get all appointments for a specific date.

        Args:
            schedule_date: Date to get appointments for
            include_relationships: Whether to load related entities

        Returns:
            List of appointments ordered by time_window_start

        Validates: Admin Dashboard Requirement 1.5
        """
        self.log_started("get_daily_schedule", date=str(schedule_date))

        stmt = (
            select(Appointment)
            .where(Appointment.scheduled_date == schedule_date)
            .order_by(Appointment.time_window_start.asc())
        )

        if include_relationships:
            stmt = stmt.options(
                selectinload(Appointment.job),
                selectinload(Appointment.staff),
            )

        result = await self.session.execute(stmt)
        appointments = list(result.scalars().all())

        self.log_completed("get_daily_schedule", count=len(appointments))
        return appointments

    async def get_staff_daily_schedule(
        self,
        staff_id: UUID,
        schedule_date: date,
        include_relationships: bool = False,
    ) -> list[Appointment]:
        """Get all appointments for a specific staff member on a specific date.

        Args:
            staff_id: UUID of the staff member
            schedule_date: Date to get appointments for
            include_relationships: Whether to load related entities

        Returns:
            List of appointments ordered by route_order then time_window_start

        Validates: Admin Dashboard Requirement 1.5
        """
        self.log_started(
            "get_staff_daily_schedule",
            staff_id=str(staff_id),
            date=str(schedule_date),
        )

        stmt = (
            select(Appointment)
            .where(Appointment.staff_id == staff_id)
            .where(Appointment.scheduled_date == schedule_date)
            .order_by(
                Appointment.route_order.asc().nullslast(),
                Appointment.time_window_start.asc(),
            )
        )

        if include_relationships:
            stmt = stmt.options(
                selectinload(Appointment.job),
                selectinload(Appointment.staff),
            )

        result = await self.session.execute(stmt)
        appointments = list(result.scalars().all())

        self.log_completed("get_staff_daily_schedule", count=len(appointments))
        return appointments

    async def get_weekly_schedule(
        self,
        start_date: date,
        include_relationships: bool = False,
    ) -> dict[date, list[Appointment]]:
        """Get all appointments for a week starting from start_date.

        Args:
            start_date: First day of the week
            include_relationships: Whether to load related entities

        Returns:
            Dictionary mapping dates to lists of appointments

        Validates: Admin Dashboard Requirement 1.5
        """
        self.log_started("get_weekly_schedule", start_date=str(start_date))

        end_date = start_date + timedelta(days=6)

        stmt = (
            select(Appointment)
            .where(Appointment.scheduled_date >= start_date)
            .where(Appointment.scheduled_date <= end_date)
            .order_by(
                Appointment.scheduled_date.asc(),
                Appointment.time_window_start.asc(),
            )
        )

        if include_relationships:
            stmt = stmt.options(
                selectinload(Appointment.job),
                selectinload(Appointment.staff),
            )

        result = await self.session.execute(stmt)
        appointments = list(result.scalars().all())

        # Group by date
        schedule: dict[date, list[Appointment]] = {}
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            schedule[current_date] = []

        for appointment in appointments:
            if appointment.scheduled_date in schedule:
                schedule[appointment.scheduled_date].append(appointment)

        self.log_completed(
            "get_weekly_schedule",
            total_appointments=len(appointments),
        )
        return schedule

    async def find_by_job(self, job_id: UUID) -> list[Appointment]:
        """Find all appointments for a specific job.

        Args:
            job_id: UUID of the job

        Returns:
            List of appointments for the job
        """
        self.log_started("find_by_job", job_id=str(job_id))

        stmt = (
            select(Appointment)
            .where(Appointment.job_id == job_id)
            .order_by(Appointment.scheduled_date.desc())
        )

        result = await self.session.execute(stmt)
        appointments = list(result.scalars().all())

        self.log_completed("find_by_job", count=len(appointments))
        return appointments

    async def find_by_staff(
        self,
        staff_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Appointment]:
        """Find all appointments for a specific staff member.

        Args:
            staff_id: UUID of the staff member
            date_from: Optional start date filter
            date_to: Optional end date filter

        Returns:
            List of appointments for the staff member
        """
        self.log_started("find_by_staff", staff_id=str(staff_id))

        stmt = select(Appointment).where(Appointment.staff_id == staff_id)

        if date_from is not None:
            stmt = stmt.where(Appointment.scheduled_date >= date_from)

        if date_to is not None:
            stmt = stmt.where(Appointment.scheduled_date <= date_to)

        stmt = stmt.order_by(
            Appointment.scheduled_date.asc(),
            Appointment.time_window_start.asc(),
        )

        result = await self.session.execute(stmt)
        appointments = list(result.scalars().all())

        self.log_completed("find_by_staff", count=len(appointments))
        return appointments

    async def find_by_status(self, status: AppointmentStatus) -> list[Appointment]:
        """Find all appointments with a specific status.

        Args:
            status: Appointment status to filter by

        Returns:
            List of appointments with the given status
        """
        self.log_started("find_by_status", status=status.value)

        stmt = (
            select(Appointment)
            .where(Appointment.status == status.value)
            .order_by(
                Appointment.scheduled_date.asc(),
                Appointment.time_window_start.asc(),
            )
        )

        result = await self.session.execute(stmt)
        appointments = list(result.scalars().all())

        self.log_completed("find_by_status", count=len(appointments))
        return appointments

    async def update_status(
        self,
        appointment_id: UUID,
        new_status: AppointmentStatus,
        arrived_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> Appointment | None:
        """Update the status of an appointment.

        Args:
            appointment_id: UUID of the appointment
            new_status: New status to set
            arrived_at: Arrival timestamp (for IN_PROGRESS status)
            completed_at: Completion timestamp (for COMPLETED status)

        Returns:
            Updated Appointment instance or None if not found
        """
        self.log_started(
            "update_status",
            appointment_id=str(appointment_id),
            new_status=new_status.value,
        )

        update_data: dict[str, Any] = {
            "status": new_status.value,
            "updated_at": datetime.now(),
        }

        if arrived_at is not None:
            update_data["arrived_at"] = arrived_at

        if completed_at is not None:
            update_data["completed_at"] = completed_at

        stmt = (
            update(Appointment)
            .where(Appointment.id == appointment_id)
            .values(**update_data)
            .returning(Appointment)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        appointment: Appointment | None = result.scalar_one_or_none()

        if appointment:
            self.log_completed(
                "update_status",
                appointment_id=str(appointment_id),
                new_status=new_status.value,
            )
        else:
            self.log_completed(
                "update_status",
                appointment_id=str(appointment_id),
                found=False,
            )

        return appointment

    async def count_by_date(self, schedule_date: date) -> int:
        """Count appointments for a specific date.

        Args:
            schedule_date: Date to count appointments for

        Returns:
            Count of appointments on the given date

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("count_by_date", date=str(schedule_date))

        stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.scheduled_date == schedule_date)
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        self.log_completed("count_by_date", count=count)
        return count
