"""Polymorphic confirmation lifecycle: extend Y/R/C tables to SalesCalendarEvent.

Adds a nullable ``sales_calendar_event_id`` FK to ``sent_messages``,
``job_confirmation_responses``, and ``reschedule_requests`` so the existing
two-way SMS confirmation infrastructure (``JobConfirmationService``,
``RescheduleRequest``, ``SMSService._try_confirmation_reply``) can route Y/R/C
replies for estimate visits as well as appointments.

Schema changes:

1. ``sales_calendar_events`` — new ``confirmation_status`` (default ``'pending'``)
   and ``confirmation_status_at`` columns, plus a CHECK constraint restricting
   ``confirmation_status`` to ``{pending, confirmed, reschedule_requested,
   cancelled}``. Backfill is implicit via the server default.

2. ``sent_messages`` — new ``sales_calendar_event_id`` FK (nullable, ``ON DELETE
   SET NULL``) + index + parallel partial index
   ``ix_sent_messages_active_confirmation_by_sales_event`` on
   ``(sales_calendar_event_id, message_type) WHERE superseded_at IS NULL``,
   mirroring the existing appointment-side index. The
   ``ck_sent_messages_message_type`` CHECK is extended to allow four new values:
   ``estimate_visit_confirmation`` and its three reply sub-types.

   No XOR CHECK on ``sent_messages``: campaign / lead-confirmation rows already
   have both ``appointment_id`` and (now) ``sales_calendar_event_id`` null.

3. ``job_confirmation_responses`` — ``appointment_id`` and ``job_id`` loosened
   to ``nullable=True`` (sales calendar events have no job FK); new
   ``sales_calendar_event_id`` FK + index; XOR CHECK
   ``(appointment_id IS NOT NULL) <> (sales_calendar_event_id IS NOT NULL)``.

4. ``reschedule_requests`` — same shape as ``job_confirmation_responses`` plus
   a parallel partial unique index
   ``uq_reschedule_requests_open_per_sales_calendar_event`` on
   ``(sales_calendar_event_id) WHERE status='open'``, mirroring the existing
   appointment-side index added in 20260421_100000.

   Pre-flight dedup is N/A: ``sales_calendar_event_id`` is brand-new on this
   table, so there are no existing rows to dedupe before the partial unique
   index is created.

Note on ``job_id`` nullability (gap not flagged in the plan's verified facts):
the existing ``job_confirmation_responses.job_id`` and
``reschedule_requests.job_id`` columns are NOT NULL. Sales calendar events have
no associated ``Job`` row, so PR B's sales-side handler must be able to insert
rows without ``job_id``. This migration loosens both. Existing appointment-side
constructors continue to set ``job_id`` so behavior is unchanged.

Revision ID: 20260509_120000
Revises: 20260508_120000
Requirements: sales-pipeline-estimate-visit-confirmation-lifecycle
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "20260509_120000"
down_revision: Union[str, None] = "20260508_120000"
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
    "'estimate_visit_confirmation',"
    "'estimate_visit_confirmation_reply_y',"
    "'estimate_visit_confirmation_reply_r',"
    "'estimate_visit_confirmation_reply_c',"
    "'reschedule_followup','payment_link','payment_receipt'"
)

_PREV_MESSAGE_TYPES = (
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


def upgrade() -> None:
    """Apply polymorphic confirmation schema."""
    # 1. sales_calendar_events: confirmation_status + timestamp + CHECK
    op.add_column(
        "sales_calendar_events",
        sa.Column(
            "confirmation_status",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "sales_calendar_events",
        sa.Column(
            "confirmation_status_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_sales_calendar_events_confirmation_status",
        "sales_calendar_events",
        "confirmation_status IN ("
        "'pending','confirmed','reschedule_requested','cancelled'"
        ")",
    )

    # 2. sent_messages: sales_calendar_event_id FK + indexes
    op.add_column(
        "sent_messages",
        sa.Column("sales_calendar_event_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_sent_messages_sales_calendar_event_id",
        "sent_messages",
        "sales_calendar_events",
        ["sales_calendar_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_sent_messages_sales_calendar_event_id",
        "sent_messages",
        ["sales_calendar_event_id"],
    )
    op.create_index(
        "ix_sent_messages_active_confirmation_by_sales_event",
        "sent_messages",
        ["sales_calendar_event_id", "message_type"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )

    # 3. sent_messages: extend MessageType CHECK to include estimate variants
    op.execute(
        "ALTER TABLE sent_messages "
        "DROP CONSTRAINT IF EXISTS ck_sent_messages_message_type",
    )
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        f"message_type IN ({_NEW_MESSAGE_TYPES})",
    )

    # 4. job_confirmation_responses: nullable appointment_id + job_id + new FK
    #    + XOR CHECK + index
    op.alter_column(
        "job_confirmation_responses",
        "appointment_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "job_confirmation_responses",
        "job_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "job_confirmation_responses",
        sa.Column("sales_calendar_event_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_job_confirmation_responses_sales_calendar_event_id",
        "job_confirmation_responses",
        "sales_calendar_events",
        ["sales_calendar_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_job_confirmation_responses_sales_calendar_event_id",
        "job_confirmation_responses",
        ["sales_calendar_event_id"],
    )
    op.create_check_constraint(
        "ck_job_confirmation_responses_target_xor",
        "job_confirmation_responses",
        "(appointment_id IS NOT NULL) <> (sales_calendar_event_id IS NOT NULL)",
    )

    # 5. reschedule_requests: same shape + parallel partial unique index
    op.alter_column(
        "reschedule_requests",
        "appointment_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "reschedule_requests",
        "job_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "reschedule_requests",
        sa.Column("sales_calendar_event_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_reschedule_requests_sales_calendar_event_id",
        "reschedule_requests",
        "sales_calendar_events",
        ["sales_calendar_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_reschedule_requests_sales_calendar_event_id",
        "reschedule_requests",
        ["sales_calendar_event_id"],
    )
    op.create_check_constraint(
        "ck_reschedule_requests_target_xor",
        "reschedule_requests",
        "(appointment_id IS NOT NULL) <> (sales_calendar_event_id IS NOT NULL)",
    )
    op.create_index(
        "uq_reschedule_requests_open_per_sales_calendar_event",
        "reschedule_requests",
        ["sales_calendar_event_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    """Reverse the polymorphic confirmation schema."""
    # Reverse in opposite order
    op.drop_index(
        "uq_reschedule_requests_open_per_sales_calendar_event",
        table_name="reschedule_requests",
    )
    op.drop_constraint(
        "ck_reschedule_requests_target_xor",
        "reschedule_requests",
        type_="check",
    )
    op.drop_index(
        "ix_reschedule_requests_sales_calendar_event_id",
        table_name="reschedule_requests",
    )
    op.drop_constraint(
        "fk_reschedule_requests_sales_calendar_event_id",
        "reschedule_requests",
        type_="foreignkey",
    )
    op.drop_column("reschedule_requests", "sales_calendar_event_id")
    op.alter_column(
        "reschedule_requests",
        "job_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "reschedule_requests",
        "appointment_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=False,
    )

    op.drop_constraint(
        "ck_job_confirmation_responses_target_xor",
        "job_confirmation_responses",
        type_="check",
    )
    op.drop_index(
        "ix_job_confirmation_responses_sales_calendar_event_id",
        table_name="job_confirmation_responses",
    )
    op.drop_constraint(
        "fk_job_confirmation_responses_sales_calendar_event_id",
        "job_confirmation_responses",
        type_="foreignkey",
    )
    op.drop_column("job_confirmation_responses", "sales_calendar_event_id")
    op.alter_column(
        "job_confirmation_responses",
        "job_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "job_confirmation_responses",
        "appointment_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=False,
    )

    op.execute(
        "ALTER TABLE sent_messages "
        "DROP CONSTRAINT IF EXISTS ck_sent_messages_message_type",
    )
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        f"message_type IN ({_PREV_MESSAGE_TYPES})",
    )

    op.drop_index(
        "ix_sent_messages_active_confirmation_by_sales_event",
        table_name="sent_messages",
    )
    op.drop_index(
        "ix_sent_messages_sales_calendar_event_id",
        table_name="sent_messages",
    )
    op.drop_constraint(
        "fk_sent_messages_sales_calendar_event_id",
        "sent_messages",
        type_="foreignkey",
    )
    op.drop_column("sent_messages", "sales_calendar_event_id")

    op.drop_constraint(
        "ck_sales_calendar_events_confirmation_status",
        "sales_calendar_events",
        type_="check",
    )
    op.drop_column("sales_calendar_events", "confirmation_status_at")
    op.drop_column("sales_calendar_events", "confirmation_status")
