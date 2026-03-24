"""Expense model for accounting/expense tracking.

Validates: CRM Gap Closure Req 53.1
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.job import Job
    from grins_platform.models.staff import Staff


class Expense(Base):
    """Expense record for accounting.

    Validates: CRM Gap Closure Req 53.1
    """

    __tablename__ = "expenses"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column("date", Date, nullable=False)
    job_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    staff_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    vendor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    receipt_file_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    receipt_amount_extracted: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    lead_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    job: Mapped["Job | None"] = relationship("Job", lazy="selectin")
    staff: Mapped["Staff | None"] = relationship("Staff", lazy="selectin")

    __table_args__ = (
        Index("idx_expenses_category", "category"),
        Index("idx_expenses_date", "date"),
        Index("idx_expenses_job_id", "job_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Expense(id={self.id}, category='{self.category}', amount={self.amount})>"
        )
