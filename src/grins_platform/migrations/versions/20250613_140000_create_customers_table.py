"""Create customers table.

Revision ID: 001_customers
Revises:
Create Date: 2025-06-13 14:00:00

This migration creates the customers table with all columns defined in the
design document, including indexes for performance and check constraints
for data integrity.

Validates: Requirement 1.1, 1.7, 9.3
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_customers"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create customers table with indexes and constraints."""
    # Create customers table
    op.create_table(
        "customers",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Name fields
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        # Contact information
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True),
        # Status and Flags
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("is_priority", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_red_flag", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "is_slow_payer",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "is_new_customer",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        # Communication Preferences
        sa.Column("sms_opt_in", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("email_opt_in", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "communication_preferences_updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        # Lead Tracking
        sa.Column("lead_source", sa.String(50), nullable=True),
        sa.Column("lead_source_details", sa.JSON(), nullable=True),
        # Soft Delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        # Check constraint for status enum
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_customers_status",
        ),
        # Check constraint for lead_source enum
        sa.CheckConstraint(
            "lead_source IS NULL OR lead_source IN "
            "('website', 'google', 'referral', 'ad', 'word_of_mouth')",
            name="ck_customers_lead_source",
        ),
    )

    # Create indexes for performance (Requirement 9.3)
    op.create_index("idx_customers_phone", "customers", ["phone"])
    op.create_index("idx_customers_email", "customers", ["email"])
    op.create_index("idx_customers_status", "customers", ["status"])
    op.create_index("idx_customers_lead_source", "customers", ["lead_source"])
    op.create_index("idx_customers_is_deleted", "customers", ["is_deleted"])
    op.create_index(
        "idx_customers_name",
        "customers",
        ["last_name", "first_name"],
    )
    # Composite index for common query pattern: active customers
    op.create_index(
        "idx_customers_active",
        "customers",
        ["status", "is_deleted"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    """Drop customers table and all indexes."""
    # Drop indexes first
    op.drop_index("idx_customers_active", table_name="customers")
    op.drop_index("idx_customers_name", table_name="customers")
    op.drop_index("idx_customers_is_deleted", table_name="customers")
    op.drop_index("idx_customers_lead_source", table_name="customers")
    op.drop_index("idx_customers_status", table_name="customers")
    op.drop_index("idx_customers_email", table_name="customers")
    op.drop_index("idx_customers_phone", table_name="customers")

    # Drop table
    op.drop_table("customers")
