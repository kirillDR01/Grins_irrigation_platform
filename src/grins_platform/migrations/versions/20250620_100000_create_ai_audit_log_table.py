"""Create ai_audit_log table.

Revision ID: 009_ai_audit_log
Revises: 008_appointments
Create Date: 2025-06-20 10:00:00

This migration creates the ai_audit_log table for tracking all AI recommendations
and user decisions. Supports human-in-the-loop principle where AI recommends but
never executes without explicit user approval.

Validates: AI Assistant Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "20250620_100000"
down_revision: Union[str, None] = "20250619_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ai_audit_log table with indexes."""
    op.create_table(
        "ai_audit_log",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("ai_recommendation", JSONB(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("user_decision", sa.String(20), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("decision_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("request_tokens", sa.Integer(), nullable=True),
        sa.Column("response_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "action_type IN ('schedule_generation', 'job_categorization', "
            "'communication_draft', 'estimate_generation', 'business_query')",
            name="ck_ai_audit_log_action_type",
        ),
        sa.CheckConstraint(
            "entity_type IN ('job', 'customer', 'appointment', 'schedule', "
            "'communication', 'estimate')",
            name="ck_ai_audit_log_entity_type",
        ),
        sa.CheckConstraint(
            "user_decision IS NULL OR user_decision IN ('approved', 'rejected', "
            "'modified', 'pending')",
            name="ck_ai_audit_log_user_decision",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR "
            "(confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_ai_audit_log_confidence_score",
        ),
    )

    op.create_index("idx_ai_audit_log_action_type", "ai_audit_log", ["action_type"])
    op.create_index("idx_ai_audit_log_entity_type", "ai_audit_log", ["entity_type"])
    op.create_index("idx_ai_audit_log_entity_id", "ai_audit_log", ["entity_id"])
    op.create_index("idx_ai_audit_log_created_at", "ai_audit_log", ["created_at"])
    op.create_index("idx_ai_audit_log_user_decision", "ai_audit_log", ["user_decision"])


def downgrade() -> None:
    """Drop ai_audit_log table and indexes."""
    op.drop_index("idx_ai_audit_log_user_decision", table_name="ai_audit_log")
    op.drop_index("idx_ai_audit_log_created_at", table_name="ai_audit_log")
    op.drop_index("idx_ai_audit_log_entity_id", table_name="ai_audit_log")
    op.drop_index("idx_ai_audit_log_entity_type", table_name="ai_audit_log")
    op.drop_index("idx_ai_audit_log_action_type", table_name="ai_audit_log")
    op.drop_table("ai_audit_log")
