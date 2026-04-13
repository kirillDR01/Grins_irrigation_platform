"""CRM2: Create sales_entries and sales_calendar_events tables.

Pipeline records for the new Sales tab and estimate appointments
for the Sales calendar (separate from main schedule).

Revision ID: 20260411_100300
Revises: 20260411_100200
Requirements: 13.3, 14.1, 14.2, 15.1
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260411_100300"
down_revision: Union[str, None] = "20260411_100200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sales_entries",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            sa.UUID(),
            sa.ForeignKey("properties.id"),
            nullable=True,
        ),
        sa.Column(
            "lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id"),
            nullable=True,
        ),
        sa.Column("job_type", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="schedule_estimate",
        ),
        sa.Column("last_contact_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "override_flag",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("closed_reason", sa.Text(), nullable=True),
        sa.Column("signwell_document_id", sa.String(255), nullable=True),
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
    op.create_index(
        "idx_sales_entries_status",
        "sales_entries",
        ["status"],
    )
    op.create_index(
        "idx_sales_entries_customer",
        "sales_entries",
        ["customer_id"],
    )

    op.create_table(
        "sales_calendar_events",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "sales_entry_id",
            sa.UUID(),
            sa.ForeignKey("sales_entries.id"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index(
        "idx_sales_calendar_date",
        "sales_calendar_events",
        ["scheduled_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_sales_calendar_date",
        table_name="sales_calendar_events",
    )
    op.drop_table("sales_calendar_events")
    op.drop_index(
        "idx_sales_entries_customer",
        table_name="sales_entries",
    )
    op.drop_index(
        "idx_sales_entries_status",
        table_name="sales_entries",
    )
    op.drop_table("sales_entries")
