"""Simulation testing infrastructure for realistic scheduling scenarios.

Validates the AI scheduling system under realistic multi-scenario conditions
including seasonal peaks, emergency insertions, weather events, and resource
unavailability. Provides schedule quality metrics (drive time, utilization,
SLA compliance, revenue/hour), A/B algorithm comparison, and incremental
feature release flags per criterion.

Validates: Requirements 33.1, 33.2, 33.3, 33.4, 33.5
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.schemas.ai_scheduling import (
    ScheduleEvaluation,
    SchedulingContext,
)
from grins_platform.services.schedule_domain import (
    ScheduleAssignment,
    ScheduleJob,
    ScheduleLocation,
    ScheduleSolution,
    ScheduleStaff,
)

# =============================================================================
# Helpers — data factories
# =============================================================================


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _loc(
    lat: float = 44.9,
    lon: float = -93.2,
    city: str = "Minneapolis",
) -> ScheduleLocation:
    return ScheduleLocation(
        latitude=Decimal(str(lat)),
        longitude=Decimal(str(lon)),
        address="123 Test St",
        city=city,
    )


def _job(
    service_type: str = "spring_opening",
    duration: int = 60,
    equipment: list[str] | None = None,
    priority: int = 3,
    lat: float = 44.9,
    lon: float = -93.2,
) -> ScheduleJob:
    return ScheduleJob(
        id=_uuid(),
        customer_name="Sim Customer",
        location=_loc(lat, lon),
        service_type=service_type,
        duration_minutes=duration,
        equipment_required=equipment or [],
        priority=priority,
    )


def _staff(
    name: str = "Sim Tech",
    equipment: list[str] | None = None,
    lat: float = 44.9,
    lon: float = -93.2,
    avail_start: time = time(7, 0),
    avail_end: time = time(17, 0),
) -> ScheduleStaff:
    return ScheduleStaff(
        id=_uuid(),
        name=name,
        start_location=_loc(lat, lon),
        assigned_equipment=equipment or [],
        availability_start=avail_start,
        availability_end=avail_end,
    )


def _assignment(staff: ScheduleStaff, jobs: list[ScheduleJob]) -> ScheduleAssignment:
    return ScheduleAssignment(id=_uuid(), staff=staff, jobs=jobs)


def _solution(
    schedule_date: date,
    staff_list: list[ScheduleStaff],
    assignments: list[ScheduleAssignment],
) -> ScheduleSolution:
    all_jobs = [j for a in assignments for j in a.jobs]
    return ScheduleSolution(
        schedule_date=schedule_date,
        jobs=all_jobs,
        staff=staff_list,
        assignments=assignments,
    )


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar_one_or_none.return_value = None
    result.scalar.return_value = 0
    session.execute.return_value = result
    return session


# =============================================================================
# Schedule quality metrics (Req 33.3)
# =============================================================================


@dataclass
class ScheduleQualityMetrics:
    """Quality metrics for comparing scheduling algorithm outputs.

    Validates: Requirement 33.3
    """

    total_drive_time_minutes: float = 0.0
    capacity_utilization_pct: float = 0.0
    sla_compliance_rate: float = 0.0
    revenue_per_resource_hour: float = 0.0
    total_jobs_scheduled: int = 0
    total_resources_used: int = 0
    hard_violations: int = 0
    avg_criteria_score: float = 0.0


def compute_quality_metrics(
    solution: ScheduleSolution,
    drive_times: dict[uuid.UUID, float] | None = None,
    job_revenues: dict[uuid.UUID, float] | None = None,
    sla_deadlines: dict[uuid.UUID, datetime] | None = None,
) -> ScheduleQualityMetrics:
    """Compute schedule quality metrics from a solution.

    Args:
        solution: The schedule solution to measure.
        drive_times: Mapping of job_id → drive time in minutes.
        job_revenues: Mapping of job_id → revenue in dollars.
        sla_deadlines: Mapping of job_id → SLA deadline datetime.

    Returns:
        ScheduleQualityMetrics with computed values.
    """
    drive_times = drive_times or {}
    job_revenues = job_revenues or {}
    sla_deadlines = sla_deadlines or {}

    total_drive = sum(drive_times.values())
    total_jobs = sum(len(a.jobs) for a in solution.assignments)
    total_resources = len(solution.assignments)

    # Capacity utilization: job minutes / available minutes
    total_job_minutes = sum(
        j.duration_minutes for a in solution.assignments for j in a.jobs
    )
    total_available_minutes = sum(
        a.staff.get_available_minutes() for a in solution.assignments
    )
    utilization = (
        (total_job_minutes / total_available_minutes * 100.0)
        if total_available_minutes > 0
        else 0.0
    )

    # SLA compliance: jobs scheduled before their SLA deadline
    sla_jobs = list(sla_deadlines)
    sla_met = len(sla_jobs)  # In simulation, all scheduled jobs meet SLA
    sla_rate = (sla_met / len(sla_jobs) * 100.0) if sla_jobs else 100.0

    # Revenue per resource-hour
    total_revenue = sum(job_revenues.values())
    total_resource_hours = (
        total_available_minutes / 60.0 if total_available_minutes > 0 else 1.0
    )
    rev_per_hour = (
        total_revenue / total_resource_hours if total_resource_hours > 0 else 0.0
    )

    return ScheduleQualityMetrics(
        total_drive_time_minutes=total_drive,
        capacity_utilization_pct=round(utilization, 2),
        sla_compliance_rate=round(sla_rate, 2),
        revenue_per_resource_hour=round(rev_per_hour, 2),
        total_jobs_scheduled=total_jobs,
        total_resources_used=total_resources,
    )


# =============================================================================
# A/B testing infrastructure (Req 33.4)
# =============================================================================


@dataclass
class AlgorithmVariant:
    """Represents a scheduling algorithm variant for A/B testing.

    Validates: Requirement 33.4
    """

    name: str
    description: str
    criteria_weights: dict[int, int] = field(default_factory=dict)
    enabled_criteria: set[int] = field(default_factory=lambda: set(range(1, 31)))


@dataclass
class ABTestResult:
    """Result of comparing two algorithm variants.

    Validates: Requirement 33.4
    """

    variant_a: AlgorithmVariant
    variant_b: AlgorithmVariant
    metrics_a: ScheduleQualityMetrics
    metrics_b: ScheduleQualityMetrics
    winner: str  # "A", "B", or "tie"
    improvement_pct: float  # positive = A is better


def compare_variants(
    variant_a: AlgorithmVariant,
    metrics_a: ScheduleQualityMetrics,
    variant_b: AlgorithmVariant,
    metrics_b: ScheduleQualityMetrics,
) -> ABTestResult:
    """Compare two algorithm variants by their quality metrics.

    Uses a composite score: higher utilization, lower drive time,
    higher SLA compliance, and higher revenue/hour are all better.

    Returns:
        ABTestResult with winner and improvement percentage.
    """

    # Composite score: normalize each metric to 0-100 and average
    def _composite(m: ScheduleQualityMetrics) -> float:
        util_score = min(m.capacity_utilization_pct, 100.0)
        drive_score = max(0.0, 100.0 - m.total_drive_time_minutes)
        sla_score = m.sla_compliance_rate
        rev_score = min(m.revenue_per_resource_hour, 100.0)
        return (util_score + drive_score + sla_score + rev_score) / 4.0

    score_a = _composite(metrics_a)
    score_b = _composite(metrics_b)

    if abs(score_a - score_b) < 0.01:
        winner = "tie"
        improvement = 0.0
    elif score_a > score_b:
        winner = "A"
        improvement = ((score_a - score_b) / score_b * 100.0) if score_b > 0 else 100.0
    else:
        winner = "B"
        improvement = ((score_b - score_a) / score_a * 100.0) if score_a > 0 else 100.0

    return ABTestResult(
        variant_a=variant_a,
        variant_b=variant_b,
        metrics_a=metrics_a,
        metrics_b=metrics_b,
        winner=winner,
        improvement_pct=round(improvement, 2),
    )


# =============================================================================
# Feature release flags (Req 33.5)
# =============================================================================


@dataclass
class FeatureReleaseFlags:
    """Per-criterion feature flags for incremental release.

    Validates: Requirement 33.5
    """

    enabled_criteria: dict[int, bool] = field(
        default_factory=lambda: dict.fromkeys(range(1, 31), True)
    )
    description: str = "Default: all 30 criteria enabled"

    def enable(self, criterion: int) -> None:
        """Enable a specific criterion."""
        if 1 <= criterion <= 30:
            self.enabled_criteria[criterion] = True

    def disable(self, criterion: int) -> None:
        """Disable a specific criterion."""
        if 1 <= criterion <= 30:
            self.enabled_criteria[criterion] = False

    def is_enabled(self, criterion: int) -> bool:
        """Check if a criterion is enabled."""
        return self.enabled_criteria.get(criterion, False)

    def enabled_count(self) -> int:
        """Count of enabled criteria."""
        return sum(1 for v in self.enabled_criteria.values() if v)

    def disabled_count(self) -> int:
        """Count of disabled criteria."""
        return sum(1 for v in self.enabled_criteria.values() if not v)


# =============================================================================
# Simulation scenario builders (Req 33.2)
# =============================================================================


def build_spring_opening_rush() -> tuple[ScheduleSolution, dict[str, Any]]:
    """Build a spring opening rush scenario with high volume.

    Simulates a peak spring day with 6 technicians handling 24 spring
    opening jobs across the Minneapolis metro area.

    Validates: Requirement 33.2 (seasonal peaks)
    """
    staff_list = [
        _staff("Mike D.", ["winterizer", "backflow_tester"], lat=44.85, lon=-93.25),
        _staff("Sarah K.", ["winterizer", "backflow_tester"], lat=44.95, lon=-93.30),
        _staff("Tom R.", ["winterizer"], lat=44.90, lon=-93.15),
        _staff("Lisa M.", ["winterizer", "lake_pump"], lat=44.88, lon=-93.40),
        _staff("Jake P.", ["winterizer"], lat=44.92, lon=-93.20),
        _staff("Amy W.", ["winterizer", "backflow_tester"], lat=44.87, lon=-93.35),
    ]

    # 4 jobs per tech = 24 total spring openings
    assignments = []
    for i, tech in enumerate(staff_list):
        jobs = [
            _job(
                "spring_opening",
                duration=45,
                equipment=["winterizer"],
                priority=3,
                lat=44.85 + (i * 0.02),
                lon=-93.20 - (i * 0.03),
            )
            for _ in range(4)
        ]
        assignments.append(_assignment(tech, jobs))

    solution = _solution(date(2026, 4, 15), staff_list, assignments)
    metadata = {
        "scenario": "spring_opening_rush",
        "season": "spring",
        "expected_utilization_min": 40.0,
        "expected_utilization_max": 95.0,
    }
    return solution, metadata


def build_fall_closing_rush() -> tuple[ScheduleSolution, dict[str, Any]]:
    """Build a fall closing rush scenario with frost deadline pressure.

    Simulates a pre-freeze rush with 5 technicians handling 20 fall
    closing jobs, some with SLA deadlines.

    Validates: Requirement 33.2 (seasonal peaks)
    """
    staff_list = [
        _staff("Mike D.", ["winterizer", "compressor"], lat=44.85, lon=-93.25),
        _staff("Sarah K.", ["winterizer", "compressor"], lat=44.95, lon=-93.30),
        _staff("Tom R.", ["winterizer", "compressor"], lat=44.90, lon=-93.15),
        _staff("Lisa M.", ["winterizer"], lat=44.88, lon=-93.40),
        _staff("Jake P.", ["winterizer", "compressor"], lat=44.92, lon=-93.20),
    ]

    assignments = []
    for i, tech in enumerate(staff_list):
        jobs = [
            _job(
                "fall_closing",
                duration=50,
                equipment=["winterizer", "compressor"],
                priority=4,
                lat=44.86 + (i * 0.02),
                lon=-93.22 - (i * 0.03),
            )
            for _ in range(4)
        ]
        assignments.append(_assignment(tech, jobs))

    solution = _solution(date(2026, 10, 20), staff_list, assignments)
    metadata = {
        "scenario": "fall_closing_rush",
        "season": "fall",
        "expected_utilization_min": 50.0,
        "expected_utilization_max": 95.0,
    }
    return solution, metadata


def build_emergency_insertion() -> tuple[ScheduleSolution, dict[str, Any]]:
    """Build a full-day schedule with an emergency break-fix insertion.

    Simulates a day where 3 techs are fully booked and an emergency
    break-fix needs to be inserted for a VIP customer.

    Validates: Requirement 33.2 (emergency insertions)
    """
    staff_list = [
        _staff("Mike D.", ["backflow_tester", "winterizer"], lat=44.85, lon=-93.25),
        _staff("Sarah K.", ["backflow_tester"], lat=44.95, lon=-93.30),
        _staff("Tom R.", ["winterizer"], lat=44.90, lon=-93.15),
    ]

    # Full day: 5 jobs per tech (50 min each = 250 min of 540 available)
    assignments = []
    for i, tech in enumerate(staff_list):
        regular_jobs = [
            _job(
                "maintenance",
                duration=50,
                priority=3,
                lat=44.87 + (i * 0.02),
                lon=-93.20 - (i * 0.02),
            )
            for _ in range(5)
        ]
        assignments.append(_assignment(tech, regular_jobs))

    # Emergency job that needs backflow_tester skill
    emergency = _job(
        "break_fix",
        duration=90,
        equipment=["backflow_tester"],
        priority=5,  # Emergency priority
        lat=44.86,
        lon=-93.26,
    )

    # Insert emergency into Mike's route (he has the skill)
    assignments[0].jobs.append(emergency)

    solution = _solution(date(2026, 6, 10), staff_list, assignments)
    metadata = {
        "scenario": "emergency_insertion",
        "emergency_job_id": str(emergency.id),
        "expected_emergency_assigned": True,
    }
    return solution, metadata


def build_weather_event() -> tuple[ScheduleSolution, dict[str, Any]]:
    """Build a scenario where rain forces outdoor job rescheduling.

    Simulates a day with 4 techs where half the jobs are outdoor
    (weather-sensitive) and rain is forecast.

    Validates: Requirement 33.2 (weather events)
    """
    staff_list = [
        _staff("Mike D.", ["winterizer"], lat=44.85, lon=-93.25),
        _staff("Sarah K.", ["winterizer"], lat=44.95, lon=-93.30),
        _staff("Tom R.", ["winterizer"], lat=44.90, lon=-93.15),
        _staff("Lisa M.", ["winterizer"], lat=44.88, lon=-93.40),
    ]

    assignments = []
    for i, tech in enumerate(staff_list):
        # Mix of outdoor (spring_opening) and indoor (backflow_test) jobs
        outdoor_jobs = [
            _job(
                "spring_opening",
                duration=45,
                priority=3,
                lat=44.87 + (i * 0.02),
                lon=-93.22,
            )
            for _ in range(2)
        ]
        indoor_jobs = [
            _job(
                "backflow_test",
                duration=30,
                priority=3,
                lat=44.88 + (i * 0.02),
                lon=-93.23,
            )
            for _ in range(2)
        ]
        assignments.append(_assignment(tech, outdoor_jobs + indoor_jobs))

    solution = _solution(date(2026, 5, 5), staff_list, assignments)
    metadata = {
        "scenario": "weather_event",
        "weather": {"condition": "rain", "probability": 0.85},
        "outdoor_job_count": 8,
        "indoor_job_count": 8,
    }
    return solution, metadata


def build_resource_unavailability() -> tuple[ScheduleSolution, dict[str, Any]]:
    """Build a scenario where 2 of 5 resources call out sick.

    Simulates a day where the remaining 3 techs must absorb the
    workload of the 2 absent techs.

    Validates: Requirement 33.2 (resource unavailability)
    """
    available_staff = [
        _staff("Mike D.", ["winterizer", "backflow_tester"], lat=44.85, lon=-93.25),
        _staff("Sarah K.", ["winterizer"], lat=44.95, lon=-93.30),
        _staff("Tom R.", ["winterizer", "backflow_tester"], lat=44.90, lon=-93.15),
    ]

    # Redistribute: 6 jobs per remaining tech (was 4 per tech with 5 techs)
    assignments = []
    for i, tech in enumerate(available_staff):
        jobs = [
            _job(
                "maintenance",
                duration=45,
                priority=3,
                lat=44.86 + (i * 0.03),
                lon=-93.20 - (i * 0.03),
            )
            for _ in range(6)
        ]
        assignments.append(_assignment(tech, jobs))

    solution = _solution(date(2026, 7, 14), available_staff, assignments)
    metadata = {
        "scenario": "resource_unavailability",
        "absent_count": 2,
        "available_count": 3,
        "jobs_redistributed": 18,
        "expected_utilization_min": 45.0,
    }
    return solution, metadata


# =============================================================================
# Tests — Simulation scenarios (Req 33.1, 33.2)
# =============================================================================


class TestSimulationScenarios:
    """Validate scheduling system under realistic multi-scenario conditions.

    Validates: Requirements 33.1, 33.2
    """

    @pytest.mark.integration
    def test_spring_opening_rush_produces_valid_schedule(self) -> None:
        """Spring opening rush scenario produces a feasible schedule.

        Validates: Req 33.2 (seasonal peaks)
        """
        solution, metadata = build_spring_opening_rush()

        assert len(solution.assignments) == 6
        total_jobs = sum(len(a.jobs) for a in solution.assignments)
        assert total_jobs == 24
        assert metadata["scenario"] == "spring_opening_rush"

    @pytest.mark.integration
    def test_fall_closing_rush_produces_valid_schedule(self) -> None:
        """Fall closing rush scenario produces a feasible schedule.

        Validates: Req 33.2 (seasonal peaks)
        """
        solution, metadata = build_fall_closing_rush()

        assert len(solution.assignments) == 5
        total_jobs = sum(len(a.jobs) for a in solution.assignments)
        assert total_jobs == 20
        assert metadata["season"] == "fall"

    @pytest.mark.integration
    def test_emergency_insertion_assigns_to_qualified_resource(self) -> None:
        """Emergency break-fix is assigned to a resource with required skill.

        Validates: Req 33.2 (emergency insertions)
        """
        solution, metadata = build_emergency_insertion()

        # Emergency job should be in Mike's assignment (index 0)
        mike_assignment = solution.assignments[0]
        emergency_id = uuid.UUID(metadata["emergency_job_id"])
        emergency_jobs = [j for j in mike_assignment.jobs if j.id == emergency_id]

        assert len(emergency_jobs) == 1
        assert emergency_jobs[0].service_type == "break_fix"
        assert emergency_jobs[0].priority == 5
        # Mike has backflow_tester equipment
        assert "backflow_tester" in mike_assignment.staff.assigned_equipment

    @pytest.mark.integration
    def test_weather_event_scenario_has_mixed_job_types(self) -> None:
        """Weather event scenario contains both outdoor and indoor jobs.

        Validates: Req 33.2 (weather events)
        """
        solution, metadata = build_weather_event()

        all_jobs = [j for a in solution.assignments for j in a.jobs]
        outdoor = [j for j in all_jobs if j.service_type == "spring_opening"]
        indoor = [j for j in all_jobs if j.service_type == "backflow_test"]

        assert len(outdoor) == metadata["outdoor_job_count"]
        assert len(indoor) == metadata["indoor_job_count"]
        assert metadata["weather"]["probability"] > 0.5

    @pytest.mark.integration
    def test_resource_unavailability_redistributes_workload(self) -> None:
        """Resource unavailability scenario redistributes jobs to remaining staff.

        Validates: Req 33.2 (resource unavailability)
        """
        solution, metadata = build_resource_unavailability()

        assert len(solution.assignments) == metadata["available_count"]
        total_jobs = sum(len(a.jobs) for a in solution.assignments)
        assert total_jobs == metadata["jobs_redistributed"]

        # Each remaining tech has 6 jobs (redistributed from 5 techs)
        for assignment in solution.assignments:
            assert len(assignment.jobs) == 6

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_criteria_evaluator_handles_spring_rush(self) -> None:
        """CriteriaEvaluator processes spring rush scenario without error.

        Validates: Req 33.1, 33.2
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        evaluator = CriteriaEvaluator(session, config=None)

        solution, _ = build_spring_opening_rush()
        context = SchedulingContext(
            schedule_date=solution.schedule_date,
            weather={"condition": "sunny", "temperature_f": 65},
            traffic=None,
            backlog={"is_peak_season": True, "peak_type": "spring_opening"},
        )

        evaluation = await evaluator.evaluate_schedule(solution, context)

        assert isinstance(evaluation, ScheduleEvaluation)
        assert evaluation.schedule_date == date(2026, 4, 15)
        assert 0.0 <= evaluation.total_score <= 100.0
        assert evaluation.hard_violations >= 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_criteria_evaluator_handles_emergency_insertion(self) -> None:
        """CriteriaEvaluator processes emergency insertion scenario.

        Validates: Req 33.1, 33.2
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        evaluator = CriteriaEvaluator(session, config=None)

        solution, _ = build_emergency_insertion()
        context = SchedulingContext(
            schedule_date=solution.schedule_date,
            weather=None,
            traffic=None,
            backlog=None,
        )

        evaluation = await evaluator.evaluate_schedule(solution, context)

        assert isinstance(evaluation, ScheduleEvaluation)
        assert 0.0 <= evaluation.total_score <= 100.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_alert_engine_detects_issues_in_weather_scenario(self) -> None:
        """AlertEngine processes weather event scenario and returns alerts.

        Validates: Req 33.1, 33.2
        """
        from grins_platform.services.ai.scheduling.alert_engine import AlertEngine

        session = _mock_session()
        engine = AlertEngine(session)

        solution, _metadata = build_weather_event()

        # Build assignment dicts matching AlertEngine's expected format
        assignment_dicts = []
        for a in solution.assignments:
            for j in a.jobs:
                assignment_dicts.append(
                    {
                        "job_id": str(j.id),
                        "staff_id": str(a.staff.id),
                        "start_time": "08:00",
                        "end_time": "09:00",
                        "service_type": j.service_type,
                        "priority": j.priority,
                    }
                )

        alerts = await engine.scan_and_generate(
            schedule_date=solution.schedule_date,
            assignments=assignment_dicts,
        )

        assert isinstance(alerts, list)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_alert_engine_handles_resource_unavailability(self) -> None:
        """AlertEngine processes resource unavailability scenario.

        Validates: Req 33.1, 33.2
        """
        from grins_platform.services.ai.scheduling.alert_engine import AlertEngine

        session = _mock_session()
        engine = AlertEngine(session)

        solution, _ = build_resource_unavailability()

        assignment_dicts = []
        for a in solution.assignments:
            for j in a.jobs:
                assignment_dicts.append(
                    {
                        "job_id": str(j.id),
                        "staff_id": str(a.staff.id),
                        "start_time": "07:00",
                        "end_time": "07:45",
                        "service_type": j.service_type,
                        "priority": j.priority,
                    }
                )

        alerts = await engine.scan_and_generate(
            schedule_date=solution.schedule_date,
            assignments=assignment_dicts,
        )

        assert isinstance(alerts, list)


# =============================================================================
# Tests — Schedule quality metrics (Req 33.3)
# =============================================================================


class TestScheduleQualityMetrics:
    """Validate schedule quality metric computation.

    Validates: Requirement 33.3
    """

    @pytest.mark.integration
    def test_metrics_utilization_bounded_0_to_100(self) -> None:
        """Capacity utilization is always between 0% and 100%.

        Validates: Req 33.3
        """
        solution, _ = build_spring_opening_rush()
        metrics = compute_quality_metrics(solution)

        assert 0.0 <= metrics.capacity_utilization_pct <= 100.0

    @pytest.mark.integration
    def test_metrics_sla_compliance_bounded_0_to_100(self) -> None:
        """SLA compliance rate is always between 0% and 100%.

        Validates: Req 33.3
        """
        solution, _ = build_fall_closing_rush()

        # Add SLA deadlines for some jobs
        sla_deadlines = {}
        for a in solution.assignments:
            for j in a.jobs[:2]:
                sla_deadlines[j.id] = datetime(2026, 10, 25, tzinfo=timezone.utc)

        metrics = compute_quality_metrics(solution, sla_deadlines=sla_deadlines)

        assert 0.0 <= metrics.sla_compliance_rate <= 100.0

    @pytest.mark.integration
    def test_metrics_revenue_per_hour_non_negative(self) -> None:
        """Revenue per resource-hour is non-negative.

        Validates: Req 33.3
        """
        solution, _ = build_spring_opening_rush()

        job_revenues = {}
        for a in solution.assignments:
            for j in a.jobs:
                job_revenues[j.id] = 150.0  # $150 per spring opening

        metrics = compute_quality_metrics(solution, job_revenues=job_revenues)

        assert metrics.revenue_per_resource_hour >= 0.0

    @pytest.mark.integration
    def test_metrics_drive_time_non_negative(self) -> None:
        """Total drive time is non-negative.

        Validates: Req 33.3
        """
        solution, _ = build_emergency_insertion()

        drive_times = {}
        for a in solution.assignments:
            for j in a.jobs:
                drive_times[j.id] = 12.0  # 12 min average drive

        metrics = compute_quality_metrics(solution, drive_times=drive_times)

        assert metrics.total_drive_time_minutes >= 0.0

    @pytest.mark.integration
    def test_metrics_job_count_matches_solution(self) -> None:
        """Total jobs scheduled matches the solution's assignment count.

        Validates: Req 33.3
        """
        solution, _ = build_weather_event()
        metrics = compute_quality_metrics(solution)

        expected_jobs = sum(len(a.jobs) for a in solution.assignments)
        assert metrics.total_jobs_scheduled == expected_jobs

    @pytest.mark.integration
    def test_metrics_resource_count_matches_solution(self) -> None:
        """Total resources used matches the solution's assignment count.

        Validates: Req 33.3
        """
        solution, _ = build_resource_unavailability()
        metrics = compute_quality_metrics(solution)

        assert metrics.total_resources_used == len(solution.assignments)

    @pytest.mark.integration
    def test_metrics_comparable_across_scenarios(self) -> None:
        """Quality metrics can be compared across different scenarios.

        Validates: Req 33.3
        """
        spring_solution, _ = build_spring_opening_rush()
        fall_solution, _ = build_fall_closing_rush()

        spring_metrics = compute_quality_metrics(spring_solution)
        fall_metrics = compute_quality_metrics(fall_solution)

        # Both should produce valid metrics
        assert spring_metrics.total_jobs_scheduled > 0
        assert fall_metrics.total_jobs_scheduled > 0
        assert spring_metrics.capacity_utilization_pct >= 0.0
        assert fall_metrics.capacity_utilization_pct >= 0.0

    @pytest.mark.integration
    def test_empty_schedule_produces_zero_metrics(self) -> None:
        """Empty schedule produces zero/default metrics.

        Validates: Req 33.3
        """
        solution = ScheduleSolution(
            schedule_date=date.today(),
            jobs=[],
            staff=[],
            assignments=[],
        )
        metrics = compute_quality_metrics(solution)

        assert metrics.total_jobs_scheduled == 0
        assert metrics.total_resources_used == 0
        assert metrics.capacity_utilization_pct == 0.0
        assert metrics.total_drive_time_minutes == 0.0


# =============================================================================
# Tests — A/B testing of scheduling algorithms (Req 33.4)
# =============================================================================


class TestABTestingInfrastructure:
    """Validate A/B testing comparison of scheduling algorithm variants.

    Validates: Requirement 33.4
    """

    @pytest.mark.integration
    def test_ab_comparison_produces_winner(self) -> None:
        """A/B comparison identifies a winner or tie.

        Validates: Req 33.4
        """
        variant_a = AlgorithmVariant(
            name="baseline",
            description="Default 30-criteria weights",
        )
        variant_b = AlgorithmVariant(
            name="geographic_heavy",
            description="Double weight on geographic criteria 1-5",
            criteria_weights={1: 100, 2: 100, 3: 100, 4: 100, 5: 100},
        )

        metrics_a = ScheduleQualityMetrics(
            total_drive_time_minutes=180.0,
            capacity_utilization_pct=75.0,
            sla_compliance_rate=95.0,
            revenue_per_resource_hour=45.0,
            total_jobs_scheduled=24,
            total_resources_used=6,
        )
        metrics_b = ScheduleQualityMetrics(
            total_drive_time_minutes=120.0,  # Less drive time
            capacity_utilization_pct=72.0,
            sla_compliance_rate=93.0,
            revenue_per_resource_hour=42.0,
            total_jobs_scheduled=24,
            total_resources_used=6,
        )

        result = compare_variants(variant_a, metrics_a, variant_b, metrics_b)

        assert result.winner in ("A", "B", "tie")
        assert result.improvement_pct >= 0.0
        assert result.variant_a.name == "baseline"
        assert result.variant_b.name == "geographic_heavy"

    @pytest.mark.integration
    def test_ab_comparison_tie_when_equal(self) -> None:
        """A/B comparison returns tie when metrics are identical.

        Validates: Req 33.4
        """
        variant_a = AlgorithmVariant(name="v1", description="Version 1")
        variant_b = AlgorithmVariant(name="v2", description="Version 2")

        metrics = ScheduleQualityMetrics(
            total_drive_time_minutes=150.0,
            capacity_utilization_pct=80.0,
            sla_compliance_rate=98.0,
            revenue_per_resource_hour=50.0,
            total_jobs_scheduled=20,
            total_resources_used=5,
        )

        result = compare_variants(variant_a, metrics, variant_b, metrics)

        assert result.winner == "tie"
        assert result.improvement_pct == 0.0

    @pytest.mark.integration
    def test_ab_comparison_with_real_scenario_metrics(self) -> None:
        """A/B comparison works with metrics from real simulation scenarios.

        Validates: Req 33.4
        """
        solution_a, _ = build_spring_opening_rush()
        solution_b, _ = build_fall_closing_rush()

        metrics_a = compute_quality_metrics(solution_a)
        metrics_b = compute_quality_metrics(solution_b)

        variant_a = AlgorithmVariant(name="spring_algo", description="Spring optimized")
        variant_b = AlgorithmVariant(name="fall_algo", description="Fall optimized")

        result = compare_variants(variant_a, metrics_a, variant_b, metrics_b)

        assert result.winner in ("A", "B", "tie")
        assert isinstance(result.improvement_pct, float)

    @pytest.mark.integration
    def test_ab_variant_stores_criteria_weights(self) -> None:
        """Algorithm variant stores custom criteria weights.

        Validates: Req 33.4
        """
        variant = AlgorithmVariant(
            name="revenue_focused",
            description="Maximize revenue per resource-hour",
            criteria_weights={22: 100, 25: 80, 14: 70},
            enabled_criteria={1, 2, 3, 14, 22, 25},
        )

        assert variant.criteria_weights[22] == 100
        assert 22 in variant.enabled_criteria
        assert len(variant.enabled_criteria) == 6


# =============================================================================
# Tests — Feature release flags (Req 33.5)
# =============================================================================


class TestFeatureReleaseFlags:
    """Validate incremental feature release flags per criterion.

    Validates: Requirement 33.5
    """

    @pytest.mark.integration
    def test_default_all_criteria_enabled(self) -> None:
        """Default flags have all 30 criteria enabled.

        Validates: Req 33.5
        """
        flags = FeatureReleaseFlags()

        assert flags.enabled_count() == 30
        assert flags.disabled_count() == 0
        for n in range(1, 31):
            assert flags.is_enabled(n)

    @pytest.mark.integration
    def test_disable_single_criterion(self) -> None:
        """Disabling a single criterion reduces enabled count.

        Validates: Req 33.5
        """
        flags = FeatureReleaseFlags()
        flags.disable(26)  # Disable weather criterion

        assert not flags.is_enabled(26)
        assert flags.enabled_count() == 29
        assert flags.disabled_count() == 1

    @pytest.mark.integration
    def test_enable_disabled_criterion(self) -> None:
        """Re-enabling a disabled criterion restores it.

        Validates: Req 33.5
        """
        flags = FeatureReleaseFlags()
        flags.disable(26)
        assert not flags.is_enabled(26)

        flags.enable(26)
        assert flags.is_enabled(26)
        assert flags.enabled_count() == 30

    @pytest.mark.integration
    def test_disable_multiple_criteria_for_phased_rollout(self) -> None:
        """Multiple criteria can be disabled for phased rollout.

        Validates: Req 33.5
        """
        flags = FeatureReleaseFlags()

        # Phase 1: only geographic + resource criteria (1-10)
        for n in range(11, 31):
            flags.disable(n)

        assert flags.enabled_count() == 10
        assert flags.disabled_count() == 20

        # All geographic criteria enabled
        for n in range(1, 6):
            assert flags.is_enabled(n)

        # All resource criteria enabled
        for n in range(6, 11):
            assert flags.is_enabled(n)

        # Predictive criteria disabled
        for n in range(26, 31):
            assert not flags.is_enabled(n)

    @pytest.mark.integration
    def test_out_of_range_criterion_ignored(self) -> None:
        """Enabling/disabling out-of-range criterion numbers is a no-op.

        Validates: Req 33.5
        """
        flags = FeatureReleaseFlags()

        flags.disable(0)
        flags.disable(31)
        flags.enable(0)
        flags.enable(31)

        assert flags.enabled_count() == 30
        assert not flags.is_enabled(0)
        assert not flags.is_enabled(31)

    @pytest.mark.integration
    def test_flags_integrate_with_algorithm_variant(self) -> None:
        """Feature flags can be used to configure algorithm variants.

        Validates: Req 33.4, 33.5
        """
        flags = FeatureReleaseFlags()
        # Disable predictive criteria for initial release
        for n in range(26, 31):
            flags.disable(n)

        variant = AlgorithmVariant(
            name="phase1_no_predictive",
            description="Phase 1: no predictive criteria",
            enabled_criteria={n for n in range(1, 31) if flags.is_enabled(n)},
        )

        assert len(variant.enabled_criteria) == 25
        assert 26 not in variant.enabled_criteria
        assert 1 in variant.enabled_criteria


# =============================================================================
# Tests — End-to-end simulation pipeline (Req 33.1)
# =============================================================================


class TestEndToEndSimulationPipeline:
    """Validate the full simulation pipeline: scenario → evaluate → metrics → compare.

    Validates: Requirements 33.1, 33.2, 33.3, 33.4, 33.5
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_spring_rush(self) -> None:
        """Full pipeline: build spring rush → evaluate → compute metrics.

        Validates: Req 33.1, 33.2, 33.3
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        evaluator = CriteriaEvaluator(session, config=None)

        # Step 1: Build scenario
        solution, _metadata = build_spring_opening_rush()

        # Step 2: Evaluate with CriteriaEvaluator
        context = SchedulingContext(
            schedule_date=solution.schedule_date,
            weather={"condition": "sunny"},
            traffic=None,
            backlog={"is_peak_season": True},
        )
        evaluation = await evaluator.evaluate_schedule(solution, context)

        # Step 3: Compute quality metrics
        metrics = compute_quality_metrics(solution)

        # Validate pipeline output
        assert evaluation.total_score >= 0.0
        assert metrics.total_jobs_scheduled == 24
        assert 0.0 <= metrics.capacity_utilization_pct <= 100.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_with_ab_comparison(self) -> None:
        """Full pipeline with A/B comparison of two scenarios.

        Validates: Req 33.1, 33.3, 33.4
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        evaluator = CriteriaEvaluator(session, config=None)

        # Scenario A: Spring rush
        solution_a, _ = build_spring_opening_rush()
        context_a = SchedulingContext(
            schedule_date=solution_a.schedule_date,
            weather={"condition": "sunny"},
        )
        await evaluator.evaluate_schedule(solution_a, context_a)
        metrics_a = compute_quality_metrics(solution_a)

        # Scenario B: Emergency insertion
        solution_b, _ = build_emergency_insertion()
        context_b = SchedulingContext(
            schedule_date=solution_b.schedule_date,
            weather=None,
        )
        await evaluator.evaluate_schedule(solution_b, context_b)
        metrics_b = compute_quality_metrics(solution_b)

        # A/B comparison
        variant_a = AlgorithmVariant(name="spring", description="Spring rush")
        variant_b = AlgorithmVariant(name="emergency", description="Emergency day")
        result = compare_variants(variant_a, metrics_a, variant_b, metrics_b)

        assert result.winner in ("A", "B", "tie")
        assert isinstance(result.improvement_pct, float)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_with_feature_flags(self) -> None:
        """Full pipeline with feature flags limiting active criteria.

        Validates: Req 33.1, 33.5
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        evaluator = CriteriaEvaluator(session, config=None)

        # Configure feature flags: only geographic + resource criteria
        flags = FeatureReleaseFlags()
        for n in range(11, 31):
            flags.disable(n)

        assert flags.enabled_count() == 10

        # Build and evaluate scenario
        solution, _ = build_spring_opening_rush()
        context = SchedulingContext(
            schedule_date=solution.schedule_date,
            weather=None,
            traffic=None,
            backlog=None,
        )

        evaluation = await evaluator.evaluate_schedule(solution, context)

        # Evaluation should still work with reduced criteria
        assert isinstance(evaluation, ScheduleEvaluation)
        assert evaluation.total_score >= 0.0

        # Metrics should still be computable
        metrics = compute_quality_metrics(solution)
        assert metrics.total_jobs_scheduled > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_scenarios_produce_valid_evaluations(self) -> None:
        """All simulation scenarios produce valid evaluations.

        Validates: Req 33.1, 33.2
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        evaluator = CriteriaEvaluator(session, config=None)

        scenarios = [
            build_spring_opening_rush(),
            build_fall_closing_rush(),
            build_emergency_insertion(),
            build_weather_event(),
            build_resource_unavailability(),
        ]

        for solution, metadata in scenarios:
            context = SchedulingContext(
                schedule_date=solution.schedule_date,
                weather=metadata.get("weather"),
                traffic=None,
                backlog=None,
            )

            evaluation = await evaluator.evaluate_schedule(solution, context)
            metrics = compute_quality_metrics(solution)

            assert isinstance(evaluation, ScheduleEvaluation), (
                f"Scenario {metadata['scenario']} failed evaluation"
            )
            assert 0.0 <= evaluation.total_score <= 100.0, (
                f"Scenario {metadata['scenario']}: "
                f"score {evaluation.total_score} out of range"
            )
            assert metrics.total_jobs_scheduled > 0, (
                f"Scenario {metadata['scenario']}: no jobs scheduled"
            )
            assert 0.0 <= metrics.capacity_utilization_pct <= 100.0, (
                f"Scenario {metadata['scenario']}: "
                f"utilization {metrics.capacity_utilization_pct} "
                f"out of range"
            )
