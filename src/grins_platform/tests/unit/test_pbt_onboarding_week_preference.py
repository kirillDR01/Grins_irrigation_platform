"""Property-based tests for onboarding week preference round-trip.

Validates: Requirements 30.6
Property 17: generate_jobs(preferences).week_of_display == preferences.values()
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.job_generator import JobGenerator
from grins_platform.utils.week_alignment import align_to_week

_resolve_dates = JobGenerator._resolve_dates

# Mondays in a realistic range
_mondays = st.dates(
    min_value=date(2024, 1, 1),
    max_value=date(2030, 12, 31),
).filter(lambda d: d.weekday() == 0)

# Job types used in the tier maps
_job_types = st.sampled_from(
    [
        "spring_startup",
        "mid_season_inspection",
        "monthly_visit",
        "fall_winterization",
    ],
)

_months = st.integers(min_value=1, max_value=12)
_years = st.integers(min_value=2024, max_value=2030)


@pytest.mark.unit
class TestOnboardingWeekPreferenceRoundTrip:
    """Property 17: Onboarding Week Preference Round-Trip — Req 30.6."""

    @given(job_type=_job_types, monday=_mondays, month=_months, year=_years)
    @settings(max_examples=200)
    def test_plain_key_round_trip(
        self,
        job_type: str,
        monday: date,
        month: int,
        year: int,
    ) -> None:
        """Week preference keyed by job_type produces matching align_to_week dates."""
        prefs = {job_type: monday.isoformat()}
        start, end = _resolve_dates(job_type, month, month, year, prefs)
        expected_start, expected_end = align_to_week(monday)
        assert start == expected_start
        assert end == expected_end

    @given(monday=_mondays, month=_months, year=_years)
    @settings(max_examples=200)
    def test_month_qualified_key_round_trip(
        self,
        monday: date,
        month: int,
        year: int,
    ) -> None:
        """Month-qualified key (e.g. monthly_visit_5) takes precedence."""
        job_type = "monthly_visit"
        qualified_key = f"{job_type}_{month}"
        prefs = {qualified_key: monday.isoformat()}
        start, end = _resolve_dates(job_type, month, month, year, prefs)
        expected_start, expected_end = align_to_week(monday)
        assert start == expected_start
        assert end == expected_end

    @given(monday=_mondays, other_monday=_mondays, month=_months, year=_years)
    @settings(max_examples=200)
    def test_month_qualified_key_overrides_plain(
        self,
        monday: date,
        other_monday: date,
        month: int,
        year: int,
    ) -> None:
        """Month-qualified key wins over plain job_type key."""
        job_type = "monthly_visit"
        qualified_key = f"{job_type}_{month}"
        prefs = {job_type: other_monday.isoformat(), qualified_key: monday.isoformat()}
        start, end = _resolve_dates(job_type, month, month, year, prefs)
        expected_start, expected_end = align_to_week(monday)
        assert start == expected_start
        assert end == expected_end

    @given(job_type=_job_types, month=_months, year=_years)
    @settings(max_examples=200)
    def test_no_preference_falls_back_to_calendar_month(
        self,
        job_type: str,
        month: int,
        year: int,
    ) -> None:
        """Empty preferences fall back to calendar-month default."""
        start, end = _resolve_dates(job_type, month, month, year, {})
        assert start == date(year, month, 1)
        assert end.month == month
        assert end.day >= 28  # last day of month

    @given(job_type=_job_types, monday=_mondays, month=_months, year=_years)
    @settings(max_examples=200)
    def test_result_is_always_monday_to_sunday(
        self,
        job_type: str,
        monday: date,
        month: int,
        year: int,
    ) -> None:
        """When preference is used, result is always Monday-Sunday."""
        prefs = {job_type: monday.isoformat()}
        start, end = _resolve_dates(job_type, month, month, year, prefs)
        assert start.weekday() == 0
        assert end.weekday() == 6
        assert end == start + timedelta(days=6)
