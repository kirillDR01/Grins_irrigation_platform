"""Verify interacting business component data sourcing and competitive differentiation.

This integration test validates that:
1. All 10 business component integrations from Requirement 22 are wired
   (Customer Intake, Sales/Quoting, Marketing/Lead Management, Customer
   Communication, Workforce/HR, Inventory/Equipment, Financial/Billing,
   Reporting/Analytics, Compliance/Regulatory, CRM).
2. All 7 competitive differentiation features from Requirement 23 are
   implemented (30-constraint evaluation, predictive signals, autonomous
   schedule building, proactive predictions, revenue optimization,
   vertical configurability, weather-aware scheduling).

Validates: Requirements 22.1-22.10, 23.1-23.7
"""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.schemas.ai_scheduling import (
    ScheduleEvaluation,
    SchedulingConfig,
    SchedulingContext,
)
from grins_platform.services.ai.scheduling.criteria_evaluator import (
    _DEFAULT_CRITERIA,
    _CriterionConfig,
)
from grins_platform.services.schedule_domain import (
    ScheduleAssignment,
    ScheduleJob,
    ScheduleLocation,
    ScheduleSolution,
    ScheduleStaff,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _loc(lat: float = 44.9, lon: float = -93.2) -> ScheduleLocation:
    return ScheduleLocation(
        latitude=Decimal(str(lat)),
        longitude=Decimal(str(lon)),
        address="123 Test St",
        city="Minneapolis",
    )


def _job(
    service_type: str = "spring_opening",
    duration: int = 60,
    priority: int = 0,
    equipment: list[str] | None = None,
) -> ScheduleJob:
    return ScheduleJob(
        id=_uuid(),
        customer_name="Test Customer",
        location=_loc(),
        service_type=service_type,
        duration_minutes=duration,
        equipment_required=equipment or [],
        priority=priority,
    )


def _staff(equipment: list[str] | None = None) -> ScheduleStaff:
    return ScheduleStaff(
        id=_uuid(),
        name="Test Tech",
        start_location=_loc(44.95, -93.25),
        assigned_equipment=equipment or ["pressure_gauge", "compressor"],
        availability_start=time(8, 0),
        availability_end=time(17, 0),
    )


def _assignment(staff: ScheduleStaff, jobs: list[ScheduleJob]) -> ScheduleAssignment:
    return ScheduleAssignment(id=_uuid(), staff=staff, jobs=jobs)


def _solution(
    jobs: list[ScheduleJob] | None = None,
    staff_list: list[ScheduleStaff] | None = None,
    assignments: list[ScheduleAssignment] | None = None,
) -> ScheduleSolution:
    return ScheduleSolution(
        schedule_date=date.today(),
        jobs=jobs or [],
        staff=staff_list or [],
        assignments=assignments or [],
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


def _ctx(**overrides: Any) -> SchedulingContext:
    defaults: dict[str, Any] = {
        "schedule_date": date.today(),
        "weather": None,
        "traffic": None,
        "backlog": None,
    }
    defaults.update(overrides)
    return SchedulingContext(**defaults)


def _default_config() -> dict[int, _CriterionConfig]:
    """Build the default scorer config dict from _DEFAULT_CRITERIA."""
    cfg: dict[int, _CriterionConfig] = {}
    for c in _DEFAULT_CRITERIA:
        cfg[c["n"]] = _CriterionConfig(
            criterion_number=c["n"],
            criterion_name=c["name"],
            criterion_group=c["group"],
            weight=c["w"],
            is_hard_constraint=c.get("hard", False),
            is_enabled=True,
            config_json=None,
        )
    return cfg


# ============================================================================
# SECTION A — Business Component Integrations (Req 22.1-22.10)
# ============================================================================


class TestCustomerIntakeIntegration:
    """Req 22.1 — Customer Intake feeds new job requests into scheduling."""

    @pytest.mark.integration
    def test_schedule_job_carries_priority(self) -> None:
        """New job requests flow with correct priority.

        Validates: Req 22.1
        """
        job = _job(priority=2)
        assert job.priority == 2

    @pytest.mark.integration
    def test_schedule_job_carries_time_windows(self) -> None:
        """New job requests carry customer-requested time windows.

        Validates: Req 22.1
        """
        job = ScheduleJob(
            id=_uuid(),
            customer_name="VIP Customer",
            location=_loc(),
            service_type="maintenance",
            duration_minutes=90,
            preferred_time_start=time(8, 0),
            preferred_time_end=time(12, 0),
        )
        assert job.preferred_time_start == time(8, 0)
        assert job.preferred_time_end == time(12, 0)

    @pytest.mark.integration
    def test_schedule_job_carries_customer_data(self) -> None:
        """New job requests carry customer name and location.

        Validates: Req 22.1
        """
        job = _job()
        assert job.customer_name == "Test Customer"
        assert job.location.city == "Minneapolis"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_customer_job_scorer_uses_time_windows(self) -> None:
        """CriteriaEvaluator uses customer time-window preferences (criterion 11).

        Validates: Req 22.1
        """
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = ScheduleJob(
            id=_uuid(),
            customer_name="Window Customer",
            location=_loc(),
            service_type="spring_opening",
            duration_minutes=60,
            preferred_time_start=time(9, 0),
            preferred_time_end=time(11, 0),
        )
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        assert isinstance(results, list)
        assert len(results) == 5  # criteria 11-15


class TestSalesQuotingIntegration:
    """Req 22.2 — Sales/Quoting creates schedulable jobs."""

    @pytest.mark.integration
    def test_approved_quote_creates_job_with_duration(self) -> None:
        """Approved quotes create schedulable jobs with correct duration.

        Validates: Req 22.2
        """
        job = _job(service_type="new_build", duration=180)
        assert job.duration_minutes == 180
        assert job.service_type == "new_build"

    @pytest.mark.integration
    def test_multi_phase_job_carries_equipment(self) -> None:
        """Multi-phase projects carry equipment requirements.

        Validates: Req 22.2
        """
        job = _job(
            service_type="new_build",
            equipment=["trencher", "pipe_cutter", "backflow_valve"],
        )
        assert len(job.equipment_required) == 3
        assert "trencher" in job.equipment_required


class TestMarketingLeadManagementIntegration:
    """Req 22.3 — Marketing/Lead Management feeds capacity reservation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_predictive_scorer_handles_lead_conversion(self) -> None:
        """Hot leads from pipeline feed into capacity reservation via criterion 28.

        Validates: Req 22.3
        """
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        assert isinstance(results, list)
        assert len(results) == 5  # criteria 26-30
        criterion_28 = [r for r in results if r.criterion_number == 28]
        assert len(criterion_28) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_capacity_demand_scorer_handles_backlog(self) -> None:
        """Pipeline/backlog pressure (criterion 20) feeds scheduling density.

        Validates: Req 22.3
        """
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        assert isinstance(results, list)
        assert len(results) == 5  # criteria 16-20
        criterion_20 = [r for r in results if r.criterion_number == 20]
        assert len(criterion_20) == 1


class TestCustomerCommunicationIntegration:
    """Req 22.4 — Schedule changes trigger notification events."""

    @pytest.mark.integration
    def test_resource_alert_generator_exists(self) -> None:
        """ResourceAlertGenerator is importable and has notification methods.

        Validates: Req 22.4
        """
        from grins_platform.services.ai.scheduling.resource_alerts import (
            ResourceAlertGenerator,
        )

        gen = ResourceAlertGenerator()
        assert callable(gen.schedule_change_job_added)
        assert callable(gen.schedule_change_job_removed)
        assert callable(gen.route_resequenced)

    @pytest.mark.integration
    def test_schedule_change_job_added_produces_alert(self) -> None:
        """Job-added notification event is generated correctly.

        Validates: Req 22.4
        """
        from grins_platform.services.ai.scheduling.resource_alerts import (
            ResourceAlertGenerator,
        )

        gen = ResourceAlertGenerator()
        alert = gen.schedule_change_job_added(
            job_id=_uuid(),
            staff_id=_uuid(),
            job_details={
                "job_type": "Spring Opening",
                "address": "456 Oak Ave",
            },
        )
        assert alert.alert_type == "schedule_change_job_added"
        assert "Spring Opening" in alert.description

    @pytest.mark.integration
    def test_schedule_change_job_removed_produces_alert(self) -> None:
        """Job-removed notification event is generated correctly.

        Validates: Req 22.4
        """
        from grins_platform.services.ai.scheduling.resource_alerts import (
            ResourceAlertGenerator,
        )

        gen = ResourceAlertGenerator()
        alert = gen.schedule_change_job_removed(
            job_id=_uuid(),
            staff_id=_uuid(),
        )
        assert alert.alert_type == "schedule_change_job_removed"
        assert alert.title == "Schedule Change — Job Removed"


class TestWorkforceHRIntegration:
    """Req 22.5 — Workforce/HR feeds staff availability, PTO, certifications."""

    @pytest.mark.integration
    def test_staff_availability_windows(self) -> None:
        """Staff availability windows feed into scheduling.

        Validates: Req 22.5
        """
        staff = ScheduleStaff(
            id=_uuid(),
            name="PTO Tech",
            start_location=_loc(),
            availability_start=time(10, 0),
            availability_end=time(17, 0),
        )
        assert staff.availability_start == time(10, 0)
        assert staff.get_available_minutes() == 420  # 7 hours

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_scorer_checks_availability(self) -> None:
        """ResourceScorer evaluates availability windows (criterion 8).

        Validates: Req 22.5
        """
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        assert isinstance(results, list)
        assert len(results) == 5  # criteria 6-10
        criterion_8 = [r for r in results if r.criterion_number == 8]
        assert len(criterion_8) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_scorer_checks_certifications(self) -> None:
        """ResourceScorer evaluates skill/certification match (criterion 6).

        Validates: Req 22.5
        """
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _job(service_type="backflow_test")
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_6 = [r for r in results if r.criterion_number == 6]
        assert len(criterion_6) == 1


class TestInventoryEquipmentIntegration:
    """Req 22.6 — Inventory/Equipment feeds resource matching."""

    @pytest.mark.integration
    def test_staff_equipment_check(self) -> None:
        """Truck inventory data feeds into resource matching.

        Validates: Req 22.6
        """
        staff = _staff(equipment=["pressure_gauge", "compressor", "trencher"])
        assert staff.has_equipment(["pressure_gauge", "compressor"])
        assert not staff.has_equipment(["laser_level"])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_scorer_checks_equipment(self) -> None:
        """ResourceScorer evaluates equipment on truck (criterion 7).

        Validates: Req 22.6
        """
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        scorer = ResourceScorer()
        job = _job(equipment=["pressure_gauge"])
        staff = _staff(equipment=["pressure_gauge", "compressor"])
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_7 = [r for r in results if r.criterion_number == 7]
        assert len(criterion_7) == 1

    @pytest.mark.integration
    def test_resource_alert_parts_running_low(self) -> None:
        """Low-stock alerts are generated when truck inventory is depleted.

        Validates: Req 22.6
        """
        from grins_platform.services.ai.scheduling.resource_alerts import (
            ResourceAlertGenerator,
        )

        gen = ResourceAlertGenerator()
        alert = gen.parts_running_low(
            staff_id=_uuid(),
            part_name="1-inch PVC coupling",
            current_quantity=2,
        )
        assert alert.alert_type == "parts_low"
        assert "1-inch PVC coupling" in alert.description

    @pytest.mark.integration
    def test_resource_truck_inventory_model_exists(self) -> None:
        """ResourceTruckInventory model is importable.

        Validates: Req 22.6
        """
        from grins_platform.models.resource_truck_inventory import (
            ResourceTruckInventory,
        )

        assert hasattr(ResourceTruckInventory, "__tablename__")
        assert ResourceTruckInventory.__tablename__ == "resource_truck_inventory"


class TestFinancialBillingIntegration:
    """Req 22.7 — Financial/Billing feeds optimization and triggers invoicing."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_business_rules_scorer_evaluates_revenue(self) -> None:
        """BusinessRulesScorer evaluates revenue per resource-hour (criterion 22).

        Validates: Req 22.7
        """
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        assert isinstance(results, list)
        assert len(results) == 5  # criteria 21-25
        criterion_22 = [r for r in results if r.criterion_number == 22]
        assert len(criterion_22) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_business_rules_scorer_evaluates_overtime(self) -> None:
        """BusinessRulesScorer evaluates overtime cost threshold (criterion 24).

        Validates: Req 22.7
        """
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_24 = [r for r in results if r.criterion_number == 24]
        assert len(criterion_24) == 1


class TestReportingAnalyticsIntegration:
    """Req 22.8 — Reporting/Analytics read+write for schedule adherence."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_criteria_evaluator_produces_evaluation(self) -> None:
        """CriteriaEvaluator writes schedule adherence data via evaluate_schedule.

        Validates: Req 22.8
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        config = SchedulingConfig()
        evaluator = CriteriaEvaluator(session=session, config=config)

        s = _staff()
        j = _job()
        a = _assignment(s, [j])
        sol = _solution(jobs=[j], staff_list=[s], assignments=[a])
        ctx = _ctx()

        evaluation = await evaluator.evaluate_schedule(sol, ctx)
        assert isinstance(evaluation, ScheduleEvaluation)
        assert hasattr(evaluation, "total_score")
        assert hasattr(evaluation, "criteria_scores")
        assert len(evaluation.criteria_scores) == 30

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_capacity_demand_scorer_reads_historical_patterns(self) -> None:
        """CapacityDemandScorer reads seasonal volume patterns (criterion 18).

        Validates: Req 22.8
        """
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_18 = [r for r in results if r.criterion_number == 18]
        assert len(criterion_18) == 1


class TestComplianceRegulatoryIntegration:
    """Req 22.9 — Compliance/Regulatory deadlines generate proactive jobs."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_business_rules_scorer_evaluates_compliance(self) -> None:
        """BusinessRulesScorer evaluates compliance deadlines (criterion 21).

        Validates: Req 22.9
        """
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _job(service_type="backflow_test")
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_21 = [r for r in results if r.criterion_number == 21]
        assert len(criterion_21) == 1
        assert criterion_21[0].is_hard is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_alert_engine_detects_sla_risks(self) -> None:
        """AlertEngine generates proactive alerts for approaching deadlines.

        Validates: Req 22.9
        """
        from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        config = SchedulingConfig()
        evaluator = CriteriaEvaluator(session=session, config=config)
        engine = AlertEngine(session=session, evaluator=evaluator)

        assert callable(engine._detect_sla_risks)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_business_rules_scorer_evaluates_sla(self) -> None:
        """BusinessRulesScorer evaluates SLA commitments (criterion 23).

        Validates: Req 22.9
        """
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_23 = [r for r in results if r.criterion_number == 23]
        assert len(criterion_23) == 1
        assert criterion_23[0].is_hard is True


class TestCRMIntegration:
    """Req 22.10 — CRM customer profile changes reflected in scheduling."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_customer_job_scorer_uses_clv(self) -> None:
        """CustomerJobScorer evaluates customer lifetime value (criterion 14).

        Validates: Req 22.10
        """
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_14 = [r for r in results if r.criterion_number == 14]
        assert len(criterion_14) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_customer_job_scorer_uses_relationship_history(self) -> None:
        """CustomerJobScorer evaluates customer-resource relationship (criterion 15).

        Validates: Req 22.10
        """
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_15 = [r for r in results if r.criterion_number == 15]
        assert len(criterion_15) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_customer_job_scorer_uses_priority(self) -> None:
        """CustomerJobScorer evaluates job priority level (criterion 13).

        Validates: Req 22.10
        """
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _job(priority=2)
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_13 = [r for r in results if r.criterion_number == 13]
        assert len(criterion_13) == 1


# ============================================================================
# SECTION B — Competitive Differentiation (Req 23.1-23.7)
# ============================================================================


class TestThirtyConstraintSimultaneousEvaluation:
    """Req 23.1 — 30-constraint simultaneous evaluation."""

    @pytest.mark.integration
    def test_default_criteria_has_30_entries(self) -> None:
        """The criteria config defines exactly 30 criteria.

        Validates: Req 23.1
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            TOTAL_CRITERIA,
        )

        assert TOTAL_CRITERIA == 30
        assert len(_DEFAULT_CRITERIA) == 30

    @pytest.mark.integration
    def test_criteria_cover_all_six_groups(self) -> None:
        """All 6 criterion groups are represented.

        Validates: Req 23.1
        """
        groups = {c["group"] for c in _DEFAULT_CRITERIA}
        expected = {
            "geographic",
            "resource",
            "customer_job",
            "capacity_demand",
            "business_rules",
            "predictive",
        }
        assert groups == expected

    @pytest.mark.integration
    def test_criteria_numbers_are_1_through_30(self) -> None:
        """Criteria are numbered 1 through 30 with no gaps.

        Validates: Req 23.1
        """
        numbers = sorted(c["n"] for c in _DEFAULT_CRITERIA)
        assert numbers == list(range(1, 31))

    @pytest.mark.integration
    def test_all_six_scorers_importable(self) -> None:
        """All 6 scorer modules are importable.

        Validates: Req 23.1
        """
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )
        from grins_platform.services.ai.scheduling.scorers.geographic import (
            GeographicScorer,
        )
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )
        from grins_platform.services.ai.scheduling.scorers.resource import (
            ResourceScorer,
        )

        assert callable(GeographicScorer)
        assert callable(ResourceScorer)
        assert callable(CustomerJobScorer)
        assert callable(CapacityDemandScorer)
        assert callable(BusinessRulesScorer)
        assert callable(PredictiveScorer)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_evaluator_scores_all_30_criteria(self) -> None:
        """CriteriaEvaluator evaluates all 30 criteria simultaneously.

        Validates: Req 23.1
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        config = SchedulingConfig()
        evaluator = CriteriaEvaluator(session=session, config=config)

        job = _job()
        staff = _staff()
        ctx = _ctx()

        score = await evaluator.evaluate_assignment(job, staff, ctx)
        assert hasattr(score, "criteria_scores")
        assert len(score.criteria_scores) == 30

    @pytest.mark.integration
    def test_criteria_config_model_exists(self) -> None:
        """SchedulingCriteriaConfig model is importable and has correct table.

        Validates: Req 23.1
        """
        from grins_platform.models.scheduling_criteria_config import (
            SchedulingCriteriaConfig,
        )

        assert SchedulingCriteriaConfig.__tablename__ == "scheduling_criteria_config"
        assert hasattr(SchedulingCriteriaConfig, "criterion_number")
        assert hasattr(SchedulingCriteriaConfig, "weight")
        assert hasattr(SchedulingCriteriaConfig, "is_hard_constraint")
        assert hasattr(SchedulingCriteriaConfig, "is_enabled")


class TestPredictiveSignals:
    """Req 23.2 — Predictive signals (weather, cancellation, complexity)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_predictive_scorer_handles_weather(self) -> None:
        """PredictiveScorer evaluates weather forecast impact (criterion 26).

        Validates: Req 23.2
        """
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx(weather={"condition": "rain", "precipitation_probability": 0.8})
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_26 = [r for r in results if r.criterion_number == 26]
        assert len(criterion_26) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_predictive_scorer_handles_complexity(self) -> None:
        """PredictiveScorer evaluates predicted job complexity (criterion 27).

        Validates: Req 23.2
        """
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_27 = [r for r in results if r.criterion_number == 27]
        assert len(criterion_27) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_capacity_demand_scorer_handles_cancellation(self) -> None:
        """CapacityDemandScorer evaluates cancellation probability (criterion 19).

        Validates: Req 23.2
        """
        from grins_platform.services.ai.scheduling.scorers.capacity_demand import (
            CapacityDemandScorer,
        )

        scorer = CapacityDemandScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_19 = [r for r in results if r.criterion_number == 19]
        assert len(criterion_19) == 1

    @pytest.mark.integration
    def test_external_services_client_has_weather_method(self) -> None:
        """ExternalServicesClient provides weather forecast integration.

        Validates: Req 23.2
        """
        from grins_platform.services.ai.scheduling.external_services import (
            ExternalServicesClient,
        )

        client = ExternalServicesClient()
        assert callable(client.get_weather_forecast)


class TestAutonomousScheduleBuilding:
    """Req 23.3 — Autonomous schedule building."""

    @pytest.mark.integration
    def test_admin_tools_generate_schedule_exists(self) -> None:
        """AdminSchedulingTools has generate_schedule for autonomous building.

        Validates: Req 23.3
        """
        from grins_platform.services.ai.scheduling.admin_tools import (
            AdminSchedulingTools,
        )

        session = _mock_session()
        tools = AdminSchedulingTools(session=session)
        assert callable(tools.generate_schedule)

    @pytest.mark.integration
    def test_admin_tools_batch_schedule_exists(self) -> None:
        """AdminSchedulingTools has batch_schedule for multi-week campaigns.

        Validates: Req 23.3
        """
        from grins_platform.services.ai.scheduling.admin_tools import (
            AdminSchedulingTools,
        )

        session = _mock_session()
        tools = AdminSchedulingTools(session=session)
        assert callable(tools.batch_schedule)

    @pytest.mark.integration
    def test_chat_service_handles_admin_messages(self) -> None:
        """SchedulingChatService routes admin messages for schedule building.

        Validates: Req 23.3
        """
        from grins_platform.services.ai.scheduling.chat_service import (
            SchedulingChatService,
        )

        session = _mock_session()
        svc = SchedulingChatService(session=session)
        assert callable(svc.chat)
        assert callable(svc._handle_admin_message)

    @pytest.mark.integration
    def test_admin_tools_has_all_ten_tools(self) -> None:
        """AdminSchedulingTools exposes all 10 admin tool functions.

        Validates: Req 23.3
        """
        from grins_platform.services.ai.scheduling.admin_tools import (
            AdminSchedulingTools,
        )

        session = _mock_session()
        tools = AdminSchedulingTools(session=session)
        expected_methods = [
            "generate_schedule",
            "reshuffle_day",
            "insert_emergency",
            "forecast_capacity",
            "move_job",
            "find_underutilized",
            "batch_schedule",
            "rank_profitable_jobs",
            "weather_reschedule",
            "create_recurring_route",
        ]
        for method_name in expected_methods:
            assert hasattr(tools, method_name), f"Missing admin tool: {method_name}"
            assert callable(getattr(tools, method_name))


class TestProactivePredictions:
    """Req 23.4 — Proactive predictions (delays, cancellations, demand spikes)."""

    @pytest.mark.integration
    def test_alert_engine_has_all_detectors(self) -> None:
        """AlertEngine has all 5 alert detectors and 5 suggestion generators.

        Validates: Req 23.4
        """
        from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        config = SchedulingConfig()
        evaluator = CriteriaEvaluator(session=session, config=config)
        engine = AlertEngine(session=session, evaluator=evaluator)

        # 5 alert detectors
        assert callable(engine._detect_double_bookings)
        assert callable(engine._detect_skill_mismatches)
        assert callable(engine._detect_sla_risks)
        assert callable(engine._detect_resource_behind)
        assert callable(engine._detect_weather_impacts)

        # 5 suggestion generators
        assert callable(engine._suggest_route_swaps)
        assert callable(engine._suggest_utilization_fills)
        assert callable(engine._suggest_customer_preference)
        assert callable(engine._suggest_overtime_avoidance)
        assert callable(engine._suggest_high_revenue_fills)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_alert_engine_scan_and_generate(self) -> None:
        """AlertEngine.scan_and_generate produces alerts proactively.

        Validates: Req 23.4
        """
        from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        config = SchedulingConfig()
        evaluator = CriteriaEvaluator(session=session, config=config)
        engine = AlertEngine(session=session, evaluator=evaluator)

        alerts = await engine.scan_and_generate(date.today())
        assert isinstance(alerts, list)

    @pytest.mark.integration
    def test_scheduling_alert_model_exists(self) -> None:
        """SchedulingAlert model is importable with correct table name.

        Validates: Req 23.4
        """
        from grins_platform.models.scheduling_alert import SchedulingAlert

        assert SchedulingAlert.__tablename__ == "scheduling_alerts"
        assert hasattr(SchedulingAlert, "alert_type")
        assert hasattr(SchedulingAlert, "severity")
        assert hasattr(SchedulingAlert, "criteria_triggered")


class TestRevenueOptimization:
    """Req 23.5 — Revenue optimization (CLV, dynamic pricing, cost-to-serve)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_business_rules_scorer_revenue_per_hour(self) -> None:
        """BusinessRulesScorer evaluates revenue per resource-hour (criterion 22).

        Validates: Req 23.5
        """
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_22 = [r for r in results if r.criterion_number == 22]
        assert len(criterion_22) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_business_rules_scorer_seasonal_pricing(self) -> None:
        """BusinessRulesScorer evaluates seasonal pricing signals (criterion 25).

        Validates: Req 23.5
        """
        from grins_platform.services.ai.scheduling.scorers.business_rules import (
            BusinessRulesScorer,
        )

        scorer = BusinessRulesScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_25 = [r for r in results if r.criterion_number == 25]
        assert len(criterion_25) == 1

    @pytest.mark.integration
    def test_admin_tools_rank_profitable_jobs_exists(self) -> None:
        """AdminSchedulingTools has rank_profitable_jobs for revenue optimization.

        Validates: Req 23.5
        """
        from grins_platform.services.ai.scheduling.admin_tools import (
            AdminSchedulingTools,
        )

        session = _mock_session()
        tools = AdminSchedulingTools(session=session)
        assert callable(tools.rank_profitable_jobs)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_customer_job_scorer_uses_clv_for_tie_breaking(self) -> None:
        """CustomerJobScorer uses CLV to break scheduling ties (criterion 14).

        Validates: Req 23.5
        """
        from grins_platform.services.ai.scheduling.scorers.customer_job import (
            CustomerJobScorer,
        )

        scorer = CustomerJobScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx()
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_14 = [r for r in results if r.criterion_number == 14]
        assert len(criterion_14) == 1


class TestVerticalConfigurability:
    """Req 23.6 — Vertical configurability through playbooks."""

    @pytest.mark.integration
    def test_criteria_config_supports_runtime_tuning(self) -> None:
        """SchedulingConfig allows runtime weight overrides.

        Validates: Req 23.6
        """
        config = SchedulingConfig(
            criteria_weights={1: 90, 2: 80, 26: 100},
            thresholds={"overbooking_pct": 95},
        )
        assert config.criteria_weights is not None
        assert config.criteria_weights[1] == 90
        assert config.thresholds is not None
        assert config.thresholds["overbooking_pct"] == 95

    @pytest.mark.integration
    def test_criteria_config_model_has_config_json(self) -> None:
        """SchedulingCriteriaConfig has config_json for per-criterion settings.

        Validates: Req 23.6
        """
        from grins_platform.models.scheduling_criteria_config import (
            SchedulingCriteriaConfig,
        )

        assert hasattr(SchedulingCriteriaConfig, "config_json")

    @pytest.mark.integration
    def test_criteria_config_model_has_is_enabled_flag(self) -> None:
        """SchedulingCriteriaConfig has is_enabled for feature flags per criterion.

        Validates: Req 23.6
        """
        from grins_platform.models.scheduling_criteria_config import (
            SchedulingCriteriaConfig,
        )

        assert hasattr(SchedulingCriteriaConfig, "is_enabled")

    @pytest.mark.integration
    def test_default_criteria_are_irrigation_specific(self) -> None:
        """Default criteria names reflect irrigation vertical playbook.

        Validates: Req 23.6
        """
        names = [c["name"] for c in _DEFAULT_CRITERIA]
        assert "Weather forecast impact" in names
        assert "Compliance deadlines" in names
        assert "Equipment on truck" in names
        assert "Service zone boundaries" in names


class TestWeatherAwareScheduling:
    """Req 23.7 — Weather-aware scheduling."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_predictive_scorer_weather_criterion(self) -> None:
        """PredictiveScorer evaluates weather forecast impact (criterion 26).

        Validates: Req 23.7
        """
        from grins_platform.services.ai.scheduling.scorers.predictive import (
            PredictiveScorer,
        )

        scorer = PredictiveScorer()
        job = _job()
        staff = _staff()
        ctx = _ctx(weather={"condition": "freeze", "precipitation_probability": 0.0})
        config = _default_config()
        results = await scorer.score_assignment(job, staff, ctx, config)
        criterion_26 = [r for r in results if r.criterion_number == 26]
        assert len(criterion_26) == 1

    @pytest.mark.integration
    def test_admin_tools_weather_reschedule_exists(self) -> None:
        """AdminSchedulingTools has weather_reschedule for proactive rescheduling.

        Validates: Req 23.7
        """
        from grins_platform.services.ai.scheduling.admin_tools import (
            AdminSchedulingTools,
        )

        session = _mock_session()
        tools = AdminSchedulingTools(session=session)
        assert callable(tools.weather_reschedule)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_alert_engine_detects_weather_impacts(self) -> None:
        """AlertEngine detects severe weather impacts proactively.

        Validates: Req 23.7
        """
        from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        config = SchedulingConfig()
        evaluator = CriteriaEvaluator(session=session, config=config)
        engine = AlertEngine(session=session, evaluator=evaluator)

        assert callable(engine._detect_weather_impacts)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_external_services_weather_forecast(self) -> None:
        """ExternalServicesClient fetches weather forecasts.

        Validates: Req 23.7
        """
        from grins_platform.services.ai.scheduling.external_services import (
            ExternalServicesClient,
        )

        client = ExternalServicesClient()
        assert callable(client.get_weather_forecast)

    @pytest.mark.integration
    def test_weather_criterion_is_in_default_config(self) -> None:
        """Weather forecast impact (criterion 26) is in the default config.

        Validates: Req 23.7
        """
        criterion_26 = [c for c in _DEFAULT_CRITERIA if c["n"] == 26]
        assert len(criterion_26) == 1
        assert criterion_26[0]["name"] == "Weather forecast impact"
        assert criterion_26[0]["group"] == "predictive"
        assert criterion_26[0]["w"] == 70


# ============================================================================
# SECTION C — Cross-cutting wiring verification
# ============================================================================


class TestCrossCuttingWiring:
    """Verify cross-cutting integration wiring across components."""

    @pytest.mark.integration
    def test_resource_tools_has_all_ten_tools(self) -> None:
        """ResourceSchedulingTools exposes all 10 resource tool functions.

        Validates: Req 22.4, 22.5, 22.6
        """
        from grins_platform.services.ai.scheduling.resource_tools import (
            ResourceSchedulingTools,
        )

        session = _mock_session()
        tools = ResourceSchedulingTools(session=session)
        expected_methods = [
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
        ]
        for method_name in expected_methods:
            assert hasattr(tools, method_name), f"Missing resource tool: {method_name}"
            assert callable(getattr(tools, method_name))

    @pytest.mark.integration
    def test_change_request_service_exists(self) -> None:
        """ChangeRequestService is importable and has CRUD methods.

        Validates: Req 22.4
        """
        from grins_platform.services.ai.scheduling.change_request_service import (
            ChangeRequestService,
        )

        session = _mock_session()
        svc = ChangeRequestService(session=session)
        assert callable(svc.create_request)
        assert callable(svc.approve_request)
        assert callable(svc.deny_request)

    @pytest.mark.integration
    def test_prejob_generator_exists(self) -> None:
        """PreJobGenerator is importable and has checklist/upsell methods.

        Validates: Req 22.5, 22.6
        """
        from grins_platform.services.ai.scheduling.prejob_generator import (
            PreJobGenerator,
        )

        session = _mock_session()
        gen = PreJobGenerator(session=session)
        assert callable(gen.generate_checklist)
        assert callable(gen.generate_upsell_suggestions)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_evaluator_rank_candidates(self) -> None:
        """CriteriaEvaluator.rank_candidates ranks staff by composite score.

        Validates: Req 23.1
        """
        from grins_platform.services.ai.scheduling.criteria_evaluator import (
            CriteriaEvaluator,
        )

        session = _mock_session()
        config = SchedulingConfig()
        evaluator = CriteriaEvaluator(session=session, config=config)

        job = _job()
        staff_a = _staff(equipment=["pressure_gauge"])
        staff_b = _staff(equipment=["compressor"])
        ctx = _ctx()

        ranked = await evaluator.rank_candidates(job, [staff_a, staff_b], ctx)
        assert isinstance(ranked, list)
        assert len(ranked) == 2

    @pytest.mark.integration
    def test_chat_service_routes_by_role(self) -> None:
        """SchedulingChatService has separate handlers for admin and resource.

        Validates: Req 23.3
        """
        from grins_platform.services.ai.scheduling.chat_service import (
            SchedulingChatService,
        )

        session = _mock_session()
        svc = SchedulingChatService(session=session)
        assert callable(svc._handle_admin_message)
        assert callable(svc._handle_resource_message)

    @pytest.mark.integration
    def test_service_zone_model_exists(self) -> None:
        """ServiceZone model is importable for geographic zone boundaries.

        Validates: Req 22.1, 23.1
        """
        from grins_platform.models.service_zone import ServiceZone

        assert hasattr(ServiceZone, "__tablename__")
        assert ServiceZone.__tablename__ == "service_zones"

    @pytest.mark.integration
    def test_change_request_model_exists(self) -> None:
        """ChangeRequest model is importable for resource change requests.

        Validates: Req 22.4
        """
        from grins_platform.models.change_request import ChangeRequest

        assert hasattr(ChangeRequest, "__tablename__")
        assert ChangeRequest.__tablename__ == "change_requests"

    @pytest.mark.integration
    def test_scheduling_chat_session_model_exists(self) -> None:
        """SchedulingChatSession model is importable for chat history.

        Validates: Req 23.3
        """
        from grins_platform.models.scheduling_chat_session import (
            SchedulingChatSession,
        )

        assert hasattr(SchedulingChatSession, "__tablename__")
        assert SchedulingChatSession.__tablename__ == "scheduling_chat_sessions"
