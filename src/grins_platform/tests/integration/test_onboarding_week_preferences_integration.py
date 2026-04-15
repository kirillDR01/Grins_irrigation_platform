"""Integration tests for onboarding week preferences → job generation.

Exercises the full flow:
  1. Service agreement with service_week_preferences JSON
  2. Job generator creates jobs with correct Week_Of dates (Monday-Sunday)
  3. Fallback to calendar-month defaults when preferences are null/empty

Validates: CRM Changes Update 2 Req 30.3, 30.4, 30.6
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.services.job_generator import JobGenerator
from grins_platform.utils.week_alignment import align_to_week


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tier(name: str = "Essential", slug: str = "essential-residential") -> MagicMock:
    """Create a mock ServiceAgreementTier."""
    tier = MagicMock()
    tier.id = uuid4()
    tier.name = name
    tier.slug = slug
    return tier


def _make_agreement(
    tier_name: str = "Essential",
    tier_slug: str = "essential-residential",
    week_prefs: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock ServiceAgreement with optional week preferences."""
    agreement = MagicMock()
    agreement.id = uuid4()
    agreement.customer_id = uuid4()
    agreement.property_id = uuid4()
    agreement.tier = _make_tier(name=tier_name, slug=tier_slug)
    agreement.service_week_preferences = week_prefs
    return agreement


