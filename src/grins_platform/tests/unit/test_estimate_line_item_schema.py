"""Unit tests for ``EstimateLineItem``.

Validates: appointment-modal umbrella plan Phase 3 / Task 3.1.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.schemas.estimate import EstimateLineItem


@pytest.mark.unit
class TestEstimateLineItemDefaults:
    """The new optional keys default to None / 0 so legacy rows keep parsing."""

    def test_legacy_payload_still_validates(self) -> None:
        # Legacy estimates persisted before Phase 3 used this exact shape.
        legacy = {
            "item": "Spring Start-Up",
            "description": "annual seasonal start-up",
            "quantity": 1,
            "unit_price": 199,
        }
        parsed = EstimateLineItem.model_validate(legacy)
        assert parsed.unit_cost is None
        assert parsed.service_offering_id is None
        assert parsed.material_markup_pct == Decimal(0)
        assert parsed.selected_tier is None

    def test_phase_3_payload_validates(self) -> None:
        oid = uuid4()
        payload = {
            "item": "Drip Install",
            "quantity": 4,
            "unit_price": 250,
            "service_offering_id": str(oid),
            "unit_cost": 80,
            "material_markup_pct": 25,
            "selected_tier": "mid",
        }
        parsed = EstimateLineItem.model_validate(payload)
        assert parsed.service_offering_id == oid
        assert parsed.unit_cost == Decimal(80)
        assert parsed.material_markup_pct == Decimal(25)
        assert parsed.selected_tier == "mid"


@pytest.mark.unit
class TestEstimateLineItemValidation:
    """Numeric guards keep bad data out without breaking inputs we accept."""

    def test_negative_unit_cost_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EstimateLineItem.model_validate({"unit_cost": -5})

    def test_markup_pct_capped_at_500(self) -> None:
        with pytest.raises(ValidationError):
            EstimateLineItem.model_validate({"material_markup_pct": 600})

    def test_extra_keys_preserved(self) -> None:
        # ``extra='allow'`` keeps any forward-compat keys round-tripping.
        parsed = EstimateLineItem.model_validate({"item": "x", "future_field": 1})
        assert parsed.model_dump()["future_field"] == 1
