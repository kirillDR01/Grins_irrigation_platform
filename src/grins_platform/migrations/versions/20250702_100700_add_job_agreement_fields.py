"""Add service agreement fields to jobs table.

Revision ID: 20250702_100700
Revises: 20250702_100600
Create Date: 2025-07-02 10:07:00

Adds service_agreement_id (FK), target_start_date, target_end_date to jobs.

Validates: Requirements 4.1, 4.2
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100700"
down_revision: Union[str, None] = "20250702_100600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add service agreement fields to jobs table."""
    op.add_column(
        "jobs",
        sa.Column(
            "service_agreement_id",
            sa.UUID(),
            sa.ForeignKey("service_agreements.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("target_start_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("target_end_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    """Remove service agreement fields from jobs table."""
    op.drop_column("jobs", "target_end_date")
    op.drop_column("jobs", "target_start_date")
    op.drop_column("jobs", "service_agreement_id")
