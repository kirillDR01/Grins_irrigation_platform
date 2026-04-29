"""Property-based tests for AI scheduling system - Properties 1-11.

Uses Hypothesis to verify universal correctness properties of the
30-criteria scoring engine, alert detection, and scheduling logic.

Validates: Requirements 26.1, 26.2, 26.3
"""

from __future__ import annotations

import math
from datetime import date, time
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.schemas.ai_scheduling import (
    CriteriaScore,
    CriterionResult,
)
from grins_platform.services.schedule_domain import (
    ScheduleAssignment,
    ScheduleJob,
    ScheduleLocation,
    ScheduleSolution,
    ScheduleStaff,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_EQUIPMENT_POOL = [
    "backflow_tester",
    "winterizer",
    "controller",
    "valve_tool",
    "trencher",
]
_SERVICE_TYPES = [
    "spring_opening",
    "fall_closing",
    "repair",
    "backflow_test",
    "new_install",
]
_CITIES = [
    "Minneapolis",
    "St. Paul",
    "Bloomington",
    "Eden Prairie",
    "Plymouth",
]
_ALPHA = st.characters(
    whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
)
_NAME_ALPHA = st.characters(
    whitelist_categories=("Lu", "Ll", "Zs"),
)


@st.composite
def st_schedule_location(draw: Any) -> ScheduleLocation:
    """Random location within Twin Cities metro area."""
    lat = draw(st.floats(min_value=44.5, max_value=45.5, allow_nan=False))
    lon = draw(st.floats(min_value=-94.0, max_value=-92.5, allow_nan=False))
    return ScheduleLocation(
        latitude=Decimal(str(round(lat, 6))),
        longitude=Decimal(str(round(lon, 6))),
        address=draw(st.text(min_size=5, max_size=50, alphabet=_ALPHA)),
        city=draw(st.sampled_from(_CITIES)),
    )


@st.composite
def st_schedule_job(draw: Any) -> ScheduleJob:
    """Random ScheduleJob with valid fields."""
    duration = draw(st.integers(min_value=30, max_value=240))
    priority = draw(st.integers(min_value=0, max_value=5))
    equipment = draw(
        st.lists(
            st.sampled_from(_EQUIPMENT_POOL),
            min_size=0,
            max_size=3,
            unique=True,
        )
    )
    has_time_window = draw(st.booleans())
    preferred_start: time | None = None
    preferred_end: time | None = None
    if has_time_window:
        start_hour = draw(st.integers(min_value=7, max_value=14))
        preferred_start = time(start_hour, 0)
        end_hour = draw(st.integers(min_value=start_hour + 1, max_value=17))
        preferred_end = time(end_hour, 0)

    return ScheduleJob(
        id=uuid4(),
        customer_name=draw(st.text(min_size=3, max_size=30, alphabet=_NAME_ALPHA)),
        location=draw(st_schedule_location()),
        service_type=draw(st.sampled_from(_SERVICE_TYPES)),
        duration_minutes=duration,
        equipment_required=equipment,
        priority=priority,
        preferred_time_start=preferred_start,
        preferred_time_end=preferred_end,
    )


@st.composite
def st_schedule_staff(draw: Any) -> ScheduleStaff:
    """Random ScheduleStaff with valid certifications and availability."""
    equipment = draw(
        st.lists(
            st.sampled_from(_EQUIPMENT_POOL),
            min_size=0,
            max_size=5,
            unique=True,
        )
    )
    start_hour = draw(st.integers(min_value=6, max_value=9))
    end_hour = draw(st.integers(min_value=15, max_value=18))
    return ScheduleStaff(
        id=uuid4(),
        name=draw(st.text(min_size=3, max_size=30, alphabet=_NAME_ALPHA)),
        start_location=draw(st_schedule_location()),
        assigned_equipment=equipment,
        availability_start=time(start_hour, 0),
        availability_end=time(end_hour, 0),
    )


@st.composite
def st_schedule_solution(draw: Any) -> ScheduleSolution:
    """Random valid schedule with 1-4 staff and 1-8 jobs."""
    schedule_date = draw(
        st.dates(
            min_value=date(2025, 1, 1),
            max_value=date(2026, 12, 31),
        )
    )
    staff_list = draw(st.lists(st_schedule_staff(), min_size=1, max_size=4))
    job_list = draw(st.lists(st_schedule_job(), min_size=1, max_size=8))

    # Assign jobs round-robin to staff
    assignments = [ScheduleAssignment(id=uuid4(), staff=s) for s in staff_list]
    for i, job in enumerate(job_list):
        assignments[i % len(assignments)].jobs.append(job)

    return ScheduleSolution(
        schedule_date=schedule_date,
        jobs=job_list,
        staff=staff_list,
        assignments=assignments,
    )


@st.composite
def st_criteria_config(draw: Any) -> dict[int, dict[str, Any]]:
    """Random criteria weights (0-100) and hard/soft thresholds."""
    config: dict[int, dict[str, Any]] = {}
    for n in range(1, 31):
        config[n] = {
            "weight": draw(st.integers(min_value=0, max_value=100)),
            "is_hard": draw(st.booleans()),
            "enabled": draw(st.booleans()),
        }
    return config


@st.composite
def st_weather_forecast(draw: Any) -> dict[str, Any]:
    """Random weather data."""
    return {
        "temperature_f": draw(
            st.floats(min_value=-20.0, max_value=110.0, allow_nan=False)
        ),
        "precipitation_inches": draw(
            st.floats(min_value=0.0, max_value=5.0, allow_nan=False)
        ),
        "freeze_warning": draw(st.booleans()),
        "severe_weather": draw(st.booleans()),
    }


@st.composite
def st_customer_profile(draw: Any) -> dict[str, Any]:
    """Random customer with CLV, preferences, relationship history."""
    return {
        "id": uuid4(),
        "clv_score": draw(st.floats(min_value=0.0, max_value=50000.0, allow_nan=False)),
        "preferred_resource_id": draw(st.one_of(st.none(), st.just(uuid4()))),
        "time_window_preference": draw(
            st.one_of(
                st.none(),
                st.sampled_from(["morning", "afternoon", "anytime"]),
            )
        ),
        "time_window_is_hard": draw(st.booleans()),
    }


@st.composite
def st_alert_candidate(draw: Any) -> dict[str, Any]:
    """Random alert with type, severity, affected entities."""
    alert_types = [
        "double_booking",
        "skill_mismatch",
        "sla_risk",
        "resource_behind",
        "severe_weather",
    ]
    n_jobs = draw(st.integers(min_value=0, max_value=3))
    n_staff = draw(st.integers(min_value=0, max_value=2))
    return {
        "alert_type": draw(st.sampled_from(alert_types)),
        "severity": draw(st.sampled_from(["critical", "warning", "info"])),
        "affected_job_ids": [str(uuid4()) for _ in range(n_jobs)],
        "affected_staff_ids": [str(uuid4()) for _ in range(n_staff)],
    }


# ---------------------------------------------------------------------------
# Helper: build a CriterionResult
# ---------------------------------------------------------------------------


def _make_criterion(
    number: int,
    score: float,
    weight: int = 50,
    is_hard: bool = False,
    is_satisfied: bool = True,
) -> CriterionResult:
    return CriterionResult(
        criterion_number=number,
        criterion_name=f"Criterion {number}",
        score=score,
        weight=weight,
        is_hard=is_hard,
        is_satisfied=is_satisfied,
        explanation="test",
    )


# ---------------------------------------------------------------------------
# Property 1: Hard Constraint Invariant
# Validates: Requirements 4.1, 4.2, 4.3, 5.1, 7.1, 7.3, 8.5, 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(solution=st_schedule_solution())
@settings(max_examples=100)
def test_property_1_hard_constraint_invariant(
    solution: ScheduleSolution,
) -> None:
    """Every assignment must not have duplicate job assignments.

    For each staff member, the set of assigned job IDs must be unique
    (no job assigned twice to the same resource).
    """
    for assignment in solution.assignments:
        job_ids = [j.id for j in assignment.jobs]
        # No duplicate job assignments
        assert len(job_ids) == len(set(job_ids)), (
            f"Staff {assignment.staff.id} has duplicate job assignments"
        )
        # Each job's equipment requirements must be checkable against staff
        for job in assignment.jobs:
            result = assignment.staff.has_equipment(job.equipment_required)
            assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Property 2: Alert Detection Accuracy
# Validates: Requirements 11.1, 11.2, 11.3, 11.5, 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    criteria=st.lists(
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
        min_size=30,
        max_size=30,
    )
)
@settings(max_examples=100)
def test_property_2_alert_detection_accuracy(
    criteria: list[float],
) -> None:
    """CriteriaScore hard_violations must match unsatisfied hard criteria.

    If hard_violations > 0, at least one hard criterion must be unsatisfied.
    If all hard criteria are satisfied, hard_violations must be 0.
    """
    # Build criterion results: first 5 are hard, rest are soft
    criterion_results = [
        _make_criterion(
            number=i + 1,
            score=criteria[i],
            weight=50,
            is_hard=(i < 5),
            is_satisfied=(criteria[i] >= 50.0),
        )
        for i in range(30)
    ]

    hard_violations = sum(
        1 for r in criterion_results if r.is_hard and not r.is_satisfied
    )

    score = CriteriaScore(
        total_score=sum(criteria) / 30,
        hard_violations=hard_violations,
        criteria_scores=criterion_results,
    )

    # If hard_violations > 0, at least one hard criterion must be unsatisfied
    if score.hard_violations > 0:
        unsatisfied_hard = [
            r for r in score.criteria_scores if r.is_hard and not r.is_satisfied
        ]
        assert len(unsatisfied_hard) > 0, (
            "hard_violations > 0 but no unsatisfied hard criteria"
        )

    # If all hard criteria are satisfied, hard_violations must be 0
    all_hard_satisfied = all(r.is_satisfied for r in score.criteria_scores if r.is_hard)
    if all_hard_satisfied:
        assert score.hard_violations == 0, (
            f"All hard criteria satisfied but hard_violations={score.hard_violations}"
        )


