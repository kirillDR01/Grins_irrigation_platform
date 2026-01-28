"""Create staff_availability table.

Revision ID: 009_staff_availability
Revises: 008_appointments
Create Date: 2025-06-16 10:00:00

This migration creates the staff_availability table for managing
staff availability calendar entries with time windows and lunch breaks.

Validates: Requirements 1.1, 1.2 (Route Optimization)
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_staff_availability"
down_revision: Union[str, None] = "008_appointments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create staff_availability table with indexes and constraints."""
    # Create staff_availability table
    op.create_table(
        "staff_availability",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Foreign key to staff
        sa.Column(
            "staff_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Date for availability
        sa.Column("date", sa.Date(), nullable=False),
        # Time window
        sa.Column(
            "start_time",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'07:00:00'"),
        ),
        sa.Column(
            "end_time",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'17:00:00'"),
        ),
        # Availability flag
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        # Lunch break configuration
        sa.Column(
            "lunch_start",
            sa.Time(),
            nullable=True,
            server_default=sa.text("'12:00:00'"),
        ),
        sa.Column(
            "lunch_duration_minutes",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        # Notes
        sa.Column("notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Unique constraint on (staff_id, date)
        sa.UniqueConstraint(
            "staff_id",
            "date",
            name="uq_staff_availability_staff_date",
        ),
        # Check constraint: start_time < end_time
        sa.CheckConstraint(
            "start_time < end_time",
            name="ck_staff_availability_time_range",
        ),
        # Check constraint: lunch_duration_minutes between 0 and 120
        sa.CheckConstraint(
            "lunch_duration_minutes >= 0 AND lunch_duration_minutes <= 120",
            name="ck_staff_availability_lunch_duration",
        ),
    )

    # Create indexes for performance
    # Index on staff_id for staff lookups
    op.create_index(
        "idx_staff_availability_staff_id",
        "staff_availability",
        ["staff_id"],
    )
    # Index on date for date queries
    op.create_index(
        "idx_staff_availability_date",
        "staff_availability",
        ["date"],
    )
    # Composite index for common query: staff_id + date
    op.create_index(
        "idx_staff_availability_staff_date",
        "staff_availability",
        ["staff_id", "date"],
    )
    # Index for finding available staff on a date
    op.create_index(
        "idx_staff_availability_date_available",
        "staff_availability",
        ["date", "is_available"],
        postgresql_where=sa.text("is_available = true"),
    )


def downgrade() -> None:
    """Drop staff_availability table and all indexes."""
    # Drop indexes first
    op.drop_index(
        "idx_staff_availability_date_available",
        table_name="staff_availability",
    )
    op.drop_index(
        "idx_staff_availability_staff_date",
        table_name="staff_availability",
    )
    op.drop_index("idx_staff_availability_date", table_name="staff_availability")
    op.drop_index("idx_staff_availability_staff_id", table_name="staff_availability")

    # Drop table
    op.drop_table("staff_availability")
