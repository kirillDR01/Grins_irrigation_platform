"""Unit tests for RateLimitTracker deserialization."""

from __future__ import annotations

import pytest

from grins_platform.services.sms.rate_limit_tracker import SMSRateLimitTracker


class TestRateLimitTrackerDeserialize:
    """Tests for _deserialize bounds checking."""

    def test_deserialize_valid(self) -> None:
        """Valid 5-part CSV deserializes correctly."""
        state = SMSRateLimitTracker._deserialize("100,5,1000,50,1700000000.0")
        assert state.hourly_allowed == 100
        assert state.hourly_used == 5
        assert state.daily_allowed == 1000
        assert state.daily_used == 50
        assert state.updated_at == 1700000000.0

    def test_deserialize_bytes(self) -> None:
        """Bytes input is decoded and deserialized."""
        state = SMSRateLimitTracker._deserialize(b"100,5,1000,50,1700000000.0")
        assert state.hourly_allowed == 100

    def test_deserialize_malformed_too_few_parts(self) -> None:
        """Fewer than 5 comma-separated parts raises ValueError."""
        with pytest.raises(ValueError, match="Malformed rate-limit state"):
            SMSRateLimitTracker._deserialize("bad")

    def test_deserialize_malformed_three_parts(self) -> None:
        """Three parts still raises ValueError."""
        with pytest.raises(ValueError, match="Malformed rate-limit state"):
            SMSRateLimitTracker._deserialize("1,2,3")

    def test_deserialize_empty_string(self) -> None:
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="Malformed rate-limit state"):
            SMSRateLimitTracker._deserialize("")
