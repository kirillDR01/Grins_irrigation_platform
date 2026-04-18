"""Create ``notes`` table for unified cross-stage notes timeline.

The notes table supports the unified Notes Timeline feature (Requirement 4)
where notes follow the lead → sales entry → customer → appointment chain.
Cross-stage threading is achieved via the ``origin_lead_id`` column which
links notes back to the originating lead for merged timeline queries.

Revision ID: 20260416_100500
Revises: 20260416_100400
Requirements: april-16th-fixes-enhancements Requirement 4
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260416_100500"
down_revision: str | None = "20260416_100400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the notes table + indexes."""
    op.create_table(
        "notes",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("subject_type", sa.String(20), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column(
            "author_id",
            sa.UUID(),
            sa.ForeignKey("staff.id"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "origin_lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id"),
            nullable=True,
        ),
        sa.Column(
            "origin_appointment_id",
            sa.UUID(),
            sa.ForeignKey("appointments.id"),
            nullable=True,
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Composite index for querying notes by subject (most common access pattern).
    op.create_index(
        "idx_notes_subject",
        "notes",
        ["subject_type", "subject_id"],
    )
    # Index for cross-stage timeline merging via origin_lead_id.
    op.create_index(
        "idx_notes_origin_lead",
        "notes",
        ["origin_lead_id"],
    )
    # Index for ordering notes by creation time (newest-first queries).
    op.create_index(
        "idx_notes_created_at",
        "notes",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop the notes table + indexes."""
    op.drop_index("idx_notes_created_at", table_name="notes")
    op.drop_index("idx_notes_origin_lead", table_name="notes")
    op.drop_index("idx_notes_subject", table_name="notes")
    op.drop_table("notes")
