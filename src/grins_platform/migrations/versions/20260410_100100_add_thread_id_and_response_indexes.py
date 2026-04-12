"""Add provider_thread_id index on sent_messages and unique partial index
on campaign_responses.provider_message_id.

BUG-M7: Speeds up correlate_reply() lookups on sent_messages.provider_thread_id.
BUG-M8: Prevents duplicate campaign_response rows from webhook retries.

Revision ID: 20260410_100100
Revises: 20260410_100000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260410_100100"
down_revision: Union[str, None] = "20260410_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # M7: Index for correlate_reply() thread-based lookups
    op.create_index(
        "ix_sent_messages_provider_thread_id",
        "sent_messages",
        ["provider_thread_id"],
    )

    # M8: Unique partial index to prevent duplicate campaign responses
    op.create_index(
        "ix_campaign_responses_provider_message_id",
        "campaign_responses",
        ["provider_message_id"],
        unique=True,
        postgresql_where="provider_message_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_campaign_responses_provider_message_id",
        table_name="campaign_responses",
    )
    op.drop_index(
        "ix_sent_messages_provider_thread_id",
        table_name="sent_messages",
    )
