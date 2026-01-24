"""Schedule reassignment model.

Validates: Requirement 11.3
"""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.staff import Staff


class ScheduleReassignment(Base):
    """Record of staff reassignment.

    Validates: Requirement 11.3
    """

    __tablename__ = "schedule_reassignments"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    original_staff_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id"),
        nullable=False,
    )
    new_staff_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id"),
        nullable=False,
    )
    reassignment_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    jobs_reassigned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    original_staff: Mapped[Staff] = relationship(
        "Staff",
        foreign_keys=[original_staff_id],
    )
    new_staff: Mapped[Staff] = relationship(
        "Staff",
        foreign_keys=[new_staff_id],
    )

    def __repr__(self) -> str:
        return (
            f"<ScheduleReassignment(id={self.id}, "
            f"from={self.original_staff_id}, to={self.new_staff_id})>"
        )
