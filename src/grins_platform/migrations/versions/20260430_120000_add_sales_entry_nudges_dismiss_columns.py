"""Add ``nudges_paused_until`` and ``dismissed_at`` to ``sales_entries``.

NEW-D introduces two persistent state columns on ``sales_entries`` so
the pipeline UI can:

- Pause/unpause the auto-nudge cadence per entry
  (``nudges_paused_until`` — nullable timestamptz, ``NULL`` = active).
- Dismiss a row from the pipeline-list view without losing it
  (``dismissed_at`` — nullable timestamptz, ``NULL`` = visible).

Both are nullable; existing rows default to ``NULL`` (active /
not-dismissed). No backfill needed.

Revision ID: 20260430_120000
Revises: 20260429_100100
Validates: sales-pipeline bug-hunt NEW-D, list-row dismiss
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260430_120000"
down_revision: str | None = "20260429_100100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``nudges_paused_until`` and ``dismissed_at`` columns."""
    op.add_column(
        "sales_entries",
        sa.Column(
            "nudges_paused_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "sales_entries",
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop the two NEW-D state columns."""
    op.drop_column("sales_entries", "dismissed_at")
    op.drop_column("sales_entries", "nudges_paused_until")
