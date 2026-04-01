"""
ServiceZone model for geographic service zone management.

This module defines the ServiceZone SQLAlchemy model representing
configurable geographic service zones for the AI scheduling system.

Validates: Requirements 3.3, 19.1
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from grins_platform.database import Base


class ServiceZone(Base):
    """ServiceZone model representing a geographic service zone.

    Attributes:
        id: Unique identifier for the service zone
        name: Zone name (e.g., North, South, East, West)
        boundary_type: Type of boundary (polygon, zip_group, radius)
        boundary_data: Polygon coordinates, ZIP codes, or center+radius
        assigned_staff_ids: Default staff assigned to this zone
        is_active: Whether the zone is currently active
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Validates: Requirements 3.3, 19.1
    """

    __tablename__ = "service_zones"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Zone details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    boundary_type: Mapped[str] = mapped_column(String(20), nullable=False)
    boundary_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    assigned_staff_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation of the service zone."""
        return (
            f"<ServiceZone(id={self.id}, name='{self.name}', "
            f"type='{self.boundary_type}')>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the service zone to a dictionary.

        Returns:
            Dictionary representation of the service zone.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "boundary_type": self.boundary_type,
            "boundary_data": self.boundary_data,
            "assigned_staff_ids": self.assigned_staff_ids,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
