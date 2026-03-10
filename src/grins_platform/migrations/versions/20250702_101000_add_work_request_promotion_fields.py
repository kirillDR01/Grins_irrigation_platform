"""Add promoted_to_lead_id and promoted_at to google_sheet_submissions.

Revision ID: 20250702_101000
Revises: 20250702_100900
Create Date: 2025-07-02 10:10:00

Adds lead promotion tracking fields to the work requests
(google_sheet_submissions) table.

Validates: Requirements 52.3, 52.4
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20250702_101000"
down_revision: Union[str, None] = "20250702_100900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add promotion tracking fields to google_sheet_submissions."""
    op.add_column(
        "google_sheet_submissions",
        sa.Column(
            "promoted_to_lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "google_sheet_submissions",
        sa.Column(
            "promoted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove promotion tracking fields from google_sheet_submissions."""
    op.drop_column("google_sheet_submissions", "promoted_at")
    op.drop_column("google_sheet_submissions", "promoted_to_lead_id")