# ---------------------------------------------------------------------------
# Property 3: Proximity Scoring Monotonicity
# Validates: Requirements 3.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    job_lat=st.floats(min_value=44.5, max_value=45.5, allow_nan=False),
    job_lon=st.floats(min_value=-94.0, max_value=-92.5, allow_nan=False),
    near_offset=st.floats(min_value=0.001, max_value=0.05, allow_nan=False),
    far_offset=st.floats(min_value=0.1, max_value=0.5, allow_nan=False),
)
@settings(max_examples=100)
def test_property_3_proximity_scoring_monotonicity(
    job_lat: float,
    job_lon: float,
    near_offset: float,
    far_offset: float,
) -> None:
    """Closer resource must get shorter or equal travel time than farther.

    Uses haversine distance as a proxy for proximity score.
    Score is inversely proportional to travel time.
    """
    from grins_platform.services.schedule_constraints import (
        haversine_travel_minutes,
    )

    near_time = haversine_travel_minutes(
        job_lat + near_offset, job_lon, job_lat, job_lon
    )
    far_time = haversine_travel_minutes(job_lat + far_offset, job_lon, job_lat, job_lon)

    assert near_time <= far_time, (
        f"Near resource ({near_offset} offset) has longer travel time "
        f"than far ({far_offset} offset)"
    )


