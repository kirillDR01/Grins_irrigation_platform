"""Populate stripe_product_id and stripe_price_id for winterization-only tiers.

Revision ID: 20250710_100700
Revises: 20250710_100600
Create Date: 2025-07-10 10:07:00

Sets the Stripe test-mode product and price IDs for the 2 winterization-only
tiers seeded by migration 20250710_100500.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20250710_100700"
down_revision: Union[str, None] = "20250710_100600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIER_STRIPE_IDS = [
    (
        "winterization-only-residential",
        "prod_U8EJ1WraZBMrYV",
        "price_1T9xqeQDNzCTp6j5MNW1NtBn",
    ),
    (
        "winterization-only-commercial",
        "prod_U8EJGKEoPiYUWN",
        "price_1T9xqfQDNzCTp6j5puTQTgYz",
    ),
]


def upgrade() -> None:
    """Set Stripe product and price IDs for winterization-only tiers."""
    for slug, product_id, price_id in TIER_STRIPE_IDS:
        op.execute(
            f"UPDATE service_agreement_tiers "
            f"SET stripe_product_id = '{product_id}', stripe_price_id = '{price_id}' "
            f"WHERE slug = '{slug}'",
        )


def downgrade() -> None:
    """Clear Stripe product and price IDs for winterization-only tiers."""
    for slug, _, _ in TIER_STRIPE_IDS:
        op.execute(
            f"UPDATE service_agreement_tiers "
            f"SET stripe_product_id = NULL, stripe_price_id = NULL "
            f"WHERE slug = '{slug}'",
        )
