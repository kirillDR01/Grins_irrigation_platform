"""Clear promotion_code on scheduled estimate follow-ups.

Drops the auto-attached SAVE10 code from any ``estimate_follow_ups`` row
that hasn't fired yet, so already-queued Day 14 / Day 21 nudges for
in-flight estimates do not text customers a discount offer after the
deploy that removes auto-discount logic. Already-sent rows keep their
historical ``promotion_code`` value for analytics integrity.

Pairs with the code change in ``EstimateService._schedule_follow_ups``
(no longer auto-attaches a code) and ``process_follow_ups`` (no longer
appends ``Use code X for a discount!`` to the SMS body).

Revision ID: 20260511_120000
Revises: 20260512_120000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260511_120000"
down_revision: Union[str, None] = "20260512_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE estimate_follow_ups "
        "SET promotion_code = NULL "
        "WHERE status = 'scheduled' AND promotion_code IS NOT NULL"
    )


def downgrade() -> None:
    # Data-only migration — original values are not reconstructable,
    # and the explicit policy is that discount nudges should never have
    # been auto-queued. Downgrade is intentionally a no-op.
    pass