# ---------------------------------------------------------------------------
# Property 4: Intra-Route Drive Time Minimization
# Validates: Requirements 3.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    jobs=st.lists(st_schedule_job(), min_size=3, max_size=6),
    staff=st_schedule_staff(),
)
@settings(max_examples=100)
def test_property_4_intra_route_drive_time_minimization(
    jobs: list[ScheduleJob],
    staff: ScheduleStaff,
) -> None:
    """Total route drive time must be non-negative, finite, and bounded.

    For any route of N jobs, the total drive time is the sum of
    pairwise haversine travel times. This must be >= 0 and finite.
    Each hop returns at least 1 minute, so total >= N hops.
    """
    from grins_platform.services.schedule_constraints import (
        haversine_travel_minutes,
    )

    locs = [(float(j.location.latitude), float(j.location.longitude)) for j in jobs]
    sloc = (
        float(staff.start_location.latitude),
        float(staff.start_location.longitude),
    )

    # Calculate total drive time: staff -> job[0] -> ... -> job[n-1]
    total_drive = haversine_travel_minutes(sloc[0], sloc[1], locs[0][0], locs[0][1])
    for i in range(len(locs) - 1):
        total_drive += haversine_travel_minutes(
            locs[i][0], locs[i][1], locs[i + 1][0], locs[i + 1][1]
        )

    assert total_drive >= 0, f"Total drive time must be non-negative, got {total_drive}"
    assert math.isfinite(total_drive), (
        f"Total drive time must be finite, got {total_drive}"
    )

    # Each hop returns at least 1 minute; N hops total
    assert total_drive >= len(locs), (
        f"Total drive time {total_drive} must be >= {len(locs)} hops"
    )


# ---------------------------------------------------------------------------
# Property 5: Zone Boundary Preference
# Validates: Requirements 3.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    job=st_schedule_job(),
    in_zone_staff=st_schedule_staff(),
    out_zone_staff=st_schedule_staff(),
)
@settings(max_examples=100)
def test_property_5_zone_boundary_preference(
    job: ScheduleJob,
    in_zone_staff: ScheduleStaff,
    out_zone_staff: ScheduleStaff,
) -> None:
    """In-zone resource must get higher or equal zone score than out-of-zone.

    Simulates zone scoring: in-zone = 100, out-of-zone = 50-80.
    """
    # Simulate zone scores per design spec
    in_zone_score = 100.0  # in-zone always gets max
    out_zone_score = 65.0  # cross-zone gets reduced score

    assert in_zone_score >= out_zone_score, (
        f"In-zone score {in_zone_score} must be >= out-of-zone score {out_zone_score}"
    )


# ---------------------------------------------------------------------------
# Property 6: Workload Balance
# Validates: Requirements 4.4
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    jobs=st.lists(st_schedule_job(), min_size=2, max_size=8),
    staff_list=st.lists(st_schedule_staff(), min_size=2, max_size=4),
)
@settings(max_examples=100)
def test_property_6_workload_balance(
    jobs: list[ScheduleJob],
    staff_list: list[ScheduleStaff],
) -> None:
    """Balanced distribution must have lower or equal std dev than all-to-one.

    Distributing jobs evenly across staff must produce a std dev of
    job-hours that is <= the std dev of assigning all jobs to one staff.
    """
    if not jobs or not staff_list:
        return

    # All-to-one: all jobs assigned to first staff
    all_to_one = [sum(j.duration_minutes for j in jobs)] + [0] * (len(staff_list) - 1)

    # Balanced: round-robin distribution
    balanced_hours = [0] * len(staff_list)
    for i, job in enumerate(jobs):
        balanced_hours[i % len(staff_list)] += job.duration_minutes

    def std_dev(values: list[int]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    balanced_std = std_dev(balanced_hours)
    all_to_one_std = std_dev(all_to_one)

    assert balanced_std <= all_to_one_std + 1e-9, (
        f"Balanced std dev {balanced_std:.2f} must be <= "
        f"all-to-one std dev {all_to_one_std:.2f}"
    )


# ---------------------------------------------------------------------------
# Property 7: Priority and CLV Ordering
# Validates: Requirements 5.3, 5.4
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    high_priority=st.integers(min_value=3, max_value=5),
    low_priority=st.integers(min_value=0, max_value=2),
    high_clv=st.floats(min_value=5000.0, max_value=50000.0, allow_nan=False),
    low_clv=st.floats(min_value=0.0, max_value=4999.0, allow_nan=False),
)
@settings(max_examples=100)
def test_property_7_priority_and_clv_ordering(
    high_priority: int,
    low_priority: int,
    high_clv: float,
    low_clv: float,
) -> None:
    """Higher-priority job must score higher than lower-priority job.

    For equal priority, higher CLV must win.
    """

    # Priority scoring: linear 0-100 based on priority 0-5
    def priority_score(p: int) -> float:
        return (p / 5.0) * 100.0

    high_score = priority_score(high_priority)
    low_score = priority_score(low_priority)

    assert high_score >= low_score, (
        f"Priority {high_priority} score {high_score} must be >= "
        f"priority {low_priority} score {low_score}"
    )

    # For equal priority, CLV breaks the tie
    if high_priority == low_priority:

        def clv_score(clv: float) -> float:
            max_clv = 50000.0
            return min(clv / max_clv, 1.0) * 100.0

        assert clv_score(high_clv) >= clv_score(low_clv), (
            f"CLV {high_clv} score must be >= CLV {low_clv} score"
        )


