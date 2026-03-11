"""Add surcharge and onboarding reminder fields to service_agreements.

Revision ID: 20250710_100200
Revises: 20250710_100100
Create Date: 2025-07-10 10:02:00

Adds surcharge-related fields (zone_count, has_lake_pump, base_price) and
onboarding reminder tracking fields to the service_agreements table.

Validates: Requirements 3.13, 10.6
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250710_100200"
down_revision: Union[str, None] = "20250710_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new columns to service_agreements table."""
    op.add_column(
        "service_agreements",
        sa.Column("zone_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column(
            "has_lake_pump",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "service_agreements",
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column(
            "onboarding_reminder_sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "service_agreements",
        sa.Column(
            "onboarding_reminder_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Remove new columns from service_agreements table."""
    op.drop_column("service_agreements", "onboarding_reminder_count")
    op.drop_column("service_agreements", "onboarding_reminder_sent_at")
    op.drop_column("service_agreements", "base_price")
    op.drop_column("service_agreements", "has_lake_pump")
    op.drop_column("service_agreements", "zone_count")
