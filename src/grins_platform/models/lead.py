"""
Lead model for website form submissions.

This module defines the Lead SQLAlchemy model representing prospects
who have submitted the website form but are not yet confirmed customers.

Validates: Requirement 4.1, 4.2
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base
from grins_platform.models.enums import (
    VALID_LEAD_STATUS_TRANSITIONS,
    LeadSituation,
    LeadStatus,
)

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.staff import Staff


class Lead(Base):
    """Lead database model for website form submissions.

    Represents a prospect who has submitted the landing page form.
    Leads are tracked independently from customers until conversion.

    Attributes:
        id: Unique identifier (UUID)
        name: Full name from form submission
        phone: Phone number (normalized to 10 digits)
        email: Email address (optional)
        zip_code: 5-digit zip code
        situation: Service situation from form dropdown
        notes: Optional notes from the prospect
        source_site: Which website/landing page the lead came from
        status: Lead pipeline status
        assigned_to: FK to staff member assigned to follow up
        customer_id: FK to customer record (populated on conversion)
        contacted_at: When the lead was first contacted
        converted_at: When the lead was converted to a customer
        created_at: Record creation timestamp
        updated_at: Record last update timestamp

    Validates: Requirement 4.1, 4.2
    """

    __tablename__ = "leads"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Form submission fields
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    situation: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_site: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="residential",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="new",
    )

    # Foreign keys
    assigned_to: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Lifecycle timestamps
    contacted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    converted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Record timestamps
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
    staff: Mapped[Optional["Staff"]] = relationship(
        "Staff",
        foreign_keys=[assigned_to],
        lazy="selectin",
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        foreign_keys=[customer_id],
        lazy="selectin",
    )

    # Table-level constraints and indexes (Requirement 4.3)
    __table_args__ = (
        Index("idx_leads_phone", "phone"),
        Index("idx_leads_status", "status"),
        Index("idx_leads_created_at", "created_at"),
        Index("idx_leads_zip_code", "zip_code"),
    )

    def __repr__(self) -> str:
        """Return string representation of the lead."""
        return (
            f"<Lead(id={self.id}, name='{self.name}', "
            f"phone='{self.phone}', status='{self.status}')>"
        )

    @property
    def status_enum(self) -> LeadStatus:
        """Get the status as an enum value."""
        return LeadStatus(self.status)

    @property
    def situation_enum(self) -> LeadSituation:
        """Get the situation as an enum value."""
        return LeadSituation(self.situation)

    def can_transition_to(self, new_status: LeadStatus) -> bool:
        """Check if the lead can transition to the given status.

        Args:
            new_status: The target status to transition to.

        Returns:
            True if the transition is valid, False otherwise.

        Validates: Requirement 6.2
        """
        current = self.status_enum
        valid_transitions = VALID_LEAD_STATUS_TRANSITIONS.get(current, set())
        return new_status in valid_transitions

    def is_terminal_status(self) -> bool:
        """Check if the lead is in a terminal status.

        Returns:
            True if the lead is converted or spam (terminal states).
        """
        return self.status in [
            LeadStatus.CONVERTED.value,
            LeadStatus.SPAM.value,
        ]

    def is_active_status(self) -> bool:
        """Check if the lead is in an active (non-terminal) status.

        Returns:
            True if the lead status is new, contacted, or qualified.
        """
        return self.status in [
            LeadStatus.NEW.value,
            LeadStatus.CONTACTED.value,
            LeadStatus.QUALIFIED.value,
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert the lead to a dictionary.

        Returns:
            Dictionary representation of the lead.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "zip_code": self.zip_code,
            "situation": self.situation,
            "notes": self.notes,
            "source_site": self.source_site,
            "status": self.status,
            "assigned_to": str(self.assigned_to) if self.assigned_to else None,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "contacted_at": (
                self.contacted_at.isoformat() if self.contacted_at else None
            ),
            "converted_at": (
                self.converted_at.isoformat() if self.converted_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