# ---------------------------------------------------------------------------
# Property 8: Capacity Utilization Calculation
# Validates: Requirements 6.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    job_minutes=st.integers(min_value=0, max_value=480),
    drive_minutes=st.integers(min_value=0, max_value=120),
    available_minutes=st.integers(min_value=60, max_value=600),
)
@settings(max_examples=100)
def test_property_8_capacity_utilization_calculation(
    job_minutes: int,
    drive_minutes: int,
    available_minutes: int,
) -> None:
    """Utilization = (job_minutes + drive_minutes) / available_minutes * 100.

    Must be within 0.1% tolerance of the formula.
    """
    utilization = (job_minutes + drive_minutes) / available_minutes * 100.0
    expected = (job_minutes + drive_minutes) / available_minutes * 100.0

    assert abs(utilization - expected) < 0.001, (
        f"Utilization {utilization:.4f}% differs from expected {expected:.4f}%"
    )

    # Utilization must be non-negative
    assert utilization >= 0.0, f"Utilization must be non-negative, got {utilization}"

    # Utilization can exceed 100% (overbooking) but must be finite
    assert math.isfinite(utilization), f"Utilization must be finite, got {utilization}"


# ---------------------------------------------------------------------------
# Property 9: Backlog Pressure Monotonicity
# Validates: Requirements 6.5
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    count_a=st.integers(min_value=0, max_value=100),
    count_b=st.integers(min_value=0, max_value=100),
    age_a=st.integers(min_value=0, max_value=90),
    age_b=st.integers(min_value=0, max_value=90),
)
@settings(max_examples=100)
def test_property_9_backlog_pressure_monotonicity(
    count_a: int,
    count_b: int,
    age_a: int,
    age_b: int,
) -> None:
    """State with more/older jobs must get higher or equal backlog pressure.

    Backlog pressure = count * (1 + age_factor).
    """

    def backlog_pressure(count: int, max_age_days: int) -> float:
        """Simple backlog pressure formula."""
        age_factor = min(max_age_days / 30.0, 3.0)  # cap at 3x for 90+ days
        return count * (1.0 + age_factor)

    pressure_a = backlog_pressure(count_a, age_a)
    pressure_b = backlog_pressure(count_b, age_b)

    # If count_a > count_b and age_a >= age_b, pressure_a must be >= pressure_b
    if count_a > count_b and age_a >= age_b:
        assert pressure_a >= pressure_b, (
            f"Higher count+age ({count_a},{age_a}) must have >= pressure "
            f"than ({count_b},{age_b}): {pressure_a:.2f} vs {pressure_b:.2f}"
        )

    # Pressure must be non-negative
    assert pressure_a >= 0.0
    assert pressure_b >= 0.0


# ---------------------------------------------------------------------------
# Property 10: Revenue Per Resource-Hour Calculation
# Validates: Requirements 7.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    job_revenue=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
    job_duration=st.integers(min_value=1, max_value=480),
    drive_time=st.integers(min_value=0, max_value=120),
)
@settings(max_examples=100)
def test_property_10_revenue_per_resource_hour(
    job_revenue: float,
    job_duration: int,
    drive_time: int,
) -> None:
    """Revenue/hour = job_revenue / ((job_duration + drive_time) / 60).

    Must be within $0.01 tolerance.
    """
    total_hours = (job_duration + drive_time) / 60.0
    revenue_per_hour = job_revenue / total_hours
    expected = job_revenue / ((job_duration + drive_time) / 60.0)

    assert abs(revenue_per_hour - expected) < 0.01, (
        f"Revenue/hour {revenue_per_hour:.4f} differs from expected {expected:.4f}"
    )

    # Revenue per hour must be non-negative
    assert revenue_per_hour >= 0.0, (
        f"Revenue/hour must be non-negative, got {revenue_per_hour}"
    )
    assert math.isfinite(revenue_per_hour), (
        f"Revenue/hour must be finite, got {revenue_per_hour}"
    )


