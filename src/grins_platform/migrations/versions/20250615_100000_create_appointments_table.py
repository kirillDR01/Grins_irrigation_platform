"""Create appointments table.

Revision ID: 008_appointments
Revises: 007_staff
Create Date: 2025-06-15 10:00:00

This migration creates the appointments table with all columns defined in the
design document, including foreign keys to jobs and staff tables, indexes for
performance, and check constraints for data integrity.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_appointments"
down_revision: Union[str, None] = "007_staff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create appointments table with foreign keys, indexes, and constraints."""
    # Create appointments table
    op.create_table(
        "appointments",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Foreign key references
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("staff_id", sa.UUID(), nullable=False),
        # Scheduling
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("time_window_start", sa.Time(), nullable=False),
        sa.Column("time_window_end", sa.Time(), nullable=False),
        # Status
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="scheduled",
        ),
        # Execution Tracking
        sa.Column("arrived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Notes
        sa.Column("notes", sa.Text(), nullable=True),
        # Route Information
        sa.Column("route_order", sa.Integer(), nullable=True),
        sa.Column("estimated_arrival", sa.Time(), nullable=True),
        # Record Timestamps
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
        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_appointments_job_id",
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff.id"],
            name="fk_appointments_staff_id",
        ),
        # Check constraint for status enum
        sa.CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'in_progress', "
            "'completed', 'cancelled')",
            name="ck_appointments_status",
        ),
        # Check constraint for valid time window
        sa.CheckConstraint(
            "time_window_start < time_window_end",
            name="ck_appointments_valid_time_window",
        ),
        # Check constraint for positive route_order
        sa.CheckConstraint(
            "route_order IS NULL OR route_order >= 0",
            name="ck_appointments_positive_route_order",
        ),
    )

    # Create indexes for performance
    # Index on job_id for job appointment lookups
    op.create_index(
        "idx_appointments_job_id",
        "appointments",
        ["job_id"],
    )
    # Index on staff_id for staff appointment lookups
    op.create_index(
        "idx_appointments_staff_id",
        "appointments",
        ["staff_id"],
    )
    # Index on scheduled_date for date filtering
    op.create_index(
        "idx_appointments_scheduled_date",
        "appointments",
        ["scheduled_date"],
    )
    # Index on status for status filtering
    op.create_index(
        "idx_appointments_status",
        "appointments",
        ["status"],
    )
    # Composite index for staff daily schedule queries
    op.create_index(
        "idx_appointments_staff_date",
        "appointments",
        ["staff_id", "scheduled_date"],
    )
    # Composite index for date range queries with status
    op.create_index(
        "idx_appointments_date_status",
        "appointments",
        ["scheduled_date", "status"],
    )


def downgrade() -> None:
    """Drop appointments table and all indexes."""
    # Drop indexes first
    op.drop_index("idx_appointments_date_status", table_name="appointments")
    op.drop_index("idx_appointments_staff_date", table_name="appointments")
    op.drop_index("idx_appointments_status", table_name="appointments")
    op.drop_index("idx_appointments_scheduled_date", table_name="appointments")
    op.drop_index("idx_appointments_staff_id", table_name="appointments")
    op.drop_index("idx_appointments_job_id", table_name="appointments")

    # Drop table
    op.drop_table("appointments")
