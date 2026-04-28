"""Replace ``ix_customers_stripe_customer_id`` with a partial unique index.

Postgres unique indexes already permit multiple NULLs, so the prior full
index ``ix_customers_stripe_customer_id`` (created in
``20250702_100800_add_customer_agreement_fields``) is functionally
equivalent to a partial unique index on ``stripe_customer_id IS NOT NULL``.
Switching to the partial form keeps the same uniqueness guarantee while
trimming space and ``ANALYZE`` cost on the (still many) un-linked rows.

This migration is a straight swap: drop the old index, create the partial
one in its place. Downgrade reverses cleanly.

Revision ID: 20260428_140000
Revises: 20260501_120000
Validates: Stripe Payment Links plan §Phase 1.1 — Customer linkage hardening.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260428_140000"
down_revision: str | None = "20260501_120000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD_INDEX = "ix_customers_stripe_customer_id"
_NEW_INDEX = "ix_customers_stripe_customer_id_active"


def upgrade() -> None:
    """Swap the full unique index for a partial one."""
    op.drop_index(_OLD_INDEX, table_name="customers")
    op.create_index(
        _NEW_INDEX,
        "customers",
        ["stripe_customer_id"],
        unique=True,
        postgresql_where="stripe_customer_id IS NOT NULL",
    )


def downgrade() -> None:
    """Restore the original full unique index."""
    op.drop_index(_NEW_INDEX, table_name="customers")
    op.create_index(
        _OLD_INDEX,
        "customers",
        ["stripe_customer_id"],
        unique=True,
    )
