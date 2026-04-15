"""CRM2: Create job_confirmation_responses and reschedule_requests tables.

Tables for the Y/R/C appointment confirmation flow via SMS
and the admin reschedule requests queue.

Revision ID: 20260411_100400
Revises: 20260411_100300
Requirements: 24.6, 25.1
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260411_100400"
down_revision: Union[str, None] = "20260411_100300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_confirmation_responses",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            sa.UUID(),
            sa.ForeignKey("appointments.id"),
            nullable=False,
        ),
        sa.Column(
            "sent_message_id",
            sa.UUID(),
            sa.ForeignKey("sent_messages.id"),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column("from_phone", sa.String(20), nullable=False),
        sa.Column("reply_keyword", sa.String(30), nullable=True),
        sa.Column("raw_reply_body", sa.Text(), nullable=False),
        sa.Column("provider_sid", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "received_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_confirmation_responses_appointment",
        "job_confirmation_responses",
        ["appointment_id"],
    )
    op.create_index(
        "idx_confirmation_responses_status",
        "job_confirmation_responses",
        ["status"],
    )

    op.create_table(
        "reschedule_requests",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            sa.UUID(),
            sa.ForeignKey("appointments.id"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column(
            "original_reply_id",
            sa.UUID(),
            sa.ForeignKey("job_confirmation_responses.id"),
            nullable=True,
        ),
        sa.Column("requested_alternatives", sa.JSON(), nullable=True),
        sa.Column("raw_alternatives_text", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_reschedule_requests_appointment",
        "reschedule_requests",
        ["appointment_id"],
    )
    op.create_index(
        "idx_reschedule_requests_status",
        "reschedule_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_reschedule_requests_status",
        table_name="reschedule_requests",
    )
    op.drop_index(
        "idx_reschedule_requests_appointment",
        table_name="reschedule_requests",
    )
    op.drop_table("reschedule_requests")
    op.drop_index(
        "idx_confirmation_responses_status",
        table_name="job_confirmation_responses",
    )
    op.drop_index(
        "idx_confirmation_responses_appointment",
        table_name="job_confirmation_responses",
    )
    op.drop_table("job_confirmation_responses")
