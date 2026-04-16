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

    # Seed the BusinessSetting row so H-12's admin UI can tune the
    # no-reply threshold without a redeploy. The business_settings
    # table is created by migration 20260324_100100; if for some
    # reason it is missing here we skip the seed silently — the H-7
    # job hardcodes DEFAULT_NO_REPLY_DAYS = 3 as a fallback.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "business_settings" in inspector.get_table_names():
        bind.execute(
            sa.text(
                """
                INSERT INTO business_settings (setting_key, setting_value)
                VALUES (
                    'confirmation_no_reply_days',
                    :payload
                )
                ON CONFLICT (setting_key) DO NOTHING
                """
            ),
            {"payload": '{"days": 3}'},
        )


def downgrade() -> None:
    """Remove the column + index + seeded setting row."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "business_settings" in inspector.get_table_names():
        bind.execute(
            sa.text(
                "DELETE FROM business_settings WHERE setting_key = "
                "'confirmation_no_reply_days'"
            )
        )

    op.drop_index(
        "ix_appointments_needs_review_reason",
        table_name="appointments",
    )
    op.drop_column("appointments", "needs_review_reason")
