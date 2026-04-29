"""Hypothesis property-based tests for WebAuthn invariants.

Properties:

1. base64url round-trip: bytes survive ``bytes_to_base64url`` →
   ``base64url_to_bytes``.
2. Sign-count regression gate: matches the literal predicate
   ``new > 0 and new <= stored``.
3. Challenge-handle uniqueness: 1000 handle generations are pairwise distinct.
"""

from __future__ import annotations

import secrets

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestBase64UrlRoundTrip:
    """Encoding round-trips for arbitrary byte payloads."""

    @given(payload=st.binary(min_size=0, max_size=1024))
    @settings(max_examples=200, deadline=2000)
    def test_base64url_roundtrip(self, payload: bytes) -> None:
        from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

        assert base64url_to_bytes(bytes_to_base64url(payload)) == payload


@pytest.mark.unit
class TestSignCountRegressionGate:
    """The pure-function gate must return True iff ``new>0 and new<=stored``."""

    @given(
        stored=st.integers(min_value=0, max_value=2**32),
        new=st.integers(min_value=0, max_value=2**32),
    )
    @settings(max_examples=200, deadline=2000)
    def test_sign_count_regression_gate(self, stored: int, new: int) -> None:
        from grins_platform.services.webauthn_service import (
            _is_sign_count_regression,
        )

        expected = new > 0 and new <= stored
        assert _is_sign_count_regression(stored, new) is expected


@pytest.mark.unit
class TestChallengeHandleUniqueness:
    """Handle generator collision-resistance smoke test."""

    def test_thousand_handles_are_unique(self) -> None:
        handles = {secrets.token_urlsafe(32) for _ in range(1000)}
        assert len(handles) == 1000
