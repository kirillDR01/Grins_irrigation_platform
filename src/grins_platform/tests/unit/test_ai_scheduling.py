"""Unit tests for AI Scheduling System.

Tests all 30 criteria scorers individually, alert/suggestion generation,
change request packaging, and PreJobGenerator logic.

All tests marked @pytest.mark.unit with mocked dependencies.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.schemas.ai_scheduling import (
    PreJobChecklist,
    SchedulingContext,
    UpsellSuggestion,
)
from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
from grins_platform.services.ai.scheduling.prejob_generator import PreJobGenerator
from grins_platform.services.ai.scheduling.resource_alerts import (
    ResourceAlertService,
)
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
# Helpers
# ---------------------------------------------------------------------------


def _session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


def _config(
    num: int, name: str, weight: int = 50, is_hard: bool = False,
) -> dict[str, Any]:
    return {
        "criterion_number": num,
        "criterion_name": name,
        "weight": weight,
        "is_hard_constraint": is_hard,
        "is_enabled": True,
    }


def _ctx(
    sched_date: date | None = None,
    weather: dict[str, Any] | None = None,
    backlog: dict[str, Any] | None = None,
    traffic: dict[str, Any] | None = None,
) -> SchedulingContext:
    return SchedulingContext(
        schedule_date=sched_date or date(2026, 4, 10),
        weather=weather,
        traffic=traffic,
        backlog=backlog,
    )


# ===========================================================================
# Task 15.12: Unit tests for all 30 criteria scorers
# ===========================================================================


@pytest.mark.unit
class TestGeographicScorer:
    """Tests for GeographicScorer criteria 1-5."""

    @pytest.mark.asyncio
    async def test_criterion_1_proximity_close(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(1, "Proximity")
        job = {"latitude": 45.0, "longitude": -93.0}
        staff = {"latitude": 45.0, "longitude": -93.0}
        result = await scorer._score_proximity(cfg, job, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_1_proximity_far(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(1, "Proximity")
        job = {"latitude": 45.0, "longitude": -93.0}
        staff = {"latitude": 46.0, "longitude": -94.0}
        result = await scorer._score_proximity(cfg, job, staff, _ctx())
        assert result.score < 100.0

    @pytest.mark.asyncio
    async def test_criterion_1_missing_coords(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(1, "Proximity")
        result = await scorer._score_proximity(cfg, {}, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_2_drive_time_zero(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(2, "Drive Time")
        staff = {"total_drive_minutes": 0}
        result = await scorer._score_intra_route_drive_time(cfg, {}, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_2_drive_time_high(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(2, "Drive Time")
        staff = {"total_drive_minutes": 400}
        result = await scorer._score_intra_route_drive_time(cfg, {}, staff, _ctx())
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_criterion_3_in_zone(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(3, "Zones")
        zone = str(uuid4())
        job = {"service_zone_id": zone}
        staff = {"service_zone_id": zone}
        result = await scorer._score_zone_boundaries(cfg, job, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_3_out_zone(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(3, "Zones")
        job = {"service_zone_id": str(uuid4())}
        staff = {"service_zone_id": str(uuid4())}
        result = await scorer._score_zone_boundaries(cfg, job, staff, _ctx())
        assert result.score == 30.0

    @pytest.mark.asyncio
    async def test_criterion_4_no_traffic(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(4, "Traffic")
        result = await scorer._score_traffic(cfg, {}, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_4_with_congestion(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(4, "Traffic")
        ctx = _ctx(traffic={"congestion_factor": 1.0})
        result = await scorer._score_traffic(cfg, {}, {}, ctx)
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_5_no_constraints(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(5, "Access")
        result = await scorer._score_access_constraints(cfg, {}, {}, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_5_with_violations(self) -> None:
        scorer = GeographicScorer(_session())
        cfg = _config(5, "Access", is_hard=True)
        job = {
            "access_constraints": {
                "hoa_start_hour": 9,
                "hoa_end_hour": 17,
            },
            "scheduled_hour": 7,
        }
        result = await scorer._score_access_constraints(cfg, job, {}, _ctx())
        assert result.score == 0.0


@pytest.mark.unit
class TestResourceScorer:
    """Tests for ResourceScorer criteria 6-10."""

    @pytest.mark.asyncio
    async def test_criterion_6_skills_match(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(6, "Skills", is_hard=True)
        job = {"required_skills": ["backflow_certified"]}
        staff = {"certifications": ["backflow_certified", "lake_pump"]}
        result = await scorer._score_skill_match(cfg, job, staff, _ctx())
        assert result.score == 100.0
        assert result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_6_skills_missing(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(6, "Skills", is_hard=True)
        job = {"required_skills": ["backflow_certified"]}
        staff = {"certifications": ["lake_pump"]}
        result = await scorer._score_skill_match(cfg, job, staff, _ctx())
        assert result.score == 0.0
        assert not result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_6_no_skills_required(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(6, "Skills", is_hard=True)
        job = {"required_skills": []}
        staff = {"certifications": []}
        result = await scorer._score_skill_match(cfg, job, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_7_equipment_match(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(7, "Equipment", is_hard=True)
        job = {"required_equipment": ["compressor"]}
        staff = {"assigned_equipment": ["compressor", "fittings"]}
        result = await scorer._score_equipment(cfg, job, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_7_equipment_missing(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(7, "Equipment", is_hard=True)
        job = {"required_equipment": ["multimeter"]}
        staff = {"assigned_equipment": ["compressor"]}
        result = await scorer._score_equipment(cfg, job, staff, _ctx())
        assert result.score == 0.0
        assert not result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_8_within_shift(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(8, "Availability", is_hard=True)
        job = {"scheduled_start": "08:00", "scheduled_end": "10:00"}
        staff = {"shift_start": "07:00", "shift_end": "17:00"}
        result = await scorer._score_availability(cfg, job, staff, _ctx())
        assert result.score == 100.0
        assert result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_8_outside_shift(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(8, "Availability", is_hard=True)
        job = {"scheduled_start": "06:00", "scheduled_end": "08:00"}
        staff = {"shift_start": "07:00", "shift_end": "17:00"}
        result = await scorer._score_availability(cfg, job, staff, _ctx())
        assert result.score == 0.0
        assert not result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_9_balanced_workload(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(9, "Workload")
        staff = {"team_job_hours": [6.0, 6.0, 6.0, 6.0]}
        result = await scorer._score_workload_balance(cfg, {}, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_9_imbalanced_workload(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(9, "Workload")
        staff = {"team_job_hours": [10.0, 2.0, 2.0, 2.0]}
        result = await scorer._score_workload_balance(cfg, {}, staff, _ctx())
        assert result.score < 100.0

    @pytest.mark.asyncio
    async def test_criterion_10_with_performance_data(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(10, "Performance")
        staff = {
            "performance_score": 90.0,
            "callback_rate": 0.05,
            "avg_satisfaction": 4.5,
        }
        result = await scorer._score_performance(cfg, {}, staff, _ctx())
        assert result.score > 50.0

    @pytest.mark.asyncio
    async def test_criterion_10_no_data(self) -> None:
        scorer = ResourceScorer(_session())
        cfg = _config(10, "Performance")
        result = await scorer._score_performance(cfg, {}, {}, _ctx())
        assert result.score == 50.0


@pytest.mark.unit
class TestCustomerJobScorer:
    """Tests for CustomerJobScorer criteria 11-15."""

    @pytest.mark.asyncio
    async def test_criterion_11_no_preference(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(11, "Time Window")
        job = {"customer": {}}
        result = await scorer._score_time_window(cfg, job, {}, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_11_hard_mismatch(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(11, "Time Window", is_hard=True)
        job = {
            "customer": {
                "time_window_preference": "am",
                "time_window_is_hard": True,
            },
            "time_slot": "pm",
            "scheduled_hour": 14,
        }
        result = await scorer._score_time_window(cfg, job, {}, _ctx())
        assert result.score == 0.0
        assert not result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_12_no_estimate(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(12, "Duration")
        result = await scorer._score_duration_estimate(cfg, {}, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_12_with_estimate(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(12, "Duration")
        job = {"estimated_duration_minutes": 60}
        result = await scorer._score_duration_estimate(cfg, job, {}, _ctx())
        assert result.score == 75.0  # no complexity data → default

    @pytest.mark.asyncio
    async def test_criterion_13_emergency(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(13, "Priority")
        job = {"priority": "emergency"}
        result = await scorer._score_priority(cfg, job, {}, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_13_flexible(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(13, "Priority")
        job = {"priority": "flexible"}
        result = await scorer._score_priority(cfg, job, {}, _ctx())
        assert result.score == 30.0

    @pytest.mark.asyncio
    async def test_criterion_14_high_clv(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(14, "CLV")
        job = {"customer": {"clv_score": 95.0}}
        result = await scorer._score_clv(cfg, job, {}, _ctx())
        assert result.score == 95.0

    @pytest.mark.asyncio
    async def test_criterion_14_no_clv(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(14, "CLV")
        job = {"customer": {}}
        result = await scorer._score_clv(cfg, job, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_15_preferred_match(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(15, "Relationship")
        sid = str(uuid4())
        job = {"customer": {"preferred_resource_id": sid}}
        staff = {"id": sid}
        result = await scorer._score_relationship(cfg, job, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_15_no_preference(self) -> None:
        scorer = CustomerJobScorer(_session())
        cfg = _config(15, "Relationship")
        job = {"customer": {}}
        result = await scorer._score_relationship(cfg, job, {}, _ctx())
        assert result.score == 50.0


@pytest.mark.unit
class TestCapacityDemandScorer:
    """Tests for CapacityDemandScorer criteria 16-20."""

    @pytest.mark.asyncio
    async def test_criterion_16_healthy_utilization(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(16, "Utilization")
        staff = {
            "assigned_job_minutes": 300,
            "assigned_drive_minutes": 60,
            "available_minutes": 480,
        }
        result = await scorer._score_daily_utilization(cfg, {}, staff, _ctx())
        assert result.score == 100.0  # 75% is healthy

    @pytest.mark.asyncio
    async def test_criterion_16_overbooked(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(16, "Utilization")
        staff = {
            "assigned_job_minutes": 450,
            "assigned_drive_minutes": 60,
            "available_minutes": 480,
        }
        result = await scorer._score_daily_utilization(cfg, {}, staff, _ctx())
        assert result.score < 100.0  # >90% penalized

    @pytest.mark.asyncio
    async def test_criterion_17_no_forecast(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(17, "Forecast")
        result = await scorer._score_weekly_forecast(cfg, {}, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_18_peak_season(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(18, "Seasonal")
        ctx = _ctx(sched_date=date(2026, 4, 15))  # April = peak
        result = await scorer._score_seasonal_peak(cfg, {}, {}, ctx)
        assert result.score == 80.0

    @pytest.mark.asyncio
    async def test_criterion_18_off_peak(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(18, "Seasonal")
        ctx = _ctx(sched_date=date(2026, 7, 15))  # July = off-peak
        result = await scorer._score_seasonal_peak(cfg, {}, {}, ctx)
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_19_no_cancel_data(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(19, "Cancellation")
        result = await scorer._score_cancellation_probability(cfg, {}, {}, _ctx())
        assert result.score == 70.0

    @pytest.mark.asyncio
    async def test_criterion_19_high_cancel_prob(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(19, "Cancellation")
        job = {"cancel_probability": 0.8}
        result = await scorer._score_cancellation_probability(cfg, job, {}, _ctx())
        assert result.score == 20.0

    @pytest.mark.asyncio
    async def test_criterion_20_no_backlog(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(20, "Backlog")
        result = await scorer._score_backlog_pressure(cfg, {}, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_20_heavy_backlog(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(20, "Backlog")
        ctx = _ctx(backlog={"unscheduled_count": 25, "avg_age_days": 10})
        result = await scorer._score_backlog_pressure(cfg, {}, {}, ctx)
        assert result.score == 100.0  # 50 + 50 = 100


@pytest.mark.unit
class TestBusinessRulesScorer:
    """Tests for BusinessRulesScorer criteria 21-25."""

    @pytest.mark.asyncio
    async def test_criterion_21_no_deadline(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(21, "Compliance", is_hard=True)
        result = await scorer._score_compliance_deadline(cfg, {}, {}, _ctx())
        assert result.score == 100.0
        assert result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_21_before_deadline(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(21, "Compliance", is_hard=True)
        job = {"compliance_deadline": "2026-04-30T23:59:59"}
        ctx = _ctx(sched_date=date(2026, 4, 10))
        result = await scorer._score_compliance_deadline(cfg, job, {}, ctx)
        assert result.score == 100.0
        assert result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_21_after_deadline(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(21, "Compliance", is_hard=True)
        job = {"compliance_deadline": "2026-04-01T23:59:59"}
        ctx = _ctx(sched_date=date(2026, 4, 10))
        result = await scorer._score_compliance_deadline(cfg, job, {}, ctx)
        assert result.score == 0.0
        assert not result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_22_with_revenue(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(22, "Revenue/Hour")
        job = {"revenue_per_hour": 150.0}
        result = await scorer._score_revenue_per_hour(cfg, job, {}, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_22_no_revenue(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(22, "Revenue/Hour")
        result = await scorer._score_revenue_per_hour(cfg, {}, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_23_no_sla(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(23, "SLA", is_hard=True)
        result = await scorer._score_sla_commitment(cfg, {}, {}, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_23_sla_met(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(23, "SLA", is_hard=True)
        job = {"sla_deadline": "2026-04-15T23:59:59"}
        ctx = _ctx(sched_date=date(2026, 4, 10))
        result = await scorer._score_sla_commitment(cfg, job, {}, ctx)
        assert result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_23_sla_missed(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(23, "SLA", is_hard=True)
        job = {"sla_deadline": "2026-04-01T23:59:59"}
        ctx = _ctx(sched_date=date(2026, 4, 10))
        result = await scorer._score_sla_commitment(cfg, job, {}, ctx)
        assert not result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_24_within_threshold(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(24, "Overtime")
        staff = {"overtime_threshold_minutes": 480, "assigned_job_minutes": 300}
        job = {"estimated_duration_minutes": 60}
        result = await scorer._score_overtime_cost(cfg, job, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_24_over_threshold(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(24, "Overtime")
        staff = {"overtime_threshold_minutes": 400, "assigned_job_minutes": 420}
        job = {"estimated_duration_minutes": 60, "revenue_per_hour": None}
        result = await scorer._score_overtime_cost(cfg, job, staff, _ctx())
        assert result.score < 100.0

    @pytest.mark.asyncio
    async def test_criterion_25_peak_standard(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(25, "Seasonal Pricing")
        job = {"priority": "standard"}
        ctx = _ctx(sched_date=date(2026, 4, 15))  # peak
        result = await scorer._score_seasonal_pricing(cfg, job, {}, ctx)
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_25_peak_flexible(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(25, "Seasonal Pricing")
        job = {"priority": "flexible"}
        ctx = _ctx(sched_date=date(2026, 4, 15))  # peak
        result = await scorer._score_seasonal_pricing(cfg, job, {}, ctx)
        assert result.score == 40.0


@pytest.mark.unit
class TestPredictiveScorer:
    """Tests for PredictiveScorer criteria 26-30."""

    @pytest.mark.asyncio
    async def test_criterion_26_indoor(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(26, "Weather")
        job = {"is_outdoor": False}
        ctx = _ctx(weather={"condition": "storm"})
        result = await scorer._score_weather_impact(cfg, job, {}, ctx)
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_26_outdoor_bad(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(26, "Weather")
        job = {"is_outdoor": True}
        ctx = _ctx(weather={"condition": "rain"})
        result = await scorer._score_weather_impact(cfg, job, {}, ctx)
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_criterion_26_outdoor_good(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(26, "Weather")
        job = {"is_outdoor": True}
        ctx = _ctx(weather={"condition": "sunny"})
        result = await scorer._score_weather_impact(cfg, job, {}, ctx)
        assert result.score == 80.0

    @pytest.mark.asyncio
    async def test_criterion_27_no_complexity(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(27, "Complexity")
        result = await scorer._score_predicted_complexity(cfg, {}, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_28_hot_lead(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(28, "Lead Conversion")
        job = {"lead_temperature": "hot"}
        result = await scorer._score_lead_conversion(cfg, job, {}, _ctx())
        assert result.score == 80.0

    @pytest.mark.asyncio
    async def test_criterion_28_cold_lead(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(28, "Lead Conversion")
        job = {"lead_temperature": "cold"}
        result = await scorer._score_lead_conversion(cfg, job, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_29_close_start(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(29, "Shift Start Location")
        job = {"latitude": 45.0, "longitude": -93.0}
        staff = {"default_start_lat": 45.0, "default_start_lng": -93.0}
        result = await scorer._score_shift_start_location(cfg, job, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_criterion_29_missing_data(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(29, "Shift Start Location")
        result = await scorer._score_shift_start_location(cfg, {}, {}, _ctx())
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_criterion_30_no_dependency(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(30, "Dependencies", is_hard=True)
        result = await scorer._score_dependency_chain(cfg, {}, {}, _ctx())
        assert result.score == 100.0
        assert result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_30_completed_prereq(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(30, "Dependencies", is_hard=True)
        job = {
            "depends_on_job_id": str(uuid4()),
            "prerequisite_status": "completed",
        }
        result = await scorer._score_dependency_chain(cfg, job, {}, _ctx())
        assert result.is_satisfied

    @pytest.mark.asyncio
    async def test_criterion_30_incomplete_prereq(self) -> None:
        scorer = PredictiveScorer(_session())
        cfg = _config(30, "Dependencies", is_hard=True)
        job = {
            "depends_on_job_id": str(uuid4()),
            "prerequisite_status": "pending",
        }
        result = await scorer._score_dependency_chain(cfg, job, {}, _ctx())
        assert not result.is_satisfied
        assert result.score == 0.0


# ===========================================================================
# Task 15.13: Unit tests for alert and suggestion generation
# ===========================================================================


@pytest.mark.unit
class TestAlertDetectors:
    """Tests for all 5 alert types."""

    @pytest.mark.asyncio
    async def test_double_booking_detected(self) -> None:
        engine = AlertEngine(_session())
        rid = str(uuid4())
        assignments = [
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "start": "08:00",
                "end": "10:00",
            },
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "start": "09:00",
                "end": "11:00",
            },
        ]
        candidates = await engine._detect_double_bookings(assignments)
        assert len(candidates) == 1
        assert candidates[0].alert_type == "double_booking"
        assert candidates[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_no_double_booking_when_sequential(self) -> None:
        engine = AlertEngine(_session())
        rid = str(uuid4())
        assignments = [
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "start": "08:00",
                "end": "09:00",
            },
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "start": "09:00",
                "end": "10:00",
            },
        ]
        candidates = await engine._detect_double_bookings(assignments)
        assert len(candidates) == 0

    @pytest.mark.asyncio
    async def test_skill_mismatch_detected(self) -> None:
        engine = AlertEngine(_session())
        assignments = [{
            "resource_id": str(uuid4()),
            "job_id": str(uuid4()),
            "required_skills": ["backflow_certified"],
            "resource_skills": ["lake_pump"],
        }]
        candidates = await engine._detect_skill_mismatches(assignments)
        assert len(candidates) == 1
        assert candidates[0].alert_type == "skill_mismatch"

    @pytest.mark.asyncio
    async def test_skill_match_no_alert(self) -> None:
        engine = AlertEngine(_session())
        assignments = [{
            "resource_id": str(uuid4()),
            "job_id": str(uuid4()),
            "required_skills": ["lake_pump"],
            "resource_skills": ["lake_pump", "backflow_certified"],
        }]
        candidates = await engine._detect_skill_mismatches(assignments)
        assert len(candidates) == 0

    @pytest.mark.asyncio
    async def test_sla_risk_detected(self) -> None:
        engine = AlertEngine(_session())
        jobs = [{
            "job_id": str(uuid4()),
            "sla_deadline": "2026-04-01",
            "scheduled_date": "2026-04-10",
        }]
        candidates = await engine._detect_sla_risks(jobs)
        assert len(candidates) == 1
        assert candidates[0].alert_type == "sla_risk"

    @pytest.mark.asyncio
    async def test_sla_ok_no_alert(self) -> None:
        engine = AlertEngine(_session())
        jobs = [{
            "job_id": str(uuid4()),
            "sla_deadline": "2026-04-30",
            "scheduled_date": "2026-04-10",
        }]
        candidates = await engine._detect_sla_risks(jobs)
        assert len(candidates) == 0

    @pytest.mark.asyncio
    async def test_resource_behind_detected(self) -> None:
        engine = AlertEngine(_session())
        assignments = [{
            "resource_id": str(uuid4()),
            "job_id": str(uuid4()),
            "delay_minutes": 45,
        }]
        candidates = await engine._detect_resource_behind(assignments)
        assert len(candidates) == 1
        assert candidates[0].alert_type == "resource_behind"

    @pytest.mark.asyncio
    async def test_resource_on_time_no_alert(self) -> None:
        engine = AlertEngine(_session())
        assignments = [{
            "resource_id": str(uuid4()),
            "job_id": str(uuid4()),
            "delay_minutes": 10,
        }]
        candidates = await engine._detect_resource_behind(assignments)
        assert len(candidates) == 0

    @pytest.mark.asyncio
    async def test_weather_no_severe(self) -> None:
        engine = AlertEngine(_session())
        jobs = [{"job_id": str(uuid4()), "is_outdoor": True}]
        candidates = await engine._detect_weather_impacts(date(2026, 4, 10), jobs)
        assert len(candidates) == 0  # severe_weather is False by default


@pytest.mark.unit
class TestSuggestionGenerators:
    """Tests for all 5 suggestion types."""

    @pytest.mark.asyncio
    async def test_route_swap_suggested(self) -> None:
        engine = AlertEngine(_session())
        rid_a = str(uuid4())
        rid_b = str(uuid4())
        assignments = [
            {"resource_id": rid_a, "job_id": str(uuid4()), "drive_time_minutes": 80},
            {"resource_id": rid_b, "job_id": str(uuid4()), "drive_time_minutes": 80},
        ]
        candidates = await engine._suggest_route_swaps(assignments)
        assert len(candidates) >= 1
        assert candidates[0].alert_type == "route_swap"
        assert candidates[0].severity == "suggestion"

    @pytest.mark.asyncio
    async def test_underutilized_suggested(self) -> None:
        engine = AlertEngine(_session())
        rid = str(uuid4())
        assignments = [{
            "resource_id": rid,
            "job_duration_minutes": 120,
            "drive_time_minutes": 30,
            "available_minutes": 480,
        }]
        candidates = await engine._suggest_utilization_fills(assignments)
        assert len(candidates) >= 1
        assert candidates[0].alert_type == "underutilized"

    @pytest.mark.asyncio
    async def test_customer_preference_suggested(self) -> None:
        engine = AlertEngine(_session())
        assignments = [{
            "resource_id": str(uuid4()),
            "job_id": str(uuid4()),
            "customer_satisfaction": 2.0,
        }]
        candidates = await engine._suggest_customer_preference(assignments)
        assert len(candidates) == 1
        assert candidates[0].alert_type == "customer_preference"

    @pytest.mark.asyncio
    async def test_overtime_avoidable_suggested(self) -> None:
        engine = AlertEngine(_session())
        rid = str(uuid4())
        assignments = [
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "job_duration_minutes": 300,
                "drive_time_minutes": 200,
                "overtime_threshold": 480,
                "priority": "flexible",
            },
        ]
        candidates = await engine._suggest_overtime_avoidance(assignments)
        assert len(candidates) >= 1
        assert candidates[0].alert_type == "overtime_avoidable"

    @pytest.mark.asyncio
    async def test_high_revenue_suggested(self) -> None:
        engine = AlertEngine(_session())
        open_slots = [{"resource_id": str(uuid4())}]
        candidates = await engine._suggest_high_revenue_fills(open_slots)
        assert len(candidates) == 1
        assert candidates[0].alert_type == "high_revenue"


# ===========================================================================
# Task 15.14: Unit tests for ChangeRequest packaging logic
# ===========================================================================


@pytest.mark.unit
class TestChangeRequestPackaging:
    """Tests for all 10 resource tool interaction types."""

    @pytest.mark.asyncio
    async def test_report_delay(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.report_delay(str(uuid4()), 30)
        assert result["status"] == "delay_reported"
        assert result["delay_minutes"] == 30
        assert result["admin_alerted"] is False

    @pytest.mark.asyncio
    async def test_report_delay_admin_alert(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.report_delay(str(uuid4()), 45)
        assert result["admin_alerted"] is True

    @pytest.mark.asyncio
    async def test_get_prejob_info(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.get_prejob_info(str(uuid4()), str(uuid4()))
        assert result["status"] == "info_retrieved"
        assert "required_equipment" in result

    @pytest.mark.asyncio
    async def test_request_followup(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.request_followup(
            str(uuid4()), str(uuid4()), "Needs repair", ["valve"],
        )
        assert result["status"] == "change_request_created"
        assert result["request_type"] == "followup_job"
        assert result["parts_needed"] == ["valve"]

    @pytest.mark.asyncio
    async def test_report_access_issue(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.report_access_issue(
            str(uuid4()), str(uuid4()), "gate_locked",
        )
        assert result["status"] == "access_issue_reported"
        assert result["issue_type"] == "gate_locked"

    @pytest.mark.asyncio
    async def test_find_nearby_work(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.find_nearby_work(str(uuid4()), "44.9,-93.2")
        assert result["status"] == "search_complete"
        assert result["radius_minutes"] == 15

    @pytest.mark.asyncio
    async def test_request_resequence(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.request_resequence(str(uuid4()), "Traffic", True)
        assert result["status"] == "change_request_created"
        assert result["request_type"] == "resequence"
        assert result["shop_stop"] is True

    @pytest.mark.asyncio
    async def test_request_assistance(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.request_assistance(
            str(uuid4()), str(uuid4()), "backflow_certified",
        )
        assert result["status"] == "change_request_created"
        assert result["request_type"] == "crew_assist"

    @pytest.mark.asyncio
    async def test_log_parts(self) -> None:
        tools = ResourceSchedulingTools(_session())
        parts = [{"part_name": "valve", "quantity_used": 2}]
        result = await tools.log_parts(str(uuid4()), str(uuid4()), parts)
        assert result["status"] == "parts_logged"
        assert len(result["parts_logged"]) == 1

    @pytest.mark.asyncio
    async def test_get_tomorrow_schedule(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.get_tomorrow_schedule(str(uuid4()))
        assert result["status"] == "schedule_retrieved"

    @pytest.mark.asyncio
    async def test_request_upgrade_quote(self) -> None:
        tools = ResourceSchedulingTools(_session())
        result = await tools.request_upgrade_quote(
            str(uuid4()), str(uuid4()), "controller",
        )
        assert result["status"] == "change_request_created"
        assert result["request_type"] == "upgrade_quote"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool(self) -> None:
        tools = ResourceSchedulingTools(_session())
        with pytest.raises(ValueError, match="Unknown resource tool"):
            await tools.dispatch_tool_call("nonexistent", "{}")


# ===========================================================================
# Task 15.15: Unit tests for PreJobGenerator, revenue/hour, capacity, backlog
# ===========================================================================


@pytest.mark.unit
class TestPreJobGenerator:
    """Tests for PreJobGenerator checklist and upsell."""

    @pytest.mark.asyncio
    async def test_generate_checklist(self) -> None:
        gen = PreJobGenerator(_session())
        checklist = await gen.generate_checklist(uuid4(), uuid4())
        assert isinstance(checklist, PreJobChecklist)
        assert checklist.job_type is not None
        assert checklist.customer_name is not None
        assert checklist.customer_address is not None
        assert isinstance(checklist.required_equipment, list)
        assert len(checklist.required_equipment) > 0
        assert isinstance(checklist.estimated_duration, int)
        assert checklist.estimated_duration > 0

    @pytest.mark.asyncio
    async def test_generate_upsell_suggestions(self) -> None:
        gen = PreJobGenerator(_session())
        suggestions = await gen.generate_upsell_suggestions(uuid4())
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1
        assert isinstance(suggestions[0], UpsellSuggestion)
        assert suggestions[0].age_years > 0
        assert suggestions[0].estimated_savings > 0


@pytest.mark.unit
class TestRevenuePerHourEdgeCases:
    """Edge cases for revenue per resource-hour calculation."""

    @pytest.mark.asyncio
    async def test_zero_revenue(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(22, "Revenue/Hour")
        job = {"revenue_per_hour": 0.0}
        result = await scorer._score_revenue_per_hour(cfg, job, {}, _ctx())
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_high_revenue(self) -> None:
        scorer = BusinessRulesScorer(_session())
        cfg = _config(22, "Revenue/Hour")
        job = {"revenue_per_hour": 300.0}
        result = await scorer._score_revenue_per_hour(cfg, job, {}, _ctx())
        assert result.score == 100.0  # capped at 100


@pytest.mark.unit
class TestCapacityUtilizationEdgeCases:
    """Edge cases for capacity utilization calculation."""

    @pytest.mark.asyncio
    async def test_zero_available(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(16, "Utilization")
        staff = {
            "assigned_job_minutes": 0,
            "assigned_drive_minutes": 0,
            "available_minutes": 0,
        }
        result = await scorer._score_daily_utilization(cfg, {}, staff, _ctx())
        assert result.score == 50.0  # neutral when no data

    @pytest.mark.asyncio
    async def test_exactly_60_percent(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(16, "Utilization")
        staff = {
            "assigned_job_minutes": 288,
            "assigned_drive_minutes": 0,
            "available_minutes": 480,
        }
        result = await scorer._score_daily_utilization(cfg, {}, staff, _ctx())
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_exactly_90_percent(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(16, "Utilization")
        staff = {
            "assigned_job_minutes": 432,
            "assigned_drive_minutes": 0,
            "available_minutes": 480,
        }
        result = await scorer._score_daily_utilization(cfg, {}, staff, _ctx())
        assert result.score == 100.0


@pytest.mark.unit
class TestBacklogPressureEdgeCases:
    """Edge cases for backlog pressure scoring."""

    @pytest.mark.asyncio
    async def test_zero_backlog(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(20, "Backlog")
        ctx = _ctx(backlog={"unscheduled_count": 0, "avg_age_days": 0})
        result = await scorer._score_backlog_pressure(cfg, {}, {}, ctx)
        assert result.score == 50.0  # neutral

    @pytest.mark.asyncio
    async def test_max_backlog(self) -> None:
        scorer = CapacityDemandScorer(_session())
        cfg = _config(20, "Backlog")
        ctx = _ctx(backlog={"unscheduled_count": 50, "avg_age_days": 30})
        result = await scorer._score_backlog_pressure(cfg, {}, {}, ctx)
        assert result.score == 100.0


@pytest.mark.unit
class TestResourceAlertService:
    """Tests for resource-facing alert and suggestion generation."""

    @pytest.mark.asyncio
    async def test_job_added_alert(self) -> None:
        svc = ResourceAlertService(_session())
        alert = await svc.generate_job_added_alert(
            uuid4(), {"job_id": str(uuid4()), "job_type": "maintenance"},
        )
        assert alert["alert_type"] == "job_added"
        assert alert["requires_action"] is False

    @pytest.mark.asyncio
    async def test_job_removed_alert(self) -> None:
        svc = ResourceAlertService(_session())
        alert = await svc.generate_job_removed_alert(
            uuid4(), {"job_id": str(uuid4()), "job_type": "maintenance"},
        )
        assert alert["alert_type"] == "job_removed"
        assert "gap_fill_suggestions" in alert

    @pytest.mark.asyncio
    async def test_route_resequenced_alert(self) -> None:
        svc = ResourceAlertService(_session())
        alert = await svc.generate_route_resequenced_alert(uuid4(), "Traffic")
        assert alert["alert_type"] == "route_resequenced"
        assert alert["requires_action"] is True

    @pytest.mark.asyncio
    async def test_equipment_alert(self) -> None:
        svc = ResourceAlertService(_session())
        alert = await svc.generate_equipment_alert(
            uuid4(), {"job_id": str(uuid4())}, ["compressor"],
        )
        assert alert["alert_type"] == "equipment_required"
        assert "compressor" in alert["required_equipment"]

    @pytest.mark.asyncio
    async def test_access_alert(self) -> None:
        svc = ResourceAlertService(_session())
        alert = await svc.generate_access_alert(
            uuid4(),
            {"job_id": str(uuid4()), "customer_name": "Smith"},
            {"gate_code": "1234", "instructions": "Ring bell"},
        )
        assert alert["alert_type"] == "access_info"
        assert alert["gate_code"] == "1234"

    @pytest.mark.asyncio
    async def test_prejob_prep_suggestion(self) -> None:
        svc = ResourceAlertService(_session())
        suggestion = await svc.generate_prejob_prep_suggestion(
            uuid4(), {"job_id": str(uuid4()), "customer_name": "Jones"},
        )
        assert suggestion["suggestion_type"] == "prejob_prep"

    @pytest.mark.asyncio
    async def test_upsell_suggestion(self) -> None:
        svc = ResourceAlertService(_session())
        suggestion = await svc.generate_upsell_suggestion(
            uuid4(),
            {"job_id": str(uuid4())},
            {"equipment_name": "Timer", "age_years": 8, "recommended_upgrade": "ESP"},
        )
        assert suggestion["suggestion_type"] == "upsell_opportunity"

    @pytest.mark.asyncio
    async def test_departure_suggestion(self) -> None:
        svc = ResourceAlertService(_session())
        suggestion = await svc.generate_departure_suggestion(
            uuid4(),
            {"recommended_departure": "7:30 AM", "traffic_level": "heavy"},
        )
        assert suggestion["suggestion_type"] == "departure_time"

    @pytest.mark.asyncio
    async def test_parts_low_suggestion(self) -> None:
        svc = ResourceAlertService(_session())
        suggestion = await svc.generate_parts_low_suggestion(
            uuid4(),
            {"part_name": "valve", "current_quantity": 2, "reorder_threshold": 5},
        )
        assert suggestion["suggestion_type"] == "parts_low"

    @pytest.mark.asyncio
    async def test_pending_approval_suggestion(self) -> None:
        svc = ResourceAlertService(_session())
        suggestion = await svc.generate_pending_approval_suggestion(uuid4(), uuid4())
        assert suggestion["suggestion_type"] == "pending_approval"
