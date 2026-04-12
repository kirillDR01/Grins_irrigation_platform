"""Add composite index for campaign_responses latest-wins query.

Covers the DISTINCT ON (campaign_id, phone) ORDER BY received_at DESC
pattern used by all read queries (summary, list, export).

Revision ID: 20260410_100000
Revises: 20260409_100000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260410_100000"
down_revision: Union[str, None] = "20260409_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_campaign_responses_campaign_phone_received",
        "campaign_responses",
        ["campaign_id", "phone", sa.text("received_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_campaign_responses_campaign_phone_received",
        table_name="campaign_responses",
    )
