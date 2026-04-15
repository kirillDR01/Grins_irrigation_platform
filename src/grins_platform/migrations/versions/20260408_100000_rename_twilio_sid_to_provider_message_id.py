"""Rename sent_messages.twilio_sid to provider_message_id.

Revision ID: 20260408_100000
Revises: 20260407_100000
Create Date: 2026-04-08

Non-breaking rename: column is nullable, existing data preserved.
Requirements: 23.1
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260408_100000"
down_revision: Union[str, None] = "20260407_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename twilio_sid to provider_message_id."""
    op.alter_column(
        "sent_messages",
        "twilio_sid",
        new_column_name="provider_message_id",
    )


def downgrade() -> None:
    """Revert provider_message_id back to twilio_sid."""
    op.alter_column(
        "sent_messages",
        "provider_message_id",
        new_column_name="twilio_sid",
    )
