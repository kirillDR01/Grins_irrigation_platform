"""Add campaigns.poll_options column and campaign_responses table.

Revision ID: 20260409_100000
Revises: 20260408_100300
Create Date: 2026-04-09

Adds poll scheduling support: a JSONB column on campaigns for poll options,
and a new campaign_responses table for storing inbound SMS replies.
Single migration for atomic rollback.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers
revision: str = "20260409_100000"
down_revision: Union[str, None] = "20260408_100300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add poll_options column and campaign_responses table."""
    # 1. Add poll_options JSONB column to campaigns
    op.execute(
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS poll_options JSONB;",
    )

    # 2. Create campaign_responses table
    op.create_table(
        "campaign_responses",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "campaign_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sent_message_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("sent_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "lead_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("recipient_name", sa.String(200), nullable=True),
        sa.Column("recipient_address", sa.Text, nullable=True),
        sa.Column("selected_option_key", sa.String(8), nullable=True),
        sa.Column("selected_option_label", sa.Text, nullable=True),
        sa.Column("raw_reply_body", sa.Text, nullable=False),
        sa.Column("provider_message_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "status IN ('parsed', 'needs_review', 'opted_out', 'orphan')",
            name="ck_campaign_responses_status",
        ),
    )

    # 3. Create indexes
    op.create_index(
        "ix_campaign_responses_campaign_id",
        "campaign_responses",
        ["campaign_id"],
    )
    op.create_index(
        "ix_campaign_responses_phone_received_at",
        "campaign_responses",
        ["phone", sa.text("received_at DESC")],
    )
    op.create_index(
        "ix_campaign_responses_status",
        "campaign_responses",
        ["status"],
    )


def downgrade() -> None:
    """Drop campaign_responses table and poll_options column."""
    op.drop_table("campaign_responses")
    op.execute("ALTER TABLE campaigns DROP COLUMN IF EXISTS poll_options;")
