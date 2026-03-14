"""Property-based tests for SurchargeCalculator.

Properties 5, 6, 7 from the integration gaps spec.

Validates: Requirements 3.2-3.10
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.surcharge_calculator import SurchargeCalculator

_TIER_SLUGS = {
    ("standard", "residential"): [
        "essential-residential",
        "professional-residential",
        "premium-residential",
    ],
    ("standard", "commercial"): [
        "essential-commercial",
        "professional-commercial",
        "premium-commercial",
    ],
    ("winterization-only", "residential"): ["winterization-only-residential"],
    ("winterization-only", "commercial"): ["winterization-only-commercial"],
}

_ZONE_RATES: dict[tuple[str, str], Decimal] = {
    ("standard", "residential"): Decimal("7.50"),
    ("standard", "commercial"): Decimal("10.00"),
    ("winterization-only", "residential"): Decimal("5.00"),
    ("winterization-only", "commercial"): Decimal("10.00"),
}

_LAKE_RATES: dict[tuple[str, str], Decimal] = {
    ("standard", "residential"): Decimal("175.00"),
    ("standard", "commercial"): Decimal("200.00"),
    ("winterization-only", "residential"): Decimal("75.00"),
    ("winterization-only", "commercial"): Decimal("100.00"),
}

tier_category_st = st.sampled_from(["standard", "winterization-only"])
package_type_st = st.sampled_from(["residential", "commercial"])
zone_count_st = st.integers(min_value=1, max_value=200)
base_price_st = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("9999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


def _pick_slug(tier_category: str, package_type: str) -> str:
    return _TIER_SLUGS[(tier_category, package_type)][0]


@pytest.mark.unit
class TestSurchargeZoneFormula:
    """Property 5: Zone surcharge formula correctness."""

    @given(
        tier_category=tier_category_st,
        package_type=package_type_st,
        zone_count=zone_count_st,
        has_lake_pump=st.booleans(),
        has_rpz_backflow=st.booleans(),
        base_price=base_price_st,
    )
    @settings(max_examples=200)
    def test_zone_surcharge_formula(
        self,
        tier_category: str,
        package_type: str,
        zone_count: int,
        has_lake_pump: bool,
        has_rpz_backflow: bool,
        base_price: Decimal,
    ) -> None:
        """Zone surcharge == rate x max(0, zone_count - 9) when >= 10, else 0."""
        slug = _pick_slug(tier_category, package_type)
        result = SurchargeCalculator.calculate(
            slug,
            package_type,
            zone_count,
            has_lake_pump,
            base_price,
            has_rpz_backflow=has_rpz_backflow,
        )
        rate = _ZONE_RATES[(tier_category, package_type)]
        expected = rate * Decimal(zone_count - 9) if zone_count >= 10 else Decimal(0)
        assert result.zone_surcharge == expected


@pytest.mark.unit
class TestSurchargeLakePump:
    """Property 6: Lake pump surcharge correctness."""

    @given(
        tier_category=tier_category_st,
        package_type=package_type_st,
        zone_count=zone_count_st,
        has_lake_pump=st.booleans(),
        has_rpz_backflow=st.booleans(),
        base_price=base_price_st,
    )
    @settings(max_examples=200)
    def test_lake_pump_surcharge(
        self,
        tier_category: str,
        package_type: str,
        zone_count: int,
        has_lake_pump: bool,
        has_rpz_backflow: bool,
        base_price: Decimal,
    ) -> None:
        """Lake pump surcharge == rate when has_lake_pump, else 0."""
        slug = _pick_slug(tier_category, package_type)
        result = SurchargeCalculator.calculate(
            slug,
            package_type,
            zone_count,
            has_lake_pump,
            base_price,
            has_rpz_backflow=has_rpz_backflow,
        )
        rate = _LAKE_RATES[(tier_category, package_type)]
        expected = rate if has_lake_pump else Decimal(0)
        assert result.lake_pump_surcharge == expected


@pytest.mark.unit
class TestSurchargeTotalSum:
    """Property 7: Total is sum of parts."""

    @given(
        tier_category=tier_category_st,
        package_type=package_type_st,
        zone_count=zone_count_st,
        has_lake_pump=st.booleans(),
        has_rpz_backflow=st.booleans(),
        base_price=base_price_st,
    )
    @settings(max_examples=200)
    def test_total_is_sum(
        self,
        tier_category: str,
        package_type: str,
        zone_count: int,
        has_lake_pump: bool,
        has_rpz_backflow: bool,
        base_price: Decimal,
    ) -> None:
        """total == base_price + zone + lake_pump + rpz_backflow surcharges."""
        slug = _pick_slug(tier_category, package_type)
        result = SurchargeCalculator.calculate(
            slug,
            package_type,
            zone_count,
            has_lake_pump,
            base_price,
            has_rpz_backflow=has_rpz_backflow,
        )
        assert result.total == (
            result.base_price
            + result.zone_surcharge
            + result.lake_pump_surcharge
            + result.rpz_backflow_surcharge
        )


@pytest.mark.unit
class TestSurchargeRpzBackflow:
    """Property 8: RPZ/backflow surcharge correctness."""

    @given(
        tier_category=tier_category_st,
        package_type=package_type_st,
        zone_count=zone_count_st,
        has_lake_pump=st.booleans(),
        has_rpz_backflow=st.booleans(),
        base_price=base_price_st,
    )
    @settings(max_examples=200)
    def test_rpz_backflow_surcharge(
        self,
        tier_category: str,
        package_type: str,
        zone_count: int,
        has_lake_pump: bool,
        has_rpz_backflow: bool,
        base_price: Decimal,
    ) -> None:
        """RPZ/backflow surcharge == $50 when has_rpz_backflow, else 0."""
        slug = _pick_slug(tier_category, package_type)
        result = SurchargeCalculator.calculate(
            slug,
            package_type,
            zone_count,
            has_lake_pump,
            base_price,
            has_rpz_backflow=has_rpz_backflow,
        )
        expected = Decimal("50.00") if has_rpz_backflow else Decimal(0)
        assert result.rpz_backflow_surcharge == expected
