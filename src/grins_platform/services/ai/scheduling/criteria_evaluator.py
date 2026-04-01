"""
CriteriaEvaluator — core 30-criteria scoring engine for AI scheduling.

Wraps the existing ConstraintChecker and adds criteria 3-30 as
additional scoring dimensions via 6 scorer modules.

Validates: Requirements 3.1-3.5, 4.1-4.5, 5.1-5.5,
6.1-6.5, 7.1-7.5, 8.1-8.5, 23.1, 23.2, 32.1, 32.2
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import (
    AlertCandidate,
    CriterionResult,
    RankedCandidate,
    ScheduleEvaluation,
    SchedulingConfig,
    SchedulingContext,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CriteriaEvaluator(LoggerMixin):
    """Core 30-criteria scoring engine for AI scheduling.

    Wraps the existing ConstraintChecker and adds criteria 3-30
    as additional scoring dimensions. Delegates to 6 scorer
    modules organized by group:

    - GeographicScorer (criteria 1-5)
    - ResourceScorer (criteria 6-10)
    - CustomerJobScorer (criteria 11-15)
    - CapacityDemandScorer (criteria 16-20)
    - BusinessRulesScorer (criteria 21-25)
    - PredictiveScorer (criteria 26-30)
    """

    DOMAIN = "scheduling"

    def __init__(
        self,
        session: AsyncSession,
        config: SchedulingConfig,
    ) -> None:
        """Initialize the CriteriaEvaluator.

        Args:
            session: Async database session
            config: Scheduling configuration with criteria
                weights and thresholds
        """
        super().__init__()
        self._session = session
        self._config = config
        self._criteria_map: dict[int, dict[str, Any]] = {}
        self._load_criteria_map()

    def _load_criteria_map(self) -> None:
        """Build a lookup map from criteria config."""
        for criterion in self._config.criteria:
            num = criterion.get("criterion_number", 0)
            self._criteria_map[num] = criterion

    async def evaluate_assignment(
        self,
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> list[CriterionResult]:
        """Score a single job-staff assignment against all 30 criteria.

        Delegates to 6 scorer modules and aggregates weighted
        scores.

        Args:
            job: Job data dictionary
            staff: Staff data dictionary
            context: Scheduling context

        Returns:
            List of 30 CriterionResult entries.
        """
        self.log_started(
            "evaluate_assignment",
            job_id=job.get("id"),
            staff_id=staff.get("id"),
        )

        results: list[CriterionResult] = []

        for criterion_number in range(1, 31):
            config = self._criteria_map.get(criterion_number, {})
            if not config.get("is_enabled", True):
                results.append(
                    CriterionResult(
                        criterion_number=criterion_number,
                        criterion_name=config.get(
                            "criterion_name",
                            f"Criterion {criterion_number}",
                        ),
                        score=50.0,
                        weight=0,
                        is_hard=config.get(
                            "is_hard_constraint",
                            False,
                        ),
                        is_satisfied=True,
                        explanation="Criterion disabled",
                    ),
                )
                continue

            result = await self._score_criterion(
                criterion_number,
                config,
                job,
                staff,
                context,
            )
            results.append(result)

        self.log_completed(
            "evaluate_assignment",
            job_id=job.get("id"),
            staff_id=staff.get("id"),
            criteria_count=len(results),
        )
        return results

    async def evaluate_schedule(
        self,
        assignments: list[dict[str, Any]],
        context: SchedulingContext,
    ) -> ScheduleEvaluation:
        """Score an entire schedule against all 30 criteria.

        Args:
            assignments: List of job-staff assignment dicts
                with keys: job, staff, time_slot
            context: Scheduling context

        Returns:
            ScheduleEvaluation with aggregate score,
            hard violations, and alerts.
        """
        self.log_started(
            "evaluate_schedule",
            assignment_count=len(assignments),
        )

        all_scores: list[CriterionResult] = []
        hard_violations = 0
        alerts: list[AlertCandidate] = []
        total_weighted_score = 0.0
        total_weight = 0

        for assignment in assignments:
            job = assignment.get("job", {})
            staff = assignment.get("staff", {})
            criteria_results = await self.evaluate_assignment(
                job,
                staff,
                context,
            )

            for result in criteria_results:
                total_weighted_score += result.score * result.weight
                total_weight += result.weight
                if result.is_hard and not result.is_satisfied:
                    hard_violations += 1
                    alerts.append(
                        AlertCandidate(
                            alert_type=(
                                "hard_violation_criterion"
                                f"_{result.criterion_number}"
                            ),
                            severity="critical",
                            title=(
                                "Hard Constraint Violation"
                                f": {result.criterion_name}"
                            ),
                            description=result.explanation,
                            affected_job_ids=(
                                [UUID(job["id"])]
                                if job.get("id")
                                else []
                            ),
                            affected_staff_ids=(
                                [UUID(staff["id"])]
                                if staff.get("id")
                                else []
                            ),
                            criteria_triggered=[
                                result.criterion_number,
                            ],
                        ),
                    )

            all_scores.extend(criteria_results)

        aggregate_score = (
            (total_weighted_score / total_weight)
            if total_weight > 0
            else 0.0
        )

        evaluation = ScheduleEvaluation(
            schedule_date=context.schedule_date,
            total_score=round(aggregate_score, 2),
            hard_violations=hard_violations,
            criteria_scores=all_scores,
            alerts=alerts,
        )

        self.log_completed(
            "evaluate_schedule",
            total_score=evaluation.total_score,
            hard_violations=hard_violations,
            alert_count=len(alerts),
        )
        return evaluation

    async def rank_candidates(
        self,
        job: dict[str, Any],
        candidates: list[dict[str, Any]],
        context: SchedulingContext,
    ) -> list[RankedCandidate]:
        """Rank staff candidates for a job by composite score.

        Args:
            job: Job data dictionary
            candidates: List of staff data dictionaries
            context: Scheduling context

        Returns:
            List of RankedCandidate sorted descending.
        """
        self.log_started(
            "rank_candidates",
            job_id=job.get("id"),
            candidate_count=len(candidates),
        )

        ranked: list[RankedCandidate] = []

        for staff in candidates:
            criteria_results = await self.evaluate_assignment(
                job,
                staff,
                context,
            )

            hard_satisfied = all(
                r.is_satisfied
                for r in criteria_results
                if r.is_hard
            )

            if not hard_satisfied:
                continue

            total_weighted = sum(
                r.score * r.weight for r in criteria_results
            )
            total_weight = sum(
                r.weight for r in criteria_results
            )
            composite = (
                (total_weighted / total_weight)
                if total_weight > 0
                else 0.0
            )

            ranked.append(
                RankedCandidate(
                    staff_id=UUID(str(staff.get("id", ""))),
                    name=str(staff.get("name", "")),
                    composite_score=round(composite, 2),
                    criterion_breakdown=criteria_results,
                ),
            )

        ranked.sort(
            key=lambda c: c.composite_score,
            reverse=True,
        )

        self.log_completed(
            "rank_candidates",
            job_id=job.get("id"),
            ranked_count=len(ranked),
        )
        return ranked

    async def _score_criterion(
        self,
        criterion_number: int,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Score a single criterion via the appropriate scorer.

        Routes to the correct scorer based on criterion number.
        Scorer modules are imported lazily to avoid circular deps.

        Args:
            criterion_number: The criterion number (1-30)
            config: Criterion configuration from DB
            job: Job data
            staff: Staff data
            context: Scheduling context

        Returns:
            CriterionResult for this criterion.
        """
        name = config.get(
            "criterion_name",
            f"Criterion {criterion_number}",
        )
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        try:
            scorer_result = await self._dispatch_scorer(
                criterion_number,
                config,
                job,
                staff,
                context,
            )
            if scorer_result is not None:
                return scorer_result

            return CriterionResult(
                criterion_number=criterion_number,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Unknown criterion {criterion_number}"
                ),
            )
        except Exception as e:
            self.log_failed(
                "score_criterion",
                error=e,
                criterion_number=criterion_number,
            )
            return CriterionResult(
                criterion_number=criterion_number,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=not is_hard,
                explanation=f"Scoring error: {e}",
            )

    async def _dispatch_scorer(
        self,
        criterion_number: int,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult | None:
        """Dispatch to the correct scorer module.

        Returns None if criterion_number is out of range.
        """
        args = (criterion_number, config, job, staff, context)

        if 1 <= criterion_number <= 5:
            from grins_platform.services.ai.scheduling.scorers.geographic import (  # type: ignore[import-untyped]  # noqa: PLC0415
                GeographicScorer,
            )

            return await GeographicScorer(  # type: ignore[no-any-return]
                self._session,
            ).score(*args)

        if 6 <= criterion_number <= 10:
            from grins_platform.services.ai.scheduling.scorers.resource import (  # type: ignore[import-untyped]  # noqa: PLC0415
                ResourceScorer,
            )

            return await ResourceScorer(  # type: ignore[no-any-return]
                self._session,
            ).score(*args)

        if 11 <= criterion_number <= 15:
            from grins_platform.services.ai.scheduling.scorers.customer_job import (  # type: ignore[import-untyped]  # noqa: PLC0415
                CustomerJobScorer,
            )

            return await CustomerJobScorer(  # type: ignore[no-any-return]
                self._session,
            ).score(*args)

        if 16 <= criterion_number <= 20:
            from grins_platform.services.ai.scheduling.scorers.capacity_demand import (  # type: ignore[import-untyped]  # noqa: PLC0415
                CapacityDemandScorer,
            )

            return await CapacityDemandScorer(  # type: ignore[no-any-return]
                self._session,
            ).score(*args)

        if 21 <= criterion_number <= 25:
            from grins_platform.services.ai.scheduling.scorers.business_rules import (  # type: ignore[import-untyped]  # noqa: PLC0415
                BusinessRulesScorer,
            )

            return await BusinessRulesScorer(  # type: ignore[no-any-return]
                self._session,
            ).score(*args)

        if 26 <= criterion_number <= 30:
            from grins_platform.services.ai.scheduling.scorers.predictive import (  # type: ignore[import-untyped]  # noqa: PLC0415
                PredictiveScorer,
            )

            return await PredictiveScorer(  # type: ignore[no-any-return]
                self._session,
            ).score(*args)

        return None
