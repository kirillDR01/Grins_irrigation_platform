"""Create service_agreements table.

Revision ID: 20250702_100100
Revises: 20250702_100000
Create Date: 2025-07-02 10:01:00

Creates the service_agreements table with unique agreement_number,
foreign keys to customers, service_agreement_tiers, properties, and staff,
plus indexes on customer_id, tier_id, status, payment_status, renewal_date.

Validates: Requirements 2.1, 2.2, 2.5
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100100"
down_revision: Union[str, None] = "20250702_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create service_agreements table."""
    op.create_table(
        "service_agreements",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("agreement_number", sa.String(20), nullable=False, unique=True),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column(
            "tier_id",
            sa.UUID(),
            sa.ForeignKey("service_agreement_tiers.id"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            sa.UUID(),
            sa.ForeignKey("properties.id"),
            nullable=True,
        ),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column(
            "auto_renew",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "cancelled_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("pause_reason", sa.Text(), nullable=True),
        sa.Column("annual_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "payment_status",
            sa.String(20),
            nullable=False,
            server_default="current",
        ),
        sa.Column(
            "last_payment_date",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("last_payment_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "renewal_approved_by",
            sa.UUID(),
            sa.ForeignKey("staff.id"),
            nullable=True,
        ),
        sa.Column(
            "renewal_approved_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "consent_recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("consent_method", sa.String(50), nullable=True),
        sa.Column("disclosure_version", sa.String(50), nullable=True),
        sa.Column(
            "last_annual_notice_sent",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_renewal_notice_sent",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("cancellation_refund_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "cancellation_refund_processed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
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
        "ix_service_agreements_customer_id",
        "service_agreements",
        ["customer_id"],
    )
    op.create_index(
        "ix_service_agreements_tier_id",
        "service_agreements",
        ["tier_id"],
    )
    op.create_index(
        "ix_service_agreements_status",
        "service_agreements",
        ["status"],
    )
    op.create_index(
        "ix_service_agreements_payment_status",
        "service_agreements",
        ["payment_status"],
    )
    op.create_index(
        "ix_service_agreements_renewal_date",
        "service_agreements",
        ["renewal_date"],
    )


def downgrade() -> None:
    """Drop service_agreements table."""
    op.drop_index("ix_service_agreements_renewal_date", "service_agreements")
    op.drop_index("ix_service_agreements_payment_status", "service_agreements")
    op.drop_index("ix_service_agreements_status", "service_agreements")
    op.drop_index("ix_service_agreements_tier_id", "service_agreements")
    op.drop_index("ix_service_agreements_customer_id", "service_agreements")
    op.drop_table("service_agreements")
