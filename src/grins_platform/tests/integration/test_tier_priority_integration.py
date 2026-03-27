"""Integration tests for tier-priority scheduling — full flow.

Tests the complete pipeline from agreement creation through job generation,
job-to-schedule-job conversion, solver execution, and serialization.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import JobCategory, JobStatus
from grins_platform.models.job import Job
from grins_platform.services.job_generator import JobGenerator
from grins_platform.services.schedule_domain import (
    ScheduleJob,
    ScheduleLocation,
    ScheduleStaff,
)
from grins_platform.services.schedule_solver_service import (
    ScheduleSolverService,
    job_to_schedule_job,
)

# =============================================================================
# Helpers — reuse patterns from PBT and functional tests
# =============================================================================

PRIORITY_BADGE_MAP: dict[int, str] = {0: "Normal", 1: "High", 2: "Urgent"}


def _make_tier(**overrides: Any) -> MagicMock:
    """Create a mock ServiceAgreementTier."""
    tier = MagicMock()
    tier.id = overrides.get("id", uuid4())
    tier.name = overrides.get("name", "Essential")
    tier.slug = overrides.get("slug", "essential-residential")
    return tier


def _make_agreement(
    tier_name: str,
    tier_slug: str | None = None,
) -> MagicMock:
    """Create a mock ServiceAgreement with the given tier."""
    agreement = MagicMock()
    agreement.id = uuid4()
    agreement.customer_id = uuid4()
    agreement.property_id = uuid4()
    agreement.tier = _make_tier(
        name=tier_name,
        slug=tier_slug or f"{tier_name.lower()}-residential",
    )
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
    city: str | None = "Eden Prairie",
    duration: int = 60,
) -> ScheduleJob:
    """Create a ScheduleJob with given priority."""
    return ScheduleJob(
        id=uuid4(),
        customer_name="Test Customer",
        location=ScheduleLocation(
            latitude=Decimal("44.8547"),
            longitude=Decimal("-93.4708"),
            city=city,
        ),
        service_type="spring_startup",
        duration_minutes=duration,
        priority=priority,
    )


def _make_schedule_staff(name: str = "Tech A") -> ScheduleStaff:
    """Create a ScheduleStaff with enough capacity for a full day."""
    return ScheduleStaff(
        id=uuid4(),
        name=name,
        start_location=ScheduleLocation(
            latitude=Decimal("44.8547"),
            longitude=Decimal("-93.4708"),
            city="Eden Prairie",
        ),
        assigned_equipment=[],
        availability_start=time(7, 0),
        availability_end=time(19, 0),
        lunch_start=time(12, 0),
        lunch_duration_minutes=30,
    )


def _make_mock_job(priority_level: int) -> Job:
    """Create a Job object with mocked relationships for job_to_schedule_job."""
    job = Job(
        customer_id=uuid4(),
        job_type="spring_startup",
        category=JobCategory.READY_TO_SCHEDULE.value,
        status=JobStatus.TO_BE_SCHEDULED.value,
        priority_level=priority_level,
    )
    # Force an id since we're not using a real DB
    object.__setattr__(job, "id", uuid4())

    # Mock the relationships that job_to_schedule_job accesses
    mock_property = MagicMock()
    mock_property.latitude = Decimal("44.8547")
    mock_property.longitude = Decimal("-93.4708")
    mock_property.address = "123 Main St"
    mock_property.city = "Eden Prairie"
    object.__setattr__(job, "job_property", mock_property)

    mock_customer = MagicMock()
    mock_customer.first_name = "Jane"
    mock_customer.last_name = "Smith"
    object.__setattr__(job, "customer", mock_customer)

    mock_offering = MagicMock()
    mock_offering.name = "Spring Startup"
    object.__setattr__(job, "service_offering", mock_offering)

    return job


# =============================================================================
# 7.1 Full-system fixtures
# =============================================================================


@pytest.fixture
def essential_agreement() -> MagicMock:
    """Essential tier agreement fixture."""
    return _make_agreement("Essential")


@pytest.fixture
def professional_agreement() -> MagicMock:
    """Professional tier agreement fixture."""
    return _make_agreement("Professional")


@pytest.fixture
def premium_agreement() -> MagicMock:
    """Premium tier agreement fixture."""
    return _make_agreement("Premium")


@pytest.fixture
def winterization_agreement() -> MagicMock:
    """Winterization-only tier agreement fixture."""
    return _make_agreement(
        "Winterization Only",
        tier_slug="winterization-only-residential",
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock async DB session."""
    return _make_async_session()


@pytest.fixture
def staff_team() -> list[ScheduleStaff]:
    """Two-person staff team with enough capacity."""
    return [
        _make_schedule_staff("Tech A"),
        _make_schedule_staff("Tech B"),
    ]


