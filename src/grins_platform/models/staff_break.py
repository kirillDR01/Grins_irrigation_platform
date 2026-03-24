"""Staff break model for break tracking.

Validates: CRM Gap Closure Req 42.3
"""

from datetime import datetime, time
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.appointment import Appointment
    from grins_platform.models.staff import Staff


class StaffBreak(Base):
    """Staff break record.

    Validates: CRM Gap Closure Req 42.3
    """

    __tablename__ = "staff_breaks"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    staff_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    staff: Mapped["Staff"] = relationship("Staff", lazy="selectin")
    appointment: Mapped["Appointment | None"] = relationship(
        "Appointment",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_staff_breaks_staff_id", "staff_id"),
        Index("idx_staff_breaks_start_time", "start_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<StaffBreak(id={self.id}, staff_id={self.staff_id}, "
            f"type='{self.break_type}')>"
        )
