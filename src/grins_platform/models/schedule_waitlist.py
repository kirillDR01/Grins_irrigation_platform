"""Schedule waitlist model for conflict resolution.

Validates: Requirements 10.4, 10.5
"""

from __future__ import annotations

from datetime import date, datetime, time  # noqa: TC003
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.job import Job


class ScheduleWaitlist(Base):
    """Waitlist entry for jobs waiting for schedule slots.

    Validates: Requirements 10.4, 10.5
    """

    __tablename__ = "schedule_waitlist"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id"),
        nullable=False,
    )
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_time_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    preferred_time_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
        onupdate=func.now(),
    )

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="waitlist_entries")

    def __repr__(self) -> str:
        return (
            f"<ScheduleWaitlist(id={self.id}, job_id={self.job_id}, "
            f"date={self.preferred_date})>"
        )
