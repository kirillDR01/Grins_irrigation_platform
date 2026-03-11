"""Unit tests for JobGenerator service.

Tests correct job count per tier, date ranges, status/category invariants,
and linking to agreement, customer, and property.

Validates: Requirements 9.1-9.7, 40.1
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import JobCategory, JobStatus
from grins_platform.services.job_generator import JobGenerator

# =============================================================================
# Helpers
# =============================================================================


_TIER_NAME_TO_SLUG: dict[str, str] = {
    "Essential": "essential-residential",
    "Professional": "professional-residential",
    "Premium": "premium-residential",
}


def _make_agreement(
    *,
    tier_name: str = "Essential",
    tier_slug: str | None = None,
    customer_id=None,
    property_id=None,
    agreement_id=None,
) -> MagicMock:
    agr = MagicMock()
    agr.id = agreement_id or uuid4()
    agr.customer_id = customer_id or uuid4()
    agr.property_id = property_id
    agr.tier = MagicMock()
    agr.tier.name = tier_name
    agr.tier.slug = tier_slug or _TIER_NAME_TO_SLUG.get(tier_name, tier_name.lower())
    return agr


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# =============================================================================
# Job count per tier
# =============================================================================


class TestJobCountPerTier:
    """Test correct number of jobs generated per tier."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_essential_generates_2_jobs(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Essential")

        jobs = await gen.generate_jobs(agreement)

        assert len(jobs) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_professional_generates_3_jobs(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Professional")

        jobs = await gen.generate_jobs(agreement)

        assert len(jobs) == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_premium_generates_7_jobs(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Premium")

        jobs = await gen.generate_jobs(agreement)

        assert len(jobs) == 7

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_tier_raises_value_error(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="NonExistent")

        with pytest.raises(ValueError, match="Unknown tier name"):
            await gen.generate_jobs(agreement)


# =============================================================================
# Date ranges
# =============================================================================


class TestDateRanges:
    """Test correct date ranges per job type."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_essential_date_ranges(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Essential")

        jobs = await gen.generate_jobs(agreement)
        year = datetime.now(timezone.utc).year

        # Spring Startup: April
        assert jobs[0].target_start_date == date(year, 4, 1)
        assert jobs[0].target_end_date == date(year, 4, 30)
        # Fall Winterization: October
        assert jobs[1].target_start_date == date(year, 10, 1)
        assert jobs[1].target_end_date == date(year, 10, 31)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_professional_date_ranges(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Professional")

        jobs = await gen.generate_jobs(agreement)
        year = datetime.now(timezone.utc).year

        assert jobs[0].target_start_date == date(year, 4, 1)
        assert jobs[0].target_end_date == date(year, 4, 30)
        # Mid-Season: July
        assert jobs[1].target_start_date == date(year, 7, 1)
        assert jobs[1].target_end_date == date(year, 7, 31)
        # Fall: October
        assert jobs[2].target_start_date == date(year, 10, 1)
        assert jobs[2].target_end_date == date(year, 10, 31)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_premium_date_ranges(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Premium")

        jobs = await gen.generate_jobs(agreement)
        year = datetime.now(timezone.utc).year

        expected_months = [4, 5, 6, 7, 8, 9, 10]
        for i, month in enumerate(expected_months):
            last_day = calendar.monthrange(year, month)[1]
            assert jobs[i].target_start_date == date(year, month, 1)
            assert jobs[i].target_end_date == date(year, month, last_day)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_jobs_have_start_before_or_equal_end(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)

        for tier in ("Essential", "Professional", "Premium"):
            agreement = _make_agreement(tier_name=tier)
            jobs = await gen.generate_jobs(agreement)
            for job in jobs:
                assert job.target_start_date <= job.target_end_date


# =============================================================================
# Status and category invariants
# =============================================================================


class TestStatusAndCategory:
    """Test all generated jobs have correct status and category."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("tier", ["Essential", "Professional", "Premium"])
    async def test_all_jobs_status_approved(self, tier: str) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name=tier)

        jobs = await gen.generate_jobs(agreement)

        for job in jobs:
            assert job.status == JobStatus.APPROVED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("tier", ["Essential", "Professional", "Premium"])
    async def test_all_jobs_category_ready_to_schedule(self, tier: str) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name=tier)

        jobs = await gen.generate_jobs(agreement)

        for job in jobs:
            assert job.category == JobCategory.READY_TO_SCHEDULE.value


# =============================================================================
# Linking to agreement, customer, property
# =============================================================================


class TestLinking:
    """Test jobs are linked to agreement, customer, and property."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_jobs_linked_to_agreement(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Essential")

        jobs = await gen.generate_jobs(agreement)

        for job in jobs:
            assert job.service_agreement_id == agreement.id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_jobs_linked_to_customer(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Essential")

        jobs = await gen.generate_jobs(agreement)

        for job in jobs:
            assert job.customer_id == agreement.customer_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_jobs_linked_to_property_when_present(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        prop_id = uuid4()
        agreement = _make_agreement(tier_name="Professional", property_id=prop_id)

        jobs = await gen.generate_jobs(agreement)

        for job in jobs:
            assert job.property_id == prop_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_jobs_property_none_when_agreement_has_none(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Essential", property_id=None)

        jobs = await gen.generate_jobs(agreement)

        for job in jobs:
            assert job.property_id is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_add_called_for_each_job(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Premium")

        await gen.generate_jobs(agreement)

        assert session.add.call_count == 7

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_flush_called(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Essential")

        await gen.generate_jobs(agreement)

        session.flush.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_jobs_have_approved_at_set(self) -> None:
        session = _make_session()
        gen = JobGenerator(session)
        agreement = _make_agreement(tier_name="Essential")

        jobs = await gen.generate_jobs(agreement)

        for job in jobs:
            assert job.approved_at is not None
