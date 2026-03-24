"""Estimate follow-up model for scheduled follow-up tracking.

Validates: CRM Gap Closure Req 51.1
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.estimate import Estimate


class EstimateFollowUp(Base):
    """Scheduled follow-up for an estimate.

    Validates: CRM Gap Closure Req 51.1
    """

    __tablename__ = "estimate_follow_ups"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    estimate_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("estimates.id", ondelete="CASCADE"),
        nullable=False,
    )
    follow_up_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    promotion_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="scheduled",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    estimate: Mapped["Estimate"] = relationship(
        "Estimate",
        back_populates="follow_ups",
    )

    __table_args__ = (
        Index("idx_estimate_follow_ups_estimate_id", "estimate_id"),
        Index("idx_estimate_follow_ups_status", "status"),
        Index("idx_estimate_follow_ups_scheduled_at", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<EstimateFollowUp(id={self.id}, estimate_id={self.estimate_id}, "
            f"number={self.follow_up_number}, status='{self.status}')>"
        )
