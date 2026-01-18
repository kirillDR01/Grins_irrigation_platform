"""Create staff table.

Revision ID: 007_staff
Revises: 006_job_status_history
Create Date: 2025-06-14 10:03:00

This migration creates the staff table with all columns defined in the
design document, including indexes for performance and check constraints
for data integrity.

Validates: Requirements 8.1, 8.7-8.10
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_staff"
down_revision: Union[str, None] = "006_job_status_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create staff table with indexes and constraints."""
    # Create staff table
    op.create_table(
        "staff",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Basic info
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),  # Requirement 8.10
        sa.Column("email", sa.String(255), nullable=True),
        # Role and skills (Requirements 8.2, 8.3)
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("skill_level", sa.String(50), nullable=True),
        sa.Column("certifications", sa.JSON(), nullable=True),  # Requirement 8.8
        # Availability (Requirement 9.1, 9.2)
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("availability_notes", sa.Text(), nullable=True),
        # Compensation (Requirement 8.9)
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        # Status
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        # Timestamps (Requirement 8.7)
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
        # Check constraint for role enum (Requirement 8.2)
        sa.CheckConstraint(
            "role IN ('tech', 'sales', 'admin')",
            name="ck_staff_role",
        ),
        # Check constraint for skill_level enum (Requirement 8.3)
        sa.CheckConstraint(
            "skill_level IS NULL OR skill_level IN ('junior', 'senior', 'lead')",
            name="ck_staff_skill_level",
        ),
        # Check constraint for positive hourly_rate (Requirement 8.9)
        sa.CheckConstraint(
            "hourly_rate IS NULL OR hourly_rate >= 0",
            name="ck_staff_positive_hourly_rate",
        ),
    )

    # Create indexes for performance
    # Index on role for role filtering (Requirement 9.4)
    op.create_index(
        "idx_staff_role",
        "staff",
        ["role"],
    )
    # Index on skill_level for skill filtering (Requirement 9.5)
    op.create_index(
        "idx_staff_skill_level",
        "staff",
        ["skill_level"],
    )
    # Index on is_available for availability filtering (Requirement 9.3)
    op.create_index(
        "idx_staff_is_available",
        "staff",
        ["is_available"],
    )
    # Index on is_active for active staff filtering
    op.create_index(
        "idx_staff_is_active",
        "staff",
        ["is_active"],
    )
    # Index on name for name lookups
    op.create_index(
        "idx_staff_name",
        "staff",
        ["name"],
    )
    # Composite index for common query pattern: available and active staff
    op.create_index(
        "idx_staff_available_active",
        "staff",
        ["is_available", "is_active"],
        postgresql_where=sa.text("is_available = true AND is_active = true"),
    )
    # Composite index for common query pattern: active staff by role
    op.create_index(
        "idx_staff_active_role",
        "staff",
        ["role", "is_active"],
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    """Drop staff table and all indexes."""
    # Drop indexes first
    op.drop_index("idx_staff_active_role", table_name="staff")
    op.drop_index("idx_staff_available_active", table_name="staff")
    op.drop_index("idx_staff_name", table_name="staff")
    op.drop_index("idx_staff_is_active", table_name="staff")
    op.drop_index("idx_staff_is_available", table_name="staff")
    op.drop_index("idx_staff_skill_level", table_name="staff")
    op.drop_index("idx_staff_role", table_name="staff")

    # Drop table
    op.drop_table("staff")
