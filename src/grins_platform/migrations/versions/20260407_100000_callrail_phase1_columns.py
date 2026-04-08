"""Add CallRail Phase 1 columns.

Revision ID: 20260407_100000
Revises: 20260404_100000
Create Date: 2026-04-07

Non-breaking additions for CallRail SMS integration Phase 1:
- campaign_recipients.sending_started_at (S13 state machine + orphan recovery)
- sms_consent_records.created_by_staff_id (S10 CSV attestation audit trail)
- sent_messages.campaign_id (B4 dedupe scoping)
- sent_messages.provider_conversation_id (CallRail conversation ID)
- sent_messages.provider_thread_id (CallRail sms_thread.id)
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "20260407_100000"
down_revision: Union[str, None] = "20260404_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 1 columns."""
    # 0a. campaign_recipients.channel (missing from original migration)
    op.add_column(
        "campaign_recipients",
        sa.Column("channel", sa.String(20), nullable=False, server_default="sms"),
    )

    # 0b. Rename campaign_recipients.status → delivery_status (model mismatch)
    #
    # IDEMPOTENT: some environments (notably the Railway dev DB) were
    # bootstrapped with ``delivery_status`` directly via a different
    # migration ancestry, so the column to rename does not exist there.
    # The original ``op.alter_column(..., new_column_name=...)`` form
    # crashed with ``UndefinedColumnError: column "status" does not
    # exist`` on the first dev deploy of this migration. Wrap the rename
    # in a conditional DO block that no-ops when ``status`` is missing.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'campaign_recipients'
                  AND column_name = 'status'
            ) THEN
                ALTER TABLE campaign_recipients
                    RENAME COLUMN status TO delivery_status;
            END IF;
        END
        $$;
        """,
    )

    # 1. campaign_recipients.sending_started_at
    op.add_column(
        "campaign_recipients",
        sa.Column("sending_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_campaign_recipients_sending_started_at",
        "campaign_recipients",
        ["sending_started_at"],
    )

    # 2. sms_consent_records.created_by_staff_id
    op.add_column(
        "sms_consent_records",
        sa.Column(
            "created_by_staff_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("staff.id", name="fk_sms_consent_records_created_by_staff"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_sms_consent_records_created_by_staff_id",
        "sms_consent_records",
        ["created_by_staff_id"],
    )

    # 3. sent_messages.campaign_id
    op.add_column(
        "sent_messages",
        sa.Column(
            "campaign_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", name="fk_sent_messages_campaign_id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_sent_messages_campaign_id",
        "sent_messages",
        ["campaign_id"],
    )

    # 4. sent_messages.provider_conversation_id
    op.add_column(
        "sent_messages",
        sa.Column("provider_conversation_id", sa.String(50), nullable=True),
    )

    # 5. sent_messages.provider_thread_id
    op.add_column(
        "sent_messages",
        sa.Column("provider_thread_id", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Remove Phase 1 columns."""
    op.drop_column("sent_messages", "provider_thread_id")
    op.drop_column("sent_messages", "provider_conversation_id")
    op.drop_index("ix_sent_messages_campaign_id", table_name="sent_messages")
    op.drop_column("sent_messages", "campaign_id")
    op.drop_index(
        "ix_sms_consent_records_created_by_staff_id",
        table_name="sms_consent_records",
    )
    op.drop_column("sms_consent_records", "created_by_staff_id")
    op.drop_index(
        "ix_campaign_recipients_sending_started_at",
        table_name="campaign_recipients",
    )
    op.drop_column("campaign_recipients", "sending_started_at")
    # Mirror the upgrade's idempotent rename: only rename back to
    # ``status`` if ``delivery_status`` exists and ``status`` does not.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'campaign_recipients'
                  AND column_name = 'delivery_status'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'campaign_recipients'
                  AND column_name = 'status'
            ) THEN
                ALTER TABLE campaign_recipients
                    RENAME COLUMN delivery_status TO status;
            END IF;
        END
        $$;
        """,
    )
    op.drop_column("campaign_recipients", "channel")
