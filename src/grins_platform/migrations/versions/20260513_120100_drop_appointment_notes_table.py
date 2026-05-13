"""Drop the ``appointment_notes`` table.

Cluster A — Notes/Photos/Tags Unification (Phase 1, T1.6).

The ``appointment_notes`` table (added 2026-04-25 in
``20260425_100000_add_appointment_notes_table.py``) was never wired
into the production UI; the appointment modal still writes through
``appointment.notes``. Cluster A consolidates every "notes" surface
onto ``customers.internal_notes`` — the per-appointment notes blob is
no longer needed.

The previous migration in this chain (``20260513_120000``) backfills
any non-empty body content from ``appointment_notes`` into
``customers.internal_notes``, so dropping the table at this point
loses only empty rows (or content already merged forward).

This migration emits a log line reporting the count of non-empty body
rows that are about to be discarded so an operator can audit the
backfill outcome.

Downgrade re-creates the empty table shell mirroring the original
``20260425_100000`` create; the row data is not reconstructable.

Revision ID: 20260513_120100
Revises: 20260513_120000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "20260513_120100"
down_revision: str | None = "20260513_120000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the appointment_notes table after logging discard count."""
    bind = op.get_bind()
    cnt = bind.execute(
        text(
            "SELECT count(*) FROM appointment_notes "
            "WHERE coalesce(body, '') <> ''"
        ),
    ).scalar()
    print(
        f"[drop_appointment_notes] discarding {cnt} non-empty body row(s); "
        "content was merged into customers.internal_notes by 20260513_120000"
    )
    op.drop_index(
        "idx_appointment_notes_appointment_id",
        table_name="appointment_notes",
    )
    op.drop_table("appointment_notes")


def downgrade() -> None:
    """Re-create the appointment_notes table shell.

    Mirrors the original CREATE from ``20260425_100000``. Row data
    from before the drop is not reconstructable — downgrade restores
    only the schema so dependent code can boot.
    """
    op.create_table(
        "appointment_notes",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "appointment_id",
            sa.UUID(),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_by_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_appointment_notes_appointment_id",
        "appointment_notes",
        ["appointment_id"],
        unique=True,
    )
