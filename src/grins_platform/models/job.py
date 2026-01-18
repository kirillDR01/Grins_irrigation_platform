"""
Job model for job request management.

This module defines the Job SQLAlchemy model representing job requests
in the Grin's Irrigation Platform.

Validates: Requirements 2.1-2.12, 4.1-4.9
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base
from grins_platform.models.enums import JobCategory, JobSource, JobStatus

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.job_status_history import JobStatusHistory
    from grins_platform.models.property import Property
    from grins_platform.models.service_offering import ServiceOffering


# Valid status transitions (Requirement 4.2-4.7)
VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
    JobStatus.REQUESTED.value: [JobStatus.APPROVED.value, JobStatus.CANCELLED.value],
    JobStatus.APPROVED.value: [JobStatus.SCHEDULED.value, JobStatus.CANCELLED.value],
    JobStatus.SCHEDULED.value: [JobStatus.IN_PROGRESS.value, JobStatus.CANCELLED.value],
    JobStatus.IN_PROGRESS.value: [JobStatus.COMPLETED.value, JobStatus.CANCELLED.value],
    JobStatus.COMPLETED.value: [JobStatus.CLOSED.value],
    JobStatus.CANCELLED.value: [],  # Terminal state
    JobStatus.CLOSED.value: [],  # Terminal state
}


class Job(Base):
    """Job model representing a work request.

    Attributes:
        id: Unique identifier for the job
        customer_id: Reference to the customer
        property_id: Reference to the property (optional)
        service_offering_id: Reference to the service offering (optional)
        job_type: Type of job (spring_startup, repair, etc.)
        category: Auto-categorization (ready_to_schedule, requires_estimate)
        status: Current status in the workflow
        description: Job description and notes
        estimated_duration_minutes: Estimated time to complete
        priority_level: Priority (0=normal, 1=high, 2=urgent)
        weather_sensitive: Whether job depends on weather
        staffing_required: Number of staff needed
        equipment_required: List of equipment needed
        materials_required: List of materials needed
        quoted_amount: Quoted price for the job
        final_amount: Final price after completion
        source: Lead source (website, google, referral, etc.)
        source_details: Additional source information
        requested_at: When the job was requested
        approved_at: When the job was approved
        scheduled_at: When the job was scheduled
        started_at: When work started
        completed_at: When work was completed
        closed_at: When the job was closed
        is_deleted: Soft delete flag
        deleted_at: When the job was deleted
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Validates: Requirements 2.1-2.12, 4.1-4.9
    """

    __tablename__ = "jobs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid(),
    )

    # Foreign keys (Requirements 10.8-10.10)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False,
    )
    property_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("properties.id"), nullable=True,
    )
    service_offering_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("service_offerings.id"),
        nullable=True,
    )

    # Job Details (Requirement 2.1)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="requested",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scheduling
    estimated_duration_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    priority_level: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    weather_sensitive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )

    # Requirements (Requirement 2.8)
    staffing_required: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1",
    )
    equipment_required: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    materials_required: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Pricing (Requirement 2.7)
    quoted_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    final_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Lead Attribution (Requirements 2.11, 2.12)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Status Timestamps (Requirement 4.9)
    requested_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Record Timestamps (Requirement 2.6)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="jobs")
    job_property: Mapped["Property | None"] = relationship(
        "Property",
        back_populates="jobs",
    )
    service_offering: Mapped["ServiceOffering | None"] = relationship("ServiceOffering")
    status_history: Mapped[list["JobStatusHistory"]] = relationship(
        "JobStatusHistory",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation of the job."""
        return (
            f"<Job(id={self.id}, job_type='{self.job_type}', status='{self.status}')>"
        )

    @property
    def status_enum(self) -> JobStatus:
        """Get the status as an enum value."""
        return JobStatus(self.status)

    @property
    def category_enum(self) -> JobCategory:
        """Get the category as an enum value."""
        return JobCategory(self.category)

    @property
    def source_enum(self) -> JobSource | None:
        """Get the source as an enum value."""
        return JobSource(self.source) if self.source else None

    def can_transition_to(self, new_status: str) -> bool:
        """Check if the job can transition to the given status.

        Args:
            new_status: The target status to transition to.

        Returns:
            True if the transition is valid, False otherwise.

        Validates: Requirement 4.10
        """
        valid_transitions = VALID_STATUS_TRANSITIONS.get(self.status, [])
        return new_status in valid_transitions

    def get_valid_transitions(self) -> list[str]:
        """Get the list of valid status transitions from current status.

        Returns:
            List of valid target statuses.
        """
        return VALID_STATUS_TRANSITIONS.get(self.status, [])

    def is_terminal_status(self) -> bool:
        """Check if the job is in a terminal status.

        Returns:
            True if the job is cancelled or closed.

        Validates: Requirement 4.7
        """
        return self.status in [JobStatus.CANCELLED.value, JobStatus.CLOSED.value]

    def to_dict(self) -> dict[str, Any]:
        """Convert the job to a dictionary.

        Returns:
            Dictionary representation of the job.
        """
        return {
            "id": str(self.id),
            "customer_id": str(self.customer_id),
            "property_id": str(self.property_id) if self.property_id else None,
            "service_offering_id": str(self.service_offering_id)
            if self.service_offering_id
            else None,
            "job_type": self.job_type,
            "category": self.category,
            "status": self.status,
            "description": self.description,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "priority_level": self.priority_level,
            "weather_sensitive": self.weather_sensitive,
            "staffing_required": self.staffing_required,
            "equipment_required": self.equipment_required,
            "materials_required": self.materials_required,
            "quoted_amount": float(self.quoted_amount) if self.quoted_amount else None,
            "final_amount": float(self.final_amount) if self.final_amount else None,
            "source": self.source,
            "source_details": self.source_details,
            "requested_at": self.requested_at.isoformat()
            if self.requested_at
            else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "scheduled_at": self.scheduled_at.isoformat()
            if self.scheduled_at
            else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
