"""
JobStatusHistory model for tracking job status transitions.

This module defines the JobStatusHistory SQLAlchemy model for recording
all status changes on jobs, enabling audit trails and workflow analysis.

Validates: Requirements 7.1-7.4
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base
from grins_platform.models.enums import JobStatus

if TYPE_CHECKING:
    from grins_platform.models.job import Job


class JobStatusHistory(Base):
    """Job status history model for tracking status transitions.

    Attributes:
        id: Unique identifier for the history record
        job_id: Reference to the job
        previous_status: Status before the transition (null for initial)
        new_status: Status after the transition
        changed_at: When the transition occurred
        changed_by: User who made the change (for future implementation)
        notes: Optional notes about the transition

    Validates: Requirements 7.1-7.4
    """

    __tablename__ = "job_status_history"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid(),
    )

    # Foreign key to job (Requirement 7.1)
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Status transition details (Requirement 7.1)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Timestamp (Requirement 7.1)
    changed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # User tracking (Requirement 7.3 - for future implementation)
    changed_by: Mapped[UUID | None] = mapped_column(nullable=True)

    # Notes/reason for change (Requirement 7.4)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    job: Mapped["Job"] = relationship("Job", back_populates="status_history")

    def __repr__(self) -> str:
        """Return string representation of the status history record."""
        return (
            f"<JobStatusHistory(id={self.id}, job_id={self.job_id}, "
            f"'{self.previous_status}' -> '{self.new_status}')>"
        )

    @property
    def previous_status_enum(self) -> JobStatus | None:
        """Get the previous status as an enum value."""
        return JobStatus(self.previous_status) if self.previous_status else None

    @property
    def new_status_enum(self) -> JobStatus:
        """Get the new status as an enum value."""
        return JobStatus(self.new_status)

    def to_dict(self) -> dict[str, Any]:
        """Convert the status history record to a dictionary.

        Returns:
            Dictionary representation of the status history.
        """
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "changed_by": str(self.changed_by) if self.changed_by else None,
            "notes": self.notes,
        }
