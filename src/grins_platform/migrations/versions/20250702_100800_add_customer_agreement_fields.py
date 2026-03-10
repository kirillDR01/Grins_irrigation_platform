"""Add service agreement fields to customers table.

Revision ID: 20250702_100800
Revises: 20250702_100700
Create Date: 2025-07-02 10:08:00

Adds stripe_customer_id, terms fields, SMS consent tracking,
preferred_service_times, internal_notes, and email opt-in tracking
to the customers table.

Validates: Requirements 28.1, 28.3, 68.1, 68.4
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100800"
down_revision: Union[str, None] = "20250702_100700"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add service agreement fields to customers table."""
    # Stripe integration
    op.add_column(
        "customers",
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_customers_stripe_customer_id",
        "customers",
        ["stripe_customer_id"],
        unique=True,
    )

    # Terms acceptance
    op.add_column(
        "customers",
        sa.Column(
            "terms_accepted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "customers",
        sa.Column("terms_accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("terms_version", sa.String(20), nullable=True),
    )

    # SMS consent tracking
    op.add_column(
        "customers",
        sa.Column("sms_opt_in_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("sms_opt_in_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("sms_consent_language_version", sa.String(20), nullable=True),
    )

    # Service preferences
    op.add_column(
        "customers",
        sa.Column("preferred_service_times", sa.JSON(), nullable=True),
    )

    # Staff-only notes
    op.add_column(
        "customers",
        sa.Column("internal_notes", sa.Text(), nullable=True),
    )

    # Email opt-in tracking (Req 68.1, 68.4)
    op.add_column(
        "customers",
        sa.Column("email_opt_in_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("email_opt_out_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("email_opt_in_source", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Remove service agreement fields from customers table."""
    op.drop_column("customers", "email_opt_in_source")
    op.drop_column("customers", "email_opt_out_at")
    op.drop_column("customers", "email_opt_in_at")
    op.drop_column("customers", "internal_notes")
    op.drop_column("customers", "preferred_service_times")
    op.drop_column("customers", "sms_consent_language_version")
    op.drop_column("customers", "sms_opt_in_source")
    op.drop_column("customers", "sms_opt_in_at")
    op.drop_column("customers", "terms_version")
    op.drop_column("customers", "terms_accepted_at")
    op.drop_column("customers", "terms_accepted")
    op.drop_index("ix_customers_stripe_customer_id", table_name="customers")
    op.drop_column("customers", "stripe_customer_id")
