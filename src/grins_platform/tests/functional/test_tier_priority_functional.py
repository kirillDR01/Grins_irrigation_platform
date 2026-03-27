"""Functional tests for tier-priority scheduling.

Tests job generation with tier-based priority assignment, priority
persistence through status transitions, and correct job counts per tier
using mocked DB sessions following the project's functional test pattern.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 4.1, 4.2
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import JobStatus
from grins_platform.services.job_generator import JobGenerator

# =============================================================================
# Helpers
# =============================================================================


def _make_tier(**overrides: Any) -> MagicMock:
    """Create a mock ServiceAgreementTier."""
    tier = MagicMock()
    tier.id = overrides.get("id", uuid4())
    tier.name = overrides.get("name", "Essential")
    tier.slug = overrides.get("slug", "essential-residential")
    tier.package_type = overrides.get("package_type", "RESIDENTIAL")
    tier.annual_price = overrides.get("annual_price", Decimal("399.00"))
    tier.included_services = overrides.get("included_services", [])
    tier.display_order = overrides.get("display_order", 1)
    tier.is_active = overrides.get("is_active", True)
    return tier


def _make_customer(**overrides: Any) -> MagicMock:
    """Create a mock Customer."""
    c = MagicMock()
    c.id = overrides.get("id", uuid4())
    c.first_name = overrides.get("first_name", "Jane")
    c.last_name = overrides.get("last_name", "Smith")
    c.phone = overrides.get("phone", "6125551234")
    return c


def _make_property(*, customer_id: Any | None = None, **overrides: Any) -> MagicMock:
    """Create a mock Property."""
    p = MagicMock()
    p.id = overrides.get("id", uuid4())
    p.customer_id = customer_id or uuid4()
    p.address = overrides.get("address", "123 Main St")
    p.city = overrides.get("city", "Eden Prairie")
    p.state = overrides.get("state", "MN")
    p.zip_code = overrides.get("zip_code", "55344")
    return p


def _make_agreement(
    *,
    tier: MagicMock | None = None,
    customer_id: Any | None = None,
    property_id: Any | None = None,
    **overrides: Any,
) -> MagicMock:
    """Create a mock ServiceAgreement linked to a tier."""
    agr = MagicMock()
    agr.id = overrides.get("id", uuid4())
    agr.customer_id = customer_id or uuid4()
    agr.property_id = property_id or uuid4()
    agr.tier_id = overrides.get("tier_id", uuid4())
    agr.tier = tier or _make_tier()
    agr.status = overrides.get("status", "active")
    agr.annual_price = overrides.get("annual_price", Decimal("399.00"))
    agr.agreement_number = overrides.get("agreement_number", "AGR-2026-001")
    return agr


# =============================================================================
# Tier fixtures
# =============================================================================

ESSENTIAL_TIER = {
    "name": "Essential",
    "slug": "essential-residential",
    "annual_price": Decimal("399.00"),
    "display_order": 1,
}

PROFESSIONAL_TIER = {
    "name": "Professional",
    "slug": "professional-residential",
    "annual_price": Decimal("599.00"),
    "display_order": 2,
}

PREMIUM_TIER = {
    "name": "Premium",
    "slug": "premium-residential",
    "annual_price": Decimal("999.00"),
    "display_order": 3,
}

WINTERIZATION_TIER = {
    "name": "Winterization Only",
    "slug": "winterization-only-residential",
    "annual_price": Decimal("149.00"),
    "display_order": 4,
}


# =============================================================================
# 1. Job Generation Produces Correct Priorities
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestJobGenerationPriorities:
    """Test job generation produces correct priority_level per tier.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
    """

    async def test_essential_tier_generates_priority_zero(self) -> None:
        """Essential tier jobs get priority_level=0 (normal)."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**ESSENTIAL_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) > 0
        for job in jobs:
            assert job.priority_level == 0
            assert job.service_agreement_id == agr.id

    async def test_professional_tier_generates_priority_one(self) -> None:
        """Professional tier jobs get priority_level=1 (high)."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**PROFESSIONAL_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) > 0
        for job in jobs:
            assert job.priority_level == 1
            assert job.service_agreement_id == agr.id

    async def test_premium_tier_generates_priority_two(self) -> None:
        """Premium tier jobs get priority_level=2 (urgent)."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**PREMIUM_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) > 0
        for job in jobs:
            assert job.priority_level == 2
            assert job.service_agreement_id == agr.id

    async def test_winterization_only_generates_priority_zero(self) -> None:
        """Winterization-only tier jobs get priority_level=0 (normal)."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**WINTERIZATION_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) > 0
        for job in jobs:
            assert job.priority_level == 0
            assert job.service_agreement_id == agr.id


# =============================================================================
# 2. Priority Persists Through Job Status Transitions
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestPriorityPersistsThroughTransitions:
    """Test priority_level remains unchanged through status lifecycle.

    Validates: Requirement 4.1
    """

    async def test_premium_priority_persists_through_full_lifecycle(
        self,
    ) -> None:
        """Premium job (priority=2) keeps priority through all transitions."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**PREMIUM_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)
        job = jobs[0]
        assert job.priority_level == 2

        # Simulate full lifecycle transitions
        lifecycle = [
            JobStatus.APPROVED.value,
            JobStatus.SCHEDULED.value,
            JobStatus.IN_PROGRESS.value,
            JobStatus.COMPLETED.value,
            JobStatus.CLOSED.value,
        ]

        for status in lifecycle:
            job.status = status
            assert job.priority_level == 2, (
                f"priority_level changed after transition to {status}"
            )

    async def test_professional_priority_persists_through_lifecycle(
        self,
    ) -> None:
        """Professional job (priority=1) keeps priority through transitions."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**PROFESSIONAL_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)
        job = jobs[0]
        assert job.priority_level == 1

        for status in [
            JobStatus.SCHEDULED.value,
            JobStatus.IN_PROGRESS.value,
            JobStatus.COMPLETED.value,
            JobStatus.CLOSED.value,
        ]:
            job.status = status
            assert job.priority_level == 1

    async def test_essential_priority_persists_through_lifecycle(
        self,
    ) -> None:
        """Essential job (priority=0) keeps priority through transitions."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**ESSENTIAL_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)
        job = jobs[0]
        assert job.priority_level == 0

        for status in [
            JobStatus.SCHEDULED.value,
            JobStatus.IN_PROGRESS.value,
            JobStatus.COMPLETED.value,
            JobStatus.CLOSED.value,
        ]:
            job.status = status
            assert job.priority_level == 0


