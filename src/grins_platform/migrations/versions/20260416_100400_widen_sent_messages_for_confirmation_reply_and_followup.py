"""Widen sent_messages.message_type CHECK for confirmation reply + followup.

bughunt M-9: ``_try_confirmation_reply`` now routes auto-replies and
the reschedule follow-up SMS through ``SMSService.send_message`` so a
``SentMessage`` row is created for compliance/audit. To keep the new
rows tagged with intent (rather than reusing ``appointment_confirmation``
for outbound replies and breaking the per-type dedup), two new message
types are added: ``appointment_confirmation_reply`` for the Y/R/C
acknowledgment auto-reply, and ``reschedule_followup`` for the
"Please reply with 2-3 dates" follow-up.

Revision ID: 20260416_100400
Revises: 20260416_100300
Requirements: bughunt M-9 / 2026-04-16

The original draft of this migration used revision id ``20260416_100000``
which collided with the H-4 payment-method-CHECK migration that landed
in the H-1..H-14 wave. Renumbered to ``20260416_100400`` and chained
off H-12's seed-business-settings migration so the dev deploy applies
cleanly. (See the post-merge fixup that introduced this rename.)
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260416_100400"
down_revision: Union[str, None] = "20260416_100300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Full set after this migration — adds confirmation_reply + reschedule_followup.
_NEW_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification','appointment_confirmation_reply',"
    "'reschedule_followup'"
)

# Previous set (from migration 20260414_100600).
_PREV_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification'"
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
