"""Widen sent_messages.message_type CHECK to allow appointment_reschedule and appointment_cancellation.

Commit ea81dc6 introduced two new MessageType enum values so the
per-appointment dedup in SMSService stops collapsing reschedule /
cancellation SMS onto the initial confirmation. The Python enum
was updated in both schemas/ai.py and models/enums.py, but the
DB CHECK constraint ``ck_sent_messages_message_type`` still only
permits the earlier set — so every outbound reschedule / cancel
INSERT raises CheckViolationError and rolls back the surrounding
transaction (observed on dev: the cancel endpoint returns 204,
but the status update gets rolled back by the failed SentMessage
insert).

Rewrite the CHECK constraint to include the two new values.

Revision ID: 20260414_100500
Revises: 20260414_100400
Requirements: CR-10 / bughunt 2026-04-14
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260414_100500"
down_revision: Union[str, None] = "20260414_100400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Full set after this migration — includes the new appointment_reschedule
# and appointment_cancellation values.
_NEW_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reschedule',"
    "'appointment_cancellation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way'"
)

# Previous set (from migration 20260411_100700).
_PREV_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reminder',"
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
