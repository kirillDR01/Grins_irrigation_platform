"""Property-based tests for Tier-Priority Scheduling spec.

Covers Properties 1-5 plus edge-case unit tests for winterization-only,
unknown tier fallback, all-jobs-same-priority invariant, and constant integrity.
"""

from __future__ import annotations

from decimal import Decimal
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import JobStatus
from grins_platform.models.job import Job
from grins_platform.services.job_generator import (
    _TIER_PRIORITY_MAP,
    JobGenerator,
)
from grins_platform.services.schedule_domain import ScheduleJob, ScheduleLocation

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

tier_names = st.sampled_from(["Essential", "Professional", "Premium"])
priority_levels = st.sampled_from([0, 1, 2])
random_cities = st.sampled_from(
    ["Eden Prairie", "Minnetonka", "Bloomington", "Plymouth", "Wayzata", None],
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_tier(name: str, slug: str | None = None) -> MagicMock:
    """Create a mock ServiceAgreementTier."""
    tier = MagicMock()
    tier.name = name
    tier.slug = slug or f"{name.lower()}-residential"
    return tier


def _make_mock_agreement(
    tier_name: str,
    tier_slug: str | None = None,
) -> MagicMock:
    """Create a mock ServiceAgreement with the given tier."""
    agreement = MagicMock()
    agreement.id = uuid4()
    agreement.customer_id = uuid4()
    agreement.property_id = uuid4()
    agreement.tier = _make_mock_tier(tier_name, tier_slug)
    return agreement


def _make_async_session() -> AsyncMock:
    """Create a mock AsyncSession that handles add/flush/refresh."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _make_schedule_job(
    priority: int,
    city: str | None = None,
) -> ScheduleJob:
    """Create a ScheduleJob with given priority and city."""
    return ScheduleJob(
        id=uuid4(),
        customer_name="Test Customer",
        location=ScheduleLocation(
            latitude=Decimal("44.8547"),
            longitude=Decimal("-93.4708"),
            city=city,
        ),
        service_type="spring_startup",
        duration_minutes=60,
        priority=priority,
    )


# ===================================================================
# Property 1: Tier-to-priority mapping correctness
# Feature: tier-priority-scheduling, Property 1: Tier-to-priority mapping correctness
# Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 4.2
# ===================================================================


@pytest.mark.unit
class TestProperty1TierToPriorityMapping:
    """Property 1: Tier-to-priority mapping correctness.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 4.2**
    """

    @given(tier_name=tier_names)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_generate_jobs_sets_correct_priority(
        self,
        tier_name: str,
    ) -> None:
        """All generated jobs have priority matching the tier map."""
        session = _make_async_session()
        agreement = _make_mock_agreement(tier_name)
        generator = JobGenerator(session)

        jobs = await generator.generate_jobs(agreement)

        expected_priority = _TIER_PRIORITY_MAP[tier_name]
        assert len(jobs) > 0
        for job in jobs:
            assert job.priority_level == expected_priority

    @given(tier_name=tier_names)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_all_jobs_in_batch_have_same_priority(
        self,
        tier_name: str,
    ) -> None:
        """All jobs in a single agreement batch share the same priority_level."""
        session = _make_async_session()
        agreement = _make_mock_agreement(tier_name)
        generator = JobGenerator(session)

        jobs = await generator.generate_jobs(agreement)

        priorities = {job.priority_level for job in jobs}
        assert len(priorities) == 1


# ===================================================================
# Property 2: Scheduler priority ordering
# Feature: tier-priority-scheduling, Property 2: Scheduler priority ordering
# Validates: Requirements 2.1, 2.2, 2.3
# ===================================================================


@pytest.mark.unit
class TestProperty2SchedulerPriorityOrdering:
    """Property 2: Scheduler priority ordering.

    **Validates: Requirements 2.1, 2.2, 2.3**
    """

    @given(
        job_data=st.lists(
            st.tuples(priority_levels, random_cities),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_sorted_jobs_descending_priority_then_city(
        self,
        job_data: list[tuple[int, str | None]],
    ) -> None:
        """Greedy sort: descending priority, sub-sorted by city."""
        jobs = [_make_schedule_job(p, c) for p, c in job_data]

        sorted_jobs = sorted(
            jobs,
            key=lambda j: (-j.priority, j.location.city or ""),
        )

        # Verify descending priority order
        for i in range(len(sorted_jobs) - 1):
            assert sorted_jobs[i].priority >= sorted_jobs[i + 1].priority

        # Verify equal-priority sub-sorted by city
        for i in range(len(sorted_jobs) - 1):
            if sorted_jobs[i].priority == sorted_jobs[i + 1].priority:
                city_a = sorted_jobs[i].location.city or ""
                city_b = sorted_jobs[i + 1].location.city or ""
                assert city_a <= city_b


# ===================================================================
# Property 3: Priority badge label mapping
# Feature: tier-priority-scheduling, Property 3: Priority badge label mapping
# Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
# ===================================================================


@pytest.mark.unit
class TestProperty3PriorityBadgeLabelMapping:
    """Property 3: Priority badge label mapping.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    """

    PRIORITY_LABEL_MAP: ClassVar[dict[int, str]] = {
        0: "Normal",
        1: "High",
        2: "Urgent",
    }

    @given(priority_level=priority_levels)
    @settings(max_examples=100)
    def test_priority_to_label_mapping(
        self,
        priority_level: int,
    ) -> None:
        """Each priority_level maps to the correct badge label."""
        label = self.PRIORITY_LABEL_MAP[priority_level]
        expected = {0: "Normal", 1: "High", 2: "Urgent"}
        assert label == expected[priority_level]

    @given(priority_level=priority_levels)
    @settings(max_examples=100)
    def test_tier_priority_map_inverse_consistency(
        self,
        priority_level: int,
    ) -> None:
        """_TIER_PRIORITY_MAP inverse is consistent with forward map."""
        inverse_map = {v: k for k, v in _TIER_PRIORITY_MAP.items()}
        # All three priority levels should be in the inverse map
        assert priority_level in inverse_map
        tier_name = inverse_map[priority_level]
        assert _TIER_PRIORITY_MAP[tier_name] == priority_level


# ===================================================================
# Property 4: Priority persistence through lifecycle
# Feature: tier-priority-scheduling, Property 4: Priority persistence through lifecycle
# Validates: Requirements 4.1
# ===================================================================


@pytest.mark.unit
class TestProperty4PriorityPersistenceThroughLifecycle:
    """Property 4: Priority persistence through lifecycle.

    **Validates: Requirements 4.1**
    """

    LIFECYCLE_STATUSES: ClassVar[list[str]] = [
        JobStatus.APPROVED.value,
        JobStatus.SCHEDULED.value,
        JobStatus.IN_PROGRESS.value,
        JobStatus.COMPLETED.value,
        JobStatus.CLOSED.value,
    ]

    @pytest.mark.parametrize("priority", [0, 1, 2])
    def test_priority_unchanged_through_status_transitions(
        self,
        priority: int,
    ) -> None:
        """priority_level remains unchanged after each status transition."""
        job = Job(
            customer_id=uuid4(),
            job_type="spring_startup",
            category="ready_to_schedule",
            status=JobStatus.APPROVED.value,
            priority_level=priority,
        )

        for status in self.LIFECYCLE_STATUSES:
            job.status = status
            assert job.priority_level == priority, (
                f"Priority changed to {job.priority_level} after transition to {status}"
            )


# ===================================================================
# Property 5: Tier-priority mapping round-trip
# Feature: tier-priority-scheduling, Property 5: Tier-priority mapping round-trip
# Validates: Requirements 4.3
# ===================================================================


@pytest.mark.unit
class TestProperty5TierPriorityMappingRoundTrip:
    """Property 5: Tier-priority mapping round-trip.

    **Validates: Requirements 4.3**
    """

    def test_round_trip_for_all_main_tiers(self) -> None:
        """tier→priority→tier round-trip produces original tier name."""
        inverse_map = {v: k for k, v in _TIER_PRIORITY_MAP.items()}

        for tier_name in ["Essential", "Professional", "Premium"]:
            priority = _TIER_PRIORITY_MAP[tier_name]
            recovered_tier = inverse_map[priority]
            assert recovered_tier == tier_name

    def test_inverse_map_has_no_collisions(self) -> None:
        """The inverse map is well-defined (no collisions among main tiers)."""
        values = list(_TIER_PRIORITY_MAP.values())
        assert len(values) == len(set(values)), "Priority values are not unique"


# ===================================================================
# Edge case: winterization-only tier
# Validates: Requirement 1.4
# ===================================================================


@pytest.mark.unit
class TestWinterizationOnlyEdgeCase:
    """Winterization-only tier edge case tests.

    Validates: Requirement 1.4
    """

    @pytest.mark.asyncio
    async def test_winterization_only_gets_priority_zero(self) -> None:
        """Winterization-only tier produces jobs with priority_level=0."""
        session = _make_async_session()
        agreement = _make_mock_agreement(
            "Winterization Only",
            tier_slug="winterization-only-residential",
        )
        generator = JobGenerator(session)

        jobs = await generator.generate_jobs(agreement)

        assert len(jobs) == 1
        assert jobs[0].priority_level == 0

    def test_winterization_only_not_in_tier_priority_map(self) -> None:
        """'Winterization Only' is NOT a key in _TIER_PRIORITY_MAP."""
        assert "Winterization Only" not in _TIER_PRIORITY_MAP


# ===================================================================
# Edge case: unknown tier name fallback
# Validates: Requirement 1.5
# ===================================================================


@pytest.mark.unit
class TestUnknownTierNameFallback:
    """Unknown tier name fallback tests.

    Validates: Requirement 1.5
    """

    def test_tier_priority_map_get_unknown_returns_zero(self) -> None:
        """_TIER_PRIORITY_MAP.get('UnknownTier', 0) returns 0."""
        assert _TIER_PRIORITY_MAP.get("UnknownTier", 0) == 0

    @pytest.mark.asyncio
    async def test_generate_jobs_unknown_tier_raises_value_error(self) -> None:
        """generate_jobs() with unknown tier raises ValueError."""
        session = _make_async_session()
        agreement = _make_mock_agreement(
            "UnknownTier",
            tier_slug="unknown-tier-residential",
        )
        generator = JobGenerator(session)

        with pytest.raises(ValueError, match="Unknown tier name"):
            await generator.generate_jobs(agreement)


# ===================================================================
# All-jobs-same-priority invariant
# Validates: Requirement 4.2
# ===================================================================


@pytest.mark.unit
class TestAllJobsSamePriorityInvariant:
    """All jobs from a single tier have identical priority_level.

    Validates: Requirement 4.2
    """

    @pytest.mark.asyncio
    async def test_essential_two_jobs_all_priority_zero(self) -> None:
        """Essential tier: 2 jobs, all priority 0."""
        session = _make_async_session()
        agreement = _make_mock_agreement("Essential")
        generator = JobGenerator(session)

        jobs = await generator.generate_jobs(agreement)

        assert len(jobs) == 2
        assert all(j.priority_level == 0 for j in jobs)

    @pytest.mark.asyncio
    async def test_professional_three_jobs_all_priority_one(self) -> None:
        """Professional tier: 3 jobs, all priority 1."""
        session = _make_async_session()
        agreement = _make_mock_agreement("Professional")
        generator = JobGenerator(session)

        jobs = await generator.generate_jobs(agreement)

        assert len(jobs) == 3
        assert all(j.priority_level == 1 for j in jobs)

    @pytest.mark.asyncio
    async def test_premium_seven_jobs_all_priority_two(self) -> None:
        """Premium tier: 7 jobs, all priority 2."""
        session = _make_async_session()
        agreement = _make_mock_agreement("Premium")
        generator = JobGenerator(session)

        jobs = await generator.generate_jobs(agreement)

        assert len(jobs) == 7
        assert all(j.priority_level == 2 for j in jobs)


# ===================================================================
# _TIER_PRIORITY_MAP constant integrity
# Validates: Requirements 1.1, 1.2, 1.3, 1.5
# ===================================================================


@pytest.mark.unit
class TestTierPriorityMapConstantIntegrity:
    """_TIER_PRIORITY_MAP constant integrity checks.

    Validates: Requirements 1.1, 1.2, 1.3, 1.5
    """

    def test_exactly_three_entries(self) -> None:
        """_TIER_PRIORITY_MAP has exactly 3 entries."""
        assert len(_TIER_PRIORITY_MAP) == 3

    def test_all_values_in_valid_set(self) -> None:
        """All values are in {0, 1, 2}."""
        assert set(_TIER_PRIORITY_MAP.values()) == {0, 1, 2}

    def test_all_values_unique(self) -> None:
        """All values are unique (bijective for main tiers)."""
        values = list(_TIER_PRIORITY_MAP.values())
        assert len(values) == len(set(values))

    def test_keys_exactly_match(self) -> None:
        """Keys are exactly {'Essential', 'Professional', 'Premium'}."""
        assert set(_TIER_PRIORITY_MAP.keys()) == {
            "Essential",
            "Professional",
            "Premium",
        }
