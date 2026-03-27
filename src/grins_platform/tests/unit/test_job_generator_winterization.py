"""Unit and property tests for JobGenerator winterization-only tier support.

Property 8: Winterization-only tier generates exactly 1 job with
job_type="fall_winterization", target_start_date=Oct 1, target_end_date=Oct 31.

Validates: Requirements 4.2
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import JobCategory, JobStatus
from grins_platform.services.job_generator import JobGenerator

# =============================================================================
# Helpers
# =============================================================================

_WINTERIZATION_SLUGS = [
    "winterization-only-residential",
    "winterization-only-commercial",
]


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _make_agreement(
    *,
    tier_name: str = "Winterization Only Residential",
    tier_slug: str = "winterization-only-residential",
    customer_id: object | None = None,
    property_id: object | None = None,
) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.customer_id = customer_id or uuid4()
    agr.property_id = property_id
    agr.tier = MagicMock()
    agr.tier.name = tier_name
    agr.tier.slug = tier_slug
    return agr


# =============================================================================
# Property 8: Winterization-only tier generates exactly 1 job
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestWinterizationOnlyProperty:
    """Property 8: Winterization-only tier generates exactly 1 job."""

    @given(slug=st.sampled_from(_WINTERIZATION_SLUGS))
    @settings(max_examples=20)
    async def test_generates_exactly_one_job(self, slug: str) -> None:
        """Winterization-only tier always produces exactly 1 job."""
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug=slug)
        jobs = await gen.generate_jobs(agr)
        assert len(jobs) == 1

    @given(slug=st.sampled_from(_WINTERIZATION_SLUGS))
    @settings(max_examples=20)
    async def test_job_type_is_fall_winterization(self, slug: str) -> None:
        """The single job has job_type='fall_winterization'."""
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug=slug)
        jobs = await gen.generate_jobs(agr)
        assert jobs[0].job_type == "fall_winterization"

    @given(slug=st.sampled_from(_WINTERIZATION_SLUGS))
    @settings(max_examples=20)
    async def test_job_dates_are_october(self, slug: str) -> None:
        """The job targets October 1 - October 31."""
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug=slug)
        jobs = await gen.generate_jobs(agr)
        year = datetime.now(timezone.utc).year
        assert jobs[0].target_start_date == date(year, 10, 1)
        assert jobs[0].target_end_date == date(year, 10, 31)


# =============================================================================
# Unit tests for winterization-only tiers
# =============================================================================


class TestWinterizationOnlyResidential:
    """Test winterization-only residential tier generates correct job."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generates_one_job(self) -> None:
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug="winterization-only-residential")
        jobs = await gen.generate_jobs(agr)
        assert len(jobs) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_job_type_and_dates(self) -> None:
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug="winterization-only-residential")
        jobs = await gen.generate_jobs(agr)
        year = datetime.now(timezone.utc).year
        assert jobs[0].job_type == "fall_winterization"
        assert jobs[0].target_start_date == date(year, 10, 1)
        assert jobs[0].target_end_date == date(year, 10, 31)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_job_status_and_category(self) -> None:
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug="winterization-only-residential")
        jobs = await gen.generate_jobs(agr)
        assert jobs[0].status == JobStatus.TO_BE_SCHEDULED.value
        assert jobs[0].category == JobCategory.READY_TO_SCHEDULE.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_job_linked_to_agreement(self) -> None:
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug="winterization-only-residential")
        jobs = await gen.generate_jobs(agr)
        assert jobs[0].service_agreement_id == agr.id
        assert jobs[0].customer_id == agr.customer_id


class TestWinterizationOnlyCommercial:
    """Test winterization-only commercial tier generates correct job."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generates_one_job(self) -> None:
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug="winterization-only-commercial")
        jobs = await gen.generate_jobs(agr)
        assert len(jobs) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_job_type_and_dates(self) -> None:
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_slug="winterization-only-commercial")
        jobs = await gen.generate_jobs(agr)
        year = datetime.now(timezone.utc).year
        assert jobs[0].job_type == "fall_winterization"
        assert jobs[0].target_start_date == date(year, 10, 1)
        assert jobs[0].target_end_date == date(year, 10, 31)


# =============================================================================
# Regression: existing tiers still generate correct job counts
# =============================================================================


class TestExistingTiersRegression:
    """Ensure existing tiers are not affected by winterization-only changes."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tier_name", "tier_slug", "expected_count"),
        [
            ("Essential", "essential-residential", 2),
            ("Professional", "professional-residential", 3),
            ("Premium", "premium-residential", 7),
        ],
    )
    async def test_existing_tier_job_counts(
        self,
        tier_name: str,
        tier_slug: str,
        expected_count: int,
    ) -> None:
        gen = JobGenerator(_make_session())
        agr = _make_agreement(tier_name=tier_name, tier_slug=tier_slug)
        jobs = await gen.generate_jobs(agr)
        assert len(jobs) == expected_count
