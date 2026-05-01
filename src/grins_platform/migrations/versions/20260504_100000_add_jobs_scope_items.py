"""Add ``scope_items`` JSONB column to ``jobs``.

Phase 0 (AJ-4): when a portal-approved estimate auto-creates a job, the
estimate's ``line_items`` JSONB are copied into ``jobs.scope_items`` so
office staff can schedule against the priced scope without re-keying.

Mirrors the existing ``Estimate.line_items`` JSONB shape verbatim.

Revision ID: 20260504_100000
Revises: 20260503_100000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260504_100000"
down_revision: str | None = "20260503_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``jobs.scope_items`` JSONB nullable."""
    op.add_column(
        "jobs",
        sa.Column("scope_items", JSONB, nullable=True),
    )


def downgrade() -> None:
    """Drop ``jobs.scope_items``."""
    op.drop_column("jobs", "scope_items")
