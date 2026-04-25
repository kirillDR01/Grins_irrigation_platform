"""Appointment notes model for centralized internal notes.

Validates: Appointment Modal V2 Req 5.1, 5.2
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.appointment import Appointment
    from grins_platform.models.staff import Staff


class AppointmentNote(Base):
    """Single centralized internal note per appointment.

    Replaces the v1 multi-author thread pattern with one shared body.

    Validates: Appointment Modal V2 Req 5.1, 5.2
    """

    __tablename__ = "appointment_notes"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    appointment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    appointment: Mapped[Appointment] = relationship(
        "Appointment",
        lazy="selectin",
    )
    updated_by: Mapped[Staff | None] = relationship(
        "Staff",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<AppointmentNote(id={self.id}, "
            f"appointment_id={self.appointment_id}, "
            f"body_len={len(self.body)})>"
        )