def _make_async_session() -> AsyncMock:
    """Create a mock AsyncSession that handles add/flush/refresh."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestOnboardingWeekPreferencesJobGeneration:
    """Integration: onboarding week preferences flow through to job dates.

    Validates: CRM Changes Update 2 Req 30.3, 30.4, 30.6
    """

    # -----------------------------------------------------------------
    # 1. Essential tier with week preferences → correct Monday-Sunday
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_essential_with_week_prefs_generates_monday_sunday_dates(
        self,
    ) -> None:
        """Jobs use customer-selected weeks when service_week_preferences set.

        **Validates: Requirements 30.3, 30.4**

        Essential tier produces 2 jobs (spring_startup Apr, fall_winterization Oct).
        When week preferences specify ISO Monday dates, each job's
        target_start_date should be that Monday and target_end_date the
        following Sunday.
        """
        spring_monday = "2026-04-06"  # Monday
        fall_monday = "2026-10-05"  # Monday

        agreement = _make_agreement(
            tier_name="Essential",
            tier_slug="essential-residential",
            week_prefs={
                "spring_startup": spring_monday,
                "fall_winterization": fall_monday,
            },
        )

        session = _make_async_session()
        generator = JobGenerator(session)
        jobs = await generator.generate_jobs(agreement)

        assert len(jobs) == 2

        spring_job = next(j for j in jobs if j.job_type == "spring_startup")
        fall_job = next(j for j in jobs if j.job_type == "fall_winterization")

        # Spring: Monday 2026-04-06 → Sunday 2026-04-12
        assert spring_job.target_start_date == date(2026, 4, 6)
        assert spring_job.target_end_date == date(2026, 4, 12)
        assert spring_job.target_start_date.weekday() == 0  # Monday
        assert spring_job.target_end_date.weekday() == 6  # Sunday

        # Fall: Monday 2026-10-05 → Sunday 2026-10-11
        assert fall_job.target_start_date == date(2026, 10, 5)
        assert fall_job.target_end_date == date(2026, 10, 11)
        assert fall_job.target_start_date.weekday() == 0
        assert fall_job.target_end_date.weekday() == 6

    # -----------------------------------------------------------------
    # 2. Premium tier with monthly visit week preferences
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_premium_with_monthly_visit_week_prefs(self) -> None:
        """Premium monthly visits use month-qualified keys (e.g. monthly_visit_5).

        **Validates: Requirements 30.3, 30.4**

        Premium tier produces 7 jobs. Monthly visits (May-Sep) use
        month-qualified preference keys like monthly_visit_5, monthly_visit_6.
        """
        week_prefs = {
            "spring_startup": "2026-04-13",  # Monday
            "monthly_visit_5": "2026-05-04",  # Monday
            "monthly_visit_6": "2026-06-08",  # Monday
            "monthly_visit_7": "2026-07-06",  # Monday
            "monthly_visit_8": "2026-08-03",  # Monday
            "monthly_visit_9": "2026-09-07",  # Monday
            "fall_winterization": "2026-10-12",  # Monday
        }

        agreement = _make_agreement(
            tier_name="Premium",
            tier_slug="premium-residential",
            week_prefs=week_prefs,
        )

        session = _make_async_session()
        generator = JobGenerator(session)
        jobs = await generator.generate_jobs(agreement)

        assert len(jobs) == 7

        # Verify every job has Monday start and Sunday end
        for job in jobs:
            assert job.target_start_date.weekday() == 0, (
                f"{job.job_type}: start is not Monday"
            )
            assert job.target_end_date.weekday() == 6, (
                f"{job.job_type}: end is not Sunday"
            )
            diff = (job.target_end_date - job.target_start_date).days
            assert diff == 6, f"{job.job_type}: span is {diff} days, expected 6"

        # Spot-check the May monthly visit
        may_jobs = [
            j for j in jobs
            if j.job_type == "monthly_visit"
            and j.target_start_date.month == 5
        ]
        assert len(may_jobs) == 1
        assert may_jobs[0].target_start_date == date(2026, 5, 4)
        assert may_jobs[0].target_end_date == date(2026, 5, 10)

    # -----------------------------------------------------------------
    # 3. Round-trip: selected weeks match generated Week_Of dates
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_round_trip_selected_weeks_match_generated_dates(self) -> None:
        """Week preferences round-trip: selected Monday → job dates → same Monday.

        **Validates: Requirements 30.6**

        For all valid service_week_preferences, generating jobs then reading
        their Week_Of display values produces dates matching the originally
        selected weeks.
        """
        selected_mondays = {
            "spring_startup": "2026-04-20",
            "fall_winterization": "2026-10-19",
        }

        agreement = _make_agreement(
            tier_name="Essential",
            tier_slug="essential-residential",
            week_prefs=selected_mondays,
        )

        session = _make_async_session()
        generator = JobGenerator(session)
        jobs = await generator.generate_jobs(agreement)

        for job in jobs:
            original_monday_iso = selected_mondays[job.job_type]
            original_monday = date.fromisoformat(original_monday_iso)

            # Round-trip: align_to_week on the job's start date should
            # return the same Monday
            rt_monday, rt_sunday = align_to_week(job.target_start_date)
            assert rt_monday == original_monday, (
                f"{job.job_type}: round-trip Monday {rt_monday} != "
                f"original {original_monday}"
            )
            assert rt_sunday == job.target_end_date

    # -----------------------------------------------------------------
    # 4. Fallback: null preferences → calendar-month defaults
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_null_preferences_falls_back_to_calendar_month(self) -> None:
        """No week preferences → jobs use full calendar-month date ranges.

        **Validates: Requirements 30.4 (fallback path)**

        When service_week_preferences is None, the job generator should
        produce jobs with target_start_date = 1st of month and
        target_end_date = last day of month.
        """
        agreement = _make_agreement(
            tier_name="Essential",
            tier_slug="essential-residential",
            week_prefs=None,
        )

        session = _make_async_session()
        generator = JobGenerator(session)
        jobs = await generator.generate_jobs(agreement)

        assert len(jobs) == 2

        spring_job = next(j for j in jobs if j.job_type == "spring_startup")
        fall_job = next(j for j in jobs if j.job_type == "fall_winterization")

        # Spring: April 1 – April 30
        year = spring_job.target_start_date.year
        assert spring_job.target_start_date.month == 4
        assert spring_job.target_start_date.day == 1
        assert spring_job.target_end_date.month == 4
        assert spring_job.target_end_date.day == calendar.monthrange(year, 4)[1]

        # Fall: October 1 – October 31
        assert fall_job.target_start_date.month == 10
        assert fall_job.target_start_date.day == 1
        assert fall_job.target_end_date.month == 10
        assert fall_job.target_end_date.day == calendar.monthrange(year, 10)[1]

    # -----------------------------------------------------------------
    # 5. Fallback: empty dict preferences → calendar-month defaults
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_dict_preferences_falls_back_to_calendar_month(self) -> None:
        """Empty dict week preferences → same fallback as null.

        **Validates: Requirements 30.4 (fallback path)**
        """
        agreement = _make_agreement(
            tier_name="Professional",
            tier_slug="professional-residential",
            week_prefs={},
        )

        session = _make_async_session()
        generator = JobGenerator(session)
        jobs = await generator.generate_jobs(agreement)

        # Professional: 3 jobs (spring Apr, mid-season Jul, fall Oct)
        assert len(jobs) == 3

        for job in jobs:
            assert job.target_start_date.day == 1, (
                f"{job.job_type}: start day should be 1st of month"
            )
            year = job.target_start_date.year
            month = job.target_start_date.month
            last_day = calendar.monthrange(year, month)[1]
            assert job.target_end_date.day == last_day, (
                f"{job.job_type}: end day should be last day of month"
            )

    # -----------------------------------------------------------------
    # 6. Partial preferences: some services have prefs, others default
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_partial_preferences_mixed_dates(self) -> None:
        """Only some services have week prefs; others fall back to month defaults.

        **Validates: Requirements 30.3, 30.4**

        When only spring_startup has a week preference but fall_winterization
        does not, spring should use the week range and fall should use the
        calendar-month range.
        """
        agreement = _make_agreement(
            tier_name="Essential",
            tier_slug="essential-residential",
            week_prefs={"spring_startup": "2026-04-13"},  # Monday
        )

        session = _make_async_session()
        generator = JobGenerator(session)
        jobs = await generator.generate_jobs(agreement)

        spring_job = next(j for j in jobs if j.job_type == "spring_startup")
        fall_job = next(j for j in jobs if j.job_type == "fall_winterization")

        # Spring: week range Monday-Sunday
        assert spring_job.target_start_date == date(2026, 4, 13)
        assert spring_job.target_end_date == date(2026, 4, 19)
        assert spring_job.target_start_date.weekday() == 0
        assert spring_job.target_end_date.weekday() == 6

        # Fall: calendar-month default (October 1-31)
        year = fall_job.target_start_date.year
        assert fall_job.target_start_date.day == 1
        assert fall_job.target_start_date.month == 10
        assert fall_job.target_end_date.day == calendar.monthrange(year, 10)[1]

    # -----------------------------------------------------------------
    # 7. Jobs linked to correct agreement and customer
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_generated_jobs_linked_to_agreement_and_customer(self) -> None:
        """Generated jobs carry the agreement's customer_id and agreement_id.

        **Validates: Requirements 30.3**
        """
        agreement = _make_agreement(
            tier_name="Essential",
            tier_slug="essential-residential",
            week_prefs={"spring_startup": "2026-04-06", "fall_winterization": "2026-10-05"},
        )

        session = _make_async_session()
        generator = JobGenerator(session)
        jobs = await generator.generate_jobs(agreement)

        for job in jobs:
            assert job.customer_id == agreement.customer_id
            assert job.service_agreement_id == agreement.id
            assert job.property_id == agreement.property_id
