"""Communication model for inbound/outbound message tracking.

Validates: CRM Gap Closure Req 4.4
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.staff import Staff


class Communication(Base):
    """Communication record for tracking inbound/outbound messages.

    Validates: CRM Gap Closure Req 4.4
    """

    __tablename__ = "communications"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    addressed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    addressed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    addressed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    addressed_by_staff: Mapped["Staff | None"] = relationship("Staff", lazy="selectin")

    __table_args__ = (
        Index("idx_communications_customer_id", "customer_id"),
        Index("idx_communications_addressed", "addressed"),
        Index("idx_communications_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Communication(id={self.id}, customer_id={self.customer_id}, "
            f"channel='{self.channel}', addressed={self.addressed})>"
        )