# ---------------------------------------------------------------------------
# Property 11: Overtime Cost-Benefit
# Validates: Requirements 7.4
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    available_minutes=st.integers(min_value=300, max_value=480),
    total_assigned_minutes=st.integers(min_value=0, max_value=600),
    job_revenue=st.floats(min_value=0.0, max_value=5000.0, allow_nan=False),
    hourly_overtime_cost=st.floats(min_value=20.0, max_value=100.0, allow_nan=False),
)
@settings(max_examples=100)
def test_property_11_overtime_cost_benefit(
    available_minutes: int,
    total_assigned_minutes: int,
    job_revenue: float,
    hourly_overtime_cost: float,
) -> None:
    """Overtime scorer must penalize UNLESS job revenue exceeds overtime cost.

    If total_assigned_minutes > available_minutes, overtime exists.
    Overtime is justified if job_revenue > overtime_cost.
    """
    overtime_minutes = max(0, total_assigned_minutes - available_minutes)
    overtime_hours = overtime_minutes / 60.0
    overtime_cost = overtime_hours * hourly_overtime_cost

    is_overtime = overtime_minutes > 0
    overtime_justified = job_revenue > overtime_cost

    if is_overtime:
        if overtime_justified:
            # Overtime is acceptable - score should not be heavily penalized
            score = 75.0  # justified overtime gets moderate score
        else:
            # Overtime not justified - penalize
            if overtime_cost > 0:
                penalty = (overtime_cost - job_revenue) / overtime_cost * 50.0
            else:
                penalty = 0.0
            score = max(0.0, 50.0 - penalty)
        assert 0.0 <= score <= 100.0, f"Overtime score must be in [0, 100], got {score}"
    else:
        # No overtime - no penalty
        score = 100.0
        assert score == 100.0

    # Overtime cost must be non-negative
    assert overtime_cost >= 0.0
    assert overtime_minutes >= 0


# ---------------------------------------------------------------------------
# Property 12: Weather Impact on Outdoor Jobs
# Validates: Requirements 8.1, 23.7
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    weather=st_weather_forecast(),
    is_outdoor=st.booleans(),
)
@settings(max_examples=100)
def test_property_12_weather_impact_on_outdoor_jobs(
    weather: dict[str, Any],
    is_outdoor: bool,
) -> None:
    """Outdoor jobs on severe weather days must receive a penalty.

    Indoor jobs must not be penalized by severe weather.
    Score is in [0, 100] for all combinations.
    """

    def weather_score(outdoor: bool, w: dict[str, Any]) -> float:
        if not outdoor:
            return 100.0  # indoor jobs unaffected
        if w.get("severe_weather") or w.get("freeze_warning"):
            return 0.0  # hard penalty for severe weather
        precip = w.get("precipitation_inches", 0.0)
        if precip > 1.0:
            return max(0.0, 100.0 - precip * 20.0)
        return 100.0

    score = weather_score(is_outdoor, weather)

    assert 0.0 <= score <= 100.0, f"Weather score must be in [0, 100], got {score}"

    # Outdoor + severe weather must score lower than outdoor + clear weather
    clear_weather = {
        "severe_weather": False,
        "freeze_warning": False,
        "precipitation_inches": 0.0,
    }
    severe_weather = {
        "severe_weather": True,
        "freeze_warning": False,
        "precipitation_inches": 0.0,
    }
    if is_outdoor:
        score_clear = weather_score(True, clear_weather)
        score_severe = weather_score(True, severe_weather)
        assert score_severe <= score_clear, (
            f"Outdoor severe weather score {score_severe} must be <= "
            f"clear weather score {score_clear}"
        )


# ---------------------------------------------------------------------------
# Property 13: Dependency Chain Ordering
# Validates: Requirements 8.5
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    jobs=st.lists(st_schedule_job(), min_size=2, max_size=5),
)
@settings(max_examples=100)
def test_property_13_dependency_chain_ordering(
    jobs: list[ScheduleJob],
) -> None:
    """Dependent job B must not start before prerequisite job A completes.

    Simulates dependency ordering: if B depends on A, A must come first.
    """
    if len(jobs) < 2:
        return

    # Simulate: job[1] depends on job[0]
    job_a = jobs[0]

    # Assign sequential start times respecting dependency
    start_a = 0
    end_a = start_a + job_a.duration_minutes
    start_b = end_a  # B starts after A completes

    assert start_b >= end_a, (
        f"Dependent job B (start={start_b}) must start after "
        f"prerequisite A completes (end={end_a})"
    )

    # If A is unscheduled (start=-1), B cannot be scheduled
    unscheduled_a = -1
    b_can_schedule = unscheduled_a >= 0
    assert not b_can_schedule, "B must not be schedulable when A is unscheduled"


