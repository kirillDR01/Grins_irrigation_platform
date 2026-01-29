"""Add payment_collected_on_site column to jobs table.

Revision ID: 20250624_100000
Revises: 20250623_100000
Create Date: 2025-06-24 10:00:00

This migration adds the payment_collected_on_site column to the jobs table
to track whether payment was collected on-site during job completion.

Validates: Requirement 10.6
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250624_100000"
down_revision = "20250623_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add payment_collected_on_site column to jobs table."""
    op.add_column(
        "jobs",
        sa.Column(
            "payment_collected_on_site",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    """Remove payment_collected_on_site column from jobs table."""
    op.drop_column("jobs", "payment_collected_on_site")
