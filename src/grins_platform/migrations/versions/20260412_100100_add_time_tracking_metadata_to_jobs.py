"""Add time_tracking_metadata JSONB column to jobs table.

Revision ID: 20260412_100100
Revises: 20260412_100000
Requirements: 27.6
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260412_100100"
down_revision: Union[str, None] = "20260412_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("time_tracking_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "time_tracking_metadata")
