"""Bug #6 — synthetic phone fallback must always pass normalize_phone.

The prior fallback ``f"000{event['id'][-7:]}"`` produced strings like
``"000SoDqVvS"`` when a Stripe event id ended in alphanumerics — those
fail the strict 10-digit normalize_phone validator and crash the
checkout.session.completed handler for any Apple-Pay agreement signup
without an attached phone.

These tests assert that the new sha256-derived synthetic always passes
the validator, is deterministic per event id, and stays within the
10-digit window.

Validates: ``.agents/plans/master-plan-run-findings-bug-resolution-2026-05-04.md``
Phase 1 / Task 1.6.
"""

from __future__ import annotations

import string

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.api.v1.webhooks import _synthetic_phone_for_event
from grins_platform.schemas.customer import normalize_phone

pytestmark = pytest.mark.unit


_EVENT_ID_ALPHABET = string.ascii_letters + string.digits + "_"


class TestSyntheticPhoneForEvent:
    def test_known_event_id_is_stable(self) -> None:
        a = _synthetic_phone_for_event("evt_1TTOFlQDNzCTp6j5nSoDqVvS")
        b = _synthetic_phone_for_event("evt_1TTOFlQDNzCTp6j5nSoDqVvS")
        assert a == b
        assert len(a) == 10
        assert a.isdigit()

    def test_known_event_id_passes_normalize_phone(self) -> None:
        synthetic = _synthetic_phone_for_event("evt_1TTOFlQDNzCTp6j5nSoDqVvS")
        # normalize_phone returns the digits-only form. Must not raise.
        assert normalize_phone(synthetic) == synthetic

    def test_different_event_ids_typically_differ(self) -> None:
        # Not a guarantee — collisions in 10**10 are theoretically
        # possible — but two known-different strings must not collide
        # for our determinism guarantee to be useful.
        a = _synthetic_phone_for_event("evt_alpha")
        b = _synthetic_phone_for_event("evt_beta")
        assert a != b

    @given(
        event_id=st.text(
            alphabet=_EVENT_ID_ALPHABET,
            min_size=4,
            max_size=100,
        ),
    )
    @settings(max_examples=200, deadline=None)
    def test_synthetic_always_passes_normalize_phone(self, event_id: str) -> None:
        synthetic = _synthetic_phone_for_event(event_id)
        assert len(synthetic) == 10
        assert synthetic.isdigit()
        # normalize_phone raises ValueError if shape is wrong.
        assert normalize_phone(synthetic) == synthetic
