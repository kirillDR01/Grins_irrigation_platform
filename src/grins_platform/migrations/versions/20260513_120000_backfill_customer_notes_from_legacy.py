"""Backfill ``customers.internal_notes`` from legacy notes sources.

Cluster A — Notes/Photos/Tags Unification (Phase 1, T1.5).

The unification moves every "notes" surface onto a single shared blob on
the Customer record. This migration backfills the existing
``customers.internal_notes`` column with the body content from the five
legacy notes locations, preserving chronological order with explicit
date-stamped dividers so the merged blob is human-readable.

Sources merged (in chronological order per customer):

* ``sales_entry.notes``  (label: ``sales entry``)
* ``estimates.notes``    (label: ``estimate``)
* ``jobs.notes``         (label: ``job``)
* ``appointments.notes`` (label: ``appointment``)
* ``appointment_notes.body`` (label: ``appointment note``) — table is
  dropped in the next migration in this chain (T1.6), so this is our
  last chance to capture its content.

Idempotency: each appended section is preceded by the divider
``\\n\\n--- From <label> (<YYYY-MM-DD>) ---\\n``. Re-running the
migration is a no-op because the divider is checked via literal-string
match against the existing blob before appending.

Schema bump: the related ``customer.internal_notes`` Pydantic
``max_length`` is raised from 10000 to 50000 in this release (see
``schemas/customer.py``) to accept the merged content. Any customer
whose merged blob exceeds 50000 chars is truncated with a trailing
suffix ``\\n\\n[...truncated by backfill]`` so the column stays inside
the schema cap.

Downgrade: no-op — the merge is not deterministically reversible.

Revision ID: 20260513_120000
Revises: 20260511_120000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "20260513_120000"
down_revision: str | None = "20260511_120000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MAX_LEN = 50_000
_TRUNCATE_SUFFIX = "\n\n[...truncated by backfill]"


def _table_exists(conn: object, table_name: str) -> bool:
    """Return True if ``table_name`` exists in the current DB."""
    return bool(
        conn.execute(  # type: ignore[attr-defined]
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_name = :t"
                ")"
            ),
            {"t": table_name},
        ).scalar()
    )


def upgrade() -> None:
    """Merge legacy notes into each customer's internal_notes blob."""
    conn = op.get_bind()
    has_appt_notes = _table_exists(conn, "appointment_notes")

    customers = conn.execute(
        text("SELECT id, COALESCE(internal_notes, '') AS notes FROM customers"),
    ).all()

    sources_query_parts = [
        # sales_entry
        """
        SELECT id AS customer_id,
               'sales entry'::text AS label,
               notes AS body,
               created_at
        FROM sales_entries
        WHERE customer_id = :cid
          AND COALESCE(notes, '') <> ''
        """,
        # estimate via customer_id
        """
        SELECT :cid AS customer_id,
               'estimate'::text AS label,
               e.notes AS body,
               e.created_at
        FROM estimates e
        WHERE e.customer_id = :cid
          AND COALESCE(e.notes, '') <> ''
        """,
        # estimate via lead.customer_id (dedupe via UNION)
        """
        SELECT :cid AS customer_id,
               'estimate'::text AS label,
               e.notes AS body,
               e.created_at
        FROM estimates e
        JOIN leads l ON l.id = e.lead_id
        WHERE l.customer_id = :cid
          AND e.customer_id IS DISTINCT FROM :cid
          AND COALESCE(e.notes, '') <> ''
        """,
        # job
        """
        SELECT :cid AS customer_id,
               'job'::text AS label,
               notes AS body,
               created_at
        FROM jobs
        WHERE customer_id = :cid
          AND COALESCE(notes, '') <> ''
        """,
        # appointment via job.customer_id (appointment has no direct customer_id)
        """
        SELECT :cid AS customer_id,
               'appointment'::text AS label,
               a.notes AS body,
               a.created_at
        FROM appointments a
        JOIN jobs j ON j.id = a.job_id
        WHERE j.customer_id = :cid
          AND COALESCE(a.notes, '') <> ''
        """,
    ]

    if has_appt_notes:
        sources_query_parts.append(
            # appointment_notes via job.customer_id
            """
            SELECT :cid AS customer_id,
                   'appointment note'::text AS label,
                   an.body AS body,
                   an.updated_at AS created_at
            FROM appointment_notes an
            JOIN appointments a ON a.id = an.appointment_id
            JOIN jobs j ON j.id = a.job_id
            WHERE j.customer_id = :cid
              AND COALESCE(an.body, '') <> ''
            """,
        )

    sources_query = " UNION ALL ".join(sources_query_parts) + " ORDER BY created_at"

    n_customers = 0
    n_sources_merged = 0
    n_truncated = 0

    for cust_id, current_notes in customers:
        n_customers += 1
        merged = current_notes or ""
        rows = conn.execute(text(sources_query), {"cid": cust_id}).all()
        for _, label, body, created_at in rows:
            date_str = created_at.date().isoformat() if created_at else "unknown"
            divider = f"\n\n--- From {label} ({date_str}) ---\n"
            # Idempotency: skip if this exact divider already exists in the blob.
            if divider in merged:
                continue
            merged += divider + (body or "")
            n_sources_merged += 1

        if merged == (current_notes or ""):
            continue  # nothing new

        if len(merged) > _MAX_LEN:
            keep = _MAX_LEN - len(_TRUNCATE_SUFFIX)
            print(
                f"[backfill] customer {cust_id} truncated "
                f"from {len(merged)} to {_MAX_LEN}"
            )
            merged = merged[:keep] + _TRUNCATE_SUFFIX
            n_truncated += 1

        conn.execute(
            text("UPDATE customers SET internal_notes = :n WHERE id = :id"),
            {"n": merged, "id": cust_id},
        )

    print(
        f"[backfill] processed {n_customers} customers, "
        f"merged {n_sources_merged} source rows, "
        f"truncated {n_truncated}"
    )


def downgrade() -> None:
    """No-op: the merge is not deterministically reversible.

    The original ``customers.internal_notes`` content (pre-backfill) is
    not retained anywhere, so we cannot reconstruct it on downgrade.
    """
