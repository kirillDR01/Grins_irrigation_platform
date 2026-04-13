"""Customer merge candidate model for duplicate detection.

Validates: CRM Changes Update 2 Req 5.1, 5.6
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer


class CustomerMergeCandidate(Base):
    """Potential duplicate customer pair with confidence score.

    Validates: CRM Changes Update 2 Req 5.1, 5.6
    """

    __tablename__ = "customer_merge_candidates"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    customer_a_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_b_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    match_signals: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    customer_a: Mapped["Customer"] = relationship(
        "Customer",
        foreign_keys=[customer_a_id],
        lazy="selectin",
    )
    customer_b: Mapped["Customer"] = relationship(
        "Customer",
        foreign_keys=[customer_b_id],
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "customer_a_id",
            "customer_b_id",
            name="uq_merge_candidates_pair",
        ),
        Index("ix_merge_candidates_score_desc", score.desc()),
        Index("ix_merge_candidates_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CustomerMergeCandidate(id={self.id}, "
            f"score={self.score}, status='{self.status}')>"
        )
