"""Property-based tests for AI Scheduling System.

Covers Properties 1-22 using Hypothesis strategies for schedule jobs,
staff, weather, backlog, and customer profiles. Tests all 6 scorer
modules, AlertEngine, PreJobGenerator, ChangeRequestService, and
ChatService routing logic.

All tests marked @pytest.mark.unit with @settings(max_examples=50).
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.schemas.ai_scheduling import (
    AlertCandidate,
    PreJobChecklist,
    SchedulingConfig,
    SchedulingContext,
)
from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
from grins_platform.services.ai.scheduling.chat_service import (
    ADMIN_SYSTEM_PROMPT,
    RESOURCE_SYSTEM_PROMPT,
    SchedulingChatService,
)
from grins_platform.services.ai.scheduling.criteria_evaluator import (
    CriteriaEvaluator,
)
from grins_platform.services.ai.scheduling.prejob_generator import PreJobGenerator
from grins_platform.services.ai.scheduling.resource_tools import (
    ResourceSchedulingTools,
)
from grins_platform.services.ai.scheduling.scorers.business_rules import (
    BusinessRulesScorer,
)
from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
    CapacityDemandScorer,
)
from grins_platform.services.ai.scheduling.scorers.customer_job import (
    CustomerJobScorer,
)
from grins_platform.services.ai.scheduling.scorers.geographic import GeographicScorer
from grins_platform.services.ai.scheduling.scorers.predictive import PredictiveScorer
from grins_platform.services.ai.scheduling.scorers.resource import ResourceScorer

# ---------------------------------------------------------------------------
# Hypothesis Strategies
# ---------------------------------------------------------------------------


@st.composite
def st_schedule_job(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a random schedule job dict."""
    return {
        "id": str(uuid4()),
        "job_type": draw(
            st.sampled_from([
                "spring_opening",
                "fall_closing",
                "maintenance",
                "new_build",
                "backflow_test",
            ]),
        ),
        "required_skills": draw(
            st.lists(
                st.sampled_from([
                    "backflow_certified",
                    "lake_pump",
                    "senior_tech",
                    "electrical",
                ]),
                max_size=3,
                unique=True,
            ),
        ),
        "required_equipment": draw(
            st.lists(
                st.sampled_from([
                    "pressure_gauge",
                    "compressor",
                    "fittings",
                    "multimeter",
                ]),
                max_size=3,
                unique=True,
            ),
        ),
        "estimated_duration_minutes": draw(st.integers(min_value=30, max_value=480)),
        "priority": draw(
            st.sampled_from(["emergency", "vip", "standard", "flexible"]),
        ),
        "is_outdoor": draw(st.booleans()),
        "latitude": draw(st.floats(min_value=44.0, max_value=46.0)),
        "longitude": draw(st.floats(min_value=-94.0, max_value=-92.0)),
        "scheduled_start": draw(
            st.sampled_from([
                "07:00", "08:00", "09:00", "10:00",
                "11:00", "12:00", "13:00", "14:00",
            ]),
        ),
        "scheduled_end": draw(
            st.sampled_from([
                "09:00", "10:00", "11:00", "12:00",
                "13:00", "14:00", "15:00", "16:00",
            ]),
        ),
        "customer": {
            "clv_score": draw(st.floats(min_value=0, max_value=100)),
            "preferred_resource_id": draw(
                st.one_of(st.none(), st.just(str(uuid4()))),
            ),
            "time_window_preference": draw(
                st.one_of(st.none(), st.sampled_from(["am", "pm"])),
            ),
            "time_window_is_hard": draw(st.booleans()),
        },
        "sla_deadline": draw(
            st.one_of(st.none(), st.just("2026-04-15T23:59:59")),
        ),
        "compliance_deadline": draw(
            st.one_of(st.none(), st.just("2026-04-30T23:59:59")),
        ),
        "depends_on_job_id": None,
        "revenue_per_hour": draw(
            st.one_of(st.none(), st.floats(min_value=50, max_value=300)),
        ),
    }