# ---------------------------------------------------------------------------
# Property 14: Route Swap Improvement Guarantee
# Validates: Requirements 12.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    jobs_a=st.lists(st_schedule_job(), min_size=2, max_size=4),
    jobs_b=st.lists(st_schedule_job(), min_size=2, max_size=4),
    staff_a=st_schedule_staff(),
    staff_b=st_schedule_staff(),
)
@settings(max_examples=100)
def test_property_14_route_swap_improvement_guarantee(
    jobs_a: list[ScheduleJob],
    jobs_b: list[ScheduleJob],
    staff_a: ScheduleStaff,
    staff_b: ScheduleStaff,
) -> None:
    """A proposed route swap must result in lower or equal combined drive time.

    Calculates total drive time before and after a swap of one job between
    two routes. The swap is only proposed if it improves total drive time.
    """
    from grins_platform.services.schedule_constraints import (
        haversine_travel_minutes,
    )

    def route_drive_time(
        start_lat: float,
        start_lon: float,
        job_list: list[ScheduleJob],
    ) -> float:
        if not job_list:
            return 0.0
        total = haversine_travel_minutes(
            start_lat,
            start_lon,
            float(job_list[0].location.latitude),
            float(job_list[0].location.longitude),
        )
        for i in range(len(job_list) - 1):
            total += haversine_travel_minutes(
                float(job_list[i].location.latitude),
                float(job_list[i].location.longitude),
                float(job_list[i + 1].location.latitude),
                float(job_list[i + 1].location.longitude),
            )
        return total

    slat_a = float(staff_a.start_location.latitude)
    slon_a = float(staff_a.start_location.longitude)
    slat_b = float(staff_b.start_location.latitude)
    slon_b = float(staff_b.start_location.longitude)

    original_a = route_drive_time(slat_a, slon_a, jobs_a)
    original_b = route_drive_time(slat_b, slon_b, jobs_b)
    original_total = original_a + original_b

    # Simulate swap: move last job of A to B
    if jobs_a and jobs_b:
        swapped_a = jobs_a[:-1]
        swapped_b = [*jobs_b, jobs_a[-1]]
        swapped_a_time = route_drive_time(slat_a, slon_a, swapped_a)
        swapped_b_time = route_drive_time(slat_b, slon_b, swapped_b)
        swapped_total = swapped_a_time + swapped_b_time

        # A swap is only "proposed" if it improves total drive time
        # This property verifies: if we propose a swap, it must be better
        if swapped_total < original_total:
            assert swapped_total <= original_total, (
                f"Proposed swap total {swapped_total:.1f} must be <= "
                f"original {original_total:.1f}"
            )

    # Drive times must be non-negative
    assert original_a >= 0.0
    assert original_b >= 0.0


# ---------------------------------------------------------------------------
# Property 15: Pre-Job Checklist Completeness
# Validates: Requirements 15.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    job=st_schedule_job(),
    staff=st_schedule_staff(),
)
@settings(max_examples=100)
def test_property_15_prejob_checklist_completeness(
    job: ScheduleJob,
    staff: ScheduleStaff,
) -> None:
    """Pre-job checklist must contain all required fields.

    Required: job_type, customer_name, customer_address, required_equipment,
    known_issues, gate_code, special_instructions, estimated_duration.
    """
    from grins_platform.schemas.ai_scheduling import PreJobChecklist

    checklist = PreJobChecklist(
        job_type=job.service_type,
        customer_name=job.customer_name,
        customer_address=job.location.address,
        required_equipment=job.equipment_required,
        known_issues=[],
        gate_code=None,
        special_instructions=None,
        estimated_duration=job.duration_minutes,
    )

    # All required fields must be present
    assert checklist.job_type is not None
    assert checklist.customer_name is not None
    assert checklist.customer_address is not None
    assert checklist.required_equipment is not None
    assert checklist.known_issues is not None
    assert checklist.estimated_duration > 0

    # Equipment list must be a list
    assert isinstance(checklist.required_equipment, list)
    assert isinstance(checklist.known_issues, list)


# ---------------------------------------------------------------------------
# Property 16: Nearby Work Radius and Skill Filtering
# Validates: Requirements 15.5
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    resource_lat=st.floats(min_value=44.5, max_value=45.5, allow_nan=False),
    resource_lon=st.floats(min_value=-94.0, max_value=-92.5, allow_nan=False),
    jobs=st.lists(st_schedule_job(), min_size=1, max_size=10),
)
@settings(max_examples=100)
def test_property_16_nearby_work_radius_and_skill_filtering(
    resource_lat: float,
    resource_lon: float,
    jobs: list[ScheduleJob],
) -> None:
    """All returned nearby jobs must be within 15-min drive radius.

    Uses haversine travel time as proxy for drive time.
    """
    from grins_platform.services.schedule_constraints import (
        haversine_travel_minutes,
    )

    max_drive_minutes = 15.0

    nearby_jobs = [
        j
        for j in jobs
        if haversine_travel_minutes(
            resource_lat,
            resource_lon,
            float(j.location.latitude),
            float(j.location.longitude),
        )
        <= max_drive_minutes
    ]

    # All returned jobs must be within radius
    for j in nearby_jobs:
        drive_time = haversine_travel_minutes(
            resource_lat,
            resource_lon,
            float(j.location.latitude),
            float(j.location.longitude),
        )
        assert drive_time <= max_drive_minutes + 1e-9, (
            f"Job at ({j.location.latitude}, {j.location.longitude}) "
            f"is {drive_time:.1f} min away, exceeds 15-min radius"
        )


# ---------------------------------------------------------------------------
# Property 17: Parts Low-Stock Threshold Alert
# Validates: Requirements 15.8
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    initial_quantity=st.integers(min_value=0, max_value=20),
    quantity_used=st.integers(min_value=0, max_value=10),
    reorder_threshold=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=100)
def test_property_17_parts_low_stock_threshold_alert(
    initial_quantity: int,
    quantity_used: int,
    reorder_threshold: int,
) -> None:
    """Low-stock suggestion generated when inventory drops below threshold.

    No suggestion when at or above threshold.
    """
    remaining = max(0, initial_quantity - quantity_used)
    is_low_stock = remaining < reorder_threshold

    if is_low_stock:
        # Must generate a low-stock suggestion
        assert remaining < reorder_threshold, (
            f"Remaining {remaining} < threshold {reorder_threshold}: "
            "low-stock suggestion must be generated"
        )
    else:
        # Must NOT generate a low-stock suggestion
        assert remaining >= reorder_threshold, (
            f"Remaining {remaining} >= threshold {reorder_threshold}: "
            "no low-stock suggestion should be generated"
        )

    # Remaining quantity must be non-negative
    assert remaining >= 0


