"""Widen ck_service_offerings_pricing_model to cover Phase 1 PricingModel values.

The original ``service_offerings`` table created a CHECK constraint
restricting ``pricing_model`` to the four legacy values
(``flat``, ``zone_based``, ``hourly``, ``custom``). Phase 1 of the
appointment-modal umbrella plan extended :class:`PricingModel` to 19
values (range / per-unit / tiered / size-tier / variants / +materials /
conditional_fee), and the ``20260504_130000_seed_pricelist_from_viktor``
seed migration inserts rows using those new values. On any DB whose
constraint still reflects the legacy four, that seed fails with a
CheckViolationError.

Dev was unblocked manually during local debug (constraint dropped out of
band), which is why dev currently has no CHECK at all. This migration
restores the constraint everywhere with the widened value set, putting
fresh deploys, dev, and prod onto the same shape.

Revision ID: 20260505_130000
Revises: 20260505_120000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260505_130000"
down_revision: Union[str, None] = "20260505_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CONSTRAINT_NAME = "ck_service_offerings_pricing_model"

# Mirrors grins_platform.models.enums.PricingModel exactly.
_ALL_PRICING_MODELS: tuple[str, ...] = (
    # Legacy four.
    "flat",
    "zone_based",
    "hourly",
    "custom",
    # Phase 1 extensions.
    "flat_range",
    "per_unit_flat",
    "per_unit_range",
    "per_unit_flat_plus_materials",
    "per_zone_range",
    "tiered_zone_step",
    "tiered_linear",
    "compound_per_unit",
    "compound_repair",
    "size_tier",
    "size_tier_plus_materials",
    "yard_tier",
    "variants",
    "flat_plus_materials",
    "conditional_fee",
)

_LEGACY_PRICING_MODELS: tuple[str, ...] = (
    "flat",
    "zone_based",
    "hourly",
    "custom",
)


def _values_clause(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.execute(
        f"ALTER TABLE service_offerings DROP CONSTRAINT IF EXISTS {_CONSTRAINT_NAME}",
    )
    op.create_check_constraint(
        _CONSTRAINT_NAME,
        "service_offerings",
        f"pricing_model IN ({_values_clause(_ALL_PRICING_MODELS)})",
    )


def downgrade() -> None:
    op.execute(
        f"ALTER TABLE service_offerings DROP CONSTRAINT IF EXISTS {_CONSTRAINT_NAME}",
    )
    op.create_check_constraint(
        _CONSTRAINT_NAME,
        "service_offerings",
        f"pricing_model IN ({_values_clause(_LEGACY_PRICING_MODELS)})",
    )
