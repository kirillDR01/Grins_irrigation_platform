"""Widen sent_messages.message_type CHECK to allow payment_receipt.

Phase 4 of the appointment-modal-umbrella plan added
``MessageType.PAYMENT_RECEIPT = "payment_receipt"`` so
``AppointmentService._send_payment_receipts`` could tag receipt SMS
rows with a distinct, analytics-friendly type. The corresponding CHECK
constraint update was missed alongside the Phase 4 commit, so every
receipt SMS would crash at INSERT time with a CheckViolationError.
This migration extends the constraint to include ``payment_receipt``.

Discovered during Phase 6 E2E pre-flight against dev Postgres.

Revision ID: 20260505_120000
Revises: 20260505_100000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260505_120000"
down_revision: Union[str, None] = "20260505_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Full set after this migration — adds payment_receipt.
_NEW_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification','appointment_confirmation_reply',"
    "'reschedule_followup','payment_link','payment_receipt'"
)

# Previous set (from 20260502_100000).
_PREV_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way',"
    "'automated_notification','appointment_confirmation_reply',"
    "'reschedule_followup','payment_link'"
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
