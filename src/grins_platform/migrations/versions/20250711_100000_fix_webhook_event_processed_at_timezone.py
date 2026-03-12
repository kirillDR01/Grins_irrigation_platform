"""Fix StripeWebhookEvent.processed_at model to match DB timezone type.

Revision ID: 20250711_100000
Revises: 20250710_100700
Create Date: 2025-07-11 10:00:00

The database column was already created as TIMESTAMP WITH TIME ZONE
(migration 20250702_100300), but the SQLAlchemy model was missing
DateTime(timezone=True). This caused asyncpg to reject timezone-aware
datetimes, crashing ALL webhook processing (BUG #10).

The model has been fixed in stripe_webhook_event.py. This migration
is a no-op since the DB column is already the correct type.

Validates: Requirements 7.1
"""

from collections.abc import Sequence
from typing import Union

revision: str = "20250711_100000"
down_revision: Union[str, None] = "20250710_100700"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: DB column already TIMESTAMP WITH TIME ZONE.

    The fix was in the SQLAlchemy model (DateTime(timezone=True)),
    not in the database schema.
    """


def downgrade() -> None:
    """No-op: reverting the model change doesn't require a migration."""
