"""Property-based tests for Y/R/C confirmation keyword parser.

Validates: CRM Changes Update 2 Req 34.1, 34.2, 34.3, 34.4, 34.5
"""

from __future__ import annotations

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import ConfirmationKeyword
from grins_platform.services.job_confirmation_service import parse_confirmation_reply

# ---------------------------------------------------------------------------
# Known keyword sets
# ---------------------------------------------------------------------------

CONFIRM_KEYWORDS = [
    "y", "yes", "confirm", "confirmed", "ok", "okay", "yup", "yeah", "1",
]
RESCHEDULE_KEYWORDS = ["r", "reschedule", "different time", "change time", "2"]
CANCEL_KEYWORDS = ["c", "cancel"]
ALL_KNOWN_KEYWORDS = CONFIRM_KEYWORDS + RESCHEDULE_KEYWORDS + CANCEL_KEYWORDS

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

confirm_keywords = st.sampled_from(CONFIRM_KEYWORDS)
reschedule_keywords = st.sampled_from(RESCHEDULE_KEYWORDS)
cancel_keywords = st.sampled_from(CANCEL_KEYWORDS)
all_known_keywords = st.sampled_from(ALL_KNOWN_KEYWORDS)

# Whitespace padding strategy
whitespace = st.text(alphabet=" \t\n\r", min_size=0, max_size=5)

# Unknown inputs: text that doesn't match any known keyword after strip+lower
unknown_inputs = st.text(min_size=1, max_size=50).filter(
    lambda s: s.strip().lower() not in ALL_KNOWN_KEYWORDS,
)


# ===================================================================
# Property 8: Y/R/C Keyword Parser Completeness
# Validates: Req 34.1, 34.2, 34.3, 34.4
# ===================================================================


@pytest.mark.unit
class TestProperty8KeywordCompleteness:
    """All known keywords map correctly, unknown inputs return None."""

    @given(kw=confirm_keywords)
    @settings(max_examples=20)
    def test_confirm_keywords_map_to_confirm(self, kw: str) -> None:
        assert parse_confirmation_reply(kw) == ConfirmationKeyword.CONFIRM

    @given(kw=reschedule_keywords)
    @settings(max_examples=20)
    def test_reschedule_keywords_map_to_reschedule(self, kw: str) -> None:
        assert parse_confirmation_reply(kw) == ConfirmationKeyword.RESCHEDULE

    @given(kw=cancel_keywords)
    @settings(max_examples=20)
    def test_cancel_keywords_map_to_cancel(self, kw: str) -> None:
        assert parse_confirmation_reply(kw) == ConfirmationKeyword.CANCEL

    @given(text=unknown_inputs)
    @settings(max_examples=100)
    def test_unknown_input_returns_none(self, text: str) -> None:
        assert parse_confirmation_reply(text) is None


# ===================================================================
# Property 9: Y/R/C Parser Idempotency
# Validates: Req 34.5
# ===================================================================


@pytest.mark.unit
class TestProperty9ParserIdempotency:
    """parse(input) == parse(input) for any input."""

    @given(text=st.text(min_size=0, max_size=50))
    @settings(max_examples=200)
    def test_parse_is_idempotent(self, text: str) -> None:
        assert parse_confirmation_reply(text) == parse_confirmation_reply(text)


# ===================================================================
# Property 10: Y/R/C Parser Case Insensitivity
# Validates: Req 34.1, 34.2, 34.3
# ===================================================================


@pytest.mark.unit
class TestProperty10CaseInsensitivity:
    """parse(upper) == parse(lower) for all known keywords."""

    @given(kw=all_known_keywords)
    @settings(max_examples=50)
    def test_upper_equals_lower(self, kw: str) -> None:
        upper = parse_confirmation_reply(kw.upper())
        lower = parse_confirmation_reply(kw.lower())
        assert upper == lower

    @given(kw=all_known_keywords, pad_l=whitespace, pad_r=whitespace)
    @settings(max_examples=50)
    def test_whitespace_padding_ignored(
        self,
        kw: str,
        pad_l: str,
        pad_r: str,
    ) -> None:
        padded = parse_confirmation_reply(pad_l + kw + pad_r)
        assert padded == parse_confirmation_reply(kw)
