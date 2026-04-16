"""Widen ``invoices.payment_method`` CHECK constraint with spec methods.

The existing ``ck_invoices_payment_method`` constraint only allows
``cash/check/venmo/zelle/stripe``. The H-4 bughunt fix (2026-04-16)
extends the :class:`~grins_platform.models.enums.PaymentMethod` enum with
``credit_card``, ``ach``, and ``other`` to match the spec vocabulary. The
DB-level check constraint must be widened to match or inserts of the new
values will raise ``IntegrityError``.

Per user decision (2026-04-16) no data migration is performed: existing
rows carrying ``stripe`` keep that value. ``stripe`` remains a valid
member of the enum and an allowed value in the constraint; the frontend
simply omits it from new-input pickers.

Revision ID: 20260416_100000
Revises: 20260414_100900
Requirements: bughunt 2026-04-16 finding H-4
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260416_100000"
down_revision: str | None = "20260414_100900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace payment_method CHECK with the widened 8-value set."""
    op.drop_constraint(
        "ck_invoices_payment_method",
        "invoices",
        type_="check",
    )
    op.create_check_constraint(
        "ck_invoices_payment_method",
        "invoices",
        "payment_method IS NULL OR payment_method IN "
        "('cash', 'check', 'venmo', 'zelle', 'stripe', "
        "'credit_card', 'ach', 'other')",
    )


def downgrade() -> None:
    """Narrow the CHECK back to the original 5-value set.

    Will fail if any row has ``payment_method`` set to one of the new
    values (``credit_card``, ``ach``, ``other``). That is intentional —
    downgrade is unsafe once the widened values have been written.
    """
    op.drop_constraint(
        "ck_invoices_payment_method",
        "invoices",
        type_="check",
    )
    op.create_check_constraint(
        "ck_invoices_payment_method",
        "invoices",
        "payment_method IS NULL OR payment_method IN "
        "('cash', 'check', 'venmo', 'zelle', 'stripe')",
    )
