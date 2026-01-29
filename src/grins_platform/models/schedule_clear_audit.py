"""Schedule Clear Audit model for tracking schedule clear operations.

This model stores audit records when schedules are cleared, including
a snapshot of deleted appointments and reset job IDs for recovery.

Requirements: 5.1-5.6
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    JSONB,
    TIMESTAMP,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grins_platform.database import Base


class ScheduleClearAudit(Base):
    """Model for tracking schedule clear operations with full audit trail."""

    __tablename__ = "schedule_clear_audit"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    schedule_date: Mapped[date] = mapped_column(Date(), nullable=False)
    appointments_data: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB(), nullable=False,
    )
    jobs_reset: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), nullable=False,
    )
    appointment_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    cleared_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    cleared_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    # Relationship to Staff
    cleared_by_staff = relationship("Staff", foreign_keys=[cleared_by])

    __table_args__ = (
        Index("ix_schedule_clear_audit_schedule_date", "schedule_date"),
        Index("ix_schedule_clear_audit_cleared_at", "cleared_at"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ScheduleClearAudit(id={self.id}, schedule_date={self.schedule_date}, "
            f"appointment_count={self.appointment_count})>"
        )
