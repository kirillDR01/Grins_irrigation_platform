"""Add ``customer_tags`` table for appointment modal tag feature.

Revision ID: 20260423_100000
Revises: 20260421_100200
Requirements: 12.1, 12.2, 12.3
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260423_100000"
down_revision: str | None = "20260421_100200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the customer_tags table."""
    op.create_table(
        "customer_tags",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(32), nullable=False),
        sa.Column(
            "tone",
            sa.String(10),
            sa.CheckConstraint(
                "tone IN ('neutral', 'blue', 'green', 'amber', 'violet')",
                name="ck_customer_tags_tone",
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(10),
            sa.CheckConstraint(
                "source IN ('manual', 'system')",
                name="ck_customer_tags_source",
            ),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "customer_id",
            "label",
            name="uq_customer_tags_customer_label",
        ),
    )
    op.create_index(
        "ix_customer_tags_customer_id",
        "customer_tags",
        ["customer_id"],
    )


def downgrade() -> None:
    """Drop the customer_tags table."""
    op.drop_index("ix_customer_tags_customer_id", table_name="customer_tags")
    op.drop_table("customer_tags")
