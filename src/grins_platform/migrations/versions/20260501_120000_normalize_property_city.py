"""One-shot data hygiene pass on ``properties.city``.

Multiple intake paths historically wrote raw addresses, mixed-case values,
and ``State + ZIP`` tails into ``properties.city``. The Pick-Jobs page's
City facet rail surfaced this dirt directly. This migration:

1. Trims and collapses whitespace.
2. Strips a trailing ``, ST 12345[-1234]`` token.
3. Title-cases the remainder.
4. For rows where ``city`` still looks address-shaped (digit prefix,
   contains a state+ZIP, or ends in a recognised street-suffix like ``St``,
   ``Ave``, ``Dr``, ``Lane``, ``Rd``, ``Blvd``, etc.), copies the value
   into ``properties.address`` (only if address is empty) and sets
   ``city = 'Unknown'``.

Idempotent — running twice on the same dataset is a no-op after step 1.
The ``downgrade`` cannot recover the original messy data so it raises
``NotImplementedError`` (matches project precedent for data-only
migrations, e.g. seed_day_2_reminder_settings).

Revision ID: 20260501_120000
Revises: 20260430_120000
Validates: Pick-Jobs page City facet hygiene
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "20260501_120000"
down_revision: str | None = "20260430_120000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Postgres regex matches a trailing ", ST 12345[-1234]" token. ``regexp_replace``
# returns the input unchanged if no match — making the statement idempotent.
_STATE_ZIP_TAIL_RE = r",\s*[A-Z]{2}\s+\d{5}(-\d{4})?\s*$"

# Recognises a city candidate as address-shaped. The street-suffix word
# must appear at the end of the string (so legitimate "St. Paul" survives —
# the ``St.`` ends with a period and is therefore not at the end).
_STREET_SUFFIX_TAIL_RE = (
    r"\s(St|Ave|Avenue|Dr|Drive|Ln|Lane|Rd|Road|Blvd|Ct|Court|Way|Ter|"
    r"Pl|Place|Pkwy|Cir|Circle|Trl|Trail)$"
)


def upgrade() -> None:
    """Normalize ``properties.city`` and quarantine address-shaped rows."""
    bind = op.get_bind()

    # Step 1+2+3: trim, strip state+ZIP tail, collapse whitespace, title-case.
    cleanup_result = bind.execute(
        text(
            """
            UPDATE properties
            SET city = INITCAP(
                regexp_replace(
                    regexp_replace(BTRIM(city), :state_zip_tail_re, '', 'g'),
                    '\\s+',
                    ' ',
                    'g'
                )
            )
            WHERE city IS NOT NULL
              AND (
                  city <> BTRIM(city)
                  OR city ~ '\\s\\s+'
                  OR city ~* :state_zip_tail_re
                  OR city <> INITCAP(city)
              )
            """,
        ),
        {"state_zip_tail_re": _STATE_ZIP_TAIL_RE},
    )
    cleanup_count = cleanup_result.rowcount or 0

    # Step 4: quarantine rows whose city still looks address-shaped. Move the
    # bad value into ``address`` only if the existing address is empty so we
    # don't clobber a legitimate street line.
    quarantine_result = bind.execute(
        text(
            """
            WITH bad AS (
                SELECT id, city
                FROM properties
                WHERE city IS NOT NULL
                  AND (
                      city ~ '^\\d'
                      OR city ~* '\\m[A-Z]{2}\\s+\\d{5}\\M'
                      OR city ~* :street_suffix_tail_re
                  )
            )
            UPDATE properties p
            SET
                address = CASE
                    WHEN p.address IS NULL OR BTRIM(p.address) = ''
                    THEN bad.city
                    ELSE p.address
                END,
                city = 'Unknown'
            FROM bad
            WHERE p.id = bad.id
            """,
        ),
        {"street_suffix_tail_re": _STREET_SUFFIX_TAIL_RE},
    )
    quarantine_count = quarantine_result.rowcount or 0

    # Surface counts in the migration log for ops review.
    op.execute(
        text(
            f"-- property city hygiene: cleaned={cleanup_count} "
            f"quarantined={quarantine_count}",
        ),
    )


def downgrade() -> None:
    """Cannot reconstruct pre-normalization values from the cleaned data."""
    msg = (
        "Downgrade not supported: original messy city values were "
        "overwritten and cannot be reconstructed."
    )
    raise NotImplementedError(msg)