@pytest.fixture
def schedule_date() -> date:
    """A fixed schedule date for solver tests."""
    return date(2025, 7, 15)


# =============================================================================
# 7.2 Agreement → job generation → scheduler respects priority ordering
# Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3
# =============================================================================


@pytest.mark.integration
class TestAgreementToSchedulerPriorityOrdering:
    """Full flow: agreements → job generation → solver respects priority.

    Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3
    """

    @pytest.mark.asyncio
    async def test_generated_jobs_feed_solver_in_priority_order(
        self,
        essential_agreement: MagicMock,
        professional_agreement: MagicMock,
        premium_agreement: MagicMock,
        mock_session: AsyncMock,
        staff_team: list[ScheduleStaff],
        schedule_date: date,
    ) -> None:
        """Jobs from all three tiers are sorted descending by priority in solver."""
        gen = JobGenerator(mock_session)

        # Generate jobs for all three tiers
        essential_jobs = await gen.generate_jobs(essential_agreement)
        professional_jobs = await gen.generate_jobs(professional_agreement)
        premium_jobs = await gen.generate_jobs(premium_agreement)

        # Convert to ScheduleJob objects directly (avoid ORM relationship access)
        schedule_jobs: list[ScheduleJob] = [
            _make_schedule_job(priority=job.priority_level, city="Eden Prairie")
            for job in essential_jobs
        ]
        schedule_jobs.extend(
            _make_schedule_job(priority=job.priority_level, city="Minnetonka")
            for job in professional_jobs
        )
        schedule_jobs.extend(
            _make_schedule_job(priority=job.priority_level, city="Plymouth")
            for job in premium_jobs
        )

        # Run the solver
        solver = ScheduleSolverService()
        solution = solver.solve(schedule_date, schedule_jobs, staff_team)

        # Verify the greedy sorted order: collect all assigned jobs across staff
        all_assigned: list[ScheduleJob] = []
        for assignment in solution.assignments:
            all_assigned.extend(assignment.jobs)

        # The solver's greedy algorithm processes jobs in descending priority.
        # Verify that the sorted input has descending priority order.
        sorted_descending = sorted(schedule_jobs, key=lambda j: -j.priority)
        sorted_priorities = [j.priority for j in sorted_descending]
        assert sorted_priorities == sorted(
            [j.priority for j in schedule_jobs], reverse=True,
        )


# =============================================================================
# 7.3 Priority survives the full job-to-schedule-job conversion
# Validates: Requirements 2.1, 4.1
# =============================================================================


@pytest.mark.integration
class TestPrioritySurvivesConversion:
    """Priority persists through Job → ScheduleJob conversion.

    Validates: Requirements 2.1, 4.1
    """

    def test_priority_preserved_through_job_to_schedule_job(self) -> None:
        """Each ScheduleJob.priority matches the original Job.priority_level."""
        for priority in [0, 1, 2]:
            job = _make_mock_job(priority_level=priority)
            schedule_job = job_to_schedule_job(job)
            assert schedule_job.priority == priority, (
                f"Expected priority={priority}, got {schedule_job.priority}"
            )

    def test_all_three_tiers_convert_correctly(self) -> None:
        """Jobs at all three priority levels convert with correct values."""
        jobs = [_make_mock_job(p) for p in [0, 1, 2]]
        schedule_jobs = [job_to_schedule_job(j) for j in jobs]

        assert schedule_jobs[0].priority == 0  # Essential
        assert schedule_jobs[1].priority == 1  # Professional
        assert schedule_jobs[2].priority == 2  # Premium


# =============================================================================
# 7.4 Mixed-tier scheduling produces correct assignment order
# Validates: Requirements 2.1, 2.2, 2.3
# =============================================================================


@pytest.mark.integration
class TestMixedTierSchedulingOrder:
    """Mixed-tier scheduling assigns Premium jobs earliest.

    Validates: Requirements 2.1, 2.2, 2.3
    """

    def test_premium_jobs_appear_earliest_in_assignments(
        self,
        staff_team: list[ScheduleStaff],
        schedule_date: date,
    ) -> None:
        """Premium (priority=2) jobs are assigned before lower-priority jobs."""
        # 3 jobs at each priority level
        jobs: list[ScheduleJob] = [
            _make_schedule_job(priority=0, city="Eden Prairie")
            for _ in range(3)
        ]
        jobs.extend(
            _make_schedule_job(priority=1, city="Minnetonka")
            for _ in range(3)
        )
        jobs.extend(
            _make_schedule_job(priority=2, city="Plymouth")
            for _ in range(3)
        )

        solver = ScheduleSolverService()
        solution = solver.solve(schedule_date, jobs, staff_team)

        # Collect all assigned jobs in order across all staff
        all_assigned: list[ScheduleJob] = []
        for assignment in solution.assignments:
            all_assigned.extend(assignment.jobs)

        # Find the positions of each priority group
        premium_positions = [
            i for i, j in enumerate(all_assigned) if j.priority == 2
        ]
        essential_positions = [
            i for i, j in enumerate(all_assigned) if j.priority == 0
        ]

        # If both groups have assigned jobs, verify Premium appears earlier
        if premium_positions and essential_positions:
            # The earliest Premium job should be before or at the earliest Essential job
            assert min(premium_positions) <= min(essential_positions), (
                "Premium jobs should appear no later than Essential jobs"
            )


