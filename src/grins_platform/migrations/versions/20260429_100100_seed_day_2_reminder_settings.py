"""Seed ``business_settings`` rows for the Day-2 No-Reply Reminder.

Gap-10 Phase 1 introduces a nightly Day-2 reminder. Two firm-wide
knobs control it:

- ``confirmation_day_2_reminder_enabled`` (bool, default ``false``) —
  feature flag so prod opt-in is deliberate. The job's hourly tick
  no-ops when this is unset / false.
- ``confirmation_day_2_reminder_offset_hours`` (int, default ``48``) —
  hours after the original ``APPOINTMENT_CONFIRMATION`` send before the
  reminder is eligible to fire.

Seeded with ``ON CONFLICT DO NOTHING`` so the migration is idempotent
and respects any value already written by an admin via the settings
UI before this migration ran (defensive: not expected on first deploy).

Revision ID: 20260429_100100
Revises: 20260429_100000
Validates: scheduling gaps gap-10 Phase 1 (Day-2 No-Reply Reminder)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260429_100100"
down_revision: str | None = "20260429_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_KEYS: tuple[str, ...] = (
    "confirmation_day_2_reminder_enabled",
    "confirmation_day_2_reminder_offset_hours",
)


def upgrade() -> None:
    """Seed gap-10 default rows into ``business_settings``.

    The values follow the ``{"value": <scalar>}`` shape that
    :class:`BusinessSettingService` reads / writes.
    ``ON CONFLICT (setting_key) DO NOTHING`` keeps the migration safe
    to re-run.
    """
    op.execute(
        sa.text(
            """
            INSERT INTO business_settings (setting_key, setting_value) VALUES
                ('confirmation_day_2_reminder_enabled', '{"value": false}'::jsonb),
                ('confirmation_day_2_reminder_offset_hours', '{"value": 48}'::jsonb)
            ON CONFLICT (setting_key) DO NOTHING;
            """,
        ),
    )


def downgrade() -> None:
    """Remove gap-10 seed rows but leave the table intact."""
    keys_sql = ", ".join(f"'{k}'" for k in _KEYS)
    op.execute(
        sa.text(
            f"DELETE FROM business_settings WHERE setting_key IN ({keys_sql});",
        ),
    )
