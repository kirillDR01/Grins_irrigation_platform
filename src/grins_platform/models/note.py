"""Note model for unified cross-stage notes timeline.

Supports the unified Notes Timeline feature where notes follow the
lead → sales entry → customer → appointment chain. Cross-stage threading
is achieved via the ``origin_lead_id`` column.

Validates: april-16th-fixes-enhancements Requirement 4
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base


class Note(Base):
    """A note attached to a lead, sales entry, customer, or appointment.

    Notes support cross-stage threading via ``origin_lead_id`` so that
    notes created on a lead remain visible when the lead is routed to
    a sales entry or customer.

    Validates: april-16th-fixes-enhancements Requirement 4
    """

    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    origin_lead_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id"),
        nullable=True,
    )
    origin_appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=True,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=func.cast(False, Boolean),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=func.cast(False, Boolean),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    author: Mapped["Staff"] = relationship("Staff", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("idx_notes_subject", "subject_type", "subject_id"),
        Index("idx_notes_origin_lead", "origin_lead_id"),
        Index("idx_notes_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Note(id={self.id}, subject_type='{self.subject_type}', "
            f"subject_id={self.subject_id}, is_system={self.is_system})>"
        )
