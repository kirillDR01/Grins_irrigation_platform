"""Unit tests for ``PriceListExportService``.

Validates: appointment-modal umbrella plan Phase 2 / Task 2.7 / P8.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.services.price_list_export_service import (
    PriceListExportService,
    _format_currency,
    _summarize_pricing_rule,
)


def _offering(
    *,
    name: str,
    category: str,
    customer_type: str | None,
    pricing_model: str,
    pricing_rule: dict[str, object] | None = None,
    display_name: str | None = None,
    includes_materials: bool = False,
    is_active: bool = True,
) -> SimpleNamespace:
    """Mimic ``ServiceOffering`` for the rendering loop."""
    return SimpleNamespace(
        name=name,
        display_name=display_name,
        category=category,
        customer_type=customer_type,
        pricing_model=pricing_model,
        pricing_rule=pricing_rule,
        includes_materials=includes_materials,
        is_active=is_active,
        updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )


def _stub_session(offerings: list[SimpleNamespace]) -> AsyncMock:
    scalars = MagicMock()
    scalars.all.return_value = offerings
    result = MagicMock()
    result.scalars.return_value = scalars
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.unit
class TestFormatCurrency:
    def test_int_renders_two_decimals(self) -> None:
        assert _format_currency(199) == "$199.00"

    def test_string_number(self) -> None:
        assert _format_currency("100.5") == "$100.50"

    def test_non_numeric_string_passes_through(self) -> None:
        assert _format_currency("custom") == "custom"

    def test_none(self) -> None:
        assert _format_currency(None) == "—"


@pytest.mark.unit
class TestSummarizePricingRule:
    def test_flat(self) -> None:
        assert _summarize_pricing_rule("flat", {"price": 199}) == "$199.00"

    def test_flat_range(self) -> None:
        out = _summarize_pricing_rule(
            "flat_range",
            {"price_min": 100, "price_max": 250},
        )
        assert out == "$100.00 - $250.00"

    def test_per_unit_flat_with_unit(self) -> None:
        out = _summarize_pricing_rule(
            "per_unit_flat",
            {"price_per_unit": 5.5, "unit": "ft"},
        )
        assert out == "$5.50 / ft"

    def test_per_zone_range(self) -> None:
        out = _summarize_pricing_rule(
            "per_zone_range",
            {"price_per_zone_min": 50, "price_per_zone_max": 75},
        )
        assert out == "$50.00 - $75.00 / zone"

    def test_hourly(self) -> None:
        out = _summarize_pricing_rule("hourly", {"price_per_hour": 95})
        assert out == "$95.00 / hr"

    def test_conditional_fee_with_default_waiver(self) -> None:
        out = _summarize_pricing_rule("conditional_fee", {"price": 89})
        assert "$89.00" in out and "waived" in out

    def test_none_rule(self) -> None:
        assert _summarize_pricing_rule("flat", None) == "—"

    def test_unknown_model_falls_back_to_keys(self) -> None:
        out = _summarize_pricing_rule(
            "tiered_zone_step",
            {"step_one": 100, "step_two": 50, "range_anchors": {"low": 1}},
        )
        # range_anchors is filtered; numeric keys render.
        assert "step_one=$100.00" in out


@pytest.mark.unit
class TestPriceListExportService:
    @pytest.mark.asyncio
    async def test_empty_returns_empty_doc(self) -> None:
        session = _stub_session([])
        out = await PriceListExportService(session=session).export_to_markdown()
        assert "No active offerings" in out
        assert "Pricelist" in out

    @pytest.mark.asyncio
    async def test_groups_by_customer_type_then_category(self) -> None:
        offerings = [
            _offering(
                name="Spring Start-Up",
                display_name="Spring Start-Up",
                category="seasonal",
                customer_type="residential",
                pricing_model="flat",
                pricing_rule={"price": 199},
            ),
            _offering(
                name="Backflow Test",
                category="diagnostic",
                customer_type="residential",
                pricing_model="flat",
                pricing_rule={"price": 95},
            ),
            _offering(
                name="Drip Install",
                category="installation",
                customer_type="commercial",
                pricing_model="per_zone_range",
                pricing_rule={"price_per_zone_min": 200, "price_per_zone_max": 300},
                includes_materials=True,
            ),
        ]
        session = _stub_session(offerings)
        out = await PriceListExportService(session=session).export_to_markdown()
        assert "## Residential" in out
        assert "## Commercial" in out
        # Headers are alphabetised within a customer-type bucket.
        res_index = out.index("## Residential")
        com_index = out.index("## Commercial")
        assert res_index < com_index
        # Materials column rendering.
        assert "yes" in out.split("## Commercial", 1)[1]

    @pytest.mark.asyncio
    async def test_uses_display_name_when_set(self) -> None:
        offerings = [
            _offering(
                name="canonical",
                display_name="Pretty Display",
                category="seasonal",
                customer_type="residential",
                pricing_model="flat",
                pricing_rule={"price": 1},
            ),
        ]
        out = await PriceListExportService(
            session=_stub_session(offerings),
        ).export_to_markdown()
        assert "Pretty Display" in out
        assert "canonical" not in out

    @pytest.mark.asyncio
    async def test_unset_customer_type_renders_other_section(self) -> None:
        offerings = [
            _offering(
                name="Misc",
                category="repair",
                customer_type=None,
                pricing_model="flat",
                pricing_rule={"price": 50},
            ),
        ]
        out = await PriceListExportService(
            session=_stub_session(offerings),
        ).export_to_markdown()
        assert "## Other" in out
