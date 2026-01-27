"""AI Usage model for tracking daily AI usage per user.

Supports rate limiting (100 requests/day) and cost tracking.

Validates: AI Assistant Requirements 2.1, 2.7, 2.8
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, Float, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import (
    TIMESTAMP,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column

from grins_platform.database import Base


class AIUsage(Base):
    """Model for tracking daily AI usage per user."""

    __tablename__ = "ai_usage"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    usage_date: Mapped[date] = mapped_column(Date(), nullable=False)
    request_count: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        server_default="0",
    )
    total_input_tokens: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        server_default="0",
    )
    total_output_tokens: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        server_default="0",
    )
    estimated_cost_usd: Mapped[float] = mapped_column(
        Float(),
        nullable=False,
        server_default="0.0",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_ai_usage_user_date"),
        CheckConstraint("request_count >= 0", name="ck_ai_usage_request_count"),
        CheckConstraint("total_input_tokens >= 0", name="ck_ai_usage_input_tokens"),
        CheckConstraint("total_output_tokens >= 0", name="ck_ai_usage_output_tokens"),
        CheckConstraint("estimated_cost_usd >= 0", name="ck_ai_usage_cost"),
        Index("idx_ai_usage_user_id", "user_id"),
        Index("idx_ai_usage_usage_date", "usage_date"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AIUsage(id={self.id}, user_id={self.user_id}, "
            f"usage_date={self.usage_date}, request_count={self.request_count})>"
        )
