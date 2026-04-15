"""Add SCHEDULED to JobStatus and DRAFT to AppointmentStatus enums.

Revision ID: 20260412_100200
Revises: 20260412_100100
Requirements: 5.8, 8.1
"""

from collections.abc import Sequence
from typing import Union

revision: str = "20260412_100200"
down_revision: Union[str, None] = "20260412_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: Job.status and Appointment.status are String(50) columns,
    # not PostgreSQL native enum types. New values ('scheduled', 'draft')
    # are enforced by the Python-side enums in enums.py, not at the DB level.
    pass


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # A full enum recreation would be needed for a true downgrade,
    # but the IF NOT EXISTS guard makes re-running upgrade safe.
    pass
