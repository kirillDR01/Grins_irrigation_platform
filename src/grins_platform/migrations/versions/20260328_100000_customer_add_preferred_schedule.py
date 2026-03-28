"""Add preferred_schedule columns to customers table.

Revision ID: 20260328_100000
Revises: 20260326_120000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260328_100000"
down_revision = "20260326_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("preferred_schedule", sa.String(30), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("preferred_schedule_details", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customers", "preferred_schedule_details")
    op.drop_column("customers", "preferred_schedule")
