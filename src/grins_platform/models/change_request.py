"""
Change request model for resource-initiated schedule changes.

Stores change requests initiated by Resources (field technicians) and
routed to User Admins for approval via the Alerts Panel.

Validates: Requirements 2.4, 20.1, 20.2, 21.1-21.4
"""

from __future__ import annotations

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
    """Resource-initiated change request.

    Represents a structured request from a Resource to the User Admin
    for schedule modifications. Requests are routed through the Alerts
    Panel for approval or denial.

    Attributes:
        id: Unique identifier (UUID).
        resource_id: Resource (staff) who initiated the request.
        request_type: Type of request (delay_report, followup_job, etc.).
        details: Request-specific details (field notes, parts list, etc.).
        affected_job_id: Primary job affected by the request.
        recommended_action: AI's recommended resolution.
        status: Current status (pending, approved, denied, expired).
        admin_id: Admin who acted on the request.
        admin_notes: Admin's notes on the decision.
        resolved_at: When the request was resolved.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "change_requests"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Request origin
    resource_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id"),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Affected job
    affected_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=True,
    )

    # AI recommendation
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resolution
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
    )
    admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff.id"),
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
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    resource: Mapped[Staff] = relationship(
        "Staff",
        foreign_keys=[resource_id],
    )
    admin: Mapped[Staff | None] = relationship(
        "Staff",
        foreign_keys=[admin_id],
    )
    affected_job: Mapped[Job | None] = relationship(
        "Job",
        foreign_keys=[affected_job_id],
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ChangeRequest("
            f"id={self.id}, "
            f"request_type='{self.request_type}', "
            f"status='{self.status}')>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
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
            "resolved_at": (self.resolved_at.isoformat() if self.resolved_at else None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
