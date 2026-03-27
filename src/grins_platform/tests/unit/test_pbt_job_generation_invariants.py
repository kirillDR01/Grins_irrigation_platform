"""Property test for generated job invariants.

Property 2: Generated Job Invariants
For any generated job: status=TO_BE_SCHEDULED, category=READY_TO_SCHEDULE,
non-null service_agreement_id matching source agreement, non-null customer_id,
matching property_id when agreement has one.

Validates: Requirements 9.4, 9.5, 9.6, 9.7
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

from grins_platform.models.enums import JobCategory, JobStatus
from grins_platform.services.job_generator import JobGenerator

TIER_NAMES = ["Essential", "Professional", "Premium"]

tiers = st.sampled_from(TIER_NAMES)
optional_property_id = st.one_of(st.just(None), st.builds(uuid4))


_TIER_NAME_TO_SLUG: dict[str, str] = {
    "Essential": "essential-residential",
    "Professional": "professional-residential",
    "Premium": "premium-residential",
}


def _make_agreement(tier_name: str, property_id: object = None) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.customer_id = uuid4()
    agr.property_id = property_id
    agr.tier = MagicMock()
    agr.tier.name = tier_name
    agr.tier.slug = _TIER_NAME_TO_SLUG.get(tier_name, tier_name.lower())
    return agr


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
class TestGeneratedJobInvariants:
    """Property-based tests for generated job field invariants."""

    @given(tier_name=tiers)
    @settings(max_examples=30)
    async def test_all_jobs_have_to_be_scheduled_status(self, tier_name: str) -> None:
        """Every generated job has status=TO_BE_SCHEDULED."""
        gen = JobGenerator(_make_session())
        jobs = await gen.generate_jobs(_make_agreement(tier_name))
        for job in jobs:
            assert job.status == JobStatus.TO_BE_SCHEDULED.value

    @given(tier_name=tiers)
    @settings(max_examples=30)
    async def test_all_jobs_have_ready_to_schedule_category(
        self,
        tier_name: str,
    ) -> None:
        """Every generated job has category=READY_TO_SCHEDULE."""
        gen = JobGenerator(_make_session())
        jobs = await gen.generate_jobs(_make_agreement(tier_name))
        for job in jobs:
            assert job.category == JobCategory.READY_TO_SCHEDULE.value

    @given(tier_name=tiers)
    @settings(max_examples=30)
    async def test_all_jobs_linked_to_agreement(self, tier_name: str) -> None:
        """Every job has non-null service_agreement_id matching agreement."""
        agreement = _make_agreement(tier_name)
        gen = JobGenerator(_make_session())
        jobs = await gen.generate_jobs(agreement)
        for job in jobs:
            assert job.service_agreement_id is not None
            assert job.service_agreement_id == agreement.id

    @given(tier_name=tiers)
    @settings(max_examples=30)
    async def test_all_jobs_have_customer_id(self, tier_name: str) -> None:
        """Every generated job has non-null customer_id matching the agreement."""
        agreement = _make_agreement(tier_name)
        gen = JobGenerator(_make_session())
        jobs = await gen.generate_jobs(agreement)
        for job in jobs:
            assert job.customer_id is not None
            assert job.customer_id == agreement.customer_id

    @given(tier_name=tiers, prop_id=optional_property_id)
    @settings(max_examples=30)
    async def test_property_id_matches_agreement(
        self,
        tier_name: str,
        prop_id: object,
    ) -> None:
        """Jobs have matching property_id when agreement has one, None otherwise."""
        agreement = _make_agreement(tier_name, property_id=prop_id)
        gen = JobGenerator(_make_session())
        jobs = await gen.generate_jobs(agreement)
        for job in jobs:
            assert job.property_id == agreement.property_id
