"""Property test for job generation count and date ranges.

Property 1: Job Generation Produces Correct Count and Non-Overlapping Date Ranges
For any valid tier, produces exactly tier-specified number of jobs (2/3/7),
each with valid target_start_date <= target_end_date, no overlapping date ranges.

Validates: Requirements 9.1, 9.2, 9.3
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.job_generator import JobGenerator

TIER_EXPECTED_COUNTS = {"Essential": 2, "Professional": 3, "Premium": 7}

tiers = st.sampled_from(list(TIER_EXPECTED_COUNTS.keys()))


def _make_agreement(tier_name: str) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.customer_id = uuid4()
    agr.property_id = uuid4()
    agr.tier = MagicMock()
    agr.tier.name = tier_name
    return agr


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
class TestJobGenerationCountAndDateRanges:
    """Property-based tests for job generation count and date range invariants."""

    @given(tier_name=tiers)
    @settings(max_examples=30)
    async def test_correct_job_count_per_tier(self, tier_name: str) -> None:
        """Each tier produces exactly the specified number of jobs."""
        gen = JobGenerator(_make_session())
        jobs = await gen.generate_jobs(_make_agreement(tier_name))
        assert len(jobs) == TIER_EXPECTED_COUNTS[tier_name]

    @given(tier_name=tiers)
    @settings(max_examples=30)
    async def test_start_date_before_or_equal_end_date(self, tier_name: str) -> None:
        """Every job has target_start_date <= target_end_date."""
        gen = JobGenerator(_make_session())
        jobs = await gen.generate_jobs(_make_agreement(tier_name))
        for job in jobs:
            assert job.target_start_date <= job.target_end_date

    @given(tier_name=tiers)
    @settings(max_examples=30)
    async def test_no_overlapping_date_ranges(self, tier_name: str) -> None:
        """No two jobs have overlapping date ranges."""
        gen = JobGenerator(_make_session())
        jobs = await gen.generate_jobs(_make_agreement(tier_name))
        sorted_jobs = sorted(jobs, key=lambda j: j.target_start_date)
        for i in range(len(sorted_jobs) - 1):
            assert sorted_jobs[i].target_end_date < sorted_jobs[i + 1].target_start_date
