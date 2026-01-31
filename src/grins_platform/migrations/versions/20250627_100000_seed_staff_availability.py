"""Seed staff availability for demo purposes.

Revision ID: 20250627_100000
Revises: 20250626_100000
Create Date: 2025-01-31

This migration seeds staff availability records for the next 30 days
so that the schedule generation feature works out of the box.

Staff availability is required for the scheduling system to know
when staff members can be assigned to jobs.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "20250627_100000"
down_revision: Union[str, None] = "20250626_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed staff availability for the next 30 days.

    Creates availability records for all active staff members
    for the next 30 days (excluding Sundays).

    Default schedule:
    - Monday-Friday: 7:00 AM - 5:00 PM
    - Saturday: 8:00 AM - 2:00 PM
    - Sunday: Off
    - Lunch: 12:00 PM - 12:30 PM
    """
    # Create availability for all active staff for the next 30 days
    # Using generate_series to create dates
    op.execute(
        text(
            """
            INSERT INTO staff_availability (
                staff_id, date, start_time, end_time,
                is_available, lunch_start, lunch_duration_minutes, notes
            )
            SELECT
                s.id as staff_id,
                d.date as date,
                CASE
                    WHEN EXTRACT(DOW FROM d.date) = 6 THEN '08:00:00'::time
                    ELSE '07:00:00'::time
                END as start_time,
                CASE
                    WHEN EXTRACT(DOW FROM d.date) = 6 THEN '14:00:00'::time
                    ELSE '17:00:00'::time
                END as end_time,
                true as is_available,
                '12:00:00'::time as lunch_start,
                30 as lunch_duration_minutes,
                'Auto-generated availability' as notes
            FROM staff s
            CROSS JOIN (
                SELECT generate_series(
                    CURRENT_DATE,
                    CURRENT_DATE + INTERVAL '30 days',
                    INTERVAL '1 day'
                )::date as date
            ) d
            WHERE s.is_active = true
              AND s.role = 'tech'
              AND EXTRACT(DOW FROM d.date) != 0
            ON CONFLICT DO NOTHING;
            """,
        ),
    )


def downgrade() -> None:
    """Remove auto-generated staff availability records."""
    op.execute(
        text(
            """
            DELETE FROM staff_availability
            WHERE notes = 'Auto-generated availability';
            """,
        ),
    )
