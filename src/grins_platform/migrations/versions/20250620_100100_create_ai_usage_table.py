"""Create ai_usage table.

Revision ID: 010_ai_usage
Revises: 009_ai_audit_log
Create Date: 2025-06-20 10:01:00

This migration creates the ai_usage table for tracking daily AI usage per user.
Supports rate limiting (100 requests/day) and cost tracking.

Validates: AI Assistant Requirements 2.1, 2.7, 2.8
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250620_100100"
down_revision: Union[str, None] = "20250620_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ai_usage table with unique constraint and indexes."""
    op.create_table(
        "ai_usage",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_input_tokens", sa.Integer(), nullable=False, server_default="0",
        ),
        sa.Column(
            "total_output_tokens", sa.Integer(), nullable=False, server_default="0",
        ),
        sa.Column(
            "estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_ai_usage_user_date"),
        sa.CheckConstraint("request_count >= 0", name="ck_ai_usage_request_count"),
        sa.CheckConstraint(
            "total_input_tokens >= 0", name="ck_ai_usage_input_tokens",
        ),
        sa.CheckConstraint(
            "total_output_tokens >= 0", name="ck_ai_usage_output_tokens",
        ),
        sa.CheckConstraint(
            "estimated_cost_usd >= 0", name="ck_ai_usage_cost",
        ),
    )

    op.create_index("idx_ai_usage_user_id", "ai_usage", ["user_id"])
    op.create_index("idx_ai_usage_usage_date", "ai_usage", ["usage_date"])


def downgrade() -> None:
    """Drop ai_usage table and indexes."""
    op.drop_index("idx_ai_usage_usage_date", table_name="ai_usage")
    op.drop_index("idx_ai_usage_user_id", table_name="ai_usage")
    op.drop_table("ai_usage")
