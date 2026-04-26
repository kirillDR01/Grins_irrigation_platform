"""Create ``appointment_reminder_log`` table for WP-10 day-2 reminder dedup.

Gap-10 Phase 1 introduces a nightly Day-2 No-Reply Reminder job. The
``appointment_reminder_log`` table is an append-only ledger of reminder
sends per (appointment, stage) so the job can guarantee at-most-once
delivery across hourly ticks even when the eligibility query keeps
matching the same row in the 48-52 h sliding window.

The ``stage`` column is a free-form String today (``day_2``) but the
column reserves space for ``day_before`` and ``morning_of`` cadences in
gap-10 Phase 2 without requiring an enum migration on a hot table.

Revision ID: 20260429_100000
Revises: 20260428_100000
Validates: scheduling gaps gap-10 Phase 1 (Day-2 No-Reply Reminder)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260429_100000"
down_revision: str | None = "20260428_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ``appointment_reminder_log`` table + indexes."""
    op.create_table(
        "appointment_reminder_log",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "appointment_id",
            sa.UUID(),
            sa.ForeignKey(
                "appointments.id",
                name="fk_appointment_reminder_log_appointment_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "sent_message_id",
            sa.UUID(),
            sa.ForeignKey(
                "sent_messages.id",
                name="fk_appointment_reminder_log_sent_message_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "cancelled_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_appointment_reminder_log_appointment_id",
        "appointment_reminder_log",
        ["appointment_id"],
    )
    # Composite index supports the dedup probe
    # ``WHERE appointment_id = ? AND stage = ?`` used by the
    # Day2ReminderJob's eligibility query.
    op.create_index(
        "idx_appointment_reminder_log_stage_appointment_id",
        "appointment_reminder_log",
        ["stage", "appointment_id"],
    )


def downgrade() -> None:
    """Drop the ``appointment_reminder_log`` table + indexes."""
    op.drop_index(
        "idx_appointment_reminder_log_stage_appointment_id",
        table_name="appointment_reminder_log",
    )
    op.drop_index(
        "ix_appointment_reminder_log_appointment_id",
        table_name="appointment_reminder_log",
    )
    op.drop_table("appointment_reminder_log")
