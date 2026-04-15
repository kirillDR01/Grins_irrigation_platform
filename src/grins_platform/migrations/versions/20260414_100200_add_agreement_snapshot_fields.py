"""Add nullable onboarding-snapshot columns to service_agreements.

Freezes the customer's onboarding-time selections on the agreement for
audit purposes. Source-of-truth for current values continues to live on
properties (gate_code, dogs, access_instructions) and customers
(preferred_service_times); these columns snapshot what was answered at
onboarding completion so later edits don't lose that record.

All columns are nullable — existing agreement rows are unaffected;
required-ness is enforced at the application layer only, and only for
new onboardings submitted via /onboarding/complete.

Revision ID: 20260414_100200
Revises: 20260414_100100
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260414_100200"
down_revision: Union[str, None] = "20260414_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_column("service_agreements", "no_preference_flags")
    op.drop_column("service_agreements", "dogs_on_property")
    op.drop_column("service_agreements", "gate_code")
    op.drop_column("service_agreements", "access_instructions")
    op.drop_column("service_agreements", "preferred_service_time")
    op.drop_column("service_agreements", "tier_name_snapshot")
    op.drop_column("service_agreements", "tier_slug_snapshot")
