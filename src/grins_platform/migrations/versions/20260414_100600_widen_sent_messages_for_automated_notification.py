"""Widen sent_messages.message_type CHECK to allow automated_notification.

Sprint 1 of the post-bughunt remediation (CR-8) migrates
``SMSService.send_automated_message`` — which previously bypassed
SentMessage audit, per-type dedup, consent check, and lead-touch — onto
the canonical ``send_message`` path. To keep dedup meaningful for
callers whose existing label did not map to an existing enum value
("automated"), a new ``MessageType.AUTOMATED_NOTIFICATION`` is added.
This migration extends the CHECK constraint so rows carrying that
value can be inserted.

Revision ID: 20260414_100600
Revises: 20260414_100500
Requirements: CR-8 / bughunt 2026-04-14
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260414_100600"
down_revision: Union[str, None] = "20260414_100500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Full set after this migration — adds automated_notification.
_NEW_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification'"
)

# Previous set (from migration 20260414_100500).
_PREV_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way'"
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE sent_messages "
        "DROP CONSTRAINT IF EXISTS ck_sent_messages_message_type",
    )
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        f"message_type IN ({_NEW_MESSAGE_TYPES})",
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE sent_messages "
        "DROP CONSTRAINT IF EXISTS ck_sent_messages_message_type",
    )
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        f"message_type IN ({_PREV_MESSAGE_TYPES})",
    )
