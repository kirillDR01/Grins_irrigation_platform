"""Property-based tests for Week Of date alignment.

Validates: Requirements 36.1, 36.2, 36.3
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.utils.week_alignment import align_to_week

_dates = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))

_mondays = _dates.filter(lambda d: d.weekday() == 0)


@pytest.mark.unit
class TestWeekOfDateAlignment:
    """Property 12: Week Of Date Alignment — Req 36.1, 36.2."""

    @given(d=_dates)
    @settings(max_examples=200)
    def test_start_is_monday(self, d: date) -> None:
        monday, _ = align_to_week(d)
        assert monday.weekday() == 0, f"{monday} is not a Monday"

    @given(d=_dates)
    @settings(max_examples=200)
    def test_end_is_sunday(self, d: date) -> None:
        _, sunday = align_to_week(d)
        assert sunday.weekday() == 6, f"{sunday} is not a Sunday"

    @given(d=_dates)
    @settings(max_examples=200)
    def test_end_equals_start_plus_six(self, d: date) -> None:
        monday, sunday = align_to_week(d)
        assert sunday == monday + timedelta(days=6)

    @given(d=_dates)
    @settings(max_examples=200)
    def test_input_within_range(self, d: date) -> None:
        monday, sunday = align_to_week(d)
        assert monday <= d <= sunday


@pytest.mark.unit
class TestWeekOfRoundTrip:
    """Property 13: Week Of Round-Trip — Req 36.3."""

    @given(monday=_mondays)
    @settings(max_examples=200)
    def test_monday_round_trip(self, monday: date) -> None:
        result_monday, result_sunday = align_to_week(monday)
        assert result_monday == monday
        assert result_sunday == monday + timedelta(days=6)
