"""Extend ``service_offerings`` for the admin pricelist editor.

Adds eight nullable columns plus two indexes that support the
appointment-modal umbrella plan Phase 1 (data model). The change is
strictly additive — existing rows are unaffected and existing API
consumers see no contract changes.

New columns
-----------
* ``slug`` — TEXT, partial unique index ``WHERE slug IS NOT NULL``.
* ``display_name`` — admin-editable label distinct from ``name``.
* ``customer_type`` — ``residential`` / ``commercial``.
* ``subcategory`` — finer grouping under ``category``.
* ``pricing_rule`` — JSONB rule body keyed by ``pricing_model``.
* ``replaced_by_id`` — self-FK seam for the future Stripe-style
  archive+create pattern (Phase 1.5).
* ``includes_materials`` — bool default false.
* ``source_text`` — original PDF source line for traceability.

Indexes
-------
* Partial unique index ``ix_service_offerings_slug_unique`` — enforces
  slug uniqueness only on rows that have a slug populated.
* ``ix_service_offerings_customer_type`` — supports filter queries.

Revision ID: 20260504_120000
Revises: 20260504_100000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID as PGUUID,
)

revision: str = "20260504_120000"
down_revision: str | None = "20260504_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_FK_NAME = "fk_service_offerings_replaced_by"
_SLUG_INDEX = "ix_service_offerings_slug_unique"
_CTYPE_INDEX = "ix_service_offerings_customer_type"


def upgrade() -> None:
    """Add pricelist columns + supporting indexes."""
    op.add_column(
        "service_offerings",
        sa.Column("slug", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("display_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("customer_type", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("subcategory", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("pricing_rule", JSONB, nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("replaced_by_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        _FK_NAME,
        source_table="service_offerings",
        referent_table="service_offerings",
        local_cols=["replaced_by_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "service_offerings",
        sa.Column(
            "includes_materials",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "service_offerings",
        sa.Column("source_text", sa.Text(), nullable=True),
    )
    op.create_index(
        _SLUG_INDEX,
        "service_offerings",
        ["slug"],
        unique=True,
        postgresql_where="slug IS NOT NULL",
    )
    op.create_index(
        _CTYPE_INDEX,
        "service_offerings",
        ["customer_type"],
    )


def downgrade() -> None:
    """Drop pricelist columns + supporting indexes."""
    op.drop_index(_CTYPE_INDEX, table_name="service_offerings")
    op.drop_index(_SLUG_INDEX, table_name="service_offerings")
    op.drop_column("service_offerings", "source_text")
    op.drop_column("service_offerings", "includes_materials")
    op.drop_constraint(
        _FK_NAME,
        "service_offerings",
        type_="foreignkey",
    )
    op.drop_column("service_offerings", "replaced_by_id")
    op.drop_column("service_offerings", "pricing_rule")
    op.drop_column("service_offerings", "subcategory")
    op.drop_column("service_offerings", "customer_type")
    op.drop_column("service_offerings", "display_name")
    op.drop_column("service_offerings", "slug")
