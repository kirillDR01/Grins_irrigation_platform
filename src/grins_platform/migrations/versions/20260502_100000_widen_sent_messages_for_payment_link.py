"""Widen sent_messages.message_type CHECK to allow payment_link.

Phase 2 of the Stripe Payment Links work (Architecture C) added
``MessageType.PAYMENT_LINK = "payment_link"`` to ``schemas/ai.py`` so the
``InvoiceService.send_payment_link`` path could tag the SMS audit row with a
distinct, analytics-friendly type. The corresponding CHECK constraint update
was missed in the original Phase 2 migration, so every send-link click
crashed at INSERT time with a CheckViolationError. This migration extends
the constraint to include ``payment_link``.

Discovered during Phase 6 E2E validation against the dev Vercel deployment.

Revision ID: 20260502_100000
Revises: 20260501_120000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260502_100000"
down_revision: Union[str, None] = "20260501_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Full set after this migration — adds payment_link.
_NEW_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification','appointment_confirmation_reply',"
    "'reschedule_followup','payment_link'"
)

# Previous set (from migration 20260416_100400).
_PREV_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification','appointment_confirmation_reply',"
    "'reschedule_followup'"
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
