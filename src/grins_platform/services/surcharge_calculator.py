"""Surcharge calculator for zone count and lake pump pricing.

Pure utility — no DB access, no side effects.

Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SurchargeBreakdown:
    """Immutable breakdown of surcharge components.

    Attributes:
        base_price: Tier base price before surcharges.
        zone_surcharge: Additional cost for zones >= 10.
        lake_pump_surcharge: Additional cost for lake pump systems.
    """

    base_price: Decimal
    zone_surcharge: Decimal
    lake_pump_surcharge: Decimal

    @property
    def total(self) -> Decimal:
        """Total price including all surcharges."""
        return self.base_price + self.zone_surcharge + self.lake_pump_surcharge


# (zone_rate_per_extra_zone, lake_pump_flat_rate)
_RATES: dict[tuple[str, str], tuple[Decimal, Decimal]] = {
    ("standard", "residential"): (Decimal("7.50"), Decimal("175.00")),
    ("standard", "commercial"): (Decimal("10.00"), Decimal("200.00")),
    ("winterization-only", "residential"): (Decimal("5.00"), Decimal("75.00")),
    ("winterization-only", "commercial"): (Decimal("10.00"), Decimal("100.00")),
}

_ZONE_THRESHOLD = 10
_INCLUDED_ZONES = 9


class SurchargeCalculator:
    """Computes zone and lake pump surcharges for service tiers.

    Validates: Requirements 3.2-3.10
    """

    @staticmethod
    def calculate(
        tier_slug: str,
        package_type: str,
        zone_count: int,
        has_lake_pump: bool,
        base_price: Decimal,
    ) -> SurchargeBreakdown:
        """Calculate surcharges for a given tier configuration.

        Args:
            tier_slug: Tier slug (e.g. "essential-residential").
            package_type: "residential" or "commercial" (case-insensitive).
            zone_count: Number of irrigation zones (>= 1).
            has_lake_pump: Whether property has a lake pump.
            base_price: Tier base annual price.

        Returns:
            SurchargeBreakdown with computed surcharges.
        """
        tier_category = (
            "winterization-only"
            if tier_slug.startswith("winterization-only-")
            else "standard"
        )
        pkg = package_type.lower()

        zone_rate, lake_pump_rate = _RATES.get(
            (tier_category, pkg),
            (Decimal(0), Decimal(0)),
        )

        zone_surcharge = (
            zone_rate * Decimal(max(0, zone_count - _INCLUDED_ZONES))
            if zone_count >= _ZONE_THRESHOLD
            else Decimal(0)
        )

        lake_pump_surcharge = lake_pump_rate if has_lake_pump else Decimal(0)

        return SurchargeBreakdown(
            base_price=base_price,
            zone_surcharge=zone_surcharge,
            lake_pump_surcharge=lake_pump_surcharge,
        )
