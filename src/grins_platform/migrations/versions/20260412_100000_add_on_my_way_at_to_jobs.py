"""Add on_my_way_at timestamp column to jobs table.

Revision ID: 20260412_100000
Revises: 20260411_100700
Requirements: 27.1, 27.6
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260412_100000"
down_revision: Union[str, None] = "20260411_100700"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("on_my_way_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "on_my_way_at")
