"""Migrate ``appointment_attachments`` rows into ``customer_photos``.

Cluster A — Notes/Photos/Tags Unification (Phase 1, T1.7).

``appointment_attachments`` is a polymorphic table (added 2026-04-16 in
``20260416_100600_create_appointment_attachments_table.py``) that
stores file uploads attached to job or estimate appointments. It has
no FK on ``appointment_id`` and tracks the surface via
``appointment_type`` (``"job"`` / ``"estimate"``).

Cluster A consolidates all photo silos onto ``customer_photos``, which
already has a ``customer_photos.appointment_id`` FK (added in the
photo-model itself). This migration:

1. Copies every ``appointment_attachments`` row into ``customer_photos``
   with ``customer_id`` resolved via ``appointments.job_id ->
   jobs.customer_id``. The ``appointment_id`` FK on the destination
   keeps the per-appointment association.
2. Emits a log line listing orphan IDs whose customer chain is broken
   (no appointment exists, or the appointment's job has no customer).
3. Drops the ``appointment_attachments`` table.

Note: ``appointments`` has no direct ``customer_id`` column — the only
path is ``appointments.job_id -> jobs.customer_id``.

Downgrade re-creates the empty ``appointment_attachments`` shell
mirroring the original CREATE; row data is not reconstructable.

Revision ID: 20260513_120200
Revises: 20260513_120100
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "20260513_120200"
down_revision: str | None = "20260513_120100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Copy appointment_attachments → customer_photos, then drop."""
    bind = op.get_bind()

    # 1. Log orphans so operators can recover them if needed.
    orphans = bind.execute(
        text(
            """
            SELECT aa.id, aa.file_key, aa.appointment_id, aa.appointment_type
            FROM appointment_attachments aa
            LEFT JOIN appointments a ON a.id = aa.appointment_id
            LEFT JOIN jobs j ON j.id = a.job_id
            WHERE j.customer_id IS NULL
            """,
        ),
    ).all()
    for row in orphans:
        print(
            f"[migrate_attachments] ORPHAN attachment "
            f"id={row.id} appointment_id={row.appointment_id} "
            f"appointment_type={row.appointment_type} "
            f"file_key={row.file_key}",
        )
    if orphans:
        print(
            f"[migrate_attachments] {len(orphans)} orphan(s) NOT migrated; "
            "see file_key values above to recover from S3 if needed.",
        )

    # 2. Copy rows we can resolve to a customer.
    result = bind.execute(
        text(
            """
            INSERT INTO customer_photos (
                id,
                customer_id,
                appointment_id,
                file_key,
                file_name,
                file_size,
                content_type,
                uploaded_by,
                created_at
            )
            SELECT
                gen_random_uuid(),
                j.customer_id,
                aa.appointment_id,
                aa.file_key,
                aa.file_name,
                aa.file_size,
                aa.content_type,
                aa.uploaded_by,
                aa.created_at
            FROM appointment_attachments aa
            JOIN appointments a ON a.id = aa.appointment_id
            JOIN jobs j ON j.id = a.job_id
            WHERE j.customer_id IS NOT NULL
            """,
        ),
    )
    print(f"[migrate_attachments] copied {result.rowcount} row(s)")

    # 3. Drop the source table.
    op.drop_index(
        "idx_appointment_attachments_appointment",
        table_name="appointment_attachments",
    )
    op.drop_table("appointment_attachments")
    print("[migrate_attachments] appointment_attachments table dropped")


def downgrade() -> None:
    """Re-create the empty appointment_attachments shell.

    Mirrors the original CREATE from ``20260416_100600``. Row data
    from before the drop is not reconstructable — downgrade restores
    only the schema so dependent code can boot.
    """
    op.create_table(
        "appointment_attachments",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("appointment_id", sa.UUID(), nullable=False),
        sa.Column("appointment_type", sa.String(20), nullable=False),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column(
            "uploaded_by",
            sa.UUID(),
            sa.ForeignKey("staff.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_appointment_attachments_appointment",
        "appointment_attachments",
        ["appointment_type", "appointment_id"],
    )
