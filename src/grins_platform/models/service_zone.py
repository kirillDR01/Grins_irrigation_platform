"""
Service zone model for geographic scheduling boundaries.

Configurable geographic service zones used by criterion #3 (service
zone boundaries) in the AI scheduling engine.

Validates: Requirements 3.3, 19.1, 19.2
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
    """Geographic service zone.

    Defines a geographic boundary (polygon, ZIP group, or radius)
    with default staff assignments. Used by the AI scheduling engine
    to keep resources within their assigned zones unless cross-zone
    assignment is more efficient.

    Attributes:
        id: Unique identifier (UUID).
        name: Zone name (North, South, etc.).
        boundary_type: Type of boundary (polygon, zip_group, radius).
        boundary_data: Polygon coordinates, ZIP codes, or center+radius.
        assigned_staff_ids: Default staff assigned to this zone.
        is_active: Whether the zone is active.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "service_zones"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Zone definition
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    boundary_type: Mapped[str] = mapped_column(String(20), nullable=False)
    boundary_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Staff assignments
    assigned_staff_ids: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ServiceZone("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"boundary_type='{self.boundary_type}')>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
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
