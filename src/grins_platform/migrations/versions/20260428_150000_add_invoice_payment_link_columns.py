"""Add Stripe Payment Link tracking columns to ``invoices``.

Adds five columns and a partial index in support of Architecture C
(Payment Links over SMS):

* ``stripe_payment_link_id`` — Stripe ``plink_*`` ID, nullable.
* ``stripe_payment_link_url`` — full URL of the hosted Stripe Checkout
  page, nullable.
* ``stripe_payment_link_active`` — whether the link is still chargeable
  on the Stripe side. Default ``true``.
* ``payment_link_sent_at`` — last time the link was delivered to the
  customer (SMS or email), nullable.
* ``payment_link_sent_count`` — number of successful sends across the
  invoice's lifetime, default ``0``.

A partial unique index on ``stripe_payment_link_id`` (``WHERE NOT NULL``)
supports webhook reconciliation lookups by link ID.

Revision ID: 20260428_150000
Revises: 20260428_140000
Validates: Stripe Payment Links plan §Phase 2.3.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_150000"
down_revision: str | None = "20260428_140000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEX_NAME = "ix_invoices_stripe_payment_link_id"


def upgrade() -> None:
    """Add Payment Link columns and supporting partial index."""
    op.add_column(
        "invoices",
        sa.Column("stripe_payment_link_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("stripe_payment_link_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "stripe_payment_link_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "payment_link_sent_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "payment_link_sent_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_index(
        _INDEX_NAME,
        "invoices",
        ["stripe_payment_link_id"],
        unique=True,
        postgresql_where="stripe_payment_link_id IS NOT NULL",
    )


def downgrade() -> None:
    """Drop the partial index and Payment Link columns."""
    op.drop_index(_INDEX_NAME, table_name="invoices")
    op.drop_column("invoices", "payment_link_sent_count")
    op.drop_column("invoices", "payment_link_sent_at")
    op.drop_column("invoices", "stripe_payment_link_active")
    op.drop_column("invoices", "stripe_payment_link_url")
    op.drop_column("invoices", "stripe_payment_link_id")
