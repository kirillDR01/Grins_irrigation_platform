"""Fix 29 DateTime columns missing timezone=True in SQLAlchemy models.

Revision ID: 20260312_100000
Revises: 20250711_100000
Create Date: 2026-03-12 10:00:00

All 29 affected columns were already created as TIMESTAMPTZ in the database
(via earlier migrations). The bug was exclusively in the SQLAlchemy model
Python code, where mapped_column() calls were missing DateTime(timezone=True).
This caused asyncpg to reject timezone-aware datetimes written by webhook
handlers, crashing checkout.session.completed processing (BUG #15).

Fixed models: job.py (9), appointment.py (5), staff.py (4),
service_offering.py (2), staff_availability.py (2),
agreement_status_log.py (1), service_agreement_tier.py (2),
job_status_history.py (1). Previously correct: customer.py, lead.py,
service_agreement.py.

This migration is a no-op — no ALTER TABLE needed.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "20260312_100000"
down_revision: Union[str, None] = "20250711_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: DB columns are already TIMESTAMPTZ."""


def downgrade() -> None:
    """No-op: reverting model-only changes has no DB effect."""
