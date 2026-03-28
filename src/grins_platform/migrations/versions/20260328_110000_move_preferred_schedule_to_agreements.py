"""Move preferred_schedule columns from customers to service_agreements.

Revision ID: 20260328_110000
Revises: 20260328_100000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260328_110000"
down_revision = "20260328_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add columns to service_agreements
    op.add_column(
        "service_agreements",
        sa.Column("preferred_schedule", sa.String(30), nullable=True),
    )
    op.add_column(
        "service_agreements",
        sa.Column("preferred_schedule_details", sa.Text(), nullable=True),
    )

    # 2. Copy data from each customer to their most recent agreement
    op.execute(
        """
        UPDATE service_agreements sa
        SET preferred_schedule = c.preferred_schedule,
            preferred_schedule_details = c.preferred_schedule_details
        FROM customers c
        WHERE sa.customer_id = c.id
          AND c.preferred_schedule IS NOT NULL
          AND sa.id = (
              SELECT sa2.id FROM service_agreements sa2
              WHERE sa2.customer_id = c.id
              ORDER BY sa2.created_at DESC LIMIT 1
          )
        """,
    )

    # 3. Drop columns from customers
    op.drop_column("customers", "preferred_schedule_details")
    op.drop_column("customers", "preferred_schedule")


def downgrade() -> None:
    # 1. Add columns back to customers
    op.add_column(
        "customers",
        sa.Column("preferred_schedule", sa.String(30), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("preferred_schedule_details", sa.Text(), nullable=True),
    )

    # 2. Copy from most recent agreement back to customer
    op.execute(
        """
        UPDATE customers c
        SET preferred_schedule = sa.preferred_schedule,
            preferred_schedule_details = sa.preferred_schedule_details
        FROM service_agreements sa
        WHERE sa.customer_id = c.id
          AND sa.preferred_schedule IS NOT NULL
          AND sa.id = (
              SELECT sa2.id FROM service_agreements sa2
              WHERE sa2.customer_id = c.id
              ORDER BY sa2.created_at DESC LIMIT 1
          )
        """,
    )

    # 3. Drop columns from service_agreements
    op.drop_column("service_agreements", "preferred_schedule_details")
    op.drop_column("service_agreements", "preferred_schedule")
