"""Add cancellation fields to appointments and create waitlist table.

Revision ID: 20250618_100000
Revises: 010_route_optimization_fields
Create Date: 2025-06-18 10:00:00.000000

Validates: Requirements 10.2, 10.3, 10.4
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "20250618_100000"
down_revision = "010_route_optimization_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add cancellation fields and create waitlist table."""
    # Add cancellation fields to appointments
    op.add_column(
        "appointments",
        sa.Column("cancellation_reason", sa.String(500), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column(
            "rescheduled_from_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id"),
            nullable=True,
        ),
    )

    # Create schedule_waitlist table
    op.create_table(
        "schedule_waitlist",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id"),
            nullable=False,
        ),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_time_start", sa.Time(), nullable=True),
        sa.Column("preferred_time_end", sa.Time(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes
    op.create_index(
        "ix_schedule_waitlist_job_id",
        "schedule_waitlist",
        ["job_id"],
    )
    op.create_index(
        "ix_schedule_waitlist_preferred_date",
        "schedule_waitlist",
        ["preferred_date"],
    )
    op.create_index(
        "ix_appointments_rescheduled_from_id",
        "appointments",
        ["rescheduled_from_id"],
    )


def downgrade() -> None:
    """Remove cancellation fields and drop waitlist table."""
    op.drop_index("ix_appointments_rescheduled_from_id", table_name="appointments")
    op.drop_index("ix_schedule_waitlist_preferred_date", table_name="schedule_waitlist")
    op.drop_index("ix_schedule_waitlist_job_id", table_name="schedule_waitlist")
    op.drop_table("schedule_waitlist")
    op.drop_column("appointments", "rescheduled_from_id")
    op.drop_column("appointments", "cancelled_at")
    op.drop_column("appointments", "cancellation_reason")
