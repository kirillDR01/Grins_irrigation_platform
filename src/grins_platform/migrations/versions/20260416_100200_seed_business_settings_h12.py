"""Seed ``business_settings`` rows for H-12 firm-wide thresholds.

H-12 (bughunt 2026-04-16) stores four firm-wide knobs in the
existing ``business_settings`` table so admins can tune them from
``/settings`` without redeploying. Defaults:

- ``lien_days_past_due`` = 60
- ``lien_min_amount`` = 500
- ``upcoming_due_days`` = 7
- ``confirmation_no_reply_days`` = 3  (used by H-7 once it lands)

The ``business_settings`` table already exists (created in
``20260324_100100_crm_create_new_tables``). This migration only seeds
the new rows with ``ON CONFLICT DO NOTHING`` so it is idempotent and
safe to re-run.

The values are stored as ``{"value": <scalar>}`` to match the shape
the :class:`BusinessSettingService` reads/writes.

Revision ID: 20260416_100200
Revises: 20260416_100100
Requirements: bughunt 2026-04-16 finding H-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260416_100200"
down_revision: str | None = "20260416_100100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_KEYS: tuple[str, ...] = (
    "lien_days_past_due",
    "lien_min_amount",
    "upcoming_due_days",
    "confirmation_no_reply_days",
)


def upgrade() -> None:
    """Seed H-12 default rows into ``business_settings``.

    Uses a JSON object with a ``value`` field to match the service's
    wrapper shape. ``ON CONFLICT (setting_key) DO NOTHING`` keeps the
    migration idempotent and respects any existing row written by
    SettingsService / the admin UI.
    """
    op.execute(
        sa.text(
            """
            INSERT INTO business_settings (setting_key, setting_value) VALUES
                ('lien_days_past_due', '{"value": 60}'::jsonb),
                ('lien_min_amount', '{"value": 500}'::jsonb),
                ('upcoming_due_days', '{"value": 7}'::jsonb),
                ('confirmation_no_reply_days', '{"value": 3}'::jsonb)
            ON CONFLICT (setting_key) DO NOTHING;
            """,
        ),
    )


def downgrade() -> None:
    """Remove H-12 seed rows but leave the table intact.

    The table itself belongs to ``20260324_100100_crm_create_new_tables``.
    """
    keys_sql = ", ".join(f"'{k}'" for k in _KEYS)
    op.execute(
        sa.text(
            f"DELETE FROM business_settings WHERE setting_key IN ({keys_sql});",
        ),
    )
