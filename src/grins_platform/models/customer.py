"""
Customer SQLAlchemy model.

This module defines the Customer model with all fields, relationships,
and behaviors as specified in the design document.

Validates: Requirement 1.1, 1.6, 1.8
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import (
    JSON,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grins_platform.database import Base
from grins_platform.models.enums import CustomerStatus, LeadSource

if TYPE_CHECKING:
    from grins_platform.models.property import Property


class Customer(Base):
    """Customer model representing a client of the irrigation business.

    This model stores customer contact information, status flags,
    communication preferences, and lead tracking data.

    Attributes:
        id: Unique identifier (UUID)
        first_name: Customer's first name
        last_name: Customer's last name
        phone: Customer's phone number (unique, normalized to 10 digits)
        email: Customer's email address (optional)
        status: Customer status (active/inactive)
        is_priority: Flag for priority customers
        is_red_flag: Flag for customers with behavioral concerns
        is_slow_payer: Flag for customers with payment issues
        is_new_customer: Flag for new vs returning customers
        sms_opt_in: SMS communication preference
        email_opt_in: Email communication preference
        communication_preferences_updated_at: When preferences were last changed
        lead_source: How the customer found the business
        lead_source_details: Additional lead source information (JSON)
        is_deleted: Soft delete flag
        deleted_at: When the customer was soft deleted
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        properties: Related properties for this customer

    Validates: Requirement 1.1, 1.6, 1.8
    """

    __tablename__ = "customers"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Name fields (Requirement 1.8)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Contact information
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status and Flags (Requirement 1.12, 3.1-3.4)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CustomerStatus.ACTIVE.value,
    )
    is_priority: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_red_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_slow_payer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_new_customer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )  # Requirement 1.11

    # Communication Preferences (Requirement 5.1, 5.2)
    sms_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    communication_preferences_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Lead Tracking (Requirement 1.9)
    lead_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    lead_source_details: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Soft Delete (Requirement 1.6)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps (Requirement 1.7)
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
    properties: Mapped[list["Property"]] = relationship(
        "Property",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        """Get the customer's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def status_enum(self) -> CustomerStatus:
        """Get the status as an enum value."""
        return CustomerStatus(self.status)

    @property
    def lead_source_enum(self) -> Optional[LeadSource]:
        """Get the lead source as an enum value."""
        if self.lead_source is None:
            return None
        return LeadSource(self.lead_source)

    def soft_delete(self) -> None:
        """Mark the customer as deleted without removing from database.

        Validates: Requirement 1.6
        """
        self.is_deleted = True
        self.deleted_at = datetime.now()

    def restore(self) -> None:
        """Restore a soft-deleted customer."""
        self.is_deleted = False
        self.deleted_at = None

    def update_communication_preferences(
        self,
        sms_opt_in: Optional[bool] = None,
        email_opt_in: Optional[bool] = None,
    ) -> None:
        """Update communication preferences with timestamp tracking.

        Args:
            sms_opt_in: New SMS opt-in status (None to keep current)
            email_opt_in: New email opt-in status (None to keep current)

        Validates: Requirement 5.3, 5.4, 5.6
        """
        changed = False
        if sms_opt_in is not None and sms_opt_in != self.sms_opt_in:
            self.sms_opt_in = sms_opt_in
            changed = True
        if email_opt_in is not None and email_opt_in != self.email_opt_in:
            self.email_opt_in = email_opt_in
            changed = True
        if changed:
            self.communication_preferences_updated_at = datetime.now()

    def __repr__(self) -> str:
        """Return string representation of customer."""
        return (
            f"<Customer(id={self.id}, name='{self.full_name}', "
            f"phone='{self.phone}', status='{self.status}')>"
        )
