"""Fold ``notes`` table rows into ``customers.internal_notes`` and ``leads.notes``, then drop the table.

This is a one-way data migration. The ``notes`` table introduced in
``20260416_100500`` is folded into the existing single-blob columns:

- ``subject_type='customer'`` rows → ``customers.internal_notes``
- ``subject_type='lead'`` rows → ``leads.notes``
- ``subject_type IN ('sales_entry','appointment')`` rows → logged and discarded

The ``downgrade()`` recreates the empty table shell but cannot reconstruct
the original rows. This is intentional — the fold is a one-way operation.

IMPORTANT: Before applying in dev, run an inspection query to count
``notes`` rows per ``subject_type``. If any sales_entry / appointment
counts are non-trivial, raise a flag and wait for product direction
before running the drop:

    SELECT subject_type, count(*) FROM notes GROUP BY subject_type;

Revision ID: 20260418_100700
Revises: 20260416_100600
Requirements: internal-notes-simplification Requirement 8
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "20260418_100700"
down_revision: str | None = "20260416_100600"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Fold notes rows into blob columns and drop the notes table."""
    conn = op.get_bind()

    # Check if the notes table exists before attempting to fold.
    # This makes the migration safe to run even if the table was already dropped.
    table_exists = conn.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_name = 'notes'"
            ")"
        )
    ).scalar()

    if not table_exists:
        print("[fold] notes table does not exist — nothing to fold.")
        return

    # 1. Fold customer notes: aggregate all notes bodies ordered by created_at,
    #    separated by \n\n, and append to existing internal_notes (with separator
    #    if non-empty).
    conn.execute(
        text("""
            UPDATE customers c
            SET internal_notes =
                CASE
                    WHEN COALESCE(TRIM(c.internal_notes), '') = ''
                        THEN folded.body
                    ELSE c.internal_notes || E'\\n\\n' || folded.body
                END
            FROM (
                SELECT subject_id,
                       string_agg(body, E'\\n\\n' ORDER BY created_at) AS body
                FROM notes
                WHERE subject_type = 'customer'
                  AND is_deleted = false
                GROUP BY subject_id
            ) folded
            WHERE c.id = folded.subject_id
        """)
    )
    print("[fold] customer notes folded into customers.internal_notes.")

    # 2. Fold lead notes: same pattern into leads.notes.
    conn.execute(
        text("""
            UPDATE leads l
            SET notes =
                CASE
                    WHEN COALESCE(TRIM(l.notes), '') = ''
                        THEN folded.body
                    ELSE l.notes || E'\\n\\n' || folded.body
                END
            FROM (
                SELECT subject_id,
                       string_agg(body, E'\\n\\n' ORDER BY created_at) AS body
                FROM notes
                WHERE subject_type = 'lead'
                  AND is_deleted = false
                GROUP BY subject_id
            ) folded
            WHERE l.id = folded.subject_id
        """)
    )
    print("[fold] lead notes folded into leads.notes.")

    # 3. Print-then-discard for sales_entry / appointment subject types.
    #    Emit count + first-10 body preview to migration output.
    rows = conn.execute(
        text("""
            SELECT subject_type,
                   count(*) AS cnt,
                   string_agg(
                       substring(body FROM 1 FOR 80),
                       ' | '
                       ORDER BY created_at
                   ) AS preview
            FROM notes
            WHERE subject_type IN ('sales_entry', 'appointment')
              AND is_deleted = false
            GROUP BY subject_type
        """)
    ).all()

    for subject_type, cnt, preview in rows:
        # Truncate preview to first 10 entries worth
        truncated = (preview or "")[:800]
        print(
            f"[fold] discarding {cnt} {subject_type} note(s); "
            f"sample: {truncated}"
        )

    if not rows:
        print("[fold] no sales_entry/appointment notes to discard.")

    # 4. Drop the notes table.
    op.drop_table("notes")
    print("[fold] notes table dropped.")


def downgrade() -> None:
    """Recreate the empty notes table shell.

    WARNING: This is a one-way fold. The original note rows cannot be
    reconstructed from the folded blob columns. This downgrade only
    recreates the table structure so that dependent code can function,
    but the data is gone.
    """
    op.create_table(
        "notes",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("subject_type", sa.String(20), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column(
            "author_id",
            sa.UUID(),
            sa.ForeignKey("staff.id"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "origin_lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id"),
            nullable=True,
        ),
        sa.Column(
            "origin_appointment_id",
            sa.UUID(),
            sa.ForeignKey("appointments.id"),
            nullable=True,
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Recreate indexes
    op.create_index(
        "idx_notes_subject",
        "notes",
        ["subject_type", "subject_id"],
    )
    op.create_index(
        "idx_notes_origin_lead",
        "notes",
        ["origin_lead_id"],
    )
    op.create_index(
        "idx_notes_created_at",
        "notes",
        ["created_at"],
    )
