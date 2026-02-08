"""Create leads table.

Revision ID: 20250628_100000
Revises: 20250627_100000
Create Date: 2025-06-28 10:00:00

This migration creates the leads table for storing website form submissions.
Includes all columns from the design document, foreign keys to staff and
customers tables with ON DELETE SET NULL, and indexes on phone, status,
created_at, and zip_code for query performance.

Validates: Requirement 4.1, 4.2, 4.3, 4.7
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250628_100000"
down_revision: Union[str, None] = "20250627_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create leads table with foreign keys, indexes, and constraints."""
    # Create leads table
    op.create_table(
        "leads",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Contact information
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        # Location
        sa.Column("zip_code", sa.String(10), nullable=False),
        # Lead details
        sa.Column("situation", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source_site",
            sa.String(100),
            nullable=False,
            server_default="residential",
        ),
        # Status and assignment
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "assigned_to",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Lifecycle timestamps
        sa.Column("contacted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("converted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Record timestamps
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
    )

    # Create indexes for performance (Requirement 4.3)
    op.create_index("idx_leads_phone", "leads", ["phone"])
    op.create_index("idx_leads_status", "leads", ["status"])
    op.create_index("idx_leads_created_at", "leads", ["created_at"])
    op.create_index("idx_leads_zip_code", "leads", ["zip_code"])


def downgrade() -> None:
    """Drop leads table and all indexes."""
    # Drop indexes first
    op.drop_index("idx_leads_zip_code", table_name="leads")
    op.drop_index("idx_leads_created_at", table_name="leads")
    op.drop_index("idx_leads_status", table_name="leads")
    op.drop_index("idx_leads_phone", table_name="leads")

    # Drop table (also drops foreign key constraints)
    op.drop_table("leads")