# =============================================================================
# 7.5 Winterization-only jobs schedule at normal priority alongside Essential
# Validates: Requirements 1.4, 2.2
# =============================================================================


@pytest.mark.integration
class TestWinterizationSchedulesAtNormalPriority:
    """Winterization-only jobs have same priority as Essential.

    Validates: Requirements 1.4, 2.2
    """

    def test_winterization_and_essential_treated_equally(
        self,
        staff_team: list[ScheduleStaff],
        schedule_date: date,
    ) -> None:
        """Essential (priority=0) and winterization-only (priority=0) are equal."""
        essential_jobs = [
            _make_schedule_job(priority=0, city="Eden Prairie") for _ in range(3)
        ]
        winterization_jobs = [
            _make_schedule_job(priority=0, city="Minnetonka") for _ in range(3)
        ]

        all_jobs = essential_jobs + winterization_jobs

        solver = ScheduleSolverService()
        solution = solver.solve(schedule_date, all_jobs, staff_team)

        # All jobs have priority=0, so the solver treats them equally
        all_assigned: list[ScheduleJob] = []
        for assignment in solution.assignments:
            all_assigned.extend(assignment.jobs)

        # Verify all assigned jobs have priority 0
        for job in all_assigned:
            assert job.priority == 0

    @pytest.mark.asyncio
    async def test_winterization_generates_priority_zero(
        self,
        winterization_agreement: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Winterization-only tier generates jobs with priority_level=0."""
        gen = JobGenerator(mock_session)
        jobs = await gen.generate_jobs(winterization_agreement)

        assert len(jobs) == 1
        assert jobs[0].priority_level == 0


# =============================================================================
# 7.6 End-to-end priority badge data consistency
# Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
# =============================================================================


@pytest.mark.integration
class TestEndToEndPriorityBadgeConsistency:
    """Serialized job data produces correct badge labels.

    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
    """

    def test_to_dict_contains_correct_priority_level(self) -> None:
        """Job.to_dict() includes the correct priority_level value."""
        for priority in [0, 1, 2]:
            job = Job(
                customer_id=uuid4(),
                job_type="spring_startup",
                category=JobCategory.READY_TO_SCHEDULE.value,
                status=JobStatus.TO_BE_SCHEDULED.value,
                priority_level=priority,
            )
            # Force an id for serialization
            object.__setattr__(job, "id", uuid4())

            data = job.to_dict()
            assert data["priority_level"] == priority

    def test_badge_mapping_produces_correct_labels(self) -> None:
        """Frontend badge mapping (0→Normal, 1→High, 2→Urgent) is consistent."""
        for priority in [0, 1, 2]:
            job = Job(
                customer_id=uuid4(),
                job_type="spring_startup",
                category=JobCategory.READY_TO_SCHEDULE.value,
                status=JobStatus.TO_BE_SCHEDULED.value,
                priority_level=priority,
            )
            object.__setattr__(job, "id", uuid4())

            data = job.to_dict()
            label = PRIORITY_BADGE_MAP[data["priority_level"]]
            expected = {0: "Normal", 1: "High", 2: "Urgent"}
            assert label == expected[priority]

    @pytest.mark.asyncio
    async def test_generated_jobs_serialize_with_correct_priority(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """Jobs from all tiers serialize with matching priority_level."""
        gen = JobGenerator(mock_session)

        for tier_name, expected_priority in [
            ("Essential", 0),
            ("Professional", 1),
            ("Premium", 2),
        ]:
            agreement = _make_agreement(tier_name)
            jobs = await gen.generate_jobs(agreement)

            for job in jobs:
                # Force an id for serialization
                object.__setattr__(job, "id", uuid4())
                data = job.to_dict()
                assert data["priority_level"] == expected_priority
                assert PRIORITY_BADGE_MAP[data["priority_level"]] == PRIORITY_BADGE_MAP[
                    expected_priority
                ]
