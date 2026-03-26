"""Update base prices and Stripe price IDs for all 8 tiers.

Revision ID: 20260325_100000
Revises: 20260324_100200
Create Date: 2026-03-25

Updates annual_price and stripe_price_id for all 8 service agreement tiers
to reflect the new pricing structure effective March 2026.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260325_100000"
down_revision: Union[str, None] = "20260324_100200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (slug, new_annual_price, new_stripe_price_id, old_annual_price, old_stripe_price_id)
TIER_UPDATES = [
    ("essential-residential", "175.00", "price_1TF2nBQDNzCTp6j5u43DTExH", "179.00", "price_1T8VAUQDNzCTp6j5KkRRR2j4"),
    ("professional-residential", "260.00", "price_1TF2nCQDNzCTp6j5sIB9OSH4", "259.00", "price_1T8VBBQDNzCTp6j5RDWwuY9S"),
    ("premium-residential", "725.00", "price_1TF2nCQDNzCTp6j5SC24GCKa", "709.00", "price_1T8VBZQDNzCTp6j5xmutCMnv"),
    ("winterization-only-residential", "85.00", "price_1TF2nDQDNzCTp6j5KmY0goPa", "89.00", "price_1T9xqeQDNzCTp6j5MNW1NtBn"),
    ("essential-commercial", "235.00", "price_1TF2nEQDNzCTp6j53W5uUqfi", "229.00", "price_1T9xk7QDNzCTp6j5u3ARHZK8"),
    ("professional-commercial", "390.00", "price_1TF2nFQDNzCTp6j5rhmqYTlJ", "379.00", "price_1T8VDzQDNzCTp6j5GQckAY7A"),
    ("premium-commercial", "880.00", "price_1TF2nGQDNzCTp6j5zWieKL0w", "859.00", "price_1T9xk7QDNzCTp6j5Qop1Et78"),
    ("winterization-only-commercial", "105.00", "price_1TF2nGQDNzCTp6j5Cieln9IO", "109.00", "price_1T9xqfQDNzCTp6j5puTQTgYz"),
]


def upgrade() -> None:
    """Update annual prices and Stripe price IDs for all 8 tiers."""
    for slug, new_price, new_stripe_id, _, _ in TIER_UPDATES:
        op.execute(
            f"UPDATE service_agreement_tiers "
            f"SET annual_price = {new_price}, stripe_price_id = '{new_stripe_id}' "
            f"WHERE slug = '{slug}'",
        )


def downgrade() -> None:
    """Revert to previous prices and Stripe price IDs."""
    for slug, _, _, old_price, old_stripe_id in TIER_UPDATES:
        op.execute(
            f"UPDATE service_agreement_tiers "
            f"SET annual_price = {old_price}, stripe_price_id = '{old_stripe_id}' "
            f"WHERE slug = '{slug}'",
        )
