"""Add schedule_reassignment table.

Revision ID: 20250619_100000
Revises: 20250618_100000
Create Date: 2025-06-19 10:00:00.000000

Validates: Requirement 11.3
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "20250619_100000"
down_revision = "20250618_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create schedule_reassignment table."""
    op.create_table(
        "schedule_reassignments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "original_staff_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("staff.id"),
            nullable=False,
        ),
        sa.Column(
            "new_staff_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("staff.id"),
            nullable=False,
        ),
        sa.Column("reassignment_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("jobs_reassigned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes
    op.create_index(
        "ix_schedule_reassignments_original_staff_id",
        "schedule_reassignments",
        ["original_staff_id"],
    )
    op.create_index(
        "ix_schedule_reassignments_date",
        "schedule_reassignments",
        ["reassignment_date"],
    )


def downgrade() -> None:
    """Drop schedule_reassignment table."""
    op.drop_index("ix_schedule_reassignments_date", table_name="schedule_reassignments")
    op.drop_index(
        "ix_schedule_reassignments_original_staff_id",
        table_name="schedule_reassignments",
    )
    op.drop_table("schedule_reassignments")
