"""Create properties table.

Revision ID: 002_properties
Revises: 001_customers
Create Date: 2025-06-13 14:01:00

This migration creates the properties table with all columns defined in the
design document, including foreign key to customers, indexes for performance,
and check constraints for data integrity.

Validates: Requirement 2.1, 2.2, 2.3, 2.4
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_properties"
down_revision: Union[str, None] = "001_customers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create properties table with indexes and constraints."""
    # Create properties table
    op.create_table(
        "properties",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Foreign key to customers
        sa.Column("customer_id", sa.UUID(), nullable=False),
        # Location fields
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(50), nullable=False, server_default="MN"),
        sa.Column("zip_code", sa.String(20), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 8), nullable=True),
        sa.Column("longitude", sa.Numeric(11, 8), nullable=True),
        # System Details
        sa.Column("zone_count", sa.Integer(), nullable=True),
        sa.Column(
            "system_type",
            sa.String(20),
            nullable=False,
            server_default="standard",
        ),
        sa.Column(
            "property_type",
            sa.String(20),
            nullable=False,
            server_default="residential",
        ),
        # Access Information
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("access_instructions", sa.Text(), nullable=True),
        sa.Column("gate_code", sa.String(50), nullable=True),
        sa.Column("has_dogs", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("special_notes", sa.Text(), nullable=True),
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
        # Foreign key constraint
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_properties_customer_id",
            ondelete="CASCADE",
        ),
        # Check constraint for zone_count (Requirement 2.2)
        sa.CheckConstraint(
            "zone_count IS NULL OR (zone_count >= 1 AND zone_count <= 50)",
            name="ck_properties_zone_count",
        ),
        # Check constraint for system_type enum (Requirement 2.3)
        sa.CheckConstraint(
            "system_type IN ('standard', 'lake_pump')",
            name="ck_properties_system_type",
        ),
        # Check constraint for property_type enum (Requirement 2.4)
        sa.CheckConstraint(
            "property_type IN ('residential', 'commercial')",
            name="ck_properties_property_type",
        ),
    )

    # Create indexes for performance
    op.create_index("idx_properties_customer", "properties", ["customer_id"])
    op.create_index("idx_properties_city", "properties", ["city"])
    # Composite index for location-based queries
    op.create_index(
        "idx_properties_location",
        "properties",
        ["latitude", "longitude"],
    )
    # Composite index for primary property lookup
    op.create_index(
        "idx_properties_is_primary",
        "properties",
        ["customer_id", "is_primary"],
    )


def downgrade() -> None:
    """Drop properties table and all indexes."""
    # Drop indexes first
    op.drop_index("idx_properties_is_primary", table_name="properties")
    op.drop_index("idx_properties_location", table_name="properties")
    op.drop_index("idx_properties_city", table_name="properties")
    op.drop_index("idx_properties_customer", table_name="properties")

    # Drop table
    op.drop_table("properties")
