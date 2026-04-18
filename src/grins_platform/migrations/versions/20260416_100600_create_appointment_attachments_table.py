"""Create ``appointment_attachments`` table for file uploads on appointments.

The appointment_attachments table supports the Calendar Enrichment feature
(Requirement 6) where staff can attach files (photos, PDFs, documents) to
both job and estimate appointments. Files are stored in S3 with metadata
tracked in this table.

Revision ID: 20260416_100600
Revises: 20260416_100500
Requirements: april-16th-fixes-enhancements Requirement 6
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260416_100600"
down_revision: str | None = "20260416_100500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the appointment_attachments table + index."""
    op.create_table(
        "appointment_attachments",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("appointment_id", sa.UUID(), nullable=False),
        sa.Column("appointment_type", sa.String(20), nullable=False),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column(
            "uploaded_by",
            sa.UUID(),
            sa.ForeignKey("staff.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Composite index for querying attachments by appointment (most common access pattern).
    op.create_index(
        "idx_appointment_attachments_appointment",
        "appointment_attachments",
        ["appointment_type", "appointment_id"],
    )


def downgrade() -> None:
    """Drop the appointment_attachments table + index."""
    op.drop_index(
        "idx_appointment_attachments_appointment",
        table_name="appointment_attachments",
    )
    op.drop_table("appointment_attachments")
