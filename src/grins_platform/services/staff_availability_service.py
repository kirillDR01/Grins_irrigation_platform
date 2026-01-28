"""
Staff Availability service for business logic operations.

This module provides the StaffAvailabilityService class for all staff
availability-related business logic operations.

Validates: Requirements 1.1-1.5 (Route Optimization)
"""

from __future__ import annotations

from datetime import (
    date as date_type,
    timedelta,
)
from typing import TYPE_CHECKING

from grins_platform.exceptions import StaffAvailabilityNotFoundError, StaffNotFoundError
from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.staff_availability_repository import (
    StaffAvailabilityRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.schemas.staff_availability import (
    AvailableStaffOnDateResponse,
    StaffAvailabilityCreate,
    StaffAvailabilityResponse,
    StaffAvailabilityUpdate,
    StaffWithAvailability,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class StaffAvailabilityService(LoggerMixin):
    """Service for staff availability business logic."""

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        super().__init__()
        self.session = session
        self.repository = StaffAvailabilityRepository(session)
        self.staff_repository = StaffRepository(session)

    async def create_availability(
        self,
        staff_id: UUID,
        data: StaffAvailabilityCreate,
    ) -> StaffAvailabilityResponse:
        """Create a new staff availability entry."""
        self.log_started(
            "create_availability",
            staff_id=str(staff_id),
            date=str(data.date),
        )

        staff = await self.staff_repository.get_by_id(staff_id)
        if staff is None:
            self.log_rejected("create_availability", reason="staff_not_found")
            raise StaffNotFoundError(staff_id)

        existing = await self.repository.get_by_staff_and_date(staff_id, data.date)
        if existing is not None:
            self.log_rejected("create_availability", reason="already_exists")
            msg = f"Availability already exists for staff {staff_id} on {data.date}"
            raise ValueError(msg)

        availability = await self.repository.create(
            staff_id=staff_id,
            availability_date=data.date,
            start_time=data.start_time,
            end_time=data.end_time,
            is_available=data.is_available,
            lunch_start=data.lunch_start,
            lunch_duration_minutes=data.lunch_duration_minutes,
            notes=data.notes,
        )

        await self.session.commit()
        self.log_completed("create_availability", availability_id=str(availability.id))
        return StaffAvailabilityResponse.model_validate(availability)  # type: ignore[no-any-return]

    async def get_availability(
        self,
        availability_id: UUID,
    ) -> StaffAvailabilityResponse:
        """Get a staff availability entry by ID."""
        self.log_started("get_availability", availability_id=str(availability_id))

        availability = await self.repository.get_by_id(availability_id)
        if availability is None:
            self.log_rejected("get_availability", reason="not_found")
            raise StaffAvailabilityNotFoundError(availability_id)

        self.log_completed("get_availability", availability_id=str(availability_id))
        return StaffAvailabilityResponse.model_validate(availability)  # type: ignore[no-any-return]

    async def get_availability_by_date(
        self,
        staff_id: UUID,
        target_date: date_type,
    ) -> StaffAvailabilityResponse:
        """Get availability for a specific staff member and date."""
        self.log_started(
            "get_availability_by_date",
            staff_id=str(staff_id),
            date=str(target_date),
        )

        staff = await self.staff_repository.get_by_id(staff_id)
        if staff is None:
            self.log_rejected("get_availability_by_date", reason="staff_not_found")
            raise StaffNotFoundError(staff_id)

        availability = await self.repository.get_by_staff_and_date(
            staff_id,
            target_date,
        )
        if availability is None:
            self.log_rejected("get_availability_by_date", reason="not_found")
            raise StaffAvailabilityNotFoundError(staff_id)

        self.log_completed(
            "get_availability_by_date",
            staff_id=str(staff_id),
            date=str(target_date),
        )
        return StaffAvailabilityResponse.model_validate(availability)  # type: ignore[no-any-return]

    async def list_availability(
        self,
        staff_id: UUID,
        start_date: date_type | None = None,
        end_date: date_type | None = None,
    ) -> list[StaffAvailabilityResponse]:
        """List availability entries for a staff member."""
        self.log_started(
            "list_availability",
            staff_id=str(staff_id),
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
        )

        staff = await self.staff_repository.get_by_id(staff_id)
        if staff is None:
            self.log_rejected("list_availability", reason="staff_not_found")
            raise StaffNotFoundError(staff_id)

        today = date_type.today()
        default_end = today + timedelta(days=30)
        availabilities = await self.repository.get_by_staff_and_date_range(
            staff_id,
            start_date or today,
            end_date or default_end,
        )

        self.log_completed(
            "list_availability",
            staff_id=str(staff_id),
            count=len(availabilities),
        )
        return [StaffAvailabilityResponse.model_validate(a) for a in availabilities]

    async def update_availability(
        self,
        staff_id: UUID,
        target_date: date_type,
        data: StaffAvailabilityUpdate,
    ) -> StaffAvailabilityResponse:
        """Update a staff availability entry."""
        self.log_started(
            "update_availability",
            staff_id=str(staff_id),
            date=str(target_date),
        )

        staff = await self.staff_repository.get_by_id(staff_id)
        if staff is None:
            self.log_rejected("update_availability", reason="staff_not_found")
            raise StaffNotFoundError(staff_id)

        availability = await self.repository.update(
            staff_id=staff_id,
            target_date=target_date,
            start_time=data.start_time,
            end_time=data.end_time,
            is_available=data.is_available,
            lunch_start=data.lunch_start,
            lunch_duration_minutes=data.lunch_duration_minutes,
            notes=data.notes,
        )

        if availability is None:
            self.log_rejected("update_availability", reason="not_found")
            raise StaffAvailabilityNotFoundError(staff_id)

        await self.session.commit()
        self.log_completed(
            "update_availability",
            staff_id=str(staff_id),
            date=str(target_date),
        )
        return StaffAvailabilityResponse.model_validate(availability)  # type: ignore[no-any-return]

    async def delete_availability(
        self,
        staff_id: UUID,
        target_date: date_type,
    ) -> None:
        """Delete a staff availability entry."""
        self.log_started(
            "delete_availability",
            staff_id=str(staff_id),
            date=str(target_date),
        )

        staff = await self.staff_repository.get_by_id(staff_id)
        if staff is None:
            self.log_rejected("delete_availability", reason="staff_not_found")
            raise StaffNotFoundError(staff_id)

        deleted = await self.repository.delete(staff_id, target_date)

        if not deleted:
            self.log_rejected("delete_availability", reason="not_found")
            raise StaffAvailabilityNotFoundError(staff_id)

        await self.session.commit()
        self.log_completed(
            "delete_availability",
            staff_id=str(staff_id),
            date=str(target_date),
        )

    async def get_available_staff_on_date(
        self,
        target_date: date_type,
    ) -> AvailableStaffOnDateResponse:
        """Get all staff members available on a specific date."""
        self.log_started("get_available_staff_on_date", date=str(target_date))

        staff_with_availability = await self.repository.get_available_staff_on_date(
            target_date,
        )

        available_staff = [
            StaffWithAvailability(
                id=staff.id,
                name=staff.name,
                availability=StaffAvailabilityResponse.model_validate(availability),
            )
            for staff, availability in staff_with_availability
        ]

        self.log_completed(
            "get_available_staff_on_date",
            date=str(target_date),
            count=len(available_staff),
        )

        return AvailableStaffOnDateResponse(
            date=target_date,
            available_staff=available_staff,
            total_available=len(available_staff),
        )
