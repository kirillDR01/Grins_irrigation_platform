"""
Staff repository for database operations.

This module provides the StaffRepository class for all staff-related
database operations using SQLAlchemy 2.0 async patterns.

Validates: Requirement 8.1-8.6, 9.1-9.5
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import SkillLevel, StaffRole  # noqa: TC001
from grins_platform.models.staff import Staff

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class StaffRepository(LoggerMixin):
    """Repository for staff database operations.

    This class handles all database operations for staff including
    CRUD operations and queries.

    Attributes:
        session: AsyncSession for database operations

    Validates: Requirement 8.1-8.6, 9.1-9.5
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
        name: str,
        phone: str,
        role: StaffRole,
        email: str | None = None,
        skill_level: SkillLevel | None = None,
        certifications: list[str] | None = None,
        hourly_rate: float | None = None,
        is_available: bool = True,
        availability_notes: str | None = None,
    ) -> Staff:
        """Create a new staff record.

        Args:
            name: Staff member name
            phone: Phone number (normalized)
            role: Staff role
            email: Email address (optional)
            skill_level: Skill level (optional)
            certifications: List of certifications
            hourly_rate: Hourly rate
            is_available: Availability status
            availability_notes: Notes about availability

        Returns:
            Created Staff instance

        Validates: Requirement 8.1
        """
        self.log_started("create", name=name, role=role.value)

        staff = Staff(
            name=name,
            phone=phone,
            email=email,
            role=role,
            skill_level=skill_level,
            certifications=certifications,
            hourly_rate=hourly_rate,
            is_available=is_available,
            availability_notes=availability_notes,
        )

        self.session.add(staff)
        await self.session.flush()
        await self.session.refresh(staff)

        self.log_completed("create", staff_id=str(staff.id))
        return staff

    async def get_by_id(
        self,
        staff_id: UUID,
        include_inactive: bool = False,
    ) -> Staff | None:
        """Get a staff member by ID.

        Args:
            staff_id: UUID of the staff member
            include_inactive: Whether to include inactive staff

        Returns:
            Staff instance or None if not found

        Validates: Requirement 8.4
        """
        self.log_started("get_by_id", staff_id=str(staff_id))

        stmt = select(Staff).where(Staff.id == staff_id)

        if not include_inactive:
            stmt = stmt.where(Staff.is_active == True)  # noqa: E712

        result = await self.session.execute(stmt)
        staff: Staff | None = result.scalar_one_or_none()

        if staff:
            self.log_completed("get_by_id", staff_id=str(staff_id))
        else:
            self.log_completed("get_by_id", staff_id=str(staff_id), found=False)

        return staff

    async def update(
        self,
        staff_id: UUID,
        data: dict[str, Any],
    ) -> Staff | None:
        """Update a staff record.

        Args:
            staff_id: UUID of the staff to update
            data: Dictionary of fields to update

        Returns:
            Updated Staff instance or None if not found

        Validates: Requirement 8.5
        """
        self.log_started("update", staff_id=str(staff_id))

        # Remove None values
        update_data = {k: v for k, v in data.items() if v is not None}

        if not update_data:
            return await self.get_by_id(staff_id, include_inactive=True)

        update_data["updated_at"] = datetime.now()

        stmt = (
            update(Staff)
            .where(Staff.id == staff_id)
            .values(**update_data)
            .returning(Staff)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        staff: Staff | None = result.scalar_one_or_none()

        if staff:
            self.log_completed("update", staff_id=str(staff_id))
        else:
            self.log_completed("update", staff_id=str(staff_id), found=False)

        return staff

    async def deactivate(self, staff_id: UUID) -> bool:
        """Deactivate a staff member (soft delete).

        Args:
            staff_id: UUID of the staff to deactivate

        Returns:
            True if staff was deactivated, False if not found

        Validates: Requirement 8.6
        """
        self.log_started("deactivate", staff_id=str(staff_id))

        stmt = (
            update(Staff)
            .where(Staff.id == staff_id)
            .where(Staff.is_active == True)  # noqa: E712
            .values(is_active=False, updated_at=datetime.now())
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        rowcount: int = getattr(result, "rowcount", 0) or 0
        deactivated: bool = rowcount > 0

        if deactivated:
            self.log_completed("deactivate", staff_id=str(staff_id))
        else:
            self.log_completed("deactivate", staff_id=str(staff_id), found=False)

        return deactivated

    async def find_available(self, active_only: bool = True) -> list[Staff]:
        """Find available staff members.

        Args:
            active_only: Whether to return only active staff

        Returns:
            List of available Staff instances

        Validates: Requirement 9.3
        """
        self.log_started("find_available")

        stmt = select(Staff).where(Staff.is_available == True)  # noqa: E712

        if active_only:
            stmt = stmt.where(Staff.is_active == True)  # noqa: E712

        stmt = stmt.order_by(Staff.name)

        result = await self.session.execute(stmt)
        staff = list(result.scalars().all())

        self.log_completed("find_available", count=len(staff))
        return staff

    async def find_by_role(
        self,
        role: StaffRole,
        active_only: bool = True,
    ) -> list[Staff]:
        """Find staff by role.

        Args:
            role: Staff role to filter by
            active_only: Whether to return only active staff

        Returns:
            List of matching Staff instances

        Validates: Requirement 9.4
        """
        self.log_started("find_by_role", role=role.value)

        stmt = select(Staff).where(Staff.role == role)

        if active_only:
            stmt = stmt.where(Staff.is_active == True)  # noqa: E712

        stmt = stmt.order_by(Staff.name)

        result = await self.session.execute(stmt)
        staff = list(result.scalars().all())

        self.log_completed("find_by_role", count=len(staff))
        return staff

    async def update_availability(
        self,
        staff_id: UUID,
        is_available: bool,
        availability_notes: str | None = None,
    ) -> Staff | None:
        """Update staff availability.

        Args:
            staff_id: UUID of the staff member
            is_available: New availability status
            availability_notes: Notes about availability

        Returns:
            Updated Staff instance or None if not found

        Validates: Requirement 9.1, 9.2
        """
        self.log_started(
            "update_availability",
            staff_id=str(staff_id),
            is_available=is_available,
        )

        update_data: dict[str, Any] = {
            "is_available": is_available,
            "updated_at": datetime.now(),
        }

        if availability_notes is not None:
            update_data["availability_notes"] = availability_notes

        stmt = (
            update(Staff)
            .where(Staff.id == staff_id)
            .where(Staff.is_active == True)  # noqa: E712
            .values(**update_data)
            .returning(Staff)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        staff: Staff | None = result.scalar_one_or_none()

        if staff:
            self.log_completed("update_availability", staff_id=str(staff_id))
        else:
            self.log_completed(
                "update_availability",
                staff_id=str(staff_id),
                found=False,
            )

        return staff

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        role: StaffRole | None = None,
        skill_level: SkillLevel | None = None,
        is_available: bool | None = None,
        is_active: bool | None = None,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> tuple[list[Staff], int]:
        """List staff with filtering and pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            role: Filter by role
            skill_level: Filter by skill level
            is_available: Filter by availability
            is_active: Filter by active status
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (list of staff, total count)

        Validates: Requirement 9.4, 9.5
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        # Base query
        base_query = select(Staff)

        # Apply filters
        if role is not None:
            base_query = base_query.where(Staff.role == role)

        if skill_level is not None:
            base_query = base_query.where(Staff.skill_level == skill_level)

        if is_available is not None:
            base_query = base_query.where(Staff.is_available == is_available)

        if is_active is not None:
            base_query = base_query.where(Staff.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Staff, sort_by, Staff.name)
        sort_column = sort_column.desc() if sort_order == "desc" else sort_column.asc()

        # Apply pagination
        offset = (page - 1) * page_size
        paginated_query = (
            base_query.order_by(sort_column).offset(offset).limit(page_size)
        )

        result = await self.session.execute(paginated_query)
        staff = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(staff), total=total)
        return staff, total
