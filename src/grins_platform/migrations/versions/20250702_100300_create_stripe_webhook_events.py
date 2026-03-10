"""Create stripe_webhook_events table.

Revision ID: 20250702_100300
Revises: 20250702_100200
Create Date: 2025-07-02 10:03:00

Creates the stripe_webhook_events table for idempotent Stripe
webhook event processing and deduplication.

Validates: Requirements 7.1
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100300"
down_revision: Union[str, None] = "20250702_100200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create stripe_webhook_events table."""
    op.create_table(
        "stripe_webhook_events",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "stripe_event_id",
            sa.String(255),
            unique=True,
            nullable=False,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_stripe_webhook_events_stripe_event_id",
        "stripe_webhook_events",
        ["stripe_event_id"],
    )


def downgrade() -> None:
    """Drop stripe_webhook_events table."""
    op.drop_index(
        "ix_stripe_webhook_events_stripe_event_id",
        "stripe_webhook_events",
    )
    op.drop_table("stripe_webhook_events")
