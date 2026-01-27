"""AI Audit Log model for tracking AI recommendations and user decisions.

This model supports the human-in-the-loop principle where AI recommends
but never executes without explicit user approval.

Validates: AI Assistant Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import (
    JSONB,
    TIMESTAMP,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column

from grins_platform.database import Base


class AIAuditLog(Base):
    """Model for tracking AI recommendations and user decisions."""

    __tablename__ = "ai_audit_log"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    ai_recommendation: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    user_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    decision_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    request_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    response_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('schedule_generation', 'job_categorization', "
            "'communication_draft', 'estimate_generation', 'business_query')",
            name="ck_ai_audit_log_action_type",
        ),
        CheckConstraint(
            "entity_type IN ('job', 'customer', 'appointment', 'schedule', "
            "'communication', 'estimate')",
            name="ck_ai_audit_log_entity_type",
        ),
        CheckConstraint(
            "user_decision IS NULL OR user_decision IN ('approved', 'rejected', "
            "'modified', 'pending')",
            name="ck_ai_audit_log_user_decision",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR "
            "(confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_ai_audit_log_confidence_score",
        ),
        Index("idx_ai_audit_log_action_type", "action_type"),
        Index("idx_ai_audit_log_entity_type", "entity_type"),
        Index("idx_ai_audit_log_entity_id", "entity_id"),
        Index("idx_ai_audit_log_created_at", "created_at"),
        Index("idx_ai_audit_log_user_decision", "user_decision"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AIAuditLog(id={self.id}, action_type={self.action_type}, "
            f"entity_type={self.entity_type}, user_decision={self.user_decision})>"
        )
