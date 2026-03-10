"""Create agreement_status_logs table.

Revision ID: 20250702_100200
Revises: 20250702_100100
Create Date: 2025-07-02 10:02:00

Creates the agreement_status_logs table for tracking service agreement
status transitions with actor, reason, and metadata.

Validates: Requirements 3.1
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100200"
down_revision: Union[str, None] = "20250702_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agreement_status_logs table."""
    op.create_table(
        "agreement_status_logs",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "agreement_id",
            sa.UUID(),
            sa.ForeignKey("service_agreements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("old_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column(
            "changed_by",
            sa.UUID(),
            sa.ForeignKey("staff.id"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index(
        "ix_agreement_status_logs_agreement_id",
        "agreement_status_logs",
        ["agreement_id"],
    )


def downgrade() -> None:
    """Drop agreement_status_logs table."""
    op.drop_index(
        "ix_agreement_status_logs_agreement_id",
        "agreement_status_logs",
    )
    op.drop_table("agreement_status_logs")
