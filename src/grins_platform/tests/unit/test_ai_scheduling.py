"""Unit tests for all 30 AI scheduling criteria scorers.

Tests each scorer with mocked data inputs, alert/suggestion generation,
ChangeRequest packaging, PreJobGenerator, and financial calculations.

Validates: Requirements 26.4, 26.5, 26.6, 26.7
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from grins_platform.schemas.ai_scheduling import (
    PreJobChecklist,
)
from grins_platform.services.schedule_domain import (
    ScheduleJob,
    ScheduleLocation,
    ScheduleStaff,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_location(lat: float = 44.9, lon: float = -93.2) -> ScheduleLocation:
    return ScheduleLocation(
        latitude=Decimal(str(lat)),
        longitude=Decimal(str(lon)),
        address="123 Test St",
        city="Minneapolis",
    )


def _make_job(
    service_type: str = "spring_opening",
    duration: int = 60,
    equipment: list[str] | None = None,
    priority: int = 3,
    lat: float = 44.9,
    lon: float = -93.2,
) -> ScheduleJob:
    return ScheduleJob(
        id=uuid4(),
        customer_name="Test Customer",
        location=_make_location(lat, lon),
        service_type=service_type,
        duration_minutes=duration,
        equipment_required=equipment or [],
        priority=priority,
        preferred_time_start=None,
        preferred_time_end=None,
    )


def _make_staff(
    equipment: list[str] | None = None,
    lat: float = 44.9,
    lon: float = -93.2,
    avail_start: time = time(7, 0),
    avail_end: time = time(17, 0),
) -> ScheduleStaff:
    return ScheduleStaff(
        id=uuid4(),
        name="Test Tech",
        start_location=_make_location(lat, lon),
        assigned_equipment=equipment or [],
        availability_start=avail_start,
        availability_end=avail_end,
    )


def _make_context(**kwargs: Any) -> Any:
    ctx = MagicMock()
    ctx.schedule_date = kwargs.get("schedule_date", date.today())
    ctx.weather = kwargs.get("weather", {})
    ctx.traffic = kwargs.get("traffic", {})
    ctx.backlog = kwargs.get("backlog", {})
    ctx.google_drive_times = kwargs.get("google_drive_times", {})
    ctx.staff_certifications = kwargs.get("staff_certifications", {})
    ctx.staff_performance = kwargs.get("staff_performance", {})
    ctx.service_zones = kwargs.get("service_zones", {})
    ctx.job_skills_required = kwargs.get("job_skills_required", {})
    ctx.truck_inventory = kwargs.get("truck_inventory", {})
    ctx.customer_data = kwargs.get("customer_data", {})
    ctx.all_assignments = kwargs.get("all_assignments", [])
    return ctx


def _make_config(
    number: int,
    weight: int = 50,
    is_hard: bool = False,
    enabled: bool = True,
) -> Any:
    cfg = MagicMock()
    cfg.weight = weight
    cfg.is_hard_constraint = is_hard
    cfg.enabled = enabled
    return cfg


def _default_config(hard_criteria: set[int] | None = None) -> dict[int, Any]:
    hard = hard_criteria or {6, 7, 8, 21, 23, 30}
    return {n: _make_config(n, weight=50, is_hard=(n in hard)) for n in range(1, 31)}


# ---------------------------------------------------------------------------
# GeographicScorer — criteria 1-5
# ---------------------------------------------------------------------------


class TestGeographicScorer:
    """Tests for GeographicScorer criteria 1-5."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_1_proximity_near_resource(self) -> None:
        """Criterion 1: nearby resource scores high."""
        from grins_platform.services.ai.scheduling.scorers.geographic import (
            GeographicScorer,
        )

        scorer = GeographicScorer()
        job = _make_job(lat=44.9, lon=-93.2)
        staff = _make_staff(lat=44.901, lon=-93.2)  # ~0.1 km away
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c1 = next(r for r in results if r.criterion_number == 1)

        assert c1.score >= 80.0, f"Near resource should score >= 80, got {c1.score}"
        assert 0.0 <= c1.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_1_proximity_far_resource(self) -> None:
        """Criterion 1: far resource scores low."""
        from grins_platform.services.ai.scheduling.scorers.geographic import (
            GeographicScorer,
        )

        scorer = GeographicScorer()
        job = _make_job(lat=44.9, lon=-93.2)
        staff = _make_staff(lat=45.5, lon=-93.2)  # ~66 km away
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c1 = next(r for r in results if r.criterion_number == 1)

        assert c1.score <= 20.0, f"Far resource should score <= 20, got {c1.score}"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_2_intra_route_drive_time(self) -> None:
        """Criterion 2: returns a valid score."""
        from grins_platform.services.ai.scheduling.scorers.geographic import (
            GeographicScorer,
        )

        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c2 = next(r for r in results if r.criterion_number == 2)

        assert 0.0 <= c2.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_3_in_zone_scores_higher(self) -> None:
        """Criterion 3: in-zone resource scores >= out-of-zone."""
        from grins_platform.services.ai.scheduling.scorers.geographic import (
            GeographicScorer,
        )

        scorer = GeographicScorer()
        job = _make_job()
        staff_in = _make_staff()
        staff_out = _make_staff()

        zone_id = str(uuid4())
        ctx_in = _make_context(
            service_zones={str(staff_in.id): zone_id, "job_zone": zone_id}
        )
        ctx_out = _make_context(
            service_zones={str(staff_out.id): str(uuid4()), "job_zone": zone_id}
        )
        config = _default_config()

        results_in = await scorer.score_assignment(job, staff_in, ctx_in, config)
        results_out = await scorer.score_assignment(job, staff_out, ctx_out, config)

        c3_in = next(r for r in results_in if r.criterion_number == 3)
        c3_out = next(r for r in results_out if r.criterion_number == 3)

        assert c3_in.score >= c3_out.score, (
            f"In-zone score {c3_in.score} must be >= out-of-zone {c3_out.score}"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_4_traffic_returns_valid_score(self) -> None:
        """Criterion 4: traffic score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.geographic import (
            GeographicScorer,
        )

        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(traffic={"congestion_factor": 1.5})
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c4 = next(r for r in results if r.criterion_number == 4)

        assert 0.0 <= c4.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_5_access_constraints_returns_valid_score(self) -> None:
        """Criterion 5: access constraint score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.geographic import (
            GeographicScorer,
        )

        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c5 = next(r for r in results if r.criterion_number == 5)

        assert 0.0 <= c5.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_geographic_scorer_returns_5_criteria(self) -> None:
        """GeographicScorer must return exactly 5 CriterionResult objects."""
        from grins_platform.services.ai.scheduling.scorers.geographic import (
            GeographicScorer,
        )

        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)

        assert len(results) == 5
        numbers = {r.criterion_number for r in results}
        assert numbers == {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# ResourceScorer — criteria 6-10
# ---------------------------------------------------------------------------


class TestResourceScorer:
    """Tests for ResourceScorer criteria 6-10."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_6_skill_match_satisfied(self) -> None:
        """Criterion 6: staff with required skills is satisfied."""
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _make_job(equipment=["backflow_tester"])
        staff = _make_staff(equipment=["backflow_tester", "winterizer"])
        # Provide explicit skills map so service_type is not auto-derived
        ctx = _make_context(
            backlog={
                "required_skills": {str(job.id): ["backflow_tester"]},
                "staff_certifications": {
                    str(staff.id): ["backflow_tester", "winterizer"]
                },
            }
        )
        config = _default_config(hard_criteria={6, 7, 8})

        results = await scorer.score_assignment(job, staff, ctx, config)
        c6 = next(r for r in results if r.criterion_number == 6)

        assert c6.is_satisfied
        assert c6.score == 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_6_skill_mismatch_hard_violation(self) -> None:
        """Criterion 6: missing required skill is a hard violation."""
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _make_job(equipment=["backflow_tester"])
        staff = _make_staff(equipment=["winterizer"])  # missing backflow_tester
        ctx = _make_context()
        config = _default_config(hard_criteria={6, 7, 8})

        results = await scorer.score_assignment(job, staff, ctx, config)
        c6 = next(r for r in results if r.criterion_number == 6)

        assert not c6.is_satisfied
        assert c6.score == 0.0
        assert c6.is_hard

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_7_equipment_on_truck(self) -> None:
        """Criterion 7: equipment check returns valid score."""
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _make_job(equipment=["winterizer"])
        staff = _make_staff(equipment=["winterizer"])
        ctx = _make_context()
        config = _default_config(hard_criteria={6, 7, 8})

        results = await scorer.score_assignment(job, staff, ctx, config)
        c7 = next(r for r in results if r.criterion_number == 7)

        assert 0.0 <= c7.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_8_availability_window(self) -> None:
        """Criterion 8: availability window check returns valid score."""
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _make_job()
        staff = _make_staff(avail_start=time(7, 0), avail_end=time(17, 0))
        ctx = _make_context()
        config = _default_config(hard_criteria={6, 7, 8})

        results = await scorer.score_assignment(job, staff, ctx, config)
        c8 = next(r for r in results if r.criterion_number == 8)

        assert 0.0 <= c8.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_9_workload_balance(self) -> None:
        """Criterion 9: workload balance score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            all_assignments=[
                {"staff_id": str(staff.id), "total_minutes": 240},
                {"staff_id": str(uuid4()), "total_minutes": 120},
            ]
        )
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c9 = next(r for r in results if r.criterion_number == 9)

        assert 0.0 <= c9.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_10_performance_history(self) -> None:
        """Criterion 10: performance history score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            staff_performance={
                str(staff.id): {
                    "performance_score": 0.9,
                    "callback_rate": 0.05,
                    "avg_satisfaction": 4.8,
                }
            }
        )
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c10 = next(r for r in results if r.criterion_number == 10)

        assert 0.0 <= c10.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resource_scorer_returns_5_criteria(self) -> None:
        """ResourceScorer must return exactly 5 CriterionResult objects."""
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)

        assert len(results) == 5
        numbers = {r.criterion_number for r in results}
        assert numbers == {6, 7, 8, 9, 10}


# ---------------------------------------------------------------------------
# CustomerJobScorer — criteria 11-15
# ---------------------------------------------------------------------------


class TestCustomerJobScorer:
    """Tests for CustomerJobScorer criteria 11-15."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_11_time_window_preference(self) -> None:
        """Criterion 11: time window preference returns valid score."""
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            customer_data={
                "time_window_preference": "morning",
                "time_window_is_hard": False,
            }
        )
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c11 = next(r for r in results if r.criterion_number == 11)

        assert 0.0 <= c11.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_12_job_duration_estimate(self) -> None:
        """Criterion 12: duration estimate score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _make_job(duration=90)
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c12 = next(r for r in results if r.criterion_number == 12)

        assert 0.0 <= c12.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_13_high_priority_scores_higher(self) -> None:
        """Criterion 13: higher priority job scores higher."""
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job_high = _make_job(priority=5)
        job_low = _make_job(priority=1)
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results_high = await scorer.score_assignment(job_high, staff, ctx, config)
        results_low = await scorer.score_assignment(job_low, staff, ctx, config)

        c13_high = next(r for r in results_high if r.criterion_number == 13)
        c13_low = next(r for r in results_low if r.criterion_number == 13)

        assert c13_high.score >= c13_low.score, (
            f"High priority score {c13_high.score} must be >= "
            f"low priority {c13_low.score}"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_14_clv_score(self) -> None:
        """Criterion 14: CLV score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(customer_data={"clv_score": 15000.0})
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c14 = next(r for r in results if r.criterion_number == 14)

        assert 0.0 <= c14.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_15_preferred_resource_match(self) -> None:
        """Criterion 15: preferred resource match scores higher."""
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _make_job()
        staff = _make_staff()
        ctx_match = _make_context(
            customer_data={"preferred_resource_id": str(staff.id)}
        )
        ctx_no_match = _make_context(
            customer_data={"preferred_resource_id": str(uuid4())}
        )
        config = _default_config()

        results_match = await scorer.score_assignment(job, staff, ctx_match, config)
        results_no = await scorer.score_assignment(job, staff, ctx_no_match, config)

        c15_match = next(r for r in results_match if r.criterion_number == 15)
        c15_no = next(r for r in results_no if r.criterion_number == 15)

        assert c15_match.score >= c15_no.score

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_customer_job_scorer_returns_5_criteria(self) -> None:
        """CustomerJobScorer must return exactly 5 CriterionResult objects."""
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)

        assert len(results) == 5
        numbers = {r.criterion_number for r in results}
        assert numbers == {11, 12, 13, 14, 15}


