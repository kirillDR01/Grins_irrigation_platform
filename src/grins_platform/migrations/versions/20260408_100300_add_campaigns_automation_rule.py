"""Add campaigns.automation_rule column if missing.

Revision ID: 20260408_100300
Revises: 20260408_100200
Create Date: 2026-04-08

The ``Campaign`` ORM model has an ``automation_rule`` JSONB column
(see ``models/campaign.py`` and the ``evaluate_automation_rules``
service method), but no migration in alembic history creates it.
The local dev Postgres happens to have it (manually patched outside
of alembic at some point); the Railway dev Postgres does not.

Symptom: every ``GET /api/v1/campaigns?page=1&page_size=20`` returns
HTTP 500 with ``UndefinedColumnError: column campaigns.automation_rule
does not exist``. This cascades into the Communications tab breaking
the Campaigns list and the New Text Campaign wizard.

This is the same drift pattern as the earlier
``status → delivery_status`` and ``delivered_at → sent_at`` renames.
The fix is another idempotent migration: ``ADD COLUMN IF NOT EXISTS``
so it's a no-op on environments that already have the column (local)
and a real ADD on environments that don't (Railway dev).
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers
revision: str = "20260408_100300"
down_revision: Union[str, None] = "20260408_100200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add campaigns.automation_rule jsonb column if not already present."""
    op.execute(
        """
        ALTER TABLE campaigns
            ADD COLUMN IF NOT EXISTS automation_rule JSONB;
        """,
    )


def downgrade() -> None:
    """Drop campaigns.automation_rule if present."""
    op.execute(
        """
        ALTER TABLE campaigns
            DROP COLUMN IF EXISTS automation_rule;
        """,
    )
