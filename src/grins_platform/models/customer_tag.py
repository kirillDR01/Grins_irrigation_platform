"""CustomerTag SQLAlchemy model.

Stores customer-scoped tags that appear across all appointments for a customer.

Validates: Requirements 12.1, 12.2, 12.3
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer


class CustomerTag(Base):
    """A label attached to a customer, visible across all their appointments.

    Attributes:
        id: UUID primary key
        customer_id: FK to customers.id (CASCADE DELETE)
        label: Short display text, max 32 chars
        tone: Visual colour variant (neutral/blue/green/amber/violet)
        source: Who created the tag (manual/system)
        created_at: Creation timestamp
    """

    __tablename__ = "customer_tags"
    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "label",
            name="uq_customer_tags_customer_label",
        ),
        CheckConstraint(
            "tone IN ('neutral', 'blue', 'green', 'amber', 'violet')",
            name="ck_customer_tags_tone",
        ),
        CheckConstraint(
            "source IN ('manual', 'system')",
            name="ck_customer_tags_source",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    tone: Mapped[str] = mapped_column(String(10), nullable=False, default="neutral")
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    customer: Mapped[Customer] = relationship("Customer", back_populates="tags")

    def __repr__(self) -> str:
        return (
            f"<CustomerTag(id={self.id}, customer_id={self.customer_id}, "
            f"label={self.label!r}, tone={self.tone!r})>"
        )
