"""Add ``needs_review_reason`` column to ``appointments`` table.

The bughunt 2026-04-16 H-7 finding introduces a nightly cron that flags
SCHEDULED appointments whose confirmation SMS has been silent for N
days (default 3). Each flagged row is marked with a short review-reason
token ("no_confirmation_response") so the ``/schedule`` queue can
surface the stale appointment for admin triage.

This migration also seeds a ``business_settings`` row for
``confirmation_no_reply_days`` so H-12's admin UI can tune the default
without redeploying. If the ``business_settings`` table does not yet
exist, the seed is skipped (H-12 migration creates it).

Revision ID: 20260416_100200
Revises: 20260416_100100
Requirements: bughunt 2026-04-16 finding H-7
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260416_100200"
down_revision: str | None = "20260416_100100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``needs_review_reason`` column + index and seed the setting."""
    op.add_column(
        "appointments",
        sa.Column(
            "needs_review_reason",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_appointments_needs_review_reason",
        "appointments",
        ["needs_review_reason"],
    )

    # Seed for ``confirmation_no_reply_days`` is owned by the H-12
    # migration (``20260416_100300_seed_business_settings_h12``) which
    # uses the canonical ``{"value": N}`` shape. H-7's cron reads either
    # ``{"value": N}`` or ``{"days": N}`` for backwards compatibility.


def downgrade() -> None:
    """Remove the column + index. The confirmation_no_reply_days seed
    is owned by the H-12 migration; we do not touch it here."""
    op.drop_index(
        "ix_appointments_needs_review_reason",
        table_name="appointments",
    )
    op.drop_column("appointments", "needs_review_reason")
