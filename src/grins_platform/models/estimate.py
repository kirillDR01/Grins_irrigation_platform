"""Estimate model for customer estimates/quotes.

Validates: CRM Gap Closure Req 48.1, 78.1
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.estimate_follow_up import EstimateFollowUp
    from grins_platform.models.estimate_template import EstimateTemplate
    from grins_platform.models.job import Job
    from grins_platform.models.lead import Lead


class Estimate(Base):
    """Estimate record with portal token support.

    Validates: CRM Gap Closure Req 48.1, 78.1
    """

    __tablename__ = "estimates"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    lead_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("estimate_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="draft",
    )
    line_items: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
    )
    promotion_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Portal token fields (Req 78)
    customer_token: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        unique=True,
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    token_readonly: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    # Approval/rejection tracking
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approved_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    approved_user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    lead: Mapped["Lead | None"] = relationship("Lead", lazy="selectin")
    customer: Mapped["Customer | None"] = relationship("Customer", lazy="selectin")
    job: Mapped["Job | None"] = relationship("Job", lazy="selectin")
    template: Mapped["EstimateTemplate | None"] = relationship(
        "EstimateTemplate",
        lazy="selectin",
    )
    follow_ups: Mapped[list["EstimateFollowUp"]] = relationship(
        "EstimateFollowUp",
        back_populates="estimate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_estimates_lead_id", "lead_id"),
        Index("idx_estimates_customer_id", "customer_id"),
        Index("idx_estimates_status", "status"),
        Index("idx_estimates_customer_token", "customer_token"),
    )

    def __repr__(self) -> str:
        return f"<Estimate(id={self.id}, status='{self.status}', total={self.total})>"
