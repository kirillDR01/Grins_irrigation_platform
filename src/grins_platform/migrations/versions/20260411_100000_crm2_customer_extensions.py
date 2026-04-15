"""CRM2: Column additions to existing tables.

Add merged_into_customer_id to customers, is_hoa to properties,
moved_to/moved_at/last_contacted_at/job_requested to leads,
and job_id to customer_photos.

Revision ID: 20260411_100000
Revises: 20260410_100100
Requirements: 5.8, 6.5, 8.2, 9.2, 10.3, 11.2, 26.3
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260411_100000"
down_revision: Union[str, None] = "20260410_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # customers: merged_into_customer_id for duplicate merge tracking
    op.add_column(
        "customers",
        sa.Column(
            "merged_into_customer_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_customers_merged_into",
        "customers",
        ["merged_into_customer_id"],
        postgresql_where=sa.text("merged_into_customer_id IS NOT NULL"),
    )

    # properties: is_hoa boolean
    op.add_column(
        "properties",
        sa.Column("is_hoa", sa.Boolean(), nullable=False, server_default="false"),
    )

    # leads: moved_to, moved_at, last_contacted_at, job_requested
    op.add_column(
        "leads",
        sa.Column("moved_to", sa.String(20), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("job_requested", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_leads_moved_to",
        "leads",
        ["moved_to"],
        postgresql_where=sa.text("moved_to IS NOT NULL"),
    )

    # customer_photos: job_id FK
    op.add_column(
        "customer_photos",
        sa.Column(
            "job_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_customer_photos_job_id",
        "customer_photos",
        ["job_id"],
        postgresql_where=sa.text("job_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_customer_photos_job_id", table_name="customer_photos")
    op.drop_column("customer_photos", "job_id")

    op.drop_index("ix_leads_moved_to", table_name="leads")
    op.drop_column("leads", "job_requested")
    op.drop_column("leads", "last_contacted_at")
    op.drop_column("leads", "moved_at")
    op.drop_column("leads", "moved_to")

    op.drop_column("properties", "is_hoa")

    op.drop_index("ix_customers_merged_into", table_name="customers")
    op.drop_column("customers", "merged_into_customer_id")
