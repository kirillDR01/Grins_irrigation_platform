"""Create job_status_history table.

Revision ID: 006_job_status_history
Revises: 005_jobs
Create Date: 2025-06-14 10:02:00

This migration creates the job_status_history table to track all status
transitions for jobs, enabling audit trails and workflow analysis.

Validates: Requirements 7.1, 7.2
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_job_status_history"
down_revision: Union[str, None] = "005_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create job_status_history table with indexes and constraints."""
    # Create job_status_history table
    op.create_table(
        "job_status_history",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Foreign key to jobs (Requirement 7.1)
        sa.Column("job_id", sa.UUID(), nullable=False),
        # Status transition details (Requirement 7.1)
        sa.Column("previous_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=False),
        # Timestamp (Requirement 7.1)
        sa.Column(
            "changed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # User tracking (Requirement 7.3 - for future implementation)
        sa.Column("changed_by", sa.UUID(), nullable=True),
        # Notes/reason for change (Requirement 7.4)
        sa.Column("notes", sa.Text(), nullable=True),
        # Foreign key constraint with cascade delete
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_status_history_job_id",
            ondelete="CASCADE",
        ),
        # Check constraint for previous_status enum
        sa.CheckConstraint(
            "previous_status IS NULL OR previous_status IN "
            "('requested', 'approved', 'scheduled', 'in_progress', "
            "'completed', 'cancelled', 'closed')",
            name="ck_job_status_history_previous_status",
        ),
        # Check constraint for new_status enum
        sa.CheckConstraint(
            "new_status IN "
            "('requested', 'approved', 'scheduled', 'in_progress', "
            "'completed', 'cancelled', 'closed')",
            name="ck_job_status_history_new_status",
        ),
    )

    # Create indexes for performance
    # Index on job_id for job history lookups
    op.create_index(
        "idx_job_status_history_job_id",
        "job_status_history",
        ["job_id"],
    )
    # Index on changed_at for chronological ordering (Requirement 7.2)
    op.create_index(
        "idx_job_status_history_changed_at",
        "job_status_history",
        ["changed_at"],
    )
    # Composite index for common query pattern: job history in order
    op.create_index(
        "idx_job_status_history_job_chronological",
        "job_status_history",
        ["job_id", "changed_at"],
    )


def downgrade() -> None:
    """Drop job_status_history table and all indexes."""
    # Drop indexes first
    op.drop_index(
        "idx_job_status_history_job_chronological",
        table_name="job_status_history",
    )
    op.drop_index(
        "idx_job_status_history_changed_at",
        table_name="job_status_history",
    )
    op.drop_index(
        "idx_job_status_history_job_id",
        table_name="job_status_history",
    )

    # Drop table
    op.drop_table("job_status_history")
