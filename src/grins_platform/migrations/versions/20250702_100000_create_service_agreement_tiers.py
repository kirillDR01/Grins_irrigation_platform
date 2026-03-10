"""Create service_agreement_tiers table and seed 6 tier records.

Revision ID: 20250702_100000
Revises: 20250701_100000
Create Date: 2025-07-02 10:00:00

Creates the service_agreement_tiers table with unique slug constraint
and seeds 6 records: Essential/Professional/Premium x Residential/Commercial.

Validates: Requirements 1.1, 1.2, 1.3
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100000"
down_revision: Union[str, None] = "20250701_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create service_agreement_tiers table and seed data."""
    op.create_table(
        "service_agreement_tiers",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("package_type", sa.String(20), nullable=False),
        sa.Column("annual_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "billing_frequency",
            sa.String(20),
            nullable=False,
            server_default="annual",
        ),
        sa.Column("included_services", sa.JSON(), nullable=False),
        sa.Column("perks", sa.JSON(), nullable=True),
        sa.Column("stripe_product_id", sa.String(255), nullable=True),
        sa.Column("stripe_price_id", sa.String(255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("display_order", sa.Integer(), nullable=False),
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

    # Seed 6 tier records (Requirement 1.3)
    tiers_table = sa.table(
        "service_agreement_tiers",
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.Text),
        sa.column("package_type", sa.String),
        sa.column("annual_price", sa.Numeric),
        sa.column("billing_frequency", sa.String),
        sa.column("included_services", sa.JSON),
        sa.column("perks", sa.JSON),
        sa.column("display_order", sa.Integer),
    )

    essential_services = [
        {
            "service_type": "spring_startup",
            "frequency": "1x",
            "description": "Spring system activation and inspection",
        },
        {
            "service_type": "fall_winterization",
            "frequency": "1x",
            "description": "Fall system winterization and blowout",
        },
    ]
    professional_services = [
        *essential_services[:1],
        {
            "service_type": "mid_season_inspection",
            "frequency": "1x",
            "description": "Mid-season system inspection and adjustment",
        },
        *essential_services[1:],
    ]
    premium_services = [
        *essential_services[:1],
        {
            "service_type": "monthly_visit",
            "frequency": "5x",
            "description": "Monthly system check and adjustment (May-Sep)",
        },
        *essential_services[1:],
    ]

    op.bulk_insert(
        tiers_table,
        [
            {
                "name": "Essential",
                "slug": "essential-residential",
                "description": "Basic seasonal coverage for residential properties",
                "package_type": "residential",
                "annual_price": 170.00,
                "billing_frequency": "annual",
                "included_services": essential_services,
                "perks": ["Priority scheduling"],
                "display_order": 1,
            },
            {
                "name": "Essential",
                "slug": "essential-commercial",
                "description": "Basic seasonal coverage for commercial properties",
                "package_type": "commercial",
                "annual_price": 225.00,
                "billing_frequency": "annual",
                "included_services": essential_services,
                "perks": ["Priority scheduling"],
                "display_order": 2,
            },
            {
                "name": "Professional",
                "slug": "professional-residential",
                "description": (
                    "Enhanced coverage with mid-season"
                    " inspection for residential properties"
                ),
                "package_type": "residential",
                "annual_price": 250.00,
                "billing_frequency": "annual",
                "included_services": professional_services,
                "perks": ["Priority scheduling", "10% repair discount"],
                "display_order": 3,
            },
            {
                "name": "Professional",
                "slug": "professional-commercial",
                "description": (
                    "Enhanced coverage with mid-season"
                    " inspection for commercial properties"
                ),
                "package_type": "commercial",
                "annual_price": 375.00,
                "billing_frequency": "annual",
                "included_services": professional_services,
                "perks": ["Priority scheduling", "10% repair discount"],
                "display_order": 4,
            },
            {
                "name": "Premium",
                "slug": "premium-residential",
                "description": (
                    "Full-service coverage with monthly"
                    " visits for residential properties"
                ),
                "package_type": "residential",
                "annual_price": 700.00,
                "billing_frequency": "annual",
                "included_services": premium_services,
                "perks": [
                    "Priority scheduling",
                    "15% repair discount",
                    "Free emergency visits",
                ],
                "display_order": 5,
            },
            {
                "name": "Premium",
                "slug": "premium-commercial",
                "description": (
                    "Full-service coverage with monthly"
                    " visits for commercial properties"
                ),
                "package_type": "commercial",
                "annual_price": 850.00,
                "billing_frequency": "annual",
                "included_services": premium_services,
                "perks": [
                    "Priority scheduling",
                    "15% repair discount",
                    "Free emergency visits",
                ],
                "display_order": 6,
            },
        ],
    )


def downgrade() -> None:
    """Drop service_agreement_tiers table."""
    op.drop_table("service_agreement_tiers")
