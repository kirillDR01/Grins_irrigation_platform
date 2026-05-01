"""Add ``preferred_maps_app`` column to ``staff``.

Phase 5.2 (umbrella plan): persists the tech's chosen Maps app
(``apple`` | ``google``) so the MapsPickerPopover can default to that
choice instead of asking on every directions click.

Revision ID: 20260505_100000
Revises: 20260504_130000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_100000"
down_revision: str | None = "20260504_130000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``staff.preferred_maps_app`` nullable VARCHAR(20)."""
    op.add_column(
        "staff",
        sa.Column("preferred_maps_app", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    """Drop ``staff.preferred_maps_app``."""
    op.drop_column("staff", "preferred_maps_app")
