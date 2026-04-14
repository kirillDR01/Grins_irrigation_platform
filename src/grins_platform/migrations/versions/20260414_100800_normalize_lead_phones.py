"""Backfill ``leads.phone`` to the canonical bare-10-digit format.

Addresses bughunt M-5: historical Lead rows hold phones in assorted
shapes (``(952) 737-3312``, ``952-737-3312``, ``952.737.3312``,
``+19527373312``). The consent lookup ``_phone_variants`` has been
widened (Sprint 6) to match every plausible form, but normalizing the
stored values keeps future lookups fast and lets downstream reporting
group per-phone cleanly.

The backfill is idempotent: rows already at a 10-digit bare format are
skipped. Rows that cannot be normalized to 10 digits (empty, too short,
too long) are left alone and reported in the log — those need manual
cleanup rather than a silent coercion that could scramble real data.

Revision ID: 20260414_100800
Revises: 20260414_100700
Requirements: bughunt M-5
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from alembic import op

revision: str = "20260414_100800"
down_revision: str | None = "20260414_100700"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_BARE_10 = re.compile(r"^\d{10}$")


def upgrade() -> None:
    """Normalize ``leads.phone`` values to bare 10-digit strings.

    Pure SQL: strip every non-digit, drop a leading ``1`` country-code
    prefix when the result is 11 digits, and write back only when the
    result is exactly 10 digits. Leaves otherwise-ambiguous values in
    place so the ops team can triage them.
    """
    connection = op.get_bind()
    # Pull the current state once; the row count here is small
    # (hundreds, not millions) so in-Python normalization is cheaper
    # than a multi-step SQL regex dance.
    rows = connection.execute(
        # ``text`` import deferred to keep the top of the module clean —
        # other migrations in this tree do the same.
        _text("SELECT id, phone FROM leads WHERE phone IS NOT NULL")
    ).fetchall()

    updated = 0
    skipped_already = 0
    skipped_bad = 0

    for row in rows:
        raw = row.phone
        if raw is None:
            continue
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if _BARE_10.match(digits):
            if digits == raw:
                skipped_already += 1
                continue
            connection.execute(
                _text("UPDATE leads SET phone = :p WHERE id = :id"),
                {"p": digits, "id": row.id},
            )
            updated += 1
        else:
            # Leave it; surface once so an operator can follow up.
            skipped_bad += 1

    # Alembic surfaces print() output on upgrade — useful for the
    # deploy log without pulling in full structured logging here.
    print(
        f"normalize_lead_phones: updated={updated} "
        f"already_normalized={skipped_already} unparseable={skipped_bad}"
    )


def downgrade() -> None:
    """Backfill is lossy (original punctuation isn't preserved) so
    the downgrade is an intentional no-op. Restore from backup if a
    regression is detected.
    """


def _text(sql: str):  # type: ignore[no-untyped-def]
    """Deferred ``sqlalchemy.text`` import so the top of the migration
    file stays light and matches the surrounding style."""
    from sqlalchemy import text

    return text(sql)
