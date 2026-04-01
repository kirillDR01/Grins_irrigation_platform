"""
ChangeRequest model for resource-initiated schedule change requests.

This module defines the ChangeRequest SQLAlchemy model representing
change requests from field resources routed to admin for approval.

Validates: Requirements 2.4, 14.3, 14.4, 14.6, 14.7, 14.10, 21.1-21.4
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.job import Job
    from grins_platform.models.staff import Staff


class ChangeRequest(Base):
    """ChangeRequest model representing a resource-initiated change request.

    Attributes:
        id: Unique identifier for the change request
        resource_id: Resource who initiated the request
        request_type: Type of request (delay_report, followup_job, etc.)
        details: Request-specific details
        affected_job_id: Primary job affected
        recommended_action: AI's recommended resolution
        status: Current status (pending, approved, denied, expired)
        admin_id: Admin who acted on the request
        admin_notes: Admin's notes on decision
        resolved_at: When the request was resolved
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Validates: Requirements 2.4, 14.3, 14.4, 14.6, 14.7, 14.10, 21.1-21.4
    """

    __tablename__ = "change_requests"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Request details
    resource_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    affected_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status and resolution
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
    )
    admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    # Relationships
    resource: Mapped["Staff"] = relationship(
        "Staff",
        foreign_keys=[resource_id],
    )
    admin: Mapped["Staff | None"] = relationship(
        "Staff",
        foreign_keys=[admin_id],
    )
    affected_job: Mapped["Job | None"] = relationship(
        "Job",
        foreign_keys=[affected_job_id],
    )

    def __repr__(self) -> str:
        """Return string representation of the change request."""
        return (
            f"<ChangeRequest(id={self.id}, type='{self.request_type}', "
            f"status='{self.status}')>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the change request to a dictionary.

        Returns:
            Dictionary representation of the change request.
        """
        return {
            "id": str(self.id),
            "resource_id": str(self.resource_id),
            "request_type": self.request_type,
            "details": self.details,
            "affected_job_id": (
                str(self.affected_job_id) if self.affected_job_id else None
            ),
            "recommended_action": self.recommended_action,
            "status": self.status,
            "admin_id": str(self.admin_id) if self.admin_id else None,
            "admin_notes": self.admin_notes,
            "resolved_at": (
                self.resolved_at.isoformat() if self.resolved_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
