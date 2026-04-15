"""Align campaign_recipients.delivered_at → sent_at across environments.

Revision ID: 20260408_100200
Revises: 20260408_100100
Create Date: 2026-04-08

The CampaignRecipient ORM model has used ``sent_at`` as the column
name since the parent CallRail SMS Integration Phase 1 work, but the
original ``20260324_100100_crm_create_new_tables`` migration created
the table with ``delivered_at``. There is no migration in alembic
history that renames it. Some environments (the dev Postgres at
local Docker) have ``sent_at`` because the schema was patched
manually outside of alembic. Other environments (Railway dev) have
``delivered_at`` because they applied the migration history as
written.

This is the same drift pattern as the earlier ``status →
delivery_status`` rename in 20260407_100000. The fix is to add a
forward migration that conditionally renames ``delivered_at →
sent_at`` only when ``delivered_at`` exists and ``sent_at`` does not.

Symptom: campaign worker tick crashes every 60 seconds with
``column campaign_recipients.sent_at does not exist`` because the
ORM SELECT references ``sent_at`` which the DB doesn't have.

Idempotency table:

| ``delivered_at`` | ``sent_at`` | Action |
|---|---|---|
| exists           | absent      | rename delivered_at → sent_at |
| absent           | exists      | no-op (local already correct) |
| exists           | exists      | impossible state, raise via PG (rare) |
| absent           | absent      | no-op (table from a future schema) |

Downgrade mirrors the same pattern in reverse so a rollback on dev
restores ``delivered_at`` and a rollback on local is a no-op.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers
revision: str = "20260408_100200"
down_revision: Union[str, None] = "20260408_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Conditionally rename campaign_recipients.delivered_at → sent_at."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'campaign_recipients'
                  AND column_name = 'delivered_at'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'campaign_recipients'
                  AND column_name = 'sent_at'
            ) THEN
                ALTER TABLE campaign_recipients
                    RENAME COLUMN delivered_at TO sent_at;
            END IF;
        END
        $$;
        """,
    )


def downgrade() -> None:
    """Conditionally rename sent_at → delivered_at."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'campaign_recipients'
                  AND column_name = 'sent_at'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'campaign_recipients'
                  AND column_name = 'delivered_at'
            ) THEN
                ALTER TABLE campaign_recipients
                    RENAME COLUMN sent_at TO delivered_at;
            END IF;
        END
        $$;
        """,
    )
