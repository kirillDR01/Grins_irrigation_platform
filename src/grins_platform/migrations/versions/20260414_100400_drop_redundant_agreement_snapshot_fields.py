"""Drop redundant onboarding-snapshot columns from service_agreements.

The seven columns added in 20260414_100200 turned out to duplicate data
already stored canonically elsewhere:

    tier_slug_snapshot       -> service_agreements.tier_id -> tier.slug
    tier_name_snapshot       -> service_agreements.tier_id -> tier.name
    preferred_service_time   -> customers.preferred_service_times
    access_instructions      -> properties.access_instructions
    gate_code                -> properties.gate_code
    dogs_on_property         -> properties.has_dogs
    no_preference_flags      -> derivable from
                                service_agreements.service_week_preferences
                                (a null value = "No preference")

Customer week selections continue to be captured in
service_agreements.service_week_preferences (JSONB) and propagated to
jobs.target_start_date / target_end_date — neither of which is touched
by this migration.

Revision ID: 20260414_100400
Revises: 20260414_100300
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260414_100400"
down_revision: Union[str, None] = "20260414_100300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("service_agreements", "no_preference_flags")
    op.drop_column("service_agreements", "dogs_on_property")
    op.drop_column("service_agreements", "gate_code")
    op.drop_column("service_agreements", "access_instructions")
    op.drop_column("service_agreements", "preferred_service_time")
    op.drop_column("service_agreements", "tier_name_snapshot")
    op.drop_column("service_agreements", "tier_slug_snapshot")


def downgrade() -> None:
    op.add_column(
        "service_agreements",
        sa.Column("tier_slug_snapshot", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column("tier_name_snapshot", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column("preferred_service_time", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column("access_instructions", sa.Text(), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column("gate_code", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column("dogs_on_property", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column("no_preference_flags", sa.JSON(), nullable=True),
    )
