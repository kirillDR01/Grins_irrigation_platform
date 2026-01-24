"""
Staff model for staff management.

This module defines the Staff SQLAlchemy model representing staff members
in the Grin's Irrigation Platform.

Validates: Requirements 8.1-8.10
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import JSON, Boolean, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base
from grins_platform.models.enums import SkillLevel, StaffRole

if TYPE_CHECKING:
    from grins_platform.models.appointment import Appointment
    from grins_platform.models.staff_availability import StaffAvailability


class Staff(Base):
    """Staff model representing an employee.

    Attributes:
        id: Unique identifier for the staff member
        name: Full name of the staff member
        phone: Phone number (required)
        email: Email address (optional)
        role: Staff role (tech, sales, admin)
        skill_level: Skill level (junior, senior, lead)
        certifications: List of certifications
        is_available: Whether currently available for work
        availability_notes: Notes about availability
        hourly_rate: Hourly compensation rate
        is_active: Whether the staff member is active
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Validates: Requirements 8.1-8.10
    """

    __tablename__ = "staff"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid(),
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)  # Requirement 8.10
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Role and skills (Requirements 8.2, 8.3)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    skill_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    certifications: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True,
    )  # Requirement 8.8

    # Availability (Requirements 9.1, 9.2)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true",
    )
    availability_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compensation (Requirement 8.9)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Equipment Assignment (Requirement 2.1 - Route Optimization)
    assigned_equipment: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, server_default="[]",
    )

    # Starting Location (Requirement 3.1 - Route Optimization)
    default_start_address: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    default_start_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_start_lat: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True,
    )
    default_start_lng: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true",
    )

    # Timestamps (Requirement 8.7)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="staff",
    )
    availability_entries: Mapped[list["StaffAvailability"]] = relationship(
        "StaffAvailability",
        back_populates="staff",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation of the staff member."""
        return f"<Staff(id={self.id}, name='{self.name}', role='{self.role}')>"

    @property
    def role_enum(self) -> StaffRole:
        """Get the role as an enum value."""
        return StaffRole(self.role)

    @property
    def skill_level_enum(self) -> Optional[SkillLevel]:
        """Get the skill level as an enum value."""
        return SkillLevel(self.skill_level) if self.skill_level else None

    def to_dict(self) -> dict[str, Any]:
        """Convert the staff member to a dictionary.

        Returns:
            Dictionary representation of the staff member.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "role": self.role,
            "skill_level": self.skill_level,
            "certifications": self.certifications,
            "assigned_equipment": self.assigned_equipment,
            "default_start_address": self.default_start_address,
            "default_start_city": self.default_start_city,
            "default_start_lat": (
                float(self.default_start_lat) if self.default_start_lat else None
            ),
            "default_start_lng": (
                float(self.default_start_lng) if self.default_start_lng else None
            ),
            "is_available": self.is_available,
            "availability_notes": self.availability_notes,
            "hourly_rate": float(self.hourly_rate) if self.hourly_rate else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