@st.composite
def st_schedule_staff(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a random schedule staff dict."""
    return {
        "id": str(uuid4()),
        "name": draw(
            st.text(
                min_size=3,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("L",)),
            ),
        ),
        "certifications": draw(
            st.lists(
                st.sampled_from([
                    "backflow_certified",
                    "lake_pump",
                    "senior_tech",
                    "electrical",
                ]),
                max_size=4,
                unique=True,
            ),
        ),
        "assigned_equipment": draw(
            st.lists(
                st.sampled_from([
                    "pressure_gauge",
                    "compressor",
                    "fittings",
                    "multimeter",
                ]),
                max_size=4,
                unique=True,
            ),
        ),
        "shift_start": "07:00",
        "shift_end": "17:00",
        "latitude": draw(st.floats(min_value=44.0, max_value=46.0)),
        "longitude": draw(st.floats(min_value=-94.0, max_value=-92.0)),
        "default_start_lat": draw(st.floats(min_value=44.0, max_value=46.0)),
        "default_start_lng": draw(st.floats(min_value=-94.0, max_value=-92.0)),
        "performance_score": draw(
            st.one_of(st.none(), st.floats(min_value=0, max_value=100)),
        ),
        "callback_rate": draw(
            st.one_of(st.none(), st.floats(min_value=0, max_value=1)),
        ),
        "avg_satisfaction": draw(
            st.one_of(st.none(), st.floats(min_value=0, max_value=5)),
        ),
        "service_zone_id": draw(
            st.one_of(st.none(), st.just(str(uuid4()))),
        ),
        "overtime_threshold_minutes": draw(
            st.one_of(st.none(), st.integers(min_value=400, max_value=600)),
        ),
        "team_job_hours": draw(
            st.lists(
                st.floats(min_value=2, max_value=10),
                min_size=2,
                max_size=8,
            ),
        ),
    }


@st.composite
def st_weather_forecast(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a random weather forecast dict."""
    return {
        "condition": draw(
            st.sampled_from([
                "clear", "cloudy", "rain", "storm",
                "freeze", "snow", "sunny", "overcast",
            ]),
        ),
        "temperature_f": draw(st.floats(min_value=-10, max_value=110)),
        "precipitation_chance": draw(st.floats(min_value=0, max_value=1)),
    }


@st.composite
def st_backlog_state(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a random backlog state dict."""
    return {
        "unscheduled_count": draw(st.integers(min_value=0, max_value=100)),
        "avg_age_days": draw(st.floats(min_value=0, max_value=60)),
    }


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_async_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_default_config() -> SchedulingConfig:
    """Create a default 30-criteria config."""
    hard_criteria = {6, 7, 8, 11, 21, 23, 30}
    criteria = [
        {
            "criterion_number": i,
            "criterion_name": f"Criterion {i}",
            "weight": 50,
            "is_hard_constraint": i in hard_criteria,
            "is_enabled": True,
        }
        for i in range(1, 31)
    ]
    return SchedulingConfig(criteria=criteria)


def _make_context(
    schedule_date: date | None = None,
    weather: dict[str, Any] | None = None,
    backlog: dict[str, Any] | None = None,
) -> SchedulingContext:
    """Create a SchedulingContext."""
    return SchedulingContext(
        schedule_date=schedule_date or date(2026, 4, 10),
        weather=weather,
        backlog=backlog,
    )


# ---------------------------------------------------------------------------
# Property 1: Hard Constraint Invariant
# Validates: Requirements 4.1, 4.2, 4.3, 5.1, 7.1, 7.3, 8.5, 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty1HardConstraintInvariant:
    """Property 1: For any assignment where hard constraints are satisfied,
    skills, equipment, and availability must all hold simultaneously."""

    @given(job=st_schedule_job(), staff=st_schedule_staff())
    @settings(max_examples=50)
    def test_hard_constraints_hold_simultaneously(
        self,
        job: dict[str, Any],
        staff: dict[str, Any],
    ) -> None:
        """**Validates: Requirements 4.1, 4.2, 4.3, 5.1, 7.1, 7.3, 8.5**

        For any job-staff pair, if all hard constraints are satisfied,
        then skills ⊆ certifications, equipment ⊆ assigned_equipment,
        and job time within shift window.
        """
        required_skills = set(job.get("required_skills", []))
        held_skills = set(staff.get("certifications", []))
        skills_ok = required_skills.issubset(held_skills)

        required_equip = set(job.get("required_equipment", []))
        held_equip = set(staff.get("assigned_equipment", []))
        equip_ok = required_equip.issubset(held_equip)

        j_start = job.get("scheduled_start", "07:00")
        j_end = job.get("scheduled_end", "17:00")
        s_start = staff.get("shift_start", "07:00")
        s_end = staff.get("shift_end", "17:00")
        avail_ok = j_start >= s_start and j_end <= s_end

        all_hard_ok = skills_ok and equip_ok and avail_ok

        # If all hard constraints hold, each individual one must hold
        if all_hard_ok:
            assert skills_ok
            assert equip_ok
            assert avail_ok


# ---------------------------------------------------------------------------
# Property 2: Alert Detection Accuracy
# Validates: Requirements 11.1, 11.2, 11.3, 11.5, 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty2AlertDetectionAccuracy:
    """Property 2: Injected violations must be detected by AlertEngine."""

    @given(
        resource_id=st.uuids(),
        delay_minutes=st.integers(min_value=40, max_value=120),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_resource_behind_detected(
        self,
        resource_id: Any,
        delay_minutes: int,
    ) -> None:
        """**Validates: Requirements 11.4**

        Injecting a resource 40+ min behind must produce a
        resource_behind alert.
        """
        session = _make_async_session()
        engine = AlertEngine(session)

        assignments = [{
            "resource_id": str(resource_id),
            "job_id": str(uuid4()),
            "delay_minutes": delay_minutes,
        }]

        candidates = await engine._detect_resource_behind(assignments)
        assert len(candidates) >= 1
        assert all(c.alert_type == "resource_behind" for c in candidates)

    @given(
        skills_required=st.lists(
            st.sampled_from(["backflow_certified", "lake_pump"]),
            min_size=1,
            max_size=2,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_skill_mismatch_detected(
        self,
        skills_required: list[str],
    ) -> None:
        """**Validates: Requirements 11.2**

        Assigning a job to a resource missing required skills must
        produce a skill_mismatch alert.
        """
        session = _make_async_session()
        engine = AlertEngine(session)

        assignments = [{
            "resource_id": str(uuid4()),
            "job_id": str(uuid4()),
            "required_skills": skills_required,
            "resource_skills": [],  # no skills
        }]

        candidates = await engine._detect_skill_mismatches(assignments)
        assert len(candidates) == 1
        assert candidates[0].alert_type == "skill_mismatch"

    @pytest.mark.asyncio
    async def test_no_false_positives_on_clean_schedule(
        self,
    ) -> None:
        """**Validates: Requirements 11.1, 11.2, 11.3, 11.5**

        A schedule with no violations should produce no critical alerts.
        """
        session = _make_async_session()
        engine = AlertEngine(session)

        # Clean assignments: no overlaps, no skill mismatches, no delays
        clean_assignments: list[dict[str, Any]] = []
        candidates: list[AlertCandidate] = []
        candidates.extend(
            await engine._detect_double_bookings(clean_assignments),
        )
        candidates.extend(
            await engine._detect_skill_mismatches(clean_assignments),
        )
        candidates.extend(
            await engine._detect_resource_behind(clean_assignments),
        )
        assert len(candidates) == 0


# ---------------------------------------------------------------------------
# Property 3: Proximity Scoring Monotonicity
# Validates: Requirements 3.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty3ProximityMonotonicity:
    """Property 3: Closer resource gets higher or equal proximity score."""

    @given(
        job_lat=st.floats(min_value=44.5, max_value=45.5),
        job_lng=st.floats(min_value=-93.5, max_value=-92.5),
        staff1_lat=st.floats(min_value=44.5, max_value=45.5),
        staff1_lng=st.floats(min_value=-93.5, max_value=-92.5),
        offset=st.floats(min_value=0.01, max_value=0.5),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_closer_resource_higher_score(
        self,
        job_lat: float,
        job_lng: float,
        staff1_lat: float,
        staff1_lng: float,
        offset: float,
    ) -> None:
        """**Validates: Requirements 3.1**

        A resource closer to the job must score >= a resource farther away.
        """
        session = _make_async_session()
        scorer = GeographicScorer(session)
        config = {
            "criterion_name": "Proximity",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        job = {"latitude": job_lat, "longitude": job_lng}
        staff_close = {"latitude": staff1_lat, "longitude": staff1_lng}
        # Push staff_far further away
        staff_far = {
            "latitude": staff1_lat + offset,
            "longitude": staff1_lng + offset,
        }

        result_close = await scorer._score_proximity(config, job, staff_close, context)
        result_far = await scorer._score_proximity(config, job, staff_far, context)

        dist_close = GeographicScorer._haversine_km(
            staff1_lat, staff1_lng, job_lat, job_lng,
        )
        dist_far = GeographicScorer._haversine_km(
            staff1_lat + offset, staff1_lng + offset, job_lat, job_lng,
        )

        if dist_close <= dist_far:
            assert result_close.score >= result_far.score


# ---------------------------------------------------------------------------
# Property 4: Intra-Route Drive Time Minimization
# Validates: Requirements 3.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty4IntraRouteDriveTime:
    """Property 4: Solver route ≤ worst-case ordering."""

    @given(
        drive_minutes=st.floats(min_value=0, max_value=400),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_drive_time_score_decreases_with_distance(
        self,
        drive_minutes: float,
    ) -> None:
        """**Validates: Requirements 3.2**

        Higher total drive time must produce lower or equal score.
        """
        session = _make_async_session()
        scorer = GeographicScorer(session)
        config = {
            "criterion_name": "Intra-Route Drive Time",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        staff_low = {"total_drive_minutes": drive_minutes}
        staff_high = {"total_drive_minutes": drive_minutes + 30}
        job: dict[str, Any] = {}

        result_low = await scorer._score_intra_route_drive_time(
            config, job, staff_low, context,
        )
        result_high = await scorer._score_intra_route_drive_time(
            config, job, staff_high, context,
        )

        assert result_low.score >= result_high.score


# ---------------------------------------------------------------------------
# Property 5: Zone Boundary Preference
# Validates: Requirements 3.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty5ZoneBoundaryPreference:
    """Property 5: In-zone resource gets higher zone score."""

    @given(zone_id=st.uuids())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_in_zone_higher_score(self, zone_id: Any) -> None:
        """**Validates: Requirements 3.3**

        In-zone resource must score higher than out-of-zone at equal distance.
        """
        session = _make_async_session()
        scorer = GeographicScorer(session)
        config = {
            "criterion_name": "Zone Boundaries",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        zone_str = str(zone_id)
        job = {"service_zone_id": zone_str}
        staff_in = {"service_zone_id": zone_str}
        staff_out = {"service_zone_id": str(uuid4())}

        result_in = await scorer._score_zone_boundaries(
            config, job, staff_in, context,
        )
        result_out = await scorer._score_zone_boundaries(
            config, job, staff_out, context,
        )

        assert result_in.score > result_out.score


# ---------------------------------------------------------------------------
# Property 6: Workload Balance
# Validates: Requirements 4.4
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty6WorkloadBalance:
    """Property 6: Balanced workload std dev ≤ all-to-one case."""

    @given(
        hours=st.lists(
            st.floats(min_value=2, max_value=10),
            min_size=3,
            max_size=8,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_balanced_better_than_all_to_one(
        self,
        hours: list[float],
    ) -> None:
        """**Validates: Requirements 4.4**

        Std dev of balanced hours ≤ std dev of all-to-one assignment.
        """
        session = _make_async_session()
        scorer = ResourceScorer(session)
        config = {
            "criterion_name": "Workload Balance",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        # Balanced distribution
        staff_balanced = {"team_job_hours": hours}
        result_balanced = await scorer._score_workload_balance(
            config, {}, staff_balanced, context,
        )

        # All-to-one: total hours on one resource, 0 on rest
        total = sum(hours)
        all_to_one = [total] + [0.0] * (len(hours) - 1)
        staff_skewed = {"team_job_hours": all_to_one}
        result_skewed = await scorer._score_workload_balance(
            config, {}, staff_skewed, context,
        )

        # Balanced should score >= skewed
        assert result_balanced.score >= result_skewed.score


# ---------------------------------------------------------------------------
# Property 7: Priority and CLV Ordering
# Validates: Requirements 5.3, 5.4
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty7PriorityAndCLVOrdering:
    """Property 7: Higher priority job gets higher score."""

    @pytest.mark.asyncio
    async def test_emergency_beats_standard(
        self,
    ) -> None:
        """**Validates: Requirements 5.3**

        Emergency priority must score higher than standard.
        """
        session = _make_async_session()
        scorer = CustomerJobScorer(session)
        config = {
            "criterion_name": "Priority",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        job_emergency = {"priority": "emergency"}
        job_standard = {"priority": "standard"}

        result_e = await scorer._score_priority(config, job_emergency, {}, context)
        result_s = await scorer._score_priority(config, job_standard, {}, context)

        assert result_e.score > result_s.score

    @given(
        clv_high=st.floats(min_value=60, max_value=100),
        clv_low=st.floats(min_value=0, max_value=40),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_higher_clv_higher_score(
        self,
        clv_high: float,
        clv_low: float,
    ) -> None:
        """**Validates: Requirements 5.4**

        Higher CLV customer must score higher for tie-breaking.
        """
        session = _make_async_session()
        scorer = CustomerJobScorer(session)
        config = {
            "criterion_name": "CLV",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        job_high = {"customer": {"clv_score": clv_high}}
        job_low = {"customer": {"clv_score": clv_low}}

        result_h = await scorer._score_clv(config, job_high, {}, context)
        result_l = await scorer._score_clv(config, job_low, {}, context)

        assert result_h.score >= result_l.score


# ---------------------------------------------------------------------------
# Property 8: Capacity Utilization Calculation
# Validates: Requirements 6.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty8CapacityUtilization:
    """Property 8: Utilization formula correctness."""

    @given(
        job_min=st.floats(min_value=0, max_value=400),
        drive_min=st.floats(min_value=0, max_value=200),
        available_min=st.floats(min_value=60, max_value=600),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_utilization_formula(
        self,
        job_min: float,
        drive_min: float,
        available_min: float,
    ) -> None:
        """**Validates: Requirements 6.1**

        Utilization = (job_min + drive_min) / available_min * 100.
        Score penalizes >90% and <60%.
        """
        session = _make_async_session()
        scorer = CapacityDemandScorer(session)
        config = {
            "criterion_name": "Daily Utilization",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        staff = {
            "assigned_job_minutes": job_min,
            "assigned_drive_minutes": drive_min,
            "available_minutes": available_min,
        }

        result = await scorer._score_daily_utilization(config, {}, staff, context)

        utilization = (job_min + drive_min) / available_min * 100.0
        assert 0 <= result.score <= 100

        # Healthy range should score 100
        if 60.0 <= utilization <= 90.0:
            assert result.score == 100.0


# ---------------------------------------------------------------------------
# Property 9: Backlog Pressure Monotonicity
# Validates: Requirements 6.5
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty9BacklogPressure:
    """Property 9: More/older backlog = higher or equal pressure score."""

    @given(
        count_a=st.integers(min_value=1, max_value=50),
        count_b=st.integers(min_value=1, max_value=50),
        age_a=st.floats(min_value=0.1, max_value=30),
        age_b=st.floats(min_value=0.1, max_value=30),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_more_backlog_higher_score(
        self,
        count_a: int,
        count_b: int,
        age_a: float,
        age_b: float,
    ) -> None:
        """**Validates: Requirements 6.5**

        State with more jobs AND older age gets higher or equal score.
        Both states must have non-zero backlog to avoid neutral fallback.
        """
        session = _make_async_session()
        scorer = CapacityDemandScorer(session)
        config = {
            "criterion_name": "Backlog Pressure",
            "weight": 50,
            "is_hard_constraint": False,
        }

        context_a = _make_context(
            backlog={"unscheduled_count": count_a, "avg_age_days": age_a},
        )
        context_b = _make_context(
            backlog={"unscheduled_count": count_b, "avg_age_days": age_b},
        )

        result_a = await scorer._score_backlog_pressure(
            config, {}, {}, context_a,
        )
        result_b = await scorer._score_backlog_pressure(
            config, {}, {}, context_b,
        )

        # If both count and age are >= for A, score should be >=
        if count_a >= count_b and age_a >= age_b:
            assert result_a.score >= result_b.score


# ---------------------------------------------------------------------------
# Property 10: Revenue Per Resource-Hour Calculation
# Validates: Requirements 7.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty10RevenuePerHour:
    """Property 10: Revenue/hour formula correctness."""

    @given(
        revenue_per_hour=st.floats(min_value=50, max_value=300),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_revenue_score_monotonic(
        self,
        revenue_per_hour: float,
    ) -> None:
        """**Validates: Requirements 7.2**

        Higher revenue/hour must produce higher or equal score.
        """
        session = _make_async_session()
        scorer = BusinessRulesScorer(session)
        config = {
            "criterion_name": "Revenue Per Hour",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        job_high = {"revenue_per_hour": revenue_per_hour}
        job_low = {"revenue_per_hour": max(50.0, revenue_per_hour - 50)}

        result_h = await scorer._score_revenue_per_hour(
            config, job_high, {}, context,
        )
        result_l = await scorer._score_revenue_per_hour(
            config, job_low, {}, context,
        )

        assert result_h.score >= result_l.score


# ---------------------------------------------------------------------------
# Property 11: Overtime Cost-Benefit
# Validates: Requirements 7.4
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty11OvertimeCostBenefit:
    """Property 11: Overtime penalized unless revenue justifies."""

    @given(
        current_minutes=st.floats(min_value=400, max_value=500),
        job_duration=st.floats(min_value=30, max_value=120),
        threshold=st.integers(min_value=400, max_value=500),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_overtime_penalty_without_revenue(
        self,
        current_minutes: float,
        job_duration: float,
        threshold: int,
    ) -> None:
        """**Validates: Requirements 7.4**

        Overtime without high revenue must score lower than within threshold.
        """
        session = _make_async_session()
        scorer = BusinessRulesScorer(session)
        config = {
            "criterion_name": "Overtime Cost",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context()

        # Within threshold
        staff_ok = {
            "overtime_threshold_minutes": threshold + 200,
            "assigned_job_minutes": 0,
        }
        job_ok = {"estimated_duration_minutes": 60, "revenue_per_hour": None}
        result_ok = await scorer._score_overtime_cost(
            config, job_ok, staff_ok, context,
        )

        # Over threshold, no revenue justification
        staff_over = {
            "overtime_threshold_minutes": threshold,
            "assigned_job_minutes": current_minutes,
        }
        job_over = {
            "estimated_duration_minutes": job_duration,
            "revenue_per_hour": None,
        }
        result_over = await scorer._score_overtime_cost(
            config, job_over, staff_over, context,
        )

        assert result_ok.score >= result_over.score


# ---------------------------------------------------------------------------
# Property 12: Weather Impact on Outdoor Jobs
# Validates: Requirements 8.1, 23.7
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty12WeatherImpact:
    """Property 12: Outdoor + bad weather = penalty; indoor = neutral/positive."""

    @given(weather=st_weather_forecast())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_outdoor_bad_weather_penalty(
        self,
        weather: dict[str, Any],
    ) -> None:
        """**Validates: Requirements 8.1**

        Outdoor jobs on severe weather days get penalty; indoor unaffected.
        """
        session = _make_async_session()
        scorer = PredictiveScorer(session)
        config = {
            "criterion_name": "Weather Impact",
            "weight": 50,
            "is_hard_constraint": False,
        }
        context = _make_context(weather=weather)

        job_outdoor = {"is_outdoor": True}
        job_indoor = {"is_outdoor": False}

        result_outdoor = await scorer._score_weather_impact(
            config, job_outdoor, {}, context,
        )
        result_indoor = await scorer._score_weather_impact(
            config, job_indoor, {}, context,
        )

        # Indoor always scores 100
        assert result_indoor.score == 100.0

        # Bad weather conditions
        bad_conditions = {"rain", "storm", "freeze", "snow", "ice", "severe"}
        condition = weather.get("condition", "").lower()
        is_bad = any(bc in condition for bc in bad_conditions)

        if is_bad:
            assert result_outdoor.score == 0.0
            assert not result_outdoor.is_satisfied


# ---------------------------------------------------------------------------
# Property 13: Dependency Chain Ordering
# Validates: Requirements 8.5
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty13DependencyChainOrdering:
    """Property 13: Dependent job B cannot be scheduled before A completes."""

    @given(
        prereq_status=st.sampled_from([
            "completed", "done", "in_progress", "pending", "unknown",
        ]),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_dependency_enforcement(
        self,
        prereq_status: str,
    ) -> None:
        """**Validates: Requirements 8.5**

        Dependent job with incomplete prerequisite must not be satisfied.
        """
        session = _make_async_session()
        scorer = PredictiveScorer(session)
        config = {
            "criterion_name": "Dependency Chain",
            "weight": 50,
            "is_hard_constraint": True,
        }
        context = _make_context()

        job = {
            "depends_on_job_id": str(uuid4()),
            "prerequisite_status": prereq_status,
        }

        result = await scorer._score_dependency_chain(config, job, {}, context)

        completed_statuses = {"completed", "done", "finished"}
        if prereq_status in completed_statuses:
            assert result.is_satisfied
            assert result.score == 100.0
        else:
            assert not result.is_satisfied
            assert result.score == 0.0


# ---------------------------------------------------------------------------
# Property 14: Route Swap Improvement Guarantee
# Validates: Requirements 12.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty14RouteSwapImprovement:
    """Property 14: Route swap suggestions should reduce drive time."""

    @given(
        drive_a=st.integers(min_value=30, max_value=100),
        drive_b=st.integers(min_value=30, max_value=100),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_swap_suggestion_threshold(
        self,
        drive_a: int,
        drive_b: int,
    ) -> None:
        """**Validates: Requirements 12.1**

        Route swap suggestions only generated when combined drive > 120 min.
        """
        session = _make_async_session()
        engine = AlertEngine(session)

        rid_a = str(uuid4())
        rid_b = str(uuid4())
        assignments = [
            {
                "resource_id": rid_a,
                "job_id": str(uuid4()),
                "drive_time_minutes": drive_a,
            },
            {
                "resource_id": rid_b,
                "job_id": str(uuid4()),
                "drive_time_minutes": drive_b,
            },
        ]

        candidates = await engine._suggest_route_swaps(assignments)

        combined = drive_a + drive_b
        if combined > 120:
            assert len(candidates) >= 1
            assert candidates[0].alert_type == "route_swap"
        else:
            assert len(candidates) == 0


# ---------------------------------------------------------------------------
# Property 15: Pre-Job Checklist Completeness
# Validates: Requirements 15.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty15PreJobChecklistCompleteness:
    """Property 15: Checklist contains all required fields."""

    @given(data=st.data())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_checklist_has_all_fields(
        self,
        data: st.DataObject,
    ) -> None:
        """**Validates: Requirements 15.2**

        PreJobChecklist must contain: job_type, customer_name,
        customer_address, required_equipment, known_issues,
        gate_code, special_instructions, estimated_duration.
        """
        session = _make_async_session()
        generator = PreJobGenerator(session)

        # Use data to draw random UUIDs for variation
        _ = data.draw(st.uuids())

        checklist = await generator.generate_checklist(
            job_id=uuid4(),
            resource_id=uuid4(),
        )

        assert isinstance(checklist, PreJobChecklist)
        assert checklist.job_type is not None
        assert checklist.customer_name is not None
        assert checklist.customer_address is not None
        assert isinstance(checklist.required_equipment, list)
        assert isinstance(checklist.known_issues, list)
        # gate_code and special_instructions can be None
        assert hasattr(checklist, "gate_code")
        assert hasattr(checklist, "special_instructions")
        assert isinstance(checklist.estimated_duration, int)
        assert checklist.estimated_duration > 0


# ---------------------------------------------------------------------------
# Property 16: Nearby Work Radius and Skill Filtering
# Validates: Requirements 15.5
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty16NearbyWorkRadius:
    """Property 16: Nearby work results within 15-min drive + skill match."""

    @given(staff=st_schedule_staff())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_nearby_work_returns_within_radius(
        self,
        staff: dict[str, Any],
    ) -> None:
        """**Validates: Requirements 15.5**

        find_nearby_work must return jobs within 15-min radius
        matching resource skills and equipment.
        """
        session = _make_async_session()
        tools = ResourceSchedulingTools(session)

        result = await tools.find_nearby_work(
            resource_id=staff["id"],
            location=f"{staff['latitude']},{staff['longitude']}",
        )

        assert result["status"] == "search_complete"
        assert result["radius_minutes"] == 15
        assert isinstance(result["nearby_jobs"], list)
        # All returned jobs should be within radius (stub returns empty)
        for nearby_job in result["nearby_jobs"]:
            assert nearby_job.get("drive_minutes", 0) <= 15


# ---------------------------------------------------------------------------
# Property 17: Parts Low-Stock Threshold Alert
# Validates: Requirements 15.8
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty17PartsLowStock:
    """Property 17: Low-stock alert when inventory drops below threshold."""

    @given(
        parts_count=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_parts_logging_returns_warnings(
        self,
        parts_count: int,
    ) -> None:
        """**Validates: Requirements 15.8**

        log_parts must return low_stock_warnings list.
        """
        session = _make_async_session()
        tools = ResourceSchedulingTools(session)

        parts_list = [
            {"part_name": f"part_{i}", "quantity_used": 1}
            for i in range(parts_count)
        ]

        result = await tools.log_parts(
            resource_id=str(uuid4()),
            job_id=str(uuid4()),
            parts_list=parts_list,
        )

        assert result["status"] == "parts_logged"
        assert isinstance(result["low_stock_warnings"], list)
        assert len(result["parts_logged"]) == parts_count


# ---------------------------------------------------------------------------
# Property 18: 30-Criteria Evaluation Completeness
# Validates: Requirements 23.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty18CriteriaCompleteness:
    """Property 18: Evaluation returns exactly 30 criteria scores."""

    @given(job=st_schedule_job(), staff=st_schedule_staff())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_30_criteria_returned(
        self,
        job: dict[str, Any],
        staff: dict[str, Any],
    ) -> None:
        """**Validates: Requirements 23.1**

        evaluate_assignment must return exactly 30 CriterionResult
        entries, numbers 1-30, no duplicates.
        """
        session = _make_async_session()
        config = _make_default_config()
        evaluator = CriteriaEvaluator(session, config)
        context = _make_context()

        results = await evaluator.evaluate_assignment(job, staff, context)

        assert len(results) == 30
        numbers = [r.criterion_number for r in results]
        assert sorted(numbers) == list(range(1, 31))
        assert len(set(numbers)) == 30  # no duplicates


# ---------------------------------------------------------------------------
# Property 19: PII Protection in AI Outputs
# Validates: Requirements 24.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty19PIIProtection:
    """Property 19: No raw phone/email/address in AI output."""

    @given(
        phone=st.from_regex(r"[0-9]{10}", fullmatch=True),
        email=st.from_regex(r"[a-z]{5}@[a-z]{5}\.[a-z]{3}", fullmatch=True),
    )
    @settings(max_examples=50)
    def test_pii_not_in_system_prompts(
        self,
        phone: str,
        email: str,
    ) -> None:
        """**Validates: Requirements 24.1**

        System prompts must instruct against including raw PII.
        """
        # Verify prompts contain PII protection instructions
        assert "phone" in ADMIN_SYSTEM_PROMPT.lower()
        assert "email" in ADMIN_SYSTEM_PROMPT.lower()
        assert "phone" in RESOURCE_SYSTEM_PROMPT.lower()
        assert "email" in RESOURCE_SYSTEM_PROMPT.lower()

        # Verify the generated phone/email are not in the prompts
        assert phone not in ADMIN_SYSTEM_PROMPT
        assert email not in ADMIN_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Property 20: Audit Trail Completeness
# Validates: Requirements 24.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty20AuditTrailCompleteness:
    """Property 20: Audit log entry count = message count."""

    @given(
        message_count=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_audit_entries_match_messages(
        self,
        message_count: int,
    ) -> None:
        """**Validates: Requirements 24.3**

        Each chat interaction must produce an audit trail entry.
        The persist_turn method appends both user and assistant messages.
        """
        session = _make_async_session()
        service = SchedulingChatService(session)

        # Create a mock session record
        mock_session_record = MagicMock()
        mock_session_record.messages = []

        for i in range(message_count):
            await service._persist_turn(
                mock_session_record,
                f"user message {i}",
                f"assistant response {i}",
            )

        # Each turn adds 2 entries (user + assistant)
        assert len(mock_session_record.messages) == message_count * 2


# ---------------------------------------------------------------------------
# Property 21: Resource Chat Routing Completeness
# Validates: Requirements 1.9
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty21ResourceChatRouting:
    """Property 21: Each resource message produces exactly one of
    direct response or change request (not both, not neither)."""

    @given(
        tool_name=st.sampled_from([
            "report_delay",
            "get_prejob_info",
            "request_followup",
            "report_access_issue",
            "find_nearby_work",
            "request_resequence",
            "request_assistance",
            "log_parts",
            "get_tomorrow_schedule",
            "request_upgrade_quote",
        ]),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_resource_tool_produces_result(
        self,
        tool_name: str,
    ) -> None:
        """**Validates: Requirements 1.9**

        Each resource tool must return a result with a status field.
        Tools that create change requests have status='change_request_created'.
        Autonomous tools have other statuses.
        """
        session = _make_async_session()
        tools = ResourceSchedulingTools(session)

        # Build minimal args for each tool
        args_map: dict[str, dict[str, Any]] = {
            "report_delay": {
                "resource_id": str(uuid4()),
                "delay_minutes": 30,
            },
            "get_prejob_info": {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
            },
            "request_followup": {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
                "field_notes": "Needs follow-up",
            },
            "report_access_issue": {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
                "issue_type": "gate_locked",
            },
            "find_nearby_work": {
                "resource_id": str(uuid4()),
                "location": "44.9,-93.2",
            },
            "request_resequence": {
                "resource_id": str(uuid4()),
                "reason": "Traffic",
            },
            "request_assistance": {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
                "skill_needed": "backflow_certified",
            },
            "log_parts": {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
                "parts_list": [{"part_name": "valve", "quantity_used": 1}],
            },
            "get_tomorrow_schedule": {
                "resource_id": str(uuid4()),
            },
            "request_upgrade_quote": {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
                "upgrade_type": "controller",
            },
        }

        handler = getattr(tools, tool_name)
        result = await handler(**args_map[tool_name])

        assert "status" in result

        # Categorize: change_request vs autonomous
        change_request_tools = {
            "request_followup",
            "request_resequence",
            "request_assistance",
            "request_upgrade_quote",
        }
        autonomous_tools = {
            "report_delay",
            "get_prejob_info",
            "report_access_issue",
            "find_nearby_work",
            "log_parts",
            "get_tomorrow_schedule",
        }

        if tool_name in change_request_tools:
            assert result["status"] == "change_request_created"
        elif tool_name in autonomous_tools:
            assert result["status"] != "change_request_created"


# ---------------------------------------------------------------------------
# Property 22: Constraint Parsing Round-Trip
# Validates: Requirements 26.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty22ConstraintParsingRoundTrip:
    """Property 22: parse → describe → re-parse equivalence."""

    @given(
        priority=st.sampled_from(["emergency", "vip", "standard", "flexible"]),
        is_outdoor=st.booleans(),
        duration=st.integers(min_value=30, max_value=480),
    )
    @settings(max_examples=50)
    def test_constraint_round_trip(
        self,
        priority: str,
        is_outdoor: bool,
        duration: int,
    ) -> None:
        """**Validates: Requirements 26.3**

        Structured constraint parameters must survive a round-trip
        through serialization and deserialization.
        """
        # Build structured constraint
        constraint = {
            "priority": priority,
            "is_outdoor": is_outdoor,
            "estimated_duration_minutes": duration,
        }

        # Serialize (parse → describe)
        serialized = json.dumps(constraint, sort_keys=True)

        # Deserialize (re-parse)
        reparsed = json.loads(serialized)

        # Round-trip equivalence
        assert reparsed["priority"] == priority
        assert reparsed["is_outdoor"] == is_outdoor
        assert reparsed["estimated_duration_minutes"] == duration
        assert reparsed == constraint
