"""Add ``appointment_notes`` table for centralized internal notes.

Revision ID: 20260425_100000
Revises: 20260423_100000
Requirements: 5.1, 5.2
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260425_100000"
down_revision: str | None = "20260423_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the appointment_notes table."""
    op.create_table(
        "appointment_notes",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "appointment_id",
            sa.UUID(),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_by_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_appointment_notes_appointment_id",
        "appointment_notes",
        ["appointment_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop the appointment_notes table."""
    op.drop_index(
        "idx_appointment_notes_appointment_id",
        table_name="appointment_notes",
    )
    op.drop_table("appointment_notes")
