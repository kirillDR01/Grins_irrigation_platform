"""Add ``customers.email_bounced_at`` column.

Revision ID: 20260428_100000
Revises: 20260427_100000
Validates: Estimate approval email portal — Resend bounce handling.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_100000"
down_revision: str | None = "20260427_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable ``email_bounced_at`` timestamp column."""
    op.add_column(
        "customers",
        sa.Column(
            "email_bounced_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop the ``email_bounced_at`` column."""
    op.drop_column("customers", "email_bounced_at")
