"""Add content_hash column to google_sheet_submissions.

Revision ID: 20260404_100000
Revises: 20260403_100000
Create Date: 2026-04-04

Replaces fragile row-number watermark dedup with content-hash-based dedup.
Adds a SHA-256 content_hash column for each submission row and drops the
unique constraint on sheet_row_number (kept as a regular column for display).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260404_100000"
down_revision: Union[str, None] = "20260403_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add content_hash column and drop sheet_row_number unique constraint."""
    # Add content_hash column
    op.add_column(
        "google_sheet_submissions",
        sa.Column("content_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_google_sheet_submissions_content_hash",
        "google_sheet_submissions",
        ["content_hash"],
        unique=True,
    )

    # Drop the unique constraint on sheet_row_number.
    # The constraint name varies by DB — try the standard naming convention.
    op.drop_constraint(
        "google_sheet_submissions_sheet_row_number_key",
        "google_sheet_submissions",
        type_="unique",
    )


def downgrade() -> None:
    """Remove content_hash column and restore sheet_row_number unique constraint."""
    op.create_unique_constraint(
        "google_sheet_submissions_sheet_row_number_key",
        "google_sheet_submissions",
        ["sheet_row_number"],
    )
    op.drop_index(
        "ix_google_sheet_submissions_content_hash",
        table_name="google_sheet_submissions",
    )
    op.drop_column("google_sheet_submissions", "content_hash")
