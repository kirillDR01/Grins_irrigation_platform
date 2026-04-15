"""CRM2: Add service_week_preferences JSONB column to service_agreements.

Stores per-service week preferences selected during onboarding,
used to auto-populate job Week_Of dates during job generation.

Revision ID: 20260411_100600
Revises: 20260411_100500
Requirements: 30.1
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260411_100600"
down_revision: Union[str, None] = "20260411_100500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_agreements",
        sa.Column("service_week_preferences", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("service_agreements", "service_week_preferences")
