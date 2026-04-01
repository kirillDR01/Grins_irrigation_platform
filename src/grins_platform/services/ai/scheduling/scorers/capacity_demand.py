"""
CapacityDemandScorer — criteria 16-20 for AI scheduling.

Scores capacity/demand factors: daily utilization, weekly demand
forecast, seasonal peaks, cancellation probability, and
pipeline/backlog pressure.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import CriterionResult, SchedulingContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CapacityDemandScorer(LoggerMixin):
    """Scores capacity/demand criteria 16-20 for job-staff assignments."""

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session

    async def score(
        self,
        criterion_number: int,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Score a capacity/demand criterion for a job-staff pair."""
        method_map: dict[int, Callable[..., Coroutine[Any, Any, CriterionResult]]] = {
            16: self._score_daily_utilization,
            17: self._score_weekly_forecast,
            18: self._score_seasonal_peak,
            19: self._score_cancellation_probability,
            20: self._score_backlog_pressure,
        }
        method = method_map.get(criterion_number)
        if method:
            return await method(config, job, staff, context)

        name = config.get("criterion_name", f"Criterion {criterion_number}")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)
        return CriterionResult(
            criterion_number=criterion_number,
            criterion_name=name,
            score=50.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation="Unknown capacity/demand criterion",
        )


    async def _score_daily_utilization(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 16: Daily capacity utilization.

        (job_min + drive_min) / available_min * 100.
        Penalizes >90% and <60%.
        """
        name = config.get("criterion_name", "Daily Capacity Utilization")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        job_min = float(staff.get("assigned_job_minutes", 0))
        drive_min = float(staff.get("assigned_drive_minutes", 0))
        available_min = float(staff.get("available_minutes", 480))

        if available_min <= 0:
            return CriterionResult(
                criterion_number=16,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No availability data; neutral score",
            )

        utilization = (job_min + drive_min) / available_min * 100.0

        if 60.0 <= utilization <= 90.0:
            raw_score = 100.0
        elif utilization > 90.0:
            overage = utilization - 90.0
            raw_score = max(0.0, 100.0 - (overage * 5.0))
        else:
            underage = 60.0 - utilization
            raw_score = max(0.0, 100.0 - (underage * 2.0))

        return CriterionResult(
            criterion_number=16,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Utilization {utilization:.1f}% → score {raw_score:.1f}"
            ),
        )

    async def _score_weekly_forecast(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 17: Weekly demand forecast.

        Higher demand = higher urgency score. Heuristic placeholder.
        """
        name = config.get("criterion_name", "Weekly Demand Forecast")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        backlog = context.backlog or {}
        forecast_volume = backlog.get("weekly_forecast_volume")

        if forecast_volume is None:
            return CriterionResult(
                criterion_number=17,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No forecast data; neutral score",
            )

        volume = float(forecast_volume)
        raw_score = min(100.0, volume * 2.0)

        return CriterionResult(
            criterion_number=17,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Forecast volume {volume:.0f} → score {raw_score:.1f}"
            ),
        )

    async def _score_seasonal_peak(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 18: Seasonal peak windows.

        Detect peak periods. During peak = higher score.
        """
        name = config.get("criterion_name", "Seasonal Peak Windows")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        month = context.schedule_date.month

        spring_peak = month in (3, 4, 5)
        fall_peak = month in (9, 10, 11)
        is_peak = spring_peak or fall_peak

        raw_score = 80.0 if is_peak else 50.0

        return CriterionResult(
            criterion_number=18,
            criterion_name=name,
            score=raw_score,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"{'Peak' if is_peak else 'Off-peak'} season "
                f"(month {month}) → score {raw_score:.0f}"
            ),
        )

    async def _score_cancellation_probability(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 19: Cancellation/no-show probability.

        ML prediction placeholder. Low cancel prob = higher score.
        """
        name = config.get(
            "criterion_name",
            "Cancellation/No-Show Probability",
        )
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        cancel_prob = job.get("cancel_probability")

        if cancel_prob is None:
            return CriterionResult(
                criterion_number=19,
                criterion_name=name,
                score=70.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No cancellation data; default score",
            )

        prob = float(cancel_prob)
        raw_score = max(0.0, 100.0 - (prob * 100.0))

        return CriterionResult(
            criterion_number=19,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Cancel probability {prob:.2f} → score {raw_score:.1f}"
            ),
        )

    async def _score_backlog_pressure(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 20: Pipeline/backlog pressure.

        More unscheduled + older = higher pressure score.
        """
        name = config.get("criterion_name", "Pipeline/Backlog Pressure")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        backlog = context.backlog or {}
        unscheduled = int(backlog.get("unscheduled_count", 0))
        avg_age_days = float(backlog.get("avg_age_days", 0))

        if unscheduled == 0 and avg_age_days == 0:
            return CriterionResult(
                criterion_number=20,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No backlog data; neutral score",
            )

        count_factor = min(50.0, unscheduled * 2.0)
        age_factor = min(50.0, avg_age_days * 5.0)
        raw_score = min(100.0, count_factor + age_factor)

        return CriterionResult(
            criterion_number=20,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Backlog: {unscheduled} jobs, "
                f"avg age {avg_age_days:.0f}d → score {raw_score:.1f}"
            ),
        )
