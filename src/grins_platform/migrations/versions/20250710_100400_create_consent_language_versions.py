"""Create consent_language_versions table and seed v1.0 record.

Revision ID: 20250710_100400
Revises: 20250710_100300
Create Date: 2025-07-10 10:04:00

Creates the consent_language_versions table for tracking TCPA disclosure
text versions. Seeds initial v1.0 record with current disclosure text.

Validates: Requirements 11.1, 11.2, 11.3
"""

import datetime
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250710_100400"
down_revision: Union[str, None] = "20250710_100300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INITIAL_CONSENT_TEXT = (
    "By providing your phone number, you consent to receive automated "
    "text messages from Grin's Irrigations regarding your service requests, "
    "appointments, and account updates. Message and data rates may apply. "
    "You can opt out at any time by replying STOP."
)


def upgrade() -> None:
    """Create consent_language_versions table and seed v1.0."""
    op.create_table(
        "consent_language_versions",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("version", sa.String(20), nullable=False, unique=True),
        sa.Column("consent_text", sa.Text(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("deprecated_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Seed v1.0 record
    versions_table = sa.table(
        "consent_language_versions",
        sa.column("version", sa.String),
        sa.column("consent_text", sa.Text),
        sa.column("effective_date", sa.Date),
    )
    op.bulk_insert(
        versions_table,
        [
            {
                "version": "v1.0",
                "consent_text": INITIAL_CONSENT_TEXT,
                "effective_date": datetime.date(2025, 7, 10),
            },
        ],
    )


def downgrade() -> None:
    """Drop consent_language_versions table."""
    op.drop_table("consent_language_versions")
