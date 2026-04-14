"""Add SCHEDULED to JobStatus and DRAFT to AppointmentStatus enums.

Revision ID: 20260412_100200
Revises: 20260412_100100
Requirements: 5.8, 8.1
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260412_100200"
down_revision: Union[str, None] = "20260412_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add SCHEDULED to JobStatus enum (after to_be_scheduled)
    op.execute(
        "ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'scheduled' AFTER 'to_be_scheduled'"
    )

    # Add DRAFT to AppointmentStatus enum (after pending)
    op.execute(
        "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'draft' AFTER 'pending'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # A full enum recreation would be needed for a true downgrade,
    # but the IF NOT EXISTS guard makes re-running upgrade safe.
    pass