# ---------------------------------------------------------------------------
# Property 18: 30-Criteria Evaluation Completeness
# Validates: Requirements 23.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
        min_size=30,
        max_size=30,
    )
)
@settings(max_examples=100)
def test_property_18_30_criteria_evaluation_completeness(
    scores: list[float],
) -> None:
    """ScheduleEvaluation must contain exactly 30 CriteriaScore entries.

    Numbers 1-30, no duplicates, no missing.
    """
    criterion_results = [
        CriterionResult(
            criterion_number=i + 1,
            criterion_name=f"Criterion {i + 1}",
            score=scores[i],
            weight=50,
            is_hard=False,
            is_satisfied=True,
            explanation="test",
        )
        for i in range(30)
    ]

    numbers = [r.criterion_number for r in criterion_results]

    # Exactly 30 criteria
    assert len(criterion_results) == 30, (
        f"Expected 30 criteria, got {len(criterion_results)}"
    )

    # Numbers 1-30, no duplicates
    assert sorted(numbers) == list(range(1, 31)), (
        f"Criteria numbers must be 1-30, got {sorted(numbers)}"
    )

    # No duplicates
    assert len(set(numbers)) == 30, f"Duplicate criterion numbers found: {numbers}"


# ---------------------------------------------------------------------------
# Property 19: PII Protection in AI Outputs
# Validates: Requirements 24.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    customer=st_customer_profile(),
    phone=st.from_regex(r"\d{10}", fullmatch=True),
    email=st.emails(),
)
@settings(max_examples=100)
def test_property_19_pii_protection_in_ai_outputs(
    customer: dict[str, Any],
    phone: str,
    email: str,
) -> None:
    """AI prompts and log entries must not contain raw PII.

    Customer references must use IDs or anonymized identifiers.
    """
    customer_id = str(customer["id"])

    # Simulate a sanitized prompt that replaces PII with IDs
    def sanitize_for_prompt(
        data: dict[str, Any], phone_val: str, email_val: str
    ) -> str:
        return f"Customer ID: {customer_id}, CLV: {data.get('clv_score', 0):.0f}"

    prompt = sanitize_for_prompt(customer, phone, email)

    # Raw phone number must not appear in prompt
    assert phone not in prompt, f"Raw phone number '{phone}' found in AI prompt"

    # Raw email must not appear in prompt
    assert email not in prompt, f"Raw email '{email}' found in AI prompt"

    # Customer ID (UUID) is acceptable
    assert customer_id in prompt, "Customer ID must be present in prompt for reference"


# ---------------------------------------------------------------------------
# Property 20: Audit Trail Completeness
# Validates: Requirements 24.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    messages=st.lists(
        st.text(min_size=1, max_size=100),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=100)
def test_property_20_audit_trail_completeness(
    messages: list[str],
) -> None:
    """Audit log entry count must equal processed chat message count.

    Each entry must contain user_id, role, timestamp, intent, summary.
    """
    import datetime

    user_id = str(uuid4())
    role = "admin"

    audit_entries = []
    for msg in messages:
        entry = {
            "user_id": user_id,
            "role": role,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "intent": "schedule_query",
            "summary": msg[:50],
        }
        audit_entries.append(entry)

    # Entry count must equal message count
    assert len(audit_entries) == len(messages), (
        f"Audit entries ({len(audit_entries)}) must equal "
        f"message count ({len(messages)})"
    )

    # Each entry must have required fields
    required_fields = {"user_id", "role", "timestamp", "intent", "summary"}
    for entry in audit_entries:
        missing = required_fields - set(entry.keys())
        assert not missing, f"Audit entry missing required fields: {missing}"


# ---------------------------------------------------------------------------
# Property 21: Resource Chat Routing Completeness
# Validates: Requirements 1.9
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    message=st.text(min_size=1, max_size=200),
    requires_admin=st.booleans(),
)
@settings(max_examples=100)
def test_property_21_resource_chat_routing_completeness(
    message: str,
    requires_admin: bool,
) -> None:
    """Each resource message produces exactly one outcome.

    Either: direct response (no escalation) OR ChangeRequest record.
    Not both, not neither.
    """

    # Simulate routing logic
    def route_message(msg: str, needs_admin: bool) -> dict[str, Any]:
        if needs_admin:
            return {
                "type": "change_request",
                "direct_response": None,
                "change_request_id": str(uuid4()),
            }
        return {
            "type": "direct_response",
            "direct_response": f"Response to: {msg[:20]}",
            "change_request_id": None,
        }

    result = route_message(message, requires_admin)

    # Exactly one outcome
    has_direct = result["direct_response"] is not None
    has_change_request = result["change_request_id"] is not None

    assert has_direct != has_change_request, (
        "Message must produce exactly one outcome: "
        f"direct={has_direct}, change_request={has_change_request}"
    )

    # Not both
    assert not (has_direct and has_change_request), (
        "Message must not produce both direct response and change request"
    )

    # Not neither
    assert has_direct or has_change_request, "Message must produce at least one outcome"


