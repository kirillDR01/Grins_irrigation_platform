"""Unit tests for customer-facing SMS formatters.

Validates bughunt H-3 (weekday date format), L-4 (service type in
template), M-11 (portable time formatting — no %-I).
"""

from __future__ import annotations

from datetime import date, time

import pytest

from grins_platform.services.sms.formatters import (
    format_job_type_display,
    format_sms_date,
    format_sms_date_long,
    format_sms_time_12h,
    format_sms_time_window,
)


@pytest.mark.unit
class TestFormatSmsDate:
    def test_produces_weekday_month_day_form(self) -> None:
        assert format_sms_date(date(2026, 4, 21)) == "Tuesday, April 21"

    def test_single_digit_day_has_no_leading_zero(self) -> None:
        assert format_sms_date(date(2026, 4, 5)) == "Sunday, April 5"

    def test_end_of_month(self) -> None:
        assert format_sms_date(date(2026, 4, 30)) == "Thursday, April 30"

    def test_december(self) -> None:
        assert format_sms_date(date(2026, 12, 31)) == "Thursday, December 31"


@pytest.mark.unit
class TestFormatSmsDateLong:
    def test_includes_year(self) -> None:
        assert format_sms_date_long(date(2026, 4, 21)) == "Tuesday, April 21, 2026"


@pytest.mark.unit
class TestFormatSmsTime12h:
    def test_morning_hour(self) -> None:
        assert format_sms_time_12h(time(9, 0)) == "9:00 AM"

    def test_noon(self) -> None:
        assert format_sms_time_12h(time(12, 0)) == "12:00 PM"

    def test_afternoon(self) -> None:
        assert format_sms_time_12h(time(15, 30)) == "3:30 PM"

    def test_midnight(self) -> None:
        assert format_sms_time_12h(time(0, 0)) == "12:00 AM"

    def test_single_digit_hour_no_leading_zero(self) -> None:
        assert format_sms_time_12h(time(1, 5)) == "1:05 AM"

    def test_empty_string_for_none(self) -> None:
        assert format_sms_time_12h(None) == ""

    def test_accepts_string_input(self) -> None:
        assert format_sms_time_12h("14:45:00") == "2:45 PM"


@pytest.mark.unit
class TestFormatSmsTimeWindow:
    def test_both_bounds(self) -> None:
        result = format_sms_time_window(time(10, 0), time(12, 0))
        assert result == " between 10:00 AM and 12:00 PM"

    def test_only_start(self) -> None:
        assert format_sms_time_window(time(9, 0), None) == " at 9:00 AM"

    def test_neither(self) -> None:
        assert format_sms_time_window(None, None) == ""


@pytest.mark.unit
class TestFormatJobTypeDisplay:
    def test_underscore_to_title_case(self) -> None:
        assert format_job_type_display("spring_startup") == "Spring Startup"

    def test_single_word(self) -> None:
        assert format_job_type_display("winterization") == "Winterization"

    def test_empty_string_for_none(self) -> None:
        assert format_job_type_display(None) == ""

    def test_empty_string_for_empty(self) -> None:
        assert format_job_type_display("") == ""
