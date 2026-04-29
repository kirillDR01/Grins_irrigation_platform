"""
Resource truck inventory model.

Tracks parts inventory per resource's truck for field consumption
tracking and reorder alerting.

Validates: Requirements 4.2, 20.1, 20.2
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.staff import Staff


class ResourceTruckInventory(Base):
    """Truck inventory item for a resource.

    Tracks individual parts/supplies on a resource's truck with
    quantity tracking and reorder threshold alerting.

    Attributes:
        id: Unique identifier (UUID).
        staff_id: Resource whose truck this inventory belongs to.
        part_name: Name of the part or supply.
        quantity: Current stock quantity.
        reorder_threshold: Minimum quantity before reorder alert.
        last_restocked: When the part was last restocked.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "resource_truck_inventory"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Owner
    staff_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id"),
        nullable=False,
    )

    # Inventory details
    part_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    reorder_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    last_restocked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    # Relationships
    staff: Mapped[Staff] = relationship(
        "Staff",
        foreign_keys=[staff_id],
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ResourceTruckInventory("
            f"id={self.id}, "
            f"part_name='{self.part_name}', "
            f"quantity={self.quantity})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "staff_id": str(self.staff_id),
            "part_name": self.part_name,
            "quantity": self.quantity,
            "reorder_threshold": self.reorder_threshold,
            "last_restocked": (
                self.last_restocked.isoformat() if self.last_restocked else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
