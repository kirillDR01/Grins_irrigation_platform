"""Fix sent_messages.message_type check constraint to include campaign + CRM values.

Revision ID: 20260408_100100
Revises: 20260408_100000
Create Date: 2026-04-08

Migration 20260324_100200 was supposed to drop and recreate
``ck_sent_messages_message_type`` with the expanded value list
(``lead_confirmation``, ``estimate_sent``, ``contract_sent``,
``review_request``, ``campaign``), but on some environments only the
column-level changes from that migration stuck and the check constraint
stayed at the pre-CRM 8-value list. The background campaign worker then
fails at insert time with a CheckViolationError, the transaction rolls
back, and the recipient stays stuck in ``pending`` forever.

This migration is idempotent: it drops and recreates the constraint to
match the model, regardless of its current state.

Requirements: CallRail SMS Integration worker recovery
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers
revision: str = "20260408_100100"
down_revision: Union[str, None] = "20260408_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ALLOWED_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign'"
)

_LEGACY_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom'"
)


def upgrade() -> None:
    """Recreate the check constraint with the expanded message_type values."""
    op.execute(
        "ALTER TABLE sent_messages "
        "DROP CONSTRAINT IF EXISTS ck_sent_messages_message_type",
    )
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        f"message_type IN ({_ALLOWED_MESSAGE_TYPES})",
    )


def downgrade() -> None:
    """Revert to the pre-CRM 8-value list."""
    op.execute(
        "ALTER TABLE sent_messages "
        "DROP CONSTRAINT IF EXISTS ck_sent_messages_message_type",
    )
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        f"message_type IN ({_LEGACY_MESSAGE_TYPES})",
    )
