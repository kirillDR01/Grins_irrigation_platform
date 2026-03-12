"""Populate stripe_product_id and stripe_price_id on service_agreement_tiers.

Revision ID: 20250710_100600
Revises: 20250710_100500
Create Date: 2025-07-10 10:06:00

Sets the Stripe test-mode product and price IDs for all 6 standard tiers
so that checkout session creation can resolve pricing.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20250710_100600"
down_revision: Union[str, None] = "20250710_100500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIER_STRIPE_IDS = [
    ("essential-residential", "prod_U6ibkYyfakHQE3", "price_1T8VAUQDNzCTp6j5KkRRR2j4"),
    ("essential-commercial", "prod_U6idaMQy8AHkat", "price_1T9xk7QDNzCTp6j5u3ARHZK8"),
    ("professional-residential", "prod_U6icBhfGIvzqLx", "price_1T8VBBQDNzCTp6j5RDWwuY9S"),
    ("professional-commercial", "prod_U6ifaZT4doEALs", "price_1T8VDzQDNzCTp6j5GQckAY7A"),
    ("premium-residential", "prod_U6icN6YaatjlVG", "price_1T8VBZQDNzCTp6j5xmutCMnv"),
    ("premium-commercial", "prod_U6ihXIsrjf83X4", "price_1T9xk7QDNzCTp6j5Qop1Et78"),
]


def upgrade() -> None:
    """Set Stripe product and price IDs for all 6 standard tiers."""
    for slug, product_id, price_id in TIER_STRIPE_IDS:
        op.execute(
            f"UPDATE service_agreement_tiers "
            f"SET stripe_product_id = '{product_id}', stripe_price_id = '{price_id}' "
            f"WHERE slug = '{slug}'"
        )


def downgrade() -> None:
    """Clear Stripe product and price IDs."""
    for slug, _, _ in TIER_STRIPE_IDS:
        op.execute(
            f"UPDATE service_agreement_tiers "
            f"SET stripe_product_id = NULL, stripe_price_id = NULL "
            f"WHERE slug = '{slug}'"
        )
