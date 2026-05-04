"""Repair invoices.line_items rows missing strict-shape fields.

Bug B-1 (2026-05-04 sign-off): collect_payment wrote
``{description, amount}`` items, but ``InvoiceLineItem`` schema requires
``{description, quantity, unit_price, total}``. Existing dev rows are
un-serializable. Rewrite each item missing 'quantity' into the strict
shape using ``amount`` (or invoice ``total_amount`` as last resort) for
``unit_price`` and ``total``, ``"1"`` for ``quantity``.

Idempotent: rows whose first item already has 'quantity' are untouched.
Downgrade is a no-op (data fixup only; no column changes).

Revision ID: 20260506_120000
Revises: 20260505_130000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260506_120000"
down_revision: Union[str, None] = "20260505_130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            """
            WITH bad AS (
                SELECT id, line_items, total_amount
                FROM invoices
                WHERE line_items IS NOT NULL
                  AND jsonb_typeof(line_items) = 'array'
                  AND jsonb_array_length(line_items) > 0
                  AND NOT (line_items->0 ? 'quantity')
            ),
            fixed AS (
                SELECT
                    bad.id,
                    jsonb_agg(
                        CASE
                            WHEN item ? 'quantity'
                                THEN item
                            ELSE jsonb_build_object(
                                'description', COALESCE(item->>'description', 'Service'),
                                'quantity',    '1',
                                'unit_price',  COALESCE(item->>'amount', bad.total_amount::text),
                                'total',       COALESCE(item->>'amount', bad.total_amount::text)
                            )
                        END
                        ORDER BY ord
                    ) AS fixed_items
                FROM bad,
                     LATERAL jsonb_array_elements(bad.line_items)
                         WITH ORDINALITY AS t(item, ord)
                GROUP BY bad.id
            )
            UPDATE invoices i
            SET line_items = fixed.fixed_items
            FROM fixed
            WHERE i.id = fixed.id
            """
        )
    )


def downgrade() -> None:
    # No-op: this is a one-shot data fixup. Reverting would re-break
    # historical rows; if needed, run a manual SQL UPDATE.
    pass
