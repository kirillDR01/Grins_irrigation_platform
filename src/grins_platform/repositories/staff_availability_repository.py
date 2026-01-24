"""
Staff Availability repository for database operations.

This module provides the StaffAvailabilityRepository class for all staff
availability-related database operations using SQLAlchemy 2.0 async patterns.

Validates: Requirements 1.1-1.5 (Route Optimization)
"""

from __future__ import annotations

from datetime import (
    date as date_type,
    datetime,
    time,
)
from typing import TYPE_CHECKING

from sqlalchemy import and_, delete, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.staff import Staff
from grins_platform.models.staff_availability import StaffAvailability

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class StaffAvailabilityRepository(LoggerMixin):
    """Repository for staff availability database operations.

    This class handles all database operations for staff availability
    including CRUD operations and queries.

    Attributes:
        session: AsyncSession for database operations

    Validates: Requirements 1.1-1.5 (Route Optimization)
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
        staff_id: UUID,
        availability_date: date_type,
        start_time: time = time(7, 0),
        end_time: time = time(17, 0),
        is_available: bool = True,
        lunch_start: time | None = time(12, 0),
        lunch_duration_minutes: int = 30,
        notes: str | None = None,
    ) -> StaffAvailability:
        """Create a new staff availability entry.

        Args:
            staff_id: UUID of the staff member
            availability_date: Date of availability
            start_time: Start time of availability window
            end_time: End time of availability window
            is_available: Whether the staff member is available
            lunch_start: Start time of lunch break
            lunch_duration_minutes: Duration of lunch break in minutes
            notes: Additional notes

        Returns:
            Created StaffAvailability instance

        Validates: Requirement 1.1
        """
        self.log_started(
            "create",
            staff_id=str(staff_id),
            date=str(availability_date),
        )

        availability = StaffAvailability(
            staff_id=staff_id,
            date=availability_date,
            start_time=start_time,
            end_time=end_time,
            is_available=is_available,
            lunch_start=lunch_start,
            lunch_duration_minutes=lunch_duration_minutes,
            notes=notes,
        )

        self.session.add(availability)
        await self.session.flush()
        await self.session.refresh(availability)

        self.log_completed("create", availability_id=str(availability.id))
        return availability

    async def get_by_id(self, availability_id: UUID) -> StaffAvailability | None:
        """Get a staff availability entry by ID.

        Args:
            availability_id: UUID of the availability entry

        Returns:
            StaffAvailability instance or None if not found
        """
        self.log_started("get_by_id", availability_id=str(availability_id))

        stmt = select(StaffAvailability).where(StaffAvailability.id == availability_id)
        result = await self.session.execute(stmt)
        availability: StaffAvailability | None = result.scalar_one_or_none()

        if availability:
            self.log_completed("get_by_id", availability_id=str(availability_id))
        else:
            self.log_completed(
                "get_by_id",
                availability_id=str(availability_id),
                found=False,
            )

        return availability

    async def get_by_staff_and_date(
        self,
        staff_id: UUID,
        target_date: date_type,
    ) -> StaffAvailability | None:
        """Get availability entry for a specific staff member and date.

        Args:
            staff_id: UUID of the staff member
            target_date: Date to query

        Returns:
            StaffAvailability instance or None if not found

        Validates: Requirement 1.2
        """
        self.log_started(
            "get_by_staff_and_date",
            staff_id=str(staff_id),
            date=str(target_date),
        )

        stmt = select(StaffAvailability).where(
            and_(
                StaffAvailability.staff_id == staff_id,
                StaffAvailability.date == target_date,
            ),
        )
        result = await self.session.execute(stmt)
        availability: StaffAvailability | None = result.scalar_one_or_none()

        if availability:
            self.log_completed(
                "get_by_staff_and_date",
                staff_id=str(staff_id),
                date=str(target_date),
            )
        else:
            self.log_completed(
                "get_by_staff_and_date",
                staff_id=str(staff_id),
                date=str(target_date),
                found=False,
            )

        return availability

    async def get_by_staff_and_date_range(
        self,
        staff_id: UUID,
        start_date: date_type,
        end_date: date_type,
    ) -> list[StaffAvailability]:
        """Get availability entries for a staff member within a date range.

        Args:
            staff_id: UUID of the staff member
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of StaffAvailability instances

        Validates: Requirement 1.2
        """
        self.log_started(
            "get_by_staff_and_date_range",
            staff_id=str(staff_id),
            start_date=str(start_date),
            end_date=str(end_date),
        )

        stmt = (
            select(StaffAvailability)
            .where(
                and_(
                    StaffAvailability.staff_id == staff_id,
                    StaffAvailability.date >= start_date,
                    StaffAvailability.date <= end_date,
                ),
            )
            .order_by(StaffAvailability.date)
        )

        result = await self.session.execute(stmt)
        availabilities = list(result.scalars().all())

        self.log_completed(
            "get_by_staff_and_date_range",
            staff_id=str(staff_id),
            count=len(availabilities),
        )
        return availabilities

    async def get_available_staff_on_date(
        self,
        target_date: date_type,
    ) -> list[tuple[Staff, StaffAvailability]]:
        """Get all staff members available on a specific date.

        Returns staff members who have is_available=true entries for the date.
        Staff without entries are treated as unavailable (Requirement 1.8).

        Args:
            target_date: Date to query

        Returns:
            List of tuples (Staff, StaffAvailability) for available staff

        Validates: Requirements 1.5, 1.8
        """
        self.log_started("get_available_staff_on_date", date=str(target_date))

        stmt = (
            select(Staff, StaffAvailability)
            .join(
                StaffAvailability,
                and_(
                    Staff.id == StaffAvailability.staff_id,
                    StaffAvailability.date == target_date,
                    StaffAvailability.is_available == True,  # noqa: E712
                ),
            )
            .where(Staff.is_active == True)  # noqa: E712
            .order_by(Staff.name)
        )

        result = await self.session.execute(stmt)
        staff_with_availability: list[tuple[Staff, StaffAvailability]] = [
            (row[0], row[1]) for row in result.all()
        ]

        self.log_completed(
            "get_available_staff_on_date",
            date=str(target_date),
            count=len(staff_with_availability),
        )
        return staff_with_availability

    async def update(
        self,
        staff_id: UUID,
        target_date: date_type,
        start_time: time | None = None,
        end_time: time | None = None,
        is_available: bool | None = None,
        lunch_start: time | None = None,
        lunch_duration_minutes: int | None = None,
        notes: str | None = None,
    ) -> StaffAvailability | None:
        """Update a staff availability entry.

        Args:
            staff_id: UUID of the staff member
            target_date: Date of the availability entry to update
            start_time: New start time (optional)
            end_time: New end time (optional)
            is_available: New availability status (optional)
            lunch_start: New lunch start time (optional)
            lunch_duration_minutes: New lunch duration (optional)
            notes: New notes (optional)

        Returns:
            Updated StaffAvailability instance or None if not found

        Validates: Requirement 1.3
        """
        self.log_started(
            "update",
            staff_id=str(staff_id),
            date=str(target_date),
        )

        # Build update data from non-None values
        update_data: dict[str, time | bool | int | str | datetime] = {
            "updated_at": datetime.now(),
        }

        if start_time is not None:
            update_data["start_time"] = start_time
        if end_time is not None:
            update_data["end_time"] = end_time
        if is_available is not None:
            update_data["is_available"] = is_available
        if lunch_start is not None:
            update_data["lunch_start"] = lunch_start
        if lunch_duration_minutes is not None:
            update_data["lunch_duration_minutes"] = lunch_duration_minutes
        if notes is not None:
            update_data["notes"] = notes

        stmt = (
            update(StaffAvailability)
            .where(
                and_(
                    StaffAvailability.staff_id == staff_id,
                    StaffAvailability.date == target_date,
                ),
            )
            .values(**update_data)
            .returning(StaffAvailability)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        availability: StaffAvailability | None = result.scalar_one_or_none()

        if availability:
            self.log_completed(
                "update",
                staff_id=str(staff_id),
                date=str(target_date),
            )
        else:
            self.log_completed(
                "update",
                staff_id=str(staff_id),
                date=str(target_date),
                found=False,
            )

        return availability

    async def delete(
        self,
        staff_id: UUID,
        target_date: date_type,
    ) -> bool:
        """Delete a staff availability entry.

        Args:
            staff_id: UUID of the staff member
            target_date: Date of the availability entry to delete

        Returns:
            True if entry was deleted, False if not found

        Validates: Requirement 1.4
        """
        self.log_started(
            "delete",
            staff_id=str(staff_id),
            date=str(target_date),
        )

        stmt = delete(StaffAvailability).where(
            and_(
                StaffAvailability.staff_id == staff_id,
                StaffAvailability.date == target_date,
            ),
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        rowcount: int = getattr(result, "rowcount", 0) or 0
        deleted: bool = rowcount > 0

        if deleted:
            self.log_completed(
                "delete",
                staff_id=str(staff_id),
                date=str(target_date),
            )
        else:
            self.log_completed(
                "delete",
                staff_id=str(staff_id),
                date=str(target_date),
                found=False,
            )

        return deleted

    async def delete_by_id(self, availability_id: UUID) -> bool:
        """Delete a staff availability entry by ID.

        Args:
            availability_id: UUID of the availability entry

        Returns:
            True if entry was deleted, False if not found
        """
        self.log_started("delete_by_id", availability_id=str(availability_id))

        stmt = delete(StaffAvailability).where(
            StaffAvailability.id == availability_id,
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        rowcount: int = getattr(result, "rowcount", 0) or 0
        deleted: bool = rowcount > 0

        if deleted:
            self.log_completed("delete_by_id", availability_id=str(availability_id))
        else:
            self.log_completed(
                "delete_by_id",
                availability_id=str(availability_id),
                found=False,
            )

        return deleted

    async def exists(
        self,
        staff_id: UUID,
        target_date: date_type,
    ) -> bool:
        """Check if an availability entry exists for a staff member and date.

        Args:
            staff_id: UUID of the staff member
            target_date: Date to check

        Returns:
            True if entry exists, False otherwise
        """
        self.log_started(
            "exists",
            staff_id=str(staff_id),
            date=str(target_date),
        )

        stmt = select(StaffAvailability.id).where(
            and_(
                StaffAvailability.staff_id == staff_id,
                StaffAvailability.date == target_date,
            ),
        )

        result = await self.session.execute(stmt)
        exists = result.scalar_one_or_none() is not None

        self.log_completed(
            "exists",
            staff_id=str(staff_id),
            date=str(target_date),
            exists=exists,
        )
        return exists
