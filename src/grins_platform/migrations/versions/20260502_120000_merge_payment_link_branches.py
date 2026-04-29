"""Merge two heads created during the payment-link work.

The Phase 2 column migration ``20260428_150000_add_invoice_payment_link_columns``
and the Phase 6 follow-up ``20260502_100000_widen_sent_messages_for_payment_link``
both descend from ``20260501_120000`` and were each tagged as a head. That
causes ``alembic upgrade head`` to fail on Railway with "Multiple head
revisions are present", which crashed the dev backend after commit 4796376.
This is a no-op merge that collapses both heads into a single head so the
deploy succeeds.

Revision ID: 20260502_120000
Revises: 20260428_150000, 20260502_100000
"""

from collections.abc import Sequence
from typing import Union


revision: str = "20260502_120000"
down_revision: Union[str, Sequence[str], None] = ("20260428_150000", "20260502_100000")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
