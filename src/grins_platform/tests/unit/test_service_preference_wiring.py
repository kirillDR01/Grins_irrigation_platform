"""
Unit tests for service preference wiring into job creation flow.

Tests _week_from_preference (preferred_week + preferred_date) and
_notes_from_preference on JobService.

Validates: CRM2 Requirements 7.2, 7.3
"""

from __future__ import annotations

from datetime import date

import pytest

from grins_platform.services.job_service import JobService


@pytest.mark.unit
class TestWeekFromPreference:
    """Tests for JobService._week_from_preference."""

    def test_preferred_week_populates_week_of(self) -> None:
        """preferred_week should be used to auto-populate Week_Of."""
        prefs = [
            {
                "service_type": "spring_startup",
                "preferred_week": "2026-04-06",  # Monday
                "preferred_date": None,
                "notes": None,
            }
        ]
        start, end = JobService._week_from_preference(prefs, "spring_startup")
        assert start == date(2026, 4, 6)  # Monday
        assert end == date(2026, 4, 12)  # Sunday

    def test_preferred_week_mid_week_aligns_to_monday(self) -> None:
        """preferred_week with a mid-week date should align to Monday."""
        prefs = [
            {
                "service_type": "fall_winterization",
                "preferred_week": "2026-10-14",  # Wednesday
                "notes": None,
            }
        ]
        start, end = JobService._week_from_preference(prefs, "fall_winterization")
        assert start == date(2026, 10, 12)  # Monday
        assert end == date(2026, 10, 18)  # Sunday

    def test_preferred_week_takes_priority_over_preferred_date(self) -> None:
        """preferred_week should be checked before preferred_date."""
        prefs = [
            {
                "service_type": "spring_startup",
                "preferred_week": "2026-04-06",
                "preferred_date": "2026-05-15",
                "notes": None,
            }
        ]
        start, end = JobService._week_from_preference(prefs, "spring_startup")
        # Should use preferred_week (April), not preferred_date (May)
        assert start == date(2026, 4, 6)
        assert end == date(2026, 4, 12)

    def test_falls_back_to_preferred_date_when_no_week(self) -> None:
        """When preferred_week is absent, preferred_date should be used."""
        prefs = [
            {
                "service_type": "spring_startup",
                "preferred_date": "2026-05-15",
                "notes": None,
            }
        ]
        start, end = JobService._week_from_preference(prefs, "spring_startup")
        assert start == date(2026, 5, 11)  # Monday of that week
        assert end == date(2026, 5, 17)  # Sunday

    def test_no_match_returns_none(self) -> None:
        """Non-matching service_type should return (None, None)."""
        prefs = [
            {
                "service_type": "spring_startup",
                "preferred_week": "2026-04-06",
            }
        ]
        start, end = JobService._week_from_preference(prefs, "fall_winterization")
        assert start is None
        assert end is None

    def test_empty_prefs_returns_none(self) -> None:
        """Empty or None prefs should return (None, None)."""
        assert JobService._week_from_preference(None, "spring_startup") == (None, None)
        assert JobService._week_from_preference([], "spring_startup") == (None, None)

    def test_case_insensitive_service_type_match(self) -> None:
        """Service type matching should be case-insensitive."""
        prefs = [
            {
                "service_type": "Spring_Startup",
                "preferred_week": "2026-04-06",
            }
        ]
        start, end = JobService._week_from_preference(prefs, "spring_startup")
        assert start == date(2026, 4, 6)

    def test_dict_format_prefs(self) -> None:
        """Legacy single-dict format should work."""
        prefs = {
            "service_type": "spring_startup",
            "preferred_week": "2026-04-06",
        }
        start, end = JobService._week_from_preference(prefs, "spring_startup")
        assert start == date(2026, 4, 6)
        assert end == date(2026, 4, 12)


@pytest.mark.unit
class TestNotesFromPreference:
    """Tests for JobService._notes_from_preference."""

    def test_returns_notes_for_matching_service_type(self) -> None:
        """Should return notes when service_type matches."""
        prefs = [
            {
                "service_type": "spring_startup",
                "notes": "Customer prefers morning visits",
            }
        ]
        result = JobService._notes_from_preference(prefs, "spring_startup")
        assert result == "Customer prefers morning visits"

    def test_returns_none_for_no_match(self) -> None:
        """Should return None when no service_type matches."""
        prefs = [
            {
                "service_type": "spring_startup",
                "notes": "Some notes",
            }
        ]
        result = JobService._notes_from_preference(prefs, "fall_winterization")
        assert result is None

    def test_returns_none_for_empty_notes(self) -> None:
        """Should return None when notes is empty or missing."""
        prefs = [
            {"service_type": "spring_startup", "notes": ""},
            {"service_type": "fall_winterization"},
        ]
        assert JobService._notes_from_preference(prefs, "spring_startup") is None
        assert JobService._notes_from_preference(prefs, "fall_winterization") is None

    def test_returns_none_for_empty_prefs(self) -> None:
        """Should return None for empty or None prefs."""
        assert JobService._notes_from_preference(None, "spring_startup") is None
        assert JobService._notes_from_preference([], "spring_startup") is None

    def test_case_insensitive_match(self) -> None:
        """Service type matching should be case-insensitive."""
        prefs = [
            {
                "service_type": "Spring_Startup",
                "notes": "HOA property - use side gate",
            }
        ]
        result = JobService._notes_from_preference(prefs, "spring_startup")
        assert result == "HOA property - use side gate"

    def test_dict_format_prefs(self) -> None:
        """Legacy single-dict format should work."""
        prefs = {
            "service_type": "spring_startup",
            "notes": "Ring doorbell on arrival",
        }
        result = JobService._notes_from_preference(prefs, "spring_startup")
        assert result == "Ring doorbell on arrival"
