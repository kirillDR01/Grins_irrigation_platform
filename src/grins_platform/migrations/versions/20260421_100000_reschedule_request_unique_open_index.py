"""Partial unique index on reschedule_requests.appointment_id WHERE status='open'.

Safety net behind the application-level idempotency guard added to
``JobConfirmationService._handle_reschedule`` for Gap 1.A. At most one
``status='open'`` row per appointment; resolved / cancelled / superseded
rows are free to coexist.

Revision ID: 20260421_100000
Revises: 20260418_100700
Requirements: gap-01 (reschedule request lifecycle)

NOTE — pre-migration dedup (dev/staging/prod):
If any environment already has duplicate ``status='open'`` rows for the
same ``appointment_id``, this migration will fail on index creation.
Run the following SQL manually *before* ``alembic upgrade head``:

    WITH ranked AS (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY appointment_id
                   ORDER BY created_at ASC
               ) AS rn
        FROM reschedule_requests
        WHERE status = 'open'
    )
    UPDATE reschedule_requests
    SET status = 'superseded', resolved_at = NOW()
    WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

TODO: verify + run this dedup step on dev/staging DBs prior to deploy.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_100000"
down_revision: str | None = "20260418_100700"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the partial unique index on open reschedule requests."""
    op.create_index(
        "uq_reschedule_requests_open_per_appointment",
        "reschedule_requests",
        ["appointment_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    """Drop the partial unique index."""
    op.drop_index(
        "uq_reschedule_requests_open_per_appointment",
        table_name="reschedule_requests",
    )
