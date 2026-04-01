"""
BusinessRulesScorer — criteria 21-25 for AI scheduling.

Scores business rule factors: compliance deadlines, revenue per
resource-hour, contract/SLA commitments, overtime cost threshold,
and seasonal pricing signals.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import CriterionResult, SchedulingContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BusinessRulesScorer(LoggerMixin):
    """Scores business rules criteria 21-25 for job-staff assignments."""

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
        """Score a business rules criterion for a job-staff pair."""
        method_map: dict[int, Callable[..., Coroutine[Any, Any, CriterionResult]]] = {
            21: self._score_compliance_deadline,
            22: self._score_revenue_per_hour,
            23: self._score_sla_commitment,
            24: self._score_overtime_cost,
            25: self._score_seasonal_pricing,
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
            explanation="Unknown business rules criterion",
        )


    @staticmethod
    def _parse_deadline(value: Any) -> datetime | None:
        """Parse a deadline value to datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except (ValueError, TypeError):
            return None

    async def _score_compliance_deadline(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 21: Compliance deadlines (HARD).

        Before deadline = 100/satisfied, after = 0/not satisfied.
        """
        name = config.get("criterion_name", "Compliance Deadlines")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", True)

        deadline = self._parse_deadline(job.get("compliance_deadline"))
        if deadline is None:
            return CriterionResult(
                criterion_number=21,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No compliance deadline",
            )

        schedule_dt = datetime.combine(
            context.schedule_date,
            datetime.max.time(),
            tzinfo=deadline.tzinfo,
        )

        if schedule_dt <= deadline:
            return CriterionResult(
                criterion_number=21,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Scheduled before compliance deadline "
                    f"{deadline.date()}"
                ),
            )

        return CriterionResult(
            criterion_number=21,
            criterion_name=name,
            score=0.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=False,
            explanation=(
                f"Scheduled after compliance deadline "
                f"{deadline.date()}"
            ),
        )

    async def _score_revenue_per_hour(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 22: Revenue per resource-hour.

        Higher revenue_per_hour = higher score.
        """
        name = config.get("criterion_name", "Revenue Per Resource-Hour")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        rph = job.get("revenue_per_hour")
        if rph is None:
            job_revenue = job.get("revenue") or job.get("total_price")
            duration = job.get("estimated_duration_minutes", 60)
            drive = job.get("drive_time_minutes", 0)
            total_min = float(duration or 60) + float(drive or 0)
            if job_revenue and total_min > 0:
                rph = float(job_revenue) / (total_min / 60.0)
            else:
                return CriterionResult(
                    criterion_number=22,
                    criterion_name=name,
                    score=50.0,
                    weight=weight,
                    is_hard=is_hard,
                    is_satisfied=True,
                    explanation="No revenue data; neutral score",
                )

        rph_val = float(rph)
        threshold = float(config.get("config_json", {}).get(
            "target_rph", 150.0,
        ) if isinstance(config.get("config_json"), dict) else 150.0)
        raw_score = min(100.0, (rph_val / threshold) * 100.0)

        return CriterionResult(
            criterion_number=22,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=f"Revenue/hour ${rph_val:.2f} → score {raw_score:.1f}",
        )

    async def _score_sla_commitment(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 23: Contract/SLA commitments (HARD).

        Before SLA deadline = 100/satisfied, after = 0/not satisfied.
        """
        name = config.get("criterion_name", "Contract/SLA Commitments")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", True)

        deadline = self._parse_deadline(job.get("sla_deadline"))
        if deadline is None:
            return CriterionResult(
                criterion_number=23,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No SLA deadline",
            )

        schedule_dt = datetime.combine(
            context.schedule_date,
            datetime.max.time(),
            tzinfo=deadline.tzinfo,
        )

        if schedule_dt <= deadline:
            return CriterionResult(
                criterion_number=23,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Scheduled before SLA deadline {deadline.date()}"
                ),
            )

        return CriterionResult(
            criterion_number=23,
            criterion_name=name,
            score=0.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=False,
            explanation=(
                f"Scheduled after SLA deadline {deadline.date()}"
            ),
        )

    async def _score_overtime_cost(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 24: Overtime cost threshold.

        Under threshold = 100, over = penalized unless revenue
        justifies.
        """
        name = config.get("criterion_name", "Overtime Cost Threshold")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        threshold = staff.get("overtime_threshold_minutes")
        current_minutes = float(staff.get("assigned_job_minutes", 0))
        job_duration = float(job.get("estimated_duration_minutes", 60))

        if threshold is None:
            return CriterionResult(
                criterion_number=24,
                criterion_name=name,
                score=75.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No overtime threshold set; default score",
            )

        projected = current_minutes + job_duration
        threshold_val = float(threshold)

        if projected <= threshold_val:
            return CriterionResult(
                criterion_number=24,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Projected {projected:.0f} min within "
                    f"threshold {threshold_val:.0f} min"
                ),
            )

        overtime_min = projected - threshold_val
        rph = job.get("revenue_per_hour")
        if rph and float(rph) > 100.0:
            raw_score = max(40.0, 100.0 - (overtime_min * 0.5))
            note = "overtime justified by revenue"
        else:
            raw_score = max(0.0, 100.0 - (overtime_min * 1.0))
            note = "overtime penalty applied"

        return CriterionResult(
            criterion_number=24,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Overtime {overtime_min:.0f} min, {note} → "
                f"score {raw_score:.1f}"
            ),
        )

    async def _score_seasonal_pricing(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 25: Seasonal pricing signals.

        Steer flexible jobs to off-peak. Peak slot + full price = 100.
        """
        name = config.get("criterion_name", "Seasonal Pricing Signals")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        month = context.schedule_date.month
        is_peak = month in (3, 4, 5, 9, 10, 11)
        priority = str(job.get("priority", "standard")).lower()
        is_flexible = priority == "flexible"

        if is_peak and not is_flexible:
            raw_score = 100.0
            explanation = "Peak season, non-flexible job → full score"
        elif is_peak and is_flexible:
            raw_score = 40.0
            explanation = "Peak season, flexible job → steer to off-peak"
        elif not is_peak and is_flexible:
            raw_score = 80.0
            explanation = "Off-peak, flexible job → good fit"
        else:
            raw_score = 60.0
            explanation = "Off-peak, standard job → moderate score"

        return CriterionResult(
            criterion_number=25,
            criterion_name=name,
            score=raw_score,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )
