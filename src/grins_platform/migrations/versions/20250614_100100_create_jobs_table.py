"""Create jobs table.

Revision ID: 005_jobs
Revises: 004_service_offerings
Create Date: 2025-06-14 10:01:00

This migration creates the jobs table with all columns defined in the
design document, including foreign keys to customers, properties, and
service_offerings tables, indexes for performance, and check constraints
for data integrity.

Validates: Requirements 2.1, 2.6-2.12, 10.8-10.10
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_jobs"
down_revision: Union[str, None] = "004_service_offerings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create jobs table with foreign keys, indexes, and constraints."""
    # Create jobs table
    op.create_table(
        "jobs",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Foreign key references (Requirements 10.8-10.10)
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("property_id", sa.UUID(), nullable=True),
        sa.Column("service_offering_id", sa.UUID(), nullable=True),
        # Job Details (Requirement 2.1)
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="requested",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        # Scheduling
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "priority_level",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "weather_sensitive",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        # Requirements (Requirement 2.8)
        sa.Column(
            "staffing_required",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("equipment_required", sa.JSON(), nullable=True),
        sa.Column("materials_required", sa.JSON(), nullable=True),
        # Pricing (Requirement 2.7)
        sa.Column("quoted_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("final_amount", sa.Numeric(10, 2), nullable=True),
        # Lead Attribution (Requirements 2.11, 2.12)
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("source_details", sa.JSON(), nullable=True),
        # Status Timestamps
        sa.Column(
            "requested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Soft Delete
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Record Timestamps (Requirement 2.6)
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
        # Foreign key constraints (Requirements 10.8-10.10)
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_jobs_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name="fk_jobs_property_id",
        ),
        sa.ForeignKeyConstraint(
            ["service_offering_id"],
            ["service_offerings.id"],
            name="fk_jobs_service_offering_id",
        ),
        # Check constraint for category enum
        sa.CheckConstraint(
            "category IN ('ready_to_schedule', 'requires_estimate')",
            name="ck_jobs_category",
        ),
        # Check constraint for status enum (Requirement 2.9)
        sa.CheckConstraint(
            "status IN "
            "('requested', 'approved', 'scheduled', 'in_progress', "
            "'completed', 'cancelled', 'closed')",
            name="ck_jobs_status",
        ),
        # Check constraint for source enum (Requirement 2.11)
        sa.CheckConstraint(
            "source IS NULL OR source IN "
            "('website', 'google', 'referral', 'phone', 'partner')",
            name="ck_jobs_source",
        ),
        # Check constraint for priority_level (Requirement 2.10)
        sa.CheckConstraint(
            "priority_level >= 0 AND priority_level <= 2",
            name="ck_jobs_priority_level",
        ),
        # Check constraint for positive quoted_amount (Requirement 2.7)
        sa.CheckConstraint(
            "quoted_amount IS NULL OR quoted_amount >= 0",
            name="ck_jobs_positive_quoted_amount",
        ),
        # Check constraint for positive final_amount (Requirement 2.7)
        sa.CheckConstraint(
            "final_amount IS NULL OR final_amount >= 0",
            name="ck_jobs_positive_final_amount",
        ),
        # Check constraint for positive duration
        sa.CheckConstraint(
            "estimated_duration_minutes IS NULL OR estimated_duration_minutes > 0",
            name="ck_jobs_positive_duration",
        ),
        # Check constraint for positive staffing
        sa.CheckConstraint(
            "staffing_required >= 1",
            name="ck_jobs_positive_staffing",
        ),
    )

    # Create indexes for performance
    # Index on customer_id for customer job lookups
    op.create_index(
        "idx_jobs_customer_id",
        "jobs",
        ["customer_id"],
    )
    # Index on property_id for property job lookups
    op.create_index(
        "idx_jobs_property_id",
        "jobs",
        ["property_id"],
    )
    # Index on service_offering_id for service job lookups
    op.create_index(
        "idx_jobs_service_offering_id",
        "jobs",
        ["service_offering_id"],
    )
    # Index on status for status filtering
    op.create_index(
        "idx_jobs_status",
        "jobs",
        ["status"],
    )
    # Index on category for category filtering
    op.create_index(
        "idx_jobs_category",
        "jobs",
        ["category"],
    )
    # Index on created_at for date range queries and sorting
    op.create_index(
        "idx_jobs_created_at",
        "jobs",
        ["created_at"],
    )
    # Index on is_deleted for soft delete filtering
    op.create_index(
        "idx_jobs_is_deleted",
        "jobs",
        ["is_deleted"],
    )
    # Index on priority_level for priority filtering
    op.create_index(
        "idx_jobs_priority_level",
        "jobs",
        ["priority_level"],
    )
    # Composite index for common query pattern: active jobs by status
    op.create_index(
        "idx_jobs_active_status",
        "jobs",
        ["status", "is_deleted"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    # Composite index for common query pattern: customer's active jobs
    op.create_index(
        "idx_jobs_customer_active",
        "jobs",
        ["customer_id", "is_deleted"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    """Drop jobs table and all indexes."""
    # Drop indexes first
    op.drop_index("idx_jobs_customer_active", table_name="jobs")
    op.drop_index("idx_jobs_active_status", table_name="jobs")
    op.drop_index("idx_jobs_priority_level", table_name="jobs")
    op.drop_index("idx_jobs_is_deleted", table_name="jobs")
    op.drop_index("idx_jobs_created_at", table_name="jobs")
    op.drop_index("idx_jobs_category", table_name="jobs")
    op.drop_index("idx_jobs_status", table_name="jobs")
    op.drop_index("idx_jobs_service_offering_id", table_name="jobs")
    op.drop_index("idx_jobs_property_id", table_name="jobs")
    op.drop_index("idx_jobs_customer_id", table_name="jobs")

    # Drop table
    op.drop_table("jobs")
