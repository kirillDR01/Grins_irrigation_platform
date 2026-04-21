"""Add sent_messages.superseded_at column and supporting partial index.

Gap 03.B: once a new confirmation-like SMS is sent for an appointment,
prior sent_messages rows of type APPOINTMENT_CONFIRMATION /
APPOINTMENT_RESCHEDULE / APPOINTMENT_CANCELLATION / APPOINTMENT_REMINDER
are stamped with ``superseded_at = NOW()`` so ``find_confirmation_message``
no longer routes a stale-thread reply to an appointment whose state has
moved on.

Revision ID: 20260421_100100
Revises: 20260421_100000
Requirements: gap-03 (thread correlation)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_100100"
down_revision: str | None = "20260421_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``superseded_at`` column + partial index on active confirmation-like rows."""
    op.add_column(
        "sent_messages",
        sa.Column(
            "superseded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_sent_messages_active_confirmation_by_appointment",
        "sent_messages",
        ["appointment_id", "message_type"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )


def downgrade() -> None:
    """Drop the partial index then the column."""
    op.drop_index(
        "ix_sent_messages_active_confirmation_by_appointment",
        table_name="sent_messages",
    )
    op.drop_column("sent_messages", "superseded_at")
