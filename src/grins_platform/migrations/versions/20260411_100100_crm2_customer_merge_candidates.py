"""CRM2: Create customer_merge_candidates table.

Table for tracking potential duplicate customer pairs with scoring
and review workflow.

Revision ID: 20260411_100100
Revises: 20260411_100000
Requirements: 5.1, 5.6
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260411_100100"
down_revision: Union[str, None] = "20260411_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_merge_candidates",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_a_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_b_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("match_signals", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(50), nullable=True),
        sa.UniqueConstraint(
            "customer_a_id",
            "customer_b_id",
            name="uq_merge_candidates_pair",
        ),
        sa.CheckConstraint(
            "status IN ('pending','merged','dismissed')",
            name="ck_merge_candidates_status",
        ),
    )
    op.create_index(
        "ix_merge_candidates_score_desc",
        "customer_merge_candidates",
        [sa.text("score DESC")],
    )
    op.create_index(
        "ix_merge_candidates_status",
        "customer_merge_candidates",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_merge_candidates_status", table_name="customer_merge_candidates")
    op.drop_index(
        "ix_merge_candidates_score_desc",
        table_name="customer_merge_candidates",
    )
    op.drop_table("customer_merge_candidates")
