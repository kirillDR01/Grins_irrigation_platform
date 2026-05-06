"""Add consent_timestamp + UTM attribution columns to leads.

The customer-site lead form already submits ``consent_timestamp`` and the
five ``utm_*`` fields on every payload, but ``LeadSubmission`` does not
declare them, so Pydantic v2's default ``extra='ignore'`` silently drops
them. This migration adds the six nullable columns so the platform can
finally persist that data.

All six are nullable with no server default — old rows stay NULL (no
back-fill data exists), and the schema-layer fix in this same change
declares the fields on ``LeadSubmission`` / ``LeadResponse`` so they
round-trip through the API.

Revision ID: 20260510_120000
Revises: 20260509_120000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260510_120000"
down_revision: Union[str, None] = "20260509_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("utm_source", sa.String(100), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("utm_medium", sa.String(100), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("utm_campaign", sa.String(100), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("utm_term", sa.String(100), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("utm_content", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leads", "utm_content")
    op.drop_column("leads", "utm_term")
    op.drop_column("leads", "utm_campaign")
    op.drop_column("leads", "utm_medium")
    op.drop_column("leads", "utm_source")
    op.drop_column("leads", "consent_timestamp")
