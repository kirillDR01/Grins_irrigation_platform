"""Widen sent_messages.message_type CHECK to allow Y/R/C reply sub-types.

F5 fix (2026-05-05): the existing ``APPOINTMENT_CONFIRMATION_REPLY`` enum
value covered all customer-facing acknowledgments to inbound Y/R/C
keywords. Combined with the 24h
``(customer_id, message_type)`` dedup at ``sms_service.py:344``, a Y-ack
silently muted any subsequent R-ack or C-ack within the same 24h window
— the customer would change their mind, send R, and never hear back.

This migration extends the CHECK constraint to allow three per-keyword
sub-types so the dedup query at the call site can include the keyword
sub-type alongside ``appointment_id``, restoring ack delivery for legit
state transitions on the same customer/appointment.

The legacy ``appointment_confirmation_reply`` value remains valid for
historical rows and any callers that have not yet migrated to the
sub-typed values.

Revision ID: 20260508_120000
Revises: 20260507_120000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260508_120000"
down_revision: Union[str, None] = "20260507_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification','appointment_confirmation_reply',"
    "'appointment_confirmation_reply_y','appointment_confirmation_reply_r',"
    "'appointment_confirmation_reply_c',"
    "'reschedule_followup','payment_link','payment_receipt'"
)

_PREV_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification','appointment_confirmation_reply',"
    "'reschedule_followup','payment_link','payment_receipt'"
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
