"""Unit tests for SurchargeCalculator.

Tests specific examples and edge cases for all tier/package combinations.

Validates: Requirements 3.2-3.10
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from grins_platform.services.surcharge_calculator import (
    SurchargeBreakdown,
    SurchargeCalculator,
)


@pytest.mark.unit
class TestSurchargeCalculatorEdgeCases:
    """Edge cases for zone count thresholds."""

    def test_zone_count_1_no_surcharge(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-residential",
            "residential",
            1,
            False,
            Decimal("299.00"),
        )
        assert r.zone_surcharge == Decimal(0)
        assert r.lake_pump_surcharge == Decimal(0)
        assert r.total == Decimal("299.00")

    def test_zone_count_9_no_surcharge(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-residential",
            "residential",
            9,
            False,
            Decimal("299.00"),
        )
        assert r.zone_surcharge == Decimal(0)

    def test_zone_count_10_one_extra_zone(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-residential",
            "residential",
            10,
            False,
            Decimal("299.00"),
        )
        assert r.zone_surcharge == Decimal("7.50")

    def test_zone_count_100_many_extra_zones(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-residential",
            "residential",
            100,
            False,
            Decimal("299.00"),
        )
        # 91 extra zones x $7.50
        assert r.zone_surcharge == Decimal("682.50")


@pytest.mark.unit
class TestSurchargeCalculatorStandardResidential:
    """Standard residential tier rates: zone=$7.50, lake=$175."""

    def test_with_surcharges(self) -> None:
        r = SurchargeCalculator.calculate(
            "professional-residential",
            "residential",
            12,
            True,
            Decimal("499.00"),
        )
        assert r.zone_surcharge == Decimal("22.50")  # 3 x $7.50
        assert r.lake_pump_surcharge == Decimal("175.00")
        assert r.total == Decimal("696.50")

    def test_no_lake_pump(self) -> None:
        r = SurchargeCalculator.calculate(
            "premium-residential",
            "residential",
            15,
            False,
            Decimal("799.00"),
        )
        assert r.zone_surcharge == Decimal("45.00")  # 6 x $7.50
        assert r.lake_pump_surcharge == Decimal(0)
        assert r.total == Decimal("844.00")


@pytest.mark.unit
class TestSurchargeCalculatorStandardCommercial:
    """Standard commercial tier rates: zone=$10, lake=$200."""

    def test_with_surcharges(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-commercial",
            "commercial",
            11,
            True,
            Decimal("399.00"),
        )
        assert r.zone_surcharge == Decimal("20.00")  # 2 x $10
        assert r.lake_pump_surcharge == Decimal("200.00")
        assert r.total == Decimal("619.00")

    def test_no_lake_pump(self) -> None:
        r = SurchargeCalculator.calculate(
            "professional-commercial",
            "commercial",
            10,
            False,
            Decimal("599.00"),
        )
        assert r.zone_surcharge == Decimal("10.00")  # 1 x $10
        assert r.lake_pump_surcharge == Decimal(0)
        assert r.total == Decimal("609.00")


@pytest.mark.unit
class TestSurchargeCalculatorWinterizationResidential:
    """Winterization-only residential: zone=$5, lake=$75."""

    def test_with_surcharges(self) -> None:
        r = SurchargeCalculator.calculate(
            "winterization-only-residential",
            "residential",
            12,
            True,
            Decimal("80.00"),
        )
        assert r.zone_surcharge == Decimal("15.00")  # 3 x $5
        assert r.lake_pump_surcharge == Decimal("75.00")
        assert r.total == Decimal("170.00")

    def test_no_lake_pump(self) -> None:
        r = SurchargeCalculator.calculate(
            "winterization-only-residential",
            "residential",
            10,
            False,
            Decimal("80.00"),
        )
        assert r.zone_surcharge == Decimal("5.00")  # 1 x $5
        assert r.lake_pump_surcharge == Decimal(0)
        assert r.total == Decimal("85.00")


@pytest.mark.unit
class TestSurchargeCalculatorWinterizationCommercial:
    """Winterization-only commercial: zone=$10, lake=$100."""

    def test_with_surcharges(self) -> None:
        r = SurchargeCalculator.calculate(
            "winterization-only-commercial",
            "commercial",
            15,
            True,
            Decimal("100.00"),
        )
        assert r.zone_surcharge == Decimal("60.00")  # 6 x $10
        assert r.lake_pump_surcharge == Decimal("100.00")
        assert r.total == Decimal("260.00")

    def test_no_lake_pump(self) -> None:
        r = SurchargeCalculator.calculate(
            "winterization-only-commercial",
            "commercial",
            9,
            False,
            Decimal("100.00"),
        )
        assert r.zone_surcharge == Decimal(0)
        assert r.lake_pump_surcharge == Decimal(0)
        assert r.total == Decimal("100.00")


@pytest.mark.unit
class TestSurchargeBreakdownFrozen:
    """SurchargeBreakdown is immutable."""

    def test_frozen(self) -> None:
        b = SurchargeBreakdown(
            base_price=Decimal(100),
            zone_surcharge=Decimal(10),
            lake_pump_surcharge=Decimal(5),
            rpz_backflow_surcharge=Decimal(50),
        )
        with pytest.raises(AttributeError):
            b.base_price = Decimal(999)  # type: ignore[misc]


@pytest.mark.unit
class TestSurchargeCalculatorCaseInsensitive:
    """Package type is case-insensitive."""

    def test_uppercase_package_type(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-residential",
            "RESIDENTIAL",
            10,
            True,
            Decimal("299.00"),
        )
        assert r.zone_surcharge == Decimal("7.50")
        assert r.lake_pump_surcharge == Decimal("175.00")

    def test_mixed_case_package_type(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-commercial",
            "Commercial",
            10,
            False,
            Decimal("399.00"),
        )
        assert r.zone_surcharge == Decimal("10.00")


@pytest.mark.unit
class TestSurchargeCalculatorRpzBackflow:
    """RPZ/backflow surcharge: flat $50 across all tiers."""

    def test_rpz_backflow_standard_residential(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-residential",
            "residential",
            5,
            False,
            Decimal("299.00"),
            has_rpz_backflow=True,
        )
        assert r.rpz_backflow_surcharge == Decimal("50.00")
        assert r.total == Decimal("349.00")

    def test_rpz_backflow_standard_commercial(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-commercial",
            "commercial",
            5,
            False,
            Decimal("399.00"),
            has_rpz_backflow=True,
        )
        assert r.rpz_backflow_surcharge == Decimal("50.00")
        assert r.total == Decimal("449.00")

    def test_rpz_backflow_winterization_residential(self) -> None:
        r = SurchargeCalculator.calculate(
            "winterization-only-residential",
            "residential",
            5,
            False,
            Decimal("80.00"),
            has_rpz_backflow=True,
        )
        assert r.rpz_backflow_surcharge == Decimal("50.00")
        assert r.total == Decimal("130.00")

    def test_rpz_backflow_winterization_commercial(self) -> None:
        r = SurchargeCalculator.calculate(
            "winterization-only-commercial",
            "commercial",
            5,
            False,
            Decimal("100.00"),
            has_rpz_backflow=True,
        )
        assert r.rpz_backflow_surcharge == Decimal("50.00")
        assert r.total == Decimal("150.00")

    def test_no_rpz_backflow(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-residential",
            "residential",
            5,
            False,
            Decimal("299.00"),
            has_rpz_backflow=False,
        )
        assert r.rpz_backflow_surcharge == Decimal(0)
        assert r.total == Decimal("299.00")

    def test_rpz_backflow_default_false(self) -> None:
        r = SurchargeCalculator.calculate(
            "essential-residential",
            "residential",
            5,
            False,
            Decimal("299.00"),
        )
        assert r.rpz_backflow_surcharge == Decimal(0)

    def test_rpz_backflow_combined_with_all_surcharges(self) -> None:
        r = SurchargeCalculator.calculate(
            "professional-residential",
            "residential",
            12,
            True,
            Decimal("499.00"),
            has_rpz_backflow=True,
        )
        assert r.zone_surcharge == Decimal("22.50")  # 3 x $7.50
        assert r.lake_pump_surcharge == Decimal("175.00")
        assert r.rpz_backflow_surcharge == Decimal("50.00")
        assert r.total == Decimal("746.50")