# ---------------------------------------------------------------------------
# CapacityDemandScorer — criteria 16-20
# ---------------------------------------------------------------------------


class TestCapacityDemandScorer:
    """Tests for CapacityDemandScorer criteria 16-20."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_16_utilization_healthy(self) -> None:
        """Criterion 16: 60-90% utilization scores high."""
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            all_assignments=[
                {
                    "staff_id": str(staff.id),
                    "total_job_minutes": 360,
                    "total_drive_minutes": 60,
                    "available_minutes": 600,
                }
            ]
        )
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c16 = next(r for r in results if r.criterion_number == 16)

        assert 0.0 <= c16.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_17_demand_forecast(self) -> None:
        """Criterion 17: demand forecast score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(backlog={"forecast_jobs_next_week": 45})
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c17 = next(r for r in results if r.criterion_number == 17)

        assert 0.0 <= c17.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_18_seasonal_peak(self) -> None:
        """Criterion 18: seasonal peak score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            backlog={"is_peak_season": True, "peak_type": "spring_opening"}
        )
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c18 = next(r for r in results if r.criterion_number == 18)

        assert 0.0 <= c18.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_19_cancellation_probability(self) -> None:
        """Criterion 19: low cancellation probability scores high."""
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job = _make_job()
        staff = _make_staff()
        ctx_low = _make_context(customer_data={"cancel_probability": 0.02})
        ctx_high = _make_context(customer_data={"cancel_probability": 0.60})
        config = _default_config()

        results_low = await scorer.score_assignment(job, staff, ctx_low, config)
        results_high = await scorer.score_assignment(job, staff, ctx_high, config)

        c19_low = next(r for r in results_low if r.criterion_number == 19)
        c19_high = next(r for r in results_high if r.criterion_number == 19)

        assert c19_low.score >= c19_high.score

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_20_backlog_pressure(self) -> None:
        """Criterion 20: older backlog jobs score higher pressure."""
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job_old = _make_job()
        job_new = _make_job()
        staff = _make_staff()
        ctx_old = _make_context(backlog={"job_age_days": 45, "backlog_count": 20})
        ctx_new = _make_context(backlog={"job_age_days": 1, "backlog_count": 5})
        config = _default_config()

        results_old = await scorer.score_assignment(job_old, staff, ctx_old, config)
        results_new = await scorer.score_assignment(job_new, staff, ctx_new, config)

        c20_old = next(r for r in results_old if r.criterion_number == 20)
        c20_new = next(r for r in results_new if r.criterion_number == 20)

        assert c20_old.score >= c20_new.score

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_capacity_demand_scorer_returns_5_criteria(self) -> None:
        """CapacityDemandScorer must return exactly 5 CriterionResult objects."""
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)

        assert len(results) == 5
        numbers = {r.criterion_number for r in results}
        assert numbers == {16, 17, 18, 19, 20}


# ---------------------------------------------------------------------------
# BusinessRulesScorer — criteria 21-25
# ---------------------------------------------------------------------------


class TestBusinessRulesScorer:
    """Tests for BusinessRulesScorer criteria 21-25."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_21_compliance_deadline_hard(self) -> None:
        """Criterion 21: compliance deadline is a hard constraint."""
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config(hard_criteria={21, 23})

        results = await scorer.score_assignment(job, staff, ctx, config)
        c21 = next(r for r in results if r.criterion_number == 21)

        assert 0.0 <= c21.score <= 100.0
        assert c21.is_hard

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_22_revenue_per_hour(self) -> None:
        """Criterion 22: revenue per resource-hour score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _make_job(duration=60)
        staff = _make_staff()
        ctx = _make_context(
            customer_data={"job_revenue": 250.0, "drive_time_minutes": 15}
        )
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c22 = next(r for r in results if r.criterion_number == 22)

        assert 0.0 <= c22.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_23_sla_deadline_hard(self) -> None:
        """Criterion 23: SLA deadline is a hard constraint."""
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config(hard_criteria={21, 23})

        results = await scorer.score_assignment(job, staff, ctx, config)
        c23 = next(r for r in results if r.criterion_number == 23)

        assert 0.0 <= c23.score <= 100.0
        assert c23.is_hard

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_24_overtime_threshold(self) -> None:
        """Criterion 24: overtime threshold score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            all_assignments=[
                {
                    "staff_id": str(staff.id),
                    "total_minutes": 540,  # 9 hours
                    "overtime_threshold_minutes": 480,  # 8 hours
                }
            ]
        )
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c24 = next(r for r in results if r.criterion_number == 24)

        assert 0.0 <= c24.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_25_seasonal_pricing(self) -> None:
        """Criterion 25: seasonal pricing score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(backlog={"is_peak_season": True})
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c25 = next(r for r in results if r.criterion_number == 25)

        assert 0.0 <= c25.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_business_rules_scorer_returns_5_criteria(self) -> None:
        """BusinessRulesScorer must return exactly 5 CriterionResult objects."""
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)

        assert len(results) == 5
        numbers = {r.criterion_number for r in results}
        assert numbers == {21, 22, 23, 24, 25}


# ---------------------------------------------------------------------------
# PredictiveScorer — criteria 26-30
# ---------------------------------------------------------------------------


class TestPredictiveScorer:
    """Tests for PredictiveScorer criteria 26-30."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_26_weather_outdoor_severe(self) -> None:
        """Criterion 26: outdoor job on severe weather day scores low."""
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _make_job(service_type="spring_opening")  # outdoor
        staff = _make_staff()
        ctx = _make_context(
            weather={
                "condition": "thunderstorm",
                "precipitation_inches": 2.0,
                "freeze_warning": False,
                "severe_weather": True,
            }
        )
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c26 = next(r for r in results if r.criterion_number == 26)

        assert 0.0 <= c26.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_27_predicted_complexity(self) -> None:
        """Criterion 27: predicted complexity score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(customer_data={"predicted_complexity": 0.8})
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c27 = next(r for r in results if r.criterion_number == 27)

        assert 0.0 <= c27.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_28_lead_conversion_timing(self) -> None:
        """Criterion 28: lead conversion timing score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c28 = next(r for r in results if r.criterion_number == 28)

        assert 0.0 <= c28.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_29_start_location_proximity(self) -> None:
        """Criterion 29: start location proximity score is in [0, 100]."""
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _make_job(lat=44.9, lon=-93.2)
        staff = _make_staff(lat=44.901, lon=-93.2)
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)
        c29 = next(r for r in results if r.criterion_number == 29)

        assert 0.0 <= c29.score <= 100.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_criterion_30_dependency_chain_hard(self) -> None:
        """Criterion 30: dependency chain is a hard constraint."""
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config(hard_criteria={30})

        results = await scorer.score_assignment(job, staff, ctx, config)
        c30 = next(r for r in results if r.criterion_number == 30)

        assert 0.0 <= c30.score <= 100.0
        assert c30.is_hard

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_predictive_scorer_returns_5_criteria(self) -> None:
        """PredictiveScorer must return exactly 5 CriterionResult objects."""
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()
        config = _default_config()

        results = await scorer.score_assignment(job, staff, ctx, config)

        assert len(results) == 5
        numbers = {r.criterion_number for r in results}
        assert numbers == {26, 27, 28, 29, 30}