# =============================================================================
# 3. Multiple Agreements Generate Independent Priority Batches
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestIndependentPriorityBatches:
    """Test multiple agreements produce independent priority batches.

    Validates: Requirement 4.2
    """

    async def test_three_tiers_generate_independent_batches(self) -> None:
        """Essential, Professional, Premium agreements produce separate batches."""
        session = AsyncMock()
        gen = JobGenerator(session)

        customer_id = uuid4()
        property_id = uuid4()

        essential_tier = _make_tier(**ESSENTIAL_TIER)
        professional_tier = _make_tier(**PROFESSIONAL_TIER)
        premium_tier = _make_tier(**PREMIUM_TIER)

        essential_agr = _make_agreement(
            tier=essential_tier,
            customer_id=customer_id,
            property_id=property_id,
        )
        professional_agr = _make_agreement(
            tier=professional_tier,
            customer_id=customer_id,
            property_id=property_id,
        )
        premium_agr = _make_agreement(
            tier=premium_tier,
            customer_id=customer_id,
            property_id=property_id,
        )

        essential_jobs = await gen.generate_jobs(essential_agr)
        professional_jobs = await gen.generate_jobs(professional_agr)
        premium_jobs = await gen.generate_jobs(premium_agr)

        # Verify each batch has uniform priority
        for job in essential_jobs:
            assert job.priority_level == 0
            assert job.service_agreement_id == essential_agr.id

        for job in professional_jobs:
            assert job.priority_level == 1
            assert job.service_agreement_id == professional_agr.id

        for job in premium_jobs:
            assert job.priority_level == 2
            assert job.service_agreement_id == premium_agr.id

        # Verify no cross-contamination: each batch linked to its own agreement
        essential_agr_ids = {j.service_agreement_id for j in essential_jobs}
        professional_agr_ids = {j.service_agreement_id for j in professional_jobs}
        premium_agr_ids = {j.service_agreement_id for j in premium_jobs}

        assert len(essential_agr_ids) == 1
        assert len(professional_agr_ids) == 1
        assert len(premium_agr_ids) == 1
        assert essential_agr_ids.isdisjoint(professional_agr_ids)
        assert essential_agr_ids.isdisjoint(premium_agr_ids)
        assert professional_agr_ids.isdisjoint(premium_agr_ids)


# =============================================================================
# 4. Job Count Per Tier Is Correct With Priority Set
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestJobCountPerTier:
    """Test each tier generates the correct number of jobs with priority.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """

    async def test_essential_generates_two_jobs_priority_zero(self) -> None:
        """Essential: 2 jobs, all priority 0."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**ESSENTIAL_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) == 2
        assert all(j.priority_level == 0 for j in jobs)

    async def test_professional_generates_three_jobs_priority_one(self) -> None:
        """Professional: 3 jobs, all priority 1."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**PROFESSIONAL_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) == 3
        assert all(j.priority_level == 1 for j in jobs)

    async def test_premium_generates_seven_jobs_priority_two(self) -> None:
        """Premium: 7 jobs, all priority 2."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**PREMIUM_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) == 7
        assert all(j.priority_level == 2 for j in jobs)

    async def test_winterization_generates_one_job_priority_zero(self) -> None:
        """Winterization-only: 1 job, priority 0."""
        session = AsyncMock()
        gen = JobGenerator(session)
        tier = _make_tier(**WINTERIZATION_TIER)
        agr = _make_agreement(tier=tier)

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) == 1
        assert jobs[0].priority_level == 0

    async def test_total_counts_across_all_tiers(self) -> None:
        """Verify total job counts: 2 + 3 + 7 + 1 = 13."""
        session = AsyncMock()
        gen = JobGenerator(session)

        all_jobs = []
        for tier_cfg, expected_count, expected_priority in [
            (ESSENTIAL_TIER, 2, 0),
            (PROFESSIONAL_TIER, 3, 1),
            (PREMIUM_TIER, 7, 2),
            (WINTERIZATION_TIER, 1, 0),
        ]:
            tier = _make_tier(**tier_cfg)
            agr = _make_agreement(tier=tier)
            jobs = await gen.generate_jobs(agr)
            assert len(jobs) == expected_count
            assert all(j.priority_level == expected_priority for j in jobs)
            all_jobs.extend(jobs)

        assert len(all_jobs) == 13
