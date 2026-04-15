"""Add zip_code, work_requested, agreed_to_terms to google_sheet_submissions.

Revision ID: 20260403_100000
Revises: 20260328_110000
Create Date: 2026-04-03

Adds columns for the new Google Form fields (columns W, Z, AC) that
were introduced when the form was restructured.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260403_100000"
down_revision: Union[str, None] = "20260328_110000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new form columns to google_sheet_submissions."""
    op.add_column(
        "google_sheet_submissions",
        sa.Column("zip_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "google_sheet_submissions",
        sa.Column("work_requested", sa.String(255), nullable=True),
    )
    op.add_column(
        "google_sheet_submissions",
        sa.Column("agreed_to_terms", sa.String(10), nullable=True),
    )


def downgrade() -> None:
    """Remove new form columns from google_sheet_submissions."""
    op.drop_column("google_sheet_submissions", "agreed_to_terms")
    op.drop_column("google_sheet_submissions", "work_requested")
    op.drop_column("google_sheet_submissions", "zip_code")
