"""Add route optimization fields to staff and service_offerings.

Revision ID: 010_route_optimization_fields
Revises: 009_staff_availability
Create Date: 2025-06-17 10:00:00

This migration adds:
- assigned_equipment JSONB to staff (Requirement 2.1)
- default_start_* fields to staff (Requirement 3.1)
- buffer_minutes to service_offerings (Requirement 8.1)
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_route_optimization_fields"
down_revision: Union[str, None] = "009_staff_availability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add route optimization fields."""
    # Task 4.1: Add assigned_equipment to staff
    op.add_column(
        "staff",
        sa.Column(
            "assigned_equipment",
            sa.JSON(),
            nullable=True,
            server_default="[]",
        ),
    )

    # Task 5.1: Add starting location fields to staff
    op.add_column(
        "staff",
        sa.Column("default_start_address", sa.String(255), nullable=True),
    )
    op.add_column(
        "staff",
        sa.Column("default_start_city", sa.String(100), nullable=True),
    )
    op.add_column(
        "staff",
        sa.Column("default_start_lat", sa.Numeric(10, 7), nullable=True),
    )
    op.add_column(
        "staff",
        sa.Column("default_start_lng", sa.Numeric(10, 7), nullable=True),
    )

    # Task 8.1: Add buffer_minutes to service_offerings
    op.add_column(
        "service_offerings",
        sa.Column(
            "buffer_minutes",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )


def downgrade() -> None:
    """Remove route optimization fields."""
    # Remove buffer_minutes from service_offerings
    op.drop_column("service_offerings", "buffer_minutes")

    # Remove starting location fields from staff
    op.drop_column("staff", "default_start_lng")
    op.drop_column("staff", "default_start_lat")
    op.drop_column("staff", "default_start_city")
    op.drop_column("staff", "default_start_address")

    # Remove assigned_equipment from staff
    op.drop_column("staff", "assigned_equipment")