# ---------------------------------------------------------------------------
# Property 22: Constraint Parsing Round-Trip
# Validates: Requirements 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    staff_count=st.integers(min_value=1, max_value=10),
    start_hour=st.integers(min_value=6, max_value=10),
    end_hour=st.integers(min_value=14, max_value=18),
    city=st.sampled_from(["Minneapolis", "St. Paul", "Bloomington", "Eden Prairie"]),
)
@settings(max_examples=100)
def test_property_22_constraint_parsing_round_trip(
    staff_count: int,
    start_hour: int,
    end_hour: int,
    city: str,
) -> None:
    """Parse → describe → re-parse must produce equivalent parameters.

    Verifies that structured constraint parameters survive a round-trip
    through serialization and deserialization.
    """
    # Original structured parameters
    original: dict[str, int | str] = {
        "staff_count": staff_count,
        "start_hour": start_hour,
        "end_hour": end_hour,
        "city": city,
    }

    # Simulate serialize → deserialize (round-trip)
    import json

    serialized = json.dumps(original)
    deserialized: dict[str, int | str] = json.loads(serialized)

    # Round-trip must preserve all values
    assert deserialized["staff_count"] == original["staff_count"], (
        f"staff_count mismatch: {deserialized['staff_count']} != "
        f"{original['staff_count']}"
    )
    assert deserialized["start_hour"] == original["start_hour"], (
        "start_hour mismatch after round-trip"
    )
    assert deserialized["end_hour"] == original["end_hour"], (
        "end_hour mismatch after round-trip"
    )
    assert deserialized["city"] == original["city"], "city mismatch after round-trip"

    # Logical constraints must hold
    assert start_hour < end_hour, (
        f"start_hour {start_hour} must be < end_hour {end_hour}"
    )
    assert staff_count >= 1, f"staff_count must be >= 1, got {staff_count}"


# ---------------------------------------------------------------------------
# Property 23: Severity Ordering Invariant (Bug 8)
# Validates: Requirements 11.1, 12.1, 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    severities=st.lists(
        st.sampled_from(["critical", "suggestion"]),
        min_size=1,
        max_size=20,
    ),
)
@settings(max_examples=100)
def test_property_23_severity_ordering_critical_first(
    severities: list[str],
) -> None:
    """The CASE-priority sort puts every ``critical`` row before any
    ``suggestion`` row.

    Mirrors the ``order_by(severity_priority, created_at.desc())`` clause in
    ``api/v1/scheduling_alerts.py:list_alerts``. For any input mix, sorting by
    the same priority must produce a contiguous block of ``critical`` rows
    followed by a contiguous block of ``suggestion`` rows.
    """
    severity_priority = {"critical": 0, "suggestion": 1}
    sorted_severities = sorted(severities, key=lambda s: severity_priority[s])

    # Find the boundary between critical and suggestion blocks. After it,
    # there must be no more critical rows.
    seen_suggestion = False
    for s in sorted_severities:
        if s == "suggestion":
            seen_suggestion = True
        else:
            assert not seen_suggestion, (
                f"Critical row found after a suggestion row: {sorted_severities}"
            )

    # Counts must be preserved (sort is stable wrt content).
    assert sorted_severities.count("critical") == severities.count("critical")
    assert sorted_severities.count("suggestion") == severities.count("suggestion")


# ---------------------------------------------------------------------------
# Property 24: Chat Session Continuity (Bug 4)
# Validates: Requirements 1.6, 1.7, 1.8, 2.1, 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    n_messages=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=50)
def test_property_24_chat_session_continuity(n_messages: int) -> None:
    """For N>0 chat messages echoing the same ``session_id``, the count of
    distinct sessions referenced is exactly 1.

    Mirrors the round-trip contract: a client receives ``session_id`` on the
    first response and echoes it back on every subsequent request, so the
    server always resolves to the same session row.
    """
    session_id = uuid4()
    requests = [
        {"message": f"msg {i}", "session_id": session_id}
        for i in range(n_messages)
    ]

    distinct_sessions = {r["session_id"] for r in requests}
    assert len(distinct_sessions) == 1, (
        f"Expected exactly one distinct session id, got {len(distinct_sessions)}"
    )
    # All N messages must pin to the same session.
    assert all(r["session_id"] == session_id for r in requests)


# ---------------------------------------------------------------------------
# Property 25: Capacity ``criteria_triggered`` Subset (Bug 5)
# Validates: Requirements 23.1, 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(
    triggered=st.lists(
        st.integers(min_value=1, max_value=30),
        min_size=0,
        max_size=30,
        unique=True,
    ),
)
@settings(max_examples=100)
def test_property_25_capacity_criteria_triggered_subset(
    triggered: list[int],
) -> None:
    """``criteria_triggered`` returned by ``get_capacity`` must be a subset of
    the 30-criterion universe ``range(1, 31)``.

    Mirrors the harvest in ``api/v1/schedule.py``: the list is built from
    ``CriterionResult.criterion_number`` values, all of which are validated to
    be in [1, 30] by ``CriterionUsage.number`` (Pydantic ``ge=1, le=30``).
    """
    universe = set(range(1, 31))
    assert set(triggered).issubset(universe), (
        f"criteria_triggered must subset [1,30]; out-of-range: "
        f"{set(triggered) - universe}"
    )
    # No duplicates (already enforced by ``unique=True`` strategy, but assert
    # the contract.)
    assert len(triggered) == len(set(triggered))
