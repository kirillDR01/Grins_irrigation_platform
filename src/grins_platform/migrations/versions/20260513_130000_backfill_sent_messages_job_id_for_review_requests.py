"""Backfill ``sent_messages.job_id`` for review-request rows.

Cluster G — Per-job review-request dedup (Phase B0).

Phase B switches the Google-review-request 30-day cooldown key from
``customer_id`` alone to ``(customer_id, job_id)``. Legacy
``sent_messages`` rows created before Phase B may have ``job_id = NULL``
because the prior ``request_google_review`` call site never passed
``job_id`` through to ``SMSService.send_message``. Without this
backfill, the new dedup query would not see those legacy rows and a
customer who received a review request the day before deploy could
receive another for the same job 5 minutes after deploy.

``appointments.job_id`` is ``NOT NULL`` (see ``models/appointment.py``),
so the join is total: every review-request row whose ``appointment_id``
is set has a deterministic ``job_id`` available.

Rows where ``appointment_id IS NULL`` (rare for review requests) are
left as-is. They fall through the dedup check as if no prior request
existed — same behavior as a brand-new customer. Acceptable per plan.

Downgrade is a no-op: re-NULLing the column would discard otherwise
correct data.

Revision ID: 20260513_130000
Revises: 20260513_120200
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "20260513_130000"
down_revision: str | None = "20260513_120200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Populate ``sent_messages.job_id`` from ``appointments.job_id``."""
    conn = op.get_bind()
    result = conn.execute(
        text(
            """
            UPDATE sent_messages sm
            SET job_id = a.job_id
            FROM appointments a
            WHERE sm.appointment_id = a.id
              AND sm.job_id IS NULL
              AND sm.message_type IN ('review_request', 'google_review_request')
            """,
        ),
    )
    print(
        f"[backfill] sent_messages.job_id populated for "
        f"{result.rowcount} review-request rows",
    )


def downgrade() -> None:
    """No-op: re-NULLing would discard correct data."""
