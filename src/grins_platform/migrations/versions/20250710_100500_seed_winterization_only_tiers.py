"""Seed winterization-only tier records into service_agreement_tiers.

Revision ID: 20250710_100500
Revises: 20250710_100400
Create Date: 2025-07-10 10:05:00

Inserts two winterization-only tiers (residential and commercial) into
the service_agreement_tiers table.

Validates: Requirements 4.1
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250710_100500"
down_revision: Union[str, None] = "20250710_100400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed winterization-only tier records."""
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
        sa.column("is_active", sa.Boolean),
    )

    winterization_services = [
        {
            "service_type": "fall_winterization",
            "frequency": "1x",
            "description": "Fall system winterization and blowout",
        },
    ]

    op.bulk_insert(
        tiers_table,
        [
            {
                "name": "Winterization Only Residential",
                "slug": "winterization-only-residential",
                "description": "Single fall winterization for residential properties",
                "package_type": "residential",
                "annual_price": 80.00,
                "billing_frequency": "annual",
                "included_services": winterization_services,
                "perks": None,
                "display_order": 7,
                "is_active": True,
            },
            {
                "name": "Winterization Only Commercial",
                "slug": "winterization-only-commercial",
                "description": "Single fall winterization for commercial properties",
                "package_type": "commercial",
                "annual_price": 100.00,
                "billing_frequency": "annual",
                "included_services": winterization_services,
                "perks": None,
                "display_order": 8,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    """Remove winterization-only tier records."""
    op.execute(
        "DELETE FROM service_agreement_tiers "
        "WHERE slug IN ("
        "'winterization-only-residential', "
        "'winterization-only-commercial')",
    )
