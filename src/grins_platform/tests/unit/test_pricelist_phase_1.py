"""Unit tests for the Phase 1 pricelist data-model extensions.

Validates: appointment-modal umbrella plan Phase 1 (Tasks 1.1, 1.4,
1.7 helpers).
"""

from __future__ import annotations

import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

from grins_platform.models.enums import PricingModel, ServiceCategory
from grins_platform.schemas.service_offering import (
    ServiceOfferingCreate,
    ServiceOfferingUpdate,
)


@pytest.mark.unit
class TestPricingModelEnumExtension:
    """Existing 4 values still parse, plus the 15 new variants are present."""

    def test_legacy_values_still_parse(self) -> None:
        for value in ("flat", "zone_based", "hourly", "custom"):
            assert PricingModel(value).value == value

    def test_extended_values_parse(self) -> None:
        for value in (
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
        ):
            assert PricingModel(value).value == value

    def test_total_member_count(self) -> None:
        # 4 legacy + 15 extended = 19 distinct members.
        assert len(list(PricingModel)) == 19


@pytest.mark.unit
class TestServiceOfferingSchemas:
    """Additive Optional fields keep existing payloads valid."""

    def test_create_without_new_fields_still_valid(self) -> None:
        # Existing API consumers don't pass any new fields.
        payload = ServiceOfferingCreate(
            name="Spring Start-Up",
            category=ServiceCategory.SEASONAL,
            pricing_model=PricingModel.FLAT,
            base_price=Decimal("199.00"),
        )
        assert payload.slug is None
        assert payload.customer_type is None
        assert payload.includes_materials is False

    def test_create_with_new_fields(self) -> None:
        payload = ServiceOfferingCreate(
            name="Spring Start-Up",
            category=ServiceCategory.SEASONAL,
            pricing_model=PricingModel.TIERED_ZONE_STEP,
            slug="spring_startup_residential",
            display_name="Spring Start-Up",
            customer_type="residential",
            subcategory="seasonal",
            pricing_rule={
                "base_amount": 175,
                "base_zones_included": 7,
                "additional_per_zone": 10,
            },
            includes_materials=False,
            source_text="$175 first 7 zones, +$10/zone above",
        )
        assert payload.customer_type == "residential"
        assert payload.pricing_rule is not None
        assert payload.pricing_rule["base_amount"] == 175

    def test_update_only_pricing_rule(self) -> None:
        payload = ServiceOfferingUpdate(
            pricing_rule={"price_min": 800, "price_max": 1000},
        )
        diff = payload.model_dump(exclude_unset=True)
        assert diff == {"pricing_rule": {"price_min": 800, "price_max": 1000}}

    def test_customer_type_rejects_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            ServiceOfferingCreate(
                name="X",
                category=ServiceCategory.LANDSCAPING,
                pricing_model=PricingModel.FLAT,
                customer_type="industrial",  # type: ignore[arg-type]
            )


def _load_seed_migration_module() -> ModuleType:
    """Dynamically load the seed migration module without alembic."""
    here = Path(__file__).resolve()
    repo_root = here.parents[4]
    migration_path = (
        repo_root
        / "src"
        / "grins_platform"
        / "migrations"
        / "versions"
        / "20260504_130000_seed_pricelist_from_viktor.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_seed_migration_test",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
class TestSeedMigrationHelpers:
    """The path-resolution + transformation helpers run without a DB."""

    def test_seed_path_resolves_to_real_file(self) -> None:
        module = _load_seed_migration_module()
        seed_path = module._resolve_seed_path()
        assert seed_path.exists(), seed_path

    def test_seed_keys_count_is_73(self) -> None:
        module = _load_seed_migration_module()
        keys = module._slug_keys()
        assert len(keys) == 73

    def test_pricing_rule_excludes_standard_fields(self) -> None:
        module = _load_seed_migration_module()
        item = {
            "key": "irrigation_install_residential",
            "name": "Irrigation System Installation",
            "category": "irrigation",
            "subcategory": "installation",
            "customer_type": "residential",
            "pricing_model": "per_zone_range",
            "source_text": "lorem",
            "price_per_zone_min": 800,
            "price_per_zone_max": 1000,
            "unit": "zone",
            "profile_factor": {"low_end": "x", "high_end": "y"},
            "includes": ["a", "b"],
        }
        rule = module._build_pricing_rule(item)
        assert "key" not in rule
        assert "name" not in rule
        assert "category" not in rule
        assert rule["price_per_zone_min"] == 800
        assert rule["price_per_zone_max"] == 1000
        assert rule["unit"] == "zone"

    def test_includes_materials_inferred_from_pricing_model(self) -> None:
        # Used inline in upgrade(); validate the suffix-based rule.
        module = _load_seed_migration_module()
        seed_file = module._resolve_seed_path()
        with seed_file.open() as f:
            data = json.load(f)
        plus_materials = [
            it
            for it in data["items"]
            if it["pricing_model"].endswith("_plus_materials")
        ]
        # Distribution: 12 per_unit_flat_plus_materials + 6
        # flat_plus_materials + 2 size_tier_plus_materials = 20.
        assert len(plus_materials) == 20
