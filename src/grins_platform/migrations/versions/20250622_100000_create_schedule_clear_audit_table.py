"""Create schedule_clear_audit table.

Revision ID: 20250622_100000
Revises: 20250621_100000
Create Date: 2025-01-29

This migration creates the schedule_clear_audit table for tracking
schedule clear operations with full audit trail:
- id: UUID primary key
- schedule_date: Date that was cleared
- appointments_data: JSONB snapshot of deleted appointments
- jobs_reset: Array of job UUIDs that were reset
- appointment_count: Number of appointments deleted
- cleared_by: Reference to staff who performed the clear
- cleared_at: Timestamp of the clear operation
- notes: Optional notes about the clear

Requirements: 5.1-5.6
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision = "20250622_100000"
down_revision = "20250621_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create schedule_clear_audit table."""
    op.create_table(
        "schedule_clear_audit",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("schedule_date", sa.Date(), nullable=False),
        sa.Column("appointments_data", JSONB(), nullable=False),
        sa.Column("jobs_reset", ARRAY(UUID(as_uuid=True)), nullable=False),
        sa.Column("appointment_count", sa.Integer(), nullable=False),
        sa.Column(
            "cleared_by",
            UUID(as_uuid=True),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cleared_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Create index on schedule_date for date-based queries
    op.create_index(
        "ix_schedule_clear_audit_schedule_date",
        "schedule_clear_audit",
        ["schedule_date"],
    )

    # Create index on cleared_at for recent clears queries
    op.create_index(
        "ix_schedule_clear_audit_cleared_at",
        "schedule_clear_audit",
        ["cleared_at"],
    )


def downgrade() -> None:
    """Drop schedule_clear_audit table."""
    op.drop_index(
        "ix_schedule_clear_audit_cleared_at", table_name="schedule_clear_audit",
    )
    op.drop_index(
        "ix_schedule_clear_audit_schedule_date", table_name="schedule_clear_audit",
    )
    op.drop_table("schedule_clear_audit")
