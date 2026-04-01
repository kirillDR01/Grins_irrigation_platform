"""
ResourceScorer — criteria 6-10 for AI scheduling.

Scores resource factors: skill/certification match, equipment,
availability windows, workload balance, and performance history.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import CriterionResult, SchedulingContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ResourceScorer(LoggerMixin):
    """Scores resource criteria 6-10 for job-staff assignments."""

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
        """Score a resource criterion for a job-staff pair."""
        method_map: dict[int, Callable[..., Coroutine[Any, Any, CriterionResult]]] = {
            6: self._score_skill_match,
            7: self._score_equipment,
            8: self._score_availability,
            9: self._score_workload_balance,
            10: self._score_performance,
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
            explanation="Unknown resource criterion",
        )


    async def _score_skill_match(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 6: Skill/certification match (HARD).

        All required skills present = 100/satisfied,
        any missing = 0/not satisfied.
        """
        name = config.get("criterion_name", "Skill/Certification Match")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", True)

        required: set[str] = set(job.get("required_skills", []))
        held: set[str] = set(staff.get("certifications", []))

        if not required:
            return CriterionResult(
                criterion_number=6,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No skills required",
            )

        missing = required - held
        if missing:
            return CriterionResult(
                criterion_number=6,
                criterion_name=name,
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=f"Missing skills: {', '.join(sorted(missing))}",
            )

        return CriterionResult(
            criterion_number=6,
            criterion_name=name,
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation="All required skills matched",
        )

    async def _score_equipment(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 7: Equipment on truck (HARD).

        All required equipment present = 100/satisfied,
        any missing = 0/not satisfied.
        """
        name = config.get("criterion_name", "Equipment on Truck")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", True)

        required: set[str] = set(job.get("required_equipment", []))
        on_truck: set[str] = set(staff.get("assigned_equipment", []))

        if not required:
            return CriterionResult(
                criterion_number=7,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No equipment required",
            )

        missing = required - on_truck
        if missing:
            return CriterionResult(
                criterion_number=7,
                criterion_name=name,
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(
                    f"Missing equipment: {', '.join(sorted(missing))}"
                ),
            )

        return CriterionResult(
            criterion_number=7,
            criterion_name=name,
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation="All required equipment on truck",
        )

    async def _score_availability(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 8: Resource availability windows (HARD).

        Job time slot within staff shift = 100/satisfied,
        outside = 0/not satisfied.
        """
        name = config.get("criterion_name", "Resource Availability Windows")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", True)

        shift_start = staff.get("shift_start")
        shift_end = staff.get("shift_end")
        job_start = job.get("scheduled_start")
        job_end = job.get("scheduled_end")

        if not all([shift_start, shift_end, job_start, job_end]):
            return CriterionResult(
                criterion_number=8,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="Incomplete schedule data; neutral score",
            )

        s_start = str(shift_start)
        s_end = str(shift_end)
        j_start = str(job_start)
        j_end = str(job_end)

        within = j_start >= s_start and j_end <= s_end
        if not within:
            return CriterionResult(
                criterion_number=8,
                criterion_name=name,
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(
                    f"Job {j_start}-{j_end} outside shift "
                    f"{s_start}-{s_end}"
                ),
            )

        return CriterionResult(
            criterion_number=8,
            criterion_name=name,
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation="Job within shift window",
        )

    async def _score_workload_balance(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 9: Workload balance.

        Lower std dev of job-hours = higher score.
        Score = max(0, 100 - (std_dev * 10)).
        """
        name = config.get("criterion_name", "Workload Balance")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        hours_list: list[float] = staff.get("team_job_hours", [])
        if len(hours_list) < 2:
            return CriterionResult(
                criterion_number=9,
                criterion_name=name,
                score=75.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="Insufficient team data; default score",
            )

        std_dev = statistics.stdev(hours_list)
        raw_score = max(0.0, 100.0 - (std_dev * 10.0))

        return CriterionResult(
            criterion_number=9,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Workload std dev {std_dev:.2f}h → score {raw_score:.1f}"
            ),
        )

    async def _score_performance(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 10: Performance history.

        Weighted average of performance_score, callback_rate,
        avg_satisfaction normalized to 0-100.
        """
        name = config.get("criterion_name", "Performance History")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        perf = staff.get("performance_score")
        callback = staff.get("callback_rate")
        satisfaction = staff.get("avg_satisfaction")

        components: list[float] = []
        weights: list[float] = []

        if perf is not None:
            components.append(float(perf))
            weights.append(0.4)
        if callback is not None:
            inv_callback = max(0.0, 100.0 - float(callback) * 100.0)
            components.append(inv_callback)
            weights.append(0.3)
        if satisfaction is not None:
            sat_norm = float(satisfaction) * 20.0
            components.append(min(100.0, sat_norm))
            weights.append(0.3)

        if not components:
            return CriterionResult(
                criterion_number=10,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No performance data; neutral score",
            )

        total_w = sum(weights)
        raw_score = sum(c * w for c, w in zip(components, weights)) / total_w
        raw_score = max(0.0, min(100.0, raw_score))

        return CriterionResult(
            criterion_number=10,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=f"Performance composite → score {raw_score:.1f}",
        )
