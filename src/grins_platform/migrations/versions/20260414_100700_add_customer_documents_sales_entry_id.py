"""Add ``sales_entry_id`` FK to ``customer_documents`` for per-pipeline scoping.

Addresses bughunt H-7: customers with more than one active Sales entry
were having ``_get_signing_document`` return the newest estimate/contract
across *all* of their entries, so the second entry's signing buttons
opened the first entry's doc. Per-entry scoping lets callers target the
right document.

Rows whose customer has exactly one ``sales_entries`` row are backfilled
deterministically. Multi-entry customers stay NULL and the signing
lookup falls back to the legacy customer-scoped behaviour with a log
warning (see ``api/v1/sales_pipeline.py::_get_signing_document``).

Revision ID: 20260414_100700
Revises: 20260414_100600
Requirements: H-7 / bughunt 2026-04-14
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260414_100700"
down_revision: Union[str, None] = "20260414_100600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_documents",
        sa.Column(
            "sales_entry_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_customer_documents_sales_entry_id",
        "customer_documents",
        "sales_entries",
        ["sales_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_customer_documents_sales_entry_id",
        "customer_documents",
        ["sales_entry_id"],
    )

    # Partial backfill: single-entry customers get their estimate/contract
    # documents auto-linked to that one entry. Multi-entry customers stay
    # NULL (ambiguous) and the signing lookup falls back to the newest
    # doc with a warning log.
    op.execute(
        """
        UPDATE customer_documents cd
        SET sales_entry_id = se.id
        FROM sales_entries se
        WHERE se.customer_id = cd.customer_id
          AND cd.document_type IN ('estimate', 'contract', 'signed_contract')
          AND (
              SELECT COUNT(*)
              FROM sales_entries s2
              WHERE s2.customer_id = cd.customer_id
          ) = 1
        """,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_documents_sales_entry_id",
        table_name="customer_documents",
    )
    op.drop_constraint(
        "fk_customer_documents_sales_entry_id",
        "customer_documents",
        type_="foreignkey",
    )
    op.drop_column("customer_documents", "sales_entry_id")
