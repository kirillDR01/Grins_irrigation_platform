"""Tests for Sprint 6 phone-normalization changes (bughunt M-5, L-13).

Covers:
- ``_phone_variants`` expansion so consent lookup matches hyphenated,
  parenthesized, dotted, and 11-digit stored forms.
- ``normalize_to_e164`` rejection of FCC 555-0100..555-0199 test
  numbers with the clearer range check.
"""

from __future__ import annotations

import pytest

from grins_platform.services.sms.consent import _phone_variants
from grins_platform.services.sms.phone_normalizer import (
    PhoneNormalizationError,
    normalize_to_e164,
)


@pytest.mark.unit
class TestPhoneVariants:
    """``_phone_variants`` must emit every form a legacy row might hold."""

    def test_e164_input_emits_all_formats(self) -> None:
        variants = _phone_variants("+16127385301")
        assert "+16127385301" in variants
        assert "6127385301" in variants
        assert "16127385301" in variants
        assert "612-738-5301" in variants
        assert "612.738.5301" in variants
        assert "(612) 738-5301" in variants
        assert "1-612-738-5301" in variants

    def test_parenthesized_input_is_normalized(self) -> None:
        """Non-E.164 input is normalized first, then expanded."""
        variants = _phone_variants("(612) 738-5301")
        assert "+16127385301" in variants
        assert "6127385301" in variants

    def test_hyphenated_11_digit_input_is_normalized(self) -> None:
        variants = _phone_variants("1-612-738-5301")
        assert "+16127385301" in variants
        assert "1-612-738-5301" in variants

    def test_unparseable_input_returns_self(self) -> None:
        """Exotic inputs that normalize_to_e164 rejects are preserved
        verbatim so callers still get at least a self-match.
        """
        # Letters => normalize_to_e164 raises; fall back to [phone]
        variants = _phone_variants("not-a-phone")
        assert variants == ["not-a-phone"]


@pytest.mark.unit
class TestFccTestNumberRejection:
    """bughunt L-13: 555-0100..555-0199 is the FCC test range."""

    @pytest.mark.parametrize("subscriber", ["0100", "0150", "0199"])
    def test_in_range_rejected(self, subscriber: str) -> None:
        with pytest.raises(PhoneNormalizationError, match="Test number"):
            normalize_to_e164(f"952-555-{subscriber}")

    @pytest.mark.parametrize("subscriber", ["0099", "0200", "1234", "0000"])
    def test_out_of_range_accepted(self, subscriber: str) -> None:
        """Neighbours of the test range must normalize cleanly —
        only 0100..0199 is the FCC reserved block.
        """
        assert normalize_to_e164(f"952-555-{subscriber}") == f"+1952555{subscriber}"

    def test_other_exchange_not_rejected(self) -> None:
        """0100 as the subscriber doesn't block a non-555 exchange."""
        assert normalize_to_e164("952-444-0100") == "+19524440100"
