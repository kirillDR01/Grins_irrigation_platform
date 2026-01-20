"""
Staff service for business logic operations.

This module provides the StaffService class for all staff-related
business operations.

Validates: Requirement 8.1-8.10, 9.1-9.5, 11.3-11.9
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grins_platform.exceptions import StaffNotFoundError
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import SkillLevel, StaffRole  # noqa: TC001

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.staff import Staff
    from grins_platform.repositories.staff_repository import StaffRepository
    from grins_platform.schemas.staff import StaffCreate, StaffUpdate


class StaffService(LoggerMixin):
    """Service for staff management operations.

    This class handles all business logic for staff including
    CRUD operations, availability management, and role filtering.

    Attributes:
        repository: StaffRepository for database operations

    Validates: Requirement 8.1-8.10, 9.1-9.5, 11.3-11.9
    """

    DOMAIN = "staff"

    def __init__(self, repository: StaffRepository) -> None:
        """Initialize service with repository.

        Args:
            repository: StaffRepository for database operations
        """
        super().__init__()
        self.repository = repository

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to 10 digits.

        Args:
            phone: Phone number string

        Returns:
            Normalized 10-digit phone number
        """
        return "".join(filter(str.isdigit, phone))

    async def create_staff(self, data: StaffCreate) -> Staff:
        """Create a new staff member.

        Args:
            data: Staff creation data

        Returns:
            Created Staff instance

        Validates: Requirement 8.1
        """
        self.log_started("create_staff", name=data.name, role=data.role.value)

        # Normalize phone number
        normalized_phone = self._normalize_phone(data.phone)

        staff = await self.repository.create(
            name=data.name,
            phone=normalized_phone,
            email=data.email,
            role=data.role,
            skill_level=data.skill_level,
            certifications=data.certifications,
            hourly_rate=float(data.hourly_rate) if data.hourly_rate else None,
            is_available=data.is_available,
            availability_notes=data.availability_notes,
        )

        self.log_completed("create_staff", staff_id=str(staff.id))
        return staff

    async def get_staff(self, staff_id: UUID) -> Staff:
        """Get staff member by ID.

        Args:
            staff_id: UUID of the staff member

        Returns:
            Staff instance

        Raises:
            StaffNotFoundError: If staff not found

        Validates: Requirement 8.4
        """
        self.log_started("get_staff", staff_id=str(staff_id))

        staff = await self.repository.get_by_id(staff_id, include_inactive=True)
        if not staff:
            self.log_rejected("get_staff", reason="not_found")
            raise StaffNotFoundError(staff_id)

        self.log_completed("get_staff", staff_id=str(staff_id))
        return staff

    async def update_staff(self, staff_id: UUID, data: StaffUpdate) -> Staff:
        """Update staff member.

        Args:
            staff_id: UUID of the staff to update
            data: Update data

        Returns:
            Updated Staff instance

        Raises:
            StaffNotFoundError: If staff not found

        Validates: Requirement 8.5
        """
        self.log_started("update_staff", staff_id=str(staff_id))

        # Check if staff exists
        staff = await self.repository.get_by_id(staff_id, include_inactive=True)
        if not staff:
            self.log_rejected("update_staff", reason="not_found")
            raise StaffNotFoundError(staff_id)

        # Build update dict
        update_data = data.model_dump(exclude_unset=True)

        # Normalize phone if provided
        if update_data.get("phone"):
            update_data["phone"] = self._normalize_phone(update_data["phone"])

        # Convert enums and decimals
        if update_data.get("role"):
            update_data["role"] = update_data["role"].value
        if update_data.get("skill_level"):
            update_data["skill_level"] = update_data["skill_level"].value
        if "hourly_rate" in update_data and update_data["hourly_rate"] is not None:
            update_data["hourly_rate"] = float(update_data["hourly_rate"])

        updated = await self.repository.update(staff_id, update_data)

        self.log_completed("update_staff", staff_id=str(staff_id))
        return updated  # type: ignore[return-value]

    async def deactivate_staff(self, staff_id: UUID) -> None:
        """Deactivate a staff member (soft delete).

        Args:
            staff_id: UUID of the staff to deactivate

        Raises:
            StaffNotFoundError: If staff not found

        Validates: Requirement 8.6
        """
        self.log_started("deactivate_staff", staff_id=str(staff_id))

        # Check if staff exists
        staff = await self.repository.get_by_id(staff_id, include_inactive=True)
        if not staff:
            self.log_rejected("deactivate_staff", reason="not_found")
            raise StaffNotFoundError(staff_id)

        await self.repository.deactivate(staff_id)

        self.log_completed("deactivate_staff", staff_id=str(staff_id))

    async def update_availability(
        self,
        staff_id: UUID,
        is_available: bool,
        availability_notes: str | None = None,
    ) -> Staff:
        """Update staff availability.

        Args:
            staff_id: UUID of the staff member
            is_available: New availability status
            availability_notes: Notes about availability

        Returns:
            Updated Staff instance

        Raises:
            StaffNotFoundError: If staff not found

        Validates: Requirement 9.1, 9.2
        """
        self.log_started(
            "update_availability",
            staff_id=str(staff_id),
            is_available=is_available,
        )

        # Check if staff exists
        staff = await self.repository.get_by_id(staff_id)
        if not staff:
            self.log_rejected("update_availability", reason="not_found")
            raise StaffNotFoundError(staff_id)

        updated = await self.repository.update_availability(
            staff_id=staff_id,
            is_available=is_available,
            availability_notes=availability_notes,
        )

        self.log_completed("update_availability", staff_id=str(staff_id))
        return updated  # type: ignore[return-value]

    async def list_staff(
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
        """List staff with filtering.

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
        self.log_started("list_staff", page=page, page_size=page_size)

        staff, total = await self.repository.list_with_filters(
            page=page,
            page_size=page_size,
            role=role,
            skill_level=skill_level,
            is_available=is_available,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        self.log_completed("list_staff", count=len(staff), total=total)
        return staff, total

    async def get_available_staff(self) -> list[Staff]:
        """Get all available and active staff.

        Returns:
            List of available Staff instances

        Validates: Requirement 9.3
        """
        self.log_started("get_available_staff")

        staff = await self.repository.find_available(active_only=True)

        self.log_completed("get_available_staff", count=len(staff))
        return staff

    async def get_by_role(self, role: StaffRole) -> list[Staff]:
        """Get all active staff by role.

        Args:
            role: Staff role to filter by

        Returns:
            List of Staff instances with the specified role

        Validates: Requirement 9.4
        """
        self.log_started("get_by_role", role=role.value)

        staff = await self.repository.find_by_role(role, active_only=True)

        self.log_completed("get_by_role", count=len(staff))
        return staff
