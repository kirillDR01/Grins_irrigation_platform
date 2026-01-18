"""Create service_offerings table.

Revision ID: 004_service_offerings
Revises: 003_updated_at_trigger
Create Date: 2025-06-14 10:00:00

This migration creates the service_offerings table with all columns defined in the
design document, including indexes for performance and check constraints
for data integrity.

Validates: Requirements 1.1, 1.7, 1.8-1.13
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_service_offerings"
down_revision: Union[str, None] = "003_updated_at_trigger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create service_offerings table with indexes and constraints."""
    # Create service_offerings table
    op.create_table(
        "service_offerings",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Service Identity
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Pricing
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_per_zone", sa.Numeric(10, 2), nullable=True),
        sa.Column("pricing_model", sa.String(50), nullable=False),
        # Duration Estimates
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("duration_per_zone_minutes", sa.Integer(), nullable=True),
        # Requirements
        sa.Column(
            "staffing_required",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("equipment_required", sa.JSON(), nullable=True),
        # Business Rules
        sa.Column(
            "lien_eligible",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "requires_prepay",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
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
        # Check constraint for category enum (Requirement 1.2)
        sa.CheckConstraint(
            "category IN "
            "('seasonal', 'repair', 'installation', 'diagnostic', 'landscaping')",
            name="ck_service_offerings_category",
        ),
        # Check constraint for pricing_model enum (Requirement 1.3)
        sa.CheckConstraint(
            "pricing_model IN ('flat', 'zone_based', 'hourly', 'custom')",
            name="ck_service_offerings_pricing_model",
        ),
        # Check constraint for positive base_price (Requirement 1.8)
        sa.CheckConstraint(
            "base_price IS NULL OR base_price >= 0",
            name="ck_service_offerings_positive_base_price",
        ),
        # Check constraint for positive price_per_zone (Requirement 1.8)
        sa.CheckConstraint(
            "price_per_zone IS NULL OR price_per_zone >= 0",
            name="ck_service_offerings_positive_price_per_zone",
        ),
        # Check constraint for positive duration (Requirement 1.9)
        sa.CheckConstraint(
            "estimated_duration_minutes IS NULL OR estimated_duration_minutes > 0",
            name="ck_service_offerings_positive_duration",
        ),
        # Check constraint for positive duration_per_zone (Requirement 1.9)
        sa.CheckConstraint(
            "duration_per_zone_minutes IS NULL OR duration_per_zone_minutes > 0",
            name="ck_service_offerings_positive_duration_per_zone",
        ),
        # Check constraint for positive staffing (Requirement 1.10)
        sa.CheckConstraint(
            "staffing_required >= 1",
            name="ck_service_offerings_positive_staffing",
        ),
    )

    # Create indexes for performance
    op.create_index(
        "idx_service_offerings_category",
        "service_offerings",
        ["category"],
    )
    op.create_index(
        "idx_service_offerings_pricing_model",
        "service_offerings",
        ["pricing_model"],
    )
    op.create_index(
        "idx_service_offerings_is_active",
        "service_offerings",
        ["is_active"],
    )
    op.create_index(
        "idx_service_offerings_name",
        "service_offerings",
        ["name"],
    )
    # Composite index for common query pattern: active services by category
    op.create_index(
        "idx_service_offerings_active_category",
        "service_offerings",
        ["category", "is_active"],
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    """Drop service_offerings table and all indexes."""
    # Drop indexes first
    op.drop_index(
        "idx_service_offerings_active_category",
        table_name="service_offerings",
    )
    op.drop_index("idx_service_offerings_name", table_name="service_offerings")
    op.drop_index("idx_service_offerings_is_active", table_name="service_offerings")
    op.drop_index("idx_service_offerings_pricing_model", table_name="service_offerings")
    op.drop_index("idx_service_offerings_category", table_name="service_offerings")

    # Drop table
    op.drop_table("service_offerings")
