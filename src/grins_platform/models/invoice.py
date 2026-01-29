"""Invoice model for invoice management.

This module defines the Invoice SQLAlchemy model representing invoices
in the Grin's Irrigation Platform.

Requirements: 7.1-7.10
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import (
    JSONB,
    TIMESTAMP,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.job import Job


class Invoice(Base):
    """Invoice model representing a customer invoice.

    Attributes:
        id: Unique identifier for the invoice
        job_id: Reference to the job
        customer_id: Reference to the customer
        invoice_number: Unique invoice number (INV-YEAR-SEQ)
        amount: Base invoice amount
        late_fee_amount: Late fee amount (default 0)
        total_amount: Total amount (amount + late_fee)
        invoice_date: Date invoice was created
        due_date: Payment due date
        status: Invoice status (draft, sent, viewed, paid, etc.)
        payment_method: Method of payment
        payment_reference: Payment reference/transaction ID
        paid_at: Timestamp when payment was received
        paid_amount: Amount paid so far
        reminder_count: Number of reminders sent
        last_reminder_sent: Timestamp of last reminder
        lien_eligible: Whether job type is lien-eligible
        lien_warning_sent: Timestamp of 45-day lien warning
        lien_filed_date: Date lien was filed
        line_items: JSONB array of line items
        notes: Optional notes
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Requirements: 7.1-7.10
    """

    __tablename__ = "invoices"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign keys
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Invoice identification
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    # Amounts (Requirement 7.2-7.4)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    late_fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # Dates (Requirement 7.5-7.6)
    invoice_date: Mapped[date] = mapped_column(
        Date(),
        nullable=False,
        server_default=func.current_date(),
    )
    due_date: Mapped[date] = mapped_column(
        Date(),
        nullable=False,
    )

    # Status (Requirement 8.1-8.10)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="draft",
    )

    # Payment info (Requirement 9.1-9.7)
    payment_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    payment_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    paid_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Reminders (Requirement 12.1-12.5)
    reminder_count: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        server_default="0",
    )
    last_reminder_sent: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Lien tracking (Requirement 11.1-11.8)
    lien_eligible: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        server_default="false",
    )
    lien_warning_sent: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    lien_filed_date: Mapped[date | None] = mapped_column(
        Date(),
        nullable=True,
    )

    # Line items (Requirement 7.8)
    line_items: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB(),
        nullable=True,
    )

    # Notes (Requirement 7.9)
    notes: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="invoices")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="invoices")

    def __repr__(self) -> str:
        """Return string representation of the invoice."""
        return (
            f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}', "
            f"status='{self.status}', total_amount={self.total_amount})>"
        )
