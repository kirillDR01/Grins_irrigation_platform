"""Create email_suppression_list table.

Revision ID: 20250702_100600
Revises: 20250702_100500
Create Date: 2025-07-02 10:06:00

Creates the email_suppression_list table for permanent email suppression.
Unique constraint on email. No expiration — entries are permanent.

Validates: Requirements 67.5, 67.7
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100600"
down_revision: Union[str, None] = "20250702_100500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create email_suppression_list table."""
    op.create_table(
        "email_suppression_list",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(255),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=True,
        ),
        sa.Column(
            "suppressed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop email_suppression_list table."""
    op.drop_table("email_suppression_list")
