"""Add ``assigned_to_user_id`` to ``sales_calendar_events``.

Revision ID: 20260426_100000
Revises: 20260425_100000
Validates: Schedule Estimate Visit feature handoff
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260426_100000"
down_revision: str | None = "20260425_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable ``assigned_to_user_id`` FK + index."""
    op.add_column(
        "sales_calendar_events",
        sa.Column(
            "assigned_to_user_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_sales_calendar_assigned_to",
        "sales_calendar_events",
        ["assigned_to_user_id"],
    )


def downgrade() -> None:
    """Drop FK + index."""
    op.drop_index(
        "ix_sales_calendar_assigned_to",
        table_name="sales_calendar_events",
    )
    op.drop_column("sales_calendar_events", "assigned_to_user_id")