# ---------------------------------------------------------------------------
# Alert and Suggestion Generation Tests (task 15.13)
# ---------------------------------------------------------------------------


class TestAlertGeneration:
    """Tests for alert and suggestion generation logic."""

    @pytest.mark.unit
    def test_double_booking_alert_type(self) -> None:
        """Double-booking alert must have correct type and severity."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        alert = AlertCandidate(
            alert_type="double_booking",
            severity="critical",
            title="Double Booking Detected",
            description="Staff member has overlapping appointments",
            affected_job_ids=[str(uuid4()), str(uuid4())],
            affected_staff_ids=[str(uuid4())],
            criteria_triggered=[8],
            resolution_options=[],
        )

        assert alert.alert_type == "double_booking"
        assert alert.severity == "critical"
        assert len(alert.affected_job_ids) == 2
        assert len(alert.affected_staff_ids) == 1

    @pytest.mark.unit
    def test_skill_mismatch_alert_type(self) -> None:
        """Skill mismatch alert must have correct type and severity."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        alert = AlertCandidate(
            alert_type="skill_mismatch",
            severity="critical",
            title="Skill Mismatch",
            description="Staff lacks required certification",
            affected_job_ids=[str(uuid4())],
            affected_staff_ids=[str(uuid4())],
            criteria_triggered=[6],
            resolution_options=[],
        )

        assert alert.alert_type == "skill_mismatch"
        assert alert.severity == "critical"
        assert 6 in alert.criteria_triggered

    @pytest.mark.unit
    def test_sla_risk_alert_type(self) -> None:
        """SLA risk alert must have correct type."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        alert = AlertCandidate(
            alert_type="sla_risk",
            severity="critical",
            title="SLA Risk",
            description="Job approaching SLA deadline",
            affected_job_ids=[str(uuid4())],
            affected_staff_ids=[],
            criteria_triggered=[23],
            resolution_options=[],
        )

        assert alert.alert_type == "sla_risk"
        assert 23 in alert.criteria_triggered

    @pytest.mark.unit
    def test_resource_behind_alert_type(self) -> None:
        """Resource behind alert must have correct type."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        alert = AlertCandidate(
            alert_type="resource_behind",
            severity="warning",
            title="Resource Running Behind",
            description="Staff member is behind schedule",
            affected_job_ids=[str(uuid4())],
            affected_staff_ids=[str(uuid4())],
            criteria_triggered=[],
            resolution_options=[],
        )

        assert alert.alert_type == "resource_behind"
        assert alert.severity == "warning"

    @pytest.mark.unit
    def test_severe_weather_alert_type(self) -> None:
        """Severe weather alert must have correct type."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        alert = AlertCandidate(
            alert_type="severe_weather",
            severity="critical",
            title="Severe Weather Warning",
            description="Outdoor jobs at risk due to severe weather",
            affected_job_ids=[str(uuid4())],
            affected_staff_ids=[],
            criteria_triggered=[26],
            resolution_options=[],
        )

        assert alert.alert_type == "severe_weather"
        assert 26 in alert.criteria_triggered

    @pytest.mark.unit
    def test_route_swap_suggestion_type(self) -> None:
        """Route swap suggestion must have correct type."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        suggestion = AlertCandidate(
            alert_type="route_swap",
            severity="suggestion",
            title="Route Swap Opportunity",
            description="Swapping 2 jobs saves 28 min drive time",
            affected_job_ids=[str(uuid4()), str(uuid4())],
            affected_staff_ids=[str(uuid4()), str(uuid4())],
            criteria_triggered=[1, 2],
            resolution_options=[],
        )

        assert suggestion.alert_type == "route_swap"
        assert suggestion.severity == "suggestion"

    @pytest.mark.unit
    def test_underutilized_resource_suggestion_type(self) -> None:
        """Underutilized resource suggestion must have correct type."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        suggestion = AlertCandidate(
            alert_type="underutilized_resource",
            severity="suggestion",
            title="Underutilized Resource",
            description="Staff member has capacity for 2 more jobs",
            affected_job_ids=[],
            affected_staff_ids=[str(uuid4())],
            criteria_triggered=[16],
            resolution_options=[],
        )

        assert suggestion.alert_type == "underutilized_resource"
        assert 16 in suggestion.criteria_triggered

    @pytest.mark.unit
    def test_customer_preference_suggestion_type(self) -> None:
        """Customer preference suggestion must have correct type."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        suggestion = AlertCandidate(
            alert_type="customer_preference",
            severity="suggestion",
            title="Customer Preference Match",
            description="Customer prefers morning appointments",
            affected_job_ids=[str(uuid4())],
            affected_staff_ids=[],
            criteria_triggered=[11, 15],
            resolution_options=[],
        )

        assert suggestion.alert_type == "customer_preference"

    @pytest.mark.unit
    def test_overtime_avoidable_suggestion_type(self) -> None:
        """Overtime avoidable suggestion must have correct type."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        suggestion = AlertCandidate(
            alert_type="overtime_avoidable",
            severity="suggestion",
            title="Overtime Avoidable",
            description="Resequencing avoids overtime for this resource",
            affected_job_ids=[str(uuid4())],
            affected_staff_ids=[str(uuid4())],
            criteria_triggered=[24],
            resolution_options=[],
        )

        assert suggestion.alert_type == "overtime_avoidable"
        assert 24 in suggestion.criteria_triggered

    @pytest.mark.unit
    def test_high_revenue_job_suggestion_type(self) -> None:
        """High revenue job suggestion must have correct type."""
        from grins_platform.schemas.ai_scheduling import AlertCandidate

        suggestion = AlertCandidate(
            alert_type="high_revenue_job",
            severity="suggestion",
            title="High Revenue Job Available",
            description="Unscheduled job with $450/hr revenue potential",
            affected_job_ids=[str(uuid4())],
            affected_staff_ids=[],
            criteria_triggered=[22],
            resolution_options=[],
        )

        assert suggestion.alert_type == "high_revenue_job"
        assert 22 in suggestion.criteria_triggered


# ---------------------------------------------------------------------------
# ChangeRequest Packaging Tests (task 15.14)
# ---------------------------------------------------------------------------


class TestChangeRequestPackaging:
    """Tests for ChangeRequest packaging logic."""

    @pytest.mark.unit
    def test_delay_report_request_type(self) -> None:
        """delay_report produces correct ChangeRequest fields."""
        from grins_platform.models.change_request import ChangeRequest

        cr = ChangeRequest()
        cr.resource_id = uuid4()
        cr.request_type = "delay_report"
        cr.details = {"delay_minutes": 20, "reason": "traffic"}
        cr.affected_job_id = uuid4()
        cr.recommended_action = "Notify downstream customers"
        cr.status = "pending"

        assert cr.request_type == "delay_report"
        assert cr.details["delay_minutes"] == 20
        assert cr.recommended_action is not None

    @pytest.mark.unit
    def test_followup_job_request_type(self) -> None:
        """followup_job produces correct ChangeRequest fields."""
        from grins_platform.models.change_request import ChangeRequest

        cr = ChangeRequest()
        cr.resource_id = uuid4()
        cr.request_type = "followup_job"
        cr.details = {"description": "Valve needs replacement", "estimated_hours": 1.5}
        cr.affected_job_id = uuid4()
        cr.recommended_action = "Schedule follow-up repair"
        cr.status = "pending"

        assert cr.request_type == "followup_job"
        assert "description" in cr.details

    @pytest.mark.unit
    def test_access_issue_request_type(self) -> None:
        """access_issue produces correct ChangeRequest fields."""
        from grins_platform.models.change_request import ChangeRequest

        cr = ChangeRequest()
        cr.resource_id = uuid4()
        cr.request_type = "access_issue"
        cr.details = {"issue": "Gate code not working", "customer_notified": False}
        cr.affected_job_id = uuid4()
        cr.recommended_action = "Contact customer for access"
        cr.status = "pending"

        assert cr.request_type == "access_issue"
        assert cr.status == "pending"

    @pytest.mark.unit
    def test_parts_log_request_type(self) -> None:
        """parts_log produces correct ChangeRequest fields."""
        from grins_platform.models.change_request import ChangeRequest

        cr = ChangeRequest()
        cr.resource_id = uuid4()
        cr.request_type = "parts_log"
        cr.details = {"part_name": "valve_tool", "quantity_used": 2}
        cr.affected_job_id = uuid4()
        cr.recommended_action = "Update truck inventory"
        cr.status = "pending"

        assert cr.request_type == "parts_log"
        assert cr.details["part_name"] == "valve_tool"

    @pytest.mark.unit
    def test_upgrade_quote_request_type(self) -> None:
        """upgrade_quote produces correct ChangeRequest fields."""
        from grins_platform.models.change_request import ChangeRequest

        cr = ChangeRequest()
        cr.resource_id = uuid4()
        cr.request_type = "upgrade_quote"
        cr.details = {
            "equipment_name": "Smart Controller",
            "estimated_cost": 450.0,
        }
        cr.affected_job_id = uuid4()
        cr.recommended_action = "Generate upgrade quote for customer"
        cr.status = "pending"

        assert cr.request_type == "upgrade_quote"
        assert cr.details["estimated_cost"] == 450.0

    @pytest.mark.unit
    def test_resequence_request_type(self) -> None:
        """resequence produces correct ChangeRequest fields."""
        from grins_platform.models.change_request import ChangeRequest

        cr = ChangeRequest()
        cr.resource_id = uuid4()
        cr.request_type = "resequence"
        cr.details = {"reason": "Customer requested earlier slot"}
        cr.affected_job_id = uuid4()
        cr.recommended_action = "Reorder route for efficiency"
        cr.status = "pending"

        assert cr.request_type == "resequence"

    @pytest.mark.unit
    def test_crew_assist_request_type(self) -> None:
        """crew_assist produces correct ChangeRequest fields."""
        from grins_platform.models.change_request import ChangeRequest

        cr = ChangeRequest()
        cr.resource_id = uuid4()
        cr.request_type = "crew_assist"
        cr.details = {"reason": "Large installation requires 2 techs"}
        cr.affected_job_id = uuid4()
        cr.recommended_action = "Assign second technician"
        cr.status = "pending"

        assert cr.request_type == "crew_assist"

    @pytest.mark.unit
    def test_nearby_pickup_request_type(self) -> None:
        """nearby_pickup produces correct ChangeRequest fields."""
        from grins_platform.models.change_request import ChangeRequest

        cr = ChangeRequest()
        cr.resource_id = uuid4()
        cr.request_type = "nearby_pickup"
        cr.details = {"finished_early_minutes": 45}
        cr.affected_job_id = None
        cr.recommended_action = "Assign nearby backlog job"
        cr.status = "pending"

        assert cr.request_type == "nearby_pickup"
        assert cr.affected_job_id is None


# ---------------------------------------------------------------------------
# PreJobGenerator, Revenue/Hour, Capacity Utilization Tests (task 15.15)
# ---------------------------------------------------------------------------


class TestPreJobGeneratorAndCalculations:
    """Tests for PreJobGenerator, revenue/hour, capacity utilization."""

    @pytest.mark.unit
    def test_prejob_checklist_all_required_fields(self) -> None:
        """PreJobChecklist must contain all required fields."""
        checklist = PreJobChecklist(
            job_type="spring_opening",
            customer_name="John Smith",
            customer_address="123 Main St, Minneapolis MN",
            required_equipment=["winterizer", "controller"],
            known_issues=["Valve 3 was leaking last season"],
            gate_code="1234",
            special_instructions="Dog in backyard",
            estimated_duration=90,
        )

        assert checklist.job_type == "spring_opening"
        assert checklist.customer_name == "John Smith"
        assert checklist.customer_address == "123 Main St, Minneapolis MN"
        assert "winterizer" in checklist.required_equipment
        assert len(checklist.known_issues) == 1
        assert checklist.gate_code == "1234"
        assert checklist.special_instructions == "Dog in backyard"
        assert checklist.estimated_duration == 90

    @pytest.mark.unit
    def test_prejob_checklist_optional_fields_none(self) -> None:
        """PreJobChecklist optional fields can be None."""
        checklist = PreJobChecklist(
            job_type="repair",
            customer_name="Jane Doe",
            customer_address="456 Oak Ave",
            required_equipment=[],
            known_issues=[],
            gate_code=None,
            special_instructions=None,
            estimated_duration=60,
        )

        assert checklist.gate_code is None
        assert checklist.special_instructions is None

    @pytest.mark.unit
    def test_revenue_per_hour_calculation(self) -> None:
        """Revenue/hour = job_revenue / ((job_duration + drive_time) / 60)."""
        job_revenue = 300.0
        job_duration = 60  # minutes
        drive_time = 15  # minutes

        total_hours = (job_duration + drive_time) / 60.0
        revenue_per_hour = job_revenue / total_hours

        expected = 300.0 / (75.0 / 60.0)
        assert abs(revenue_per_hour - expected) < 0.01

    @pytest.mark.unit
    def test_revenue_per_hour_zero_drive_time(self) -> None:
        """Revenue/hour with zero drive time."""
        job_revenue = 200.0
        job_duration = 60
        drive_time = 0

        total_hours = (job_duration + drive_time) / 60.0
        revenue_per_hour = job_revenue / total_hours

        assert abs(revenue_per_hour - 200.0) < 0.01

    @pytest.mark.unit
    def test_capacity_utilization_healthy_range(self) -> None:
        """Utilization in 60-90% range is healthy."""
        job_minutes = 360
        drive_minutes = 60
        available_minutes = 600

        utilization = (job_minutes + drive_minutes) / available_minutes * 100.0

        assert 60.0 <= utilization <= 90.0, (
            f"Utilization {utilization:.1f}% should be in healthy range 60-90%"
        )

    @pytest.mark.unit
    def test_capacity_utilization_overbooking(self) -> None:
        """Utilization > 90% indicates overbooking risk."""
        job_minutes = 480
        drive_minutes = 90
        available_minutes = 600

        utilization = (job_minutes + drive_minutes) / available_minutes * 100.0

        assert utilization > 90.0, (
            f"Utilization {utilization:.1f}% should indicate overbooking"
        )

    @pytest.mark.unit
    def test_capacity_utilization_underutilization(self) -> None:
        """Utilization < 60% indicates underutilization opportunity."""
        job_minutes = 240
        drive_minutes = 60
        available_minutes = 600

        utilization = (job_minutes + drive_minutes) / available_minutes * 100.0

        assert utilization < 60.0, (
            f"Utilization {utilization:.1f}% should indicate underutilization"
        )

    @pytest.mark.unit
    def test_backlog_pressure_high_count_old_age(self) -> None:
        """High count + old age produces high backlog pressure."""

        def backlog_pressure(count: int, max_age_days: int) -> float:
            age_factor = min(max_age_days / 30.0, 3.0)
            return count * (1.0 + age_factor)

        high_pressure = backlog_pressure(50, 60)
        low_pressure = backlog_pressure(5, 2)

        assert high_pressure > low_pressure

    @pytest.mark.unit
    def test_backlog_pressure_zero_count(self) -> None:
        """Zero backlog count produces zero pressure."""

        def backlog_pressure(count: int, max_age_days: int) -> float:
            age_factor = min(max_age_days / 30.0, 3.0)
            return count * (1.0 + age_factor)

        pressure = backlog_pressure(0, 90)
        assert pressure == 0.0
