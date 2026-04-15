"""Property-based tests for poll reply parser.

Property 2: Valid-key round-trip — any valid key K parses correctly,
            including whitespace/punctuation and "Option N" variants.
Property 3: Idempotence — parsing same input twice gives identical results.
Property 4: Rejects unrecognized input — non-digit, non-"Option N" → needs_review.

Validates: Requirements 4.1, 4.2, 4.3, 4.5, 17.4, 17.5
"""

from __future__ import annotations

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.campaign_response_service import (
    CampaignResponseService,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_WHITESPACE = st.sampled_from(["", " ", "  ", "\t", "\n", " \n "])
_PUNCTUATION = st.sampled_from(["", ".", "!", "?", ",", "!!", "..", ")"])


def _make_options(count: int) -> list[dict[str, str]]:
    """Build a poll_options list with *count* sequential keys."""
    return [{"key": str(i), "label": f"Week {i}"} for i in range(1, count + 1)]


# Strategy: generate a valid option count (2-5) and a key within range
@st.composite
def valid_key_and_options(draw: st.DrawFn) -> tuple[str, list[dict[str, str]]]:
    count = draw(st.integers(min_value=2, max_value=5))
    key = draw(st.integers(min_value=1, max_value=count))
    return str(key), _make_options(count)


# Strategy: non-digit, non-"option N" text that should be rejected
_UNRECOGNIZED = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(categories=["L"]),  # letters only
).filter(lambda s: not s.lower().startswith("option"))


# ---------------------------------------------------------------------------
# Property 2: Valid-key round-trip
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReplyParserValidKeyRoundTrip:
    """Property 2 — valid key always parses correctly."""

    @given(data=valid_key_and_options())
    @settings(max_examples=50)
    def test_bare_digit_parses(
        self,
        data: tuple[str, list[dict[str, str]]],
    ) -> None:
        key, options = data
        result = CampaignResponseService.parse_poll_reply(key, options)
        assert result.ok is True
        assert result.option_key == key
        assert result.option_label == f"Week {key}"

    @given(
        data=valid_key_and_options(),
        leading=_WHITESPACE,
        trailing=_WHITESPACE,
        trail_punct=_PUNCTUATION,
    )
    @settings(max_examples=50)
    def test_digit_with_whitespace_and_punctuation(
        self,
        data: tuple[str, list[dict[str, str]]],
        leading: str,
        trailing: str,
        trail_punct: str,
    ) -> None:
        key, options = data
        body = f"{leading}{key}{trailing}{trail_punct}"
        result = CampaignResponseService.parse_poll_reply(body, options)
        assert result.ok is True
        assert result.option_key == key

    @given(data=valid_key_and_options())
    @settings(max_examples=30)
    def test_option_n_format(
        self,
        data: tuple[str, list[dict[str, str]]],
    ) -> None:
        key, options = data
        body = f"Option {key}"
        result = CampaignResponseService.parse_poll_reply(body, options)
        assert result.ok is True
        assert result.option_key == key

    @given(data=valid_key_and_options())
    @settings(max_examples=30)
    def test_option_n_case_insensitive(
        self,
        data: tuple[str, list[dict[str, str]]],
    ) -> None:
        key, options = data
        body = f"OPTION {key}"
        result = CampaignResponseService.parse_poll_reply(body, options)
        assert result.ok is True
        assert result.option_key == key


# ---------------------------------------------------------------------------
# Property 3: Idempotence
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReplyParserIdempotence:
    """Property 3 — parsing same input twice gives identical results."""

    @given(
        data=valid_key_and_options(),
        leading=_WHITESPACE,
        trail_punct=_PUNCTUATION,
    )
    @settings(max_examples=50)
    def test_parsed_result_is_idempotent(
        self,
        data: tuple[str, list[dict[str, str]]],
        leading: str,
        trail_punct: str,
    ) -> None:
        key, options = data
        body = f"{leading}{key}{trail_punct}"
        r1 = CampaignResponseService.parse_poll_reply(body, options)
        r2 = CampaignResponseService.parse_poll_reply(body, options)
        assert r1 == r2

    @given(body=_UNRECOGNIZED)
    @settings(max_examples=30)
    def test_rejected_result_is_idempotent(
        self,
        body: str,
    ) -> None:
        options = _make_options(3)
        r1 = CampaignResponseService.parse_poll_reply(body, options)
        r2 = CampaignResponseService.parse_poll_reply(body, options)
        assert r1 == r2


# ---------------------------------------------------------------------------
# Property 4: Rejects unrecognized input
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReplyParserRejectsUnrecognized:
    """Property 4 — non-digit, non-'Option N' → needs_review (ok=False)."""

    @given(body=_UNRECOGNIZED)
    @settings(max_examples=50)
    def test_letter_strings_rejected(
        self,
        body: str,
    ) -> None:
        options = _make_options(3)
        result = CampaignResponseService.parse_poll_reply(body, options)
        assert result.ok is False
        assert result.option_key is None

    @given(
        count=st.integers(min_value=2, max_value=5),
        digit=st.integers(min_value=6, max_value=9),
    )
    @settings(max_examples=30)
    def test_out_of_range_digit_rejected(
        self,
        count: int,
        digit: int,
    ) -> None:
        options = _make_options(count)
        result = CampaignResponseService.parse_poll_reply(str(digit), options)
        assert result.ok is False

    def test_empty_string_rejected(self) -> None:
        options = _make_options(3)
        result = CampaignResponseService.parse_poll_reply("", options)
        assert result.ok is False

    def test_zero_rejected(self) -> None:
        options = _make_options(3)
        result = CampaignResponseService.parse_poll_reply("0", options)
        assert result.ok is False

    @given(body=st.text(min_size=2, max_size=20, alphabet="abcdefghijklmnop"))
    @settings(max_examples=30)
    def test_multi_char_non_option_rejected(self, body: str) -> None:
        options = _make_options(3)
        result = CampaignResponseService.parse_poll_reply(body, options)
        assert result.ok is False
