"""Widen ``job_confirmation_responses.status`` to VARCHAR(50).

The existing column is ``String(30)``, but the service writes the
status value ``'reschedule_alternatives_received'`` (35 chars) when a
customer sends a free-text follow-up to an R reply. PostgreSQL rejects
the UPDATE with ``StringDataRightTruncationError: value too long for
type character varying(30)``; the surrounding transaction rolls back,
which silently drops the customer's reply (nothing is persisted —
neither the JobConfirmationResponse row nor the appended
``requested_alternatives`` entry on the RescheduleRequest).

Unit tests don't catch this because they stub the session with
MagicMocks and never hit Postgres. The E2E walkthrough on 2026-04-14
surfaced it on the first real inbound non-Y/R/C reply in the
reschedule flow.

This migration only widens the column. The existing data fits, so no
backfill or conversion is needed. The column remains ``nullable=False``
with the same default ("pending").

Revision ID: 20260414_100900
Revises: 20260414_100800
Requirements: bughunt E2E finding (2026-04-14)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260414_100900"
down_revision: str | None = "20260414_100800"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Widen status column from VARCHAR(30) to VARCHAR(50)."""
    op.alter_column(
        "job_confirmation_responses",
        "status",
        existing_type=sa.String(length=30),
        type_=sa.String(length=50),
        existing_nullable=False,
        existing_server_default=sa.text("'pending'"),
    )


def downgrade() -> None:
    """Narrow back to VARCHAR(30) — will fail if any row has a value
    longer than 30 chars. That's intentional: downgrade is unsafe once
    ``'reschedule_alternatives_received'`` has been written."""
    op.alter_column(
        "job_confirmation_responses",
        "status",
        existing_type=sa.String(length=50),
        type_=sa.String(length=30),
        existing_nullable=False,
        existing_server_default=sa.text("'pending'"),
    )
