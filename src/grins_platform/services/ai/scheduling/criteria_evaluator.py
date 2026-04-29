"""
CriteriaEvaluator — 30-criteria scoring engine for AI scheduling.

This is the core evaluation service that scores job-staff assignments against
all 30 decision criteria. It delegates to 6 scorer modules (geographic,
resource, customer_job, capacity_demand, business_rules, predictive) and
aggregates weighted scores into composite results.

The evaluator wraps the existing ``ConstraintChecker`` from
``services/schedule_constraints.py`` and layers additional scoring dimensions
on top of the hard/soft constraint foundation.

Validates: Requirements 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.5,
           7.1-7.5, 8.1-8.5, 23.1, 23.2, 32.1, 32.2
"""

from __future__ import annotations

import time as time_mod
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.scheduling_criteria_config import (
    SchedulingCriteriaConfig,
)
from grins_platform.schemas.ai_scheduling import (
    CriteriaScore,
    CriterionResult,
    RankedCandidate,
    ScheduleEvaluation,
    SchedulingConfig,
    SchedulingContext,
)
from grins_platform.services.schedule_constraints import ConstraintChecker

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.services.schedule_domain import (
        ScheduleJob,
        ScheduleSolution,
        ScheduleStaff,
    )


# ---------------------------------------------------------------------------
# Scorer protocol — each scorer module implements this interface
# ---------------------------------------------------------------------------


class ScorerProtocol(Protocol):
    """Protocol that all 6 scorer modules must implement.

    Each scorer is responsible for a group of 5 criteria (e.g. criteria
    1-5 for GeographicScorer). The ``score_assignment`` method evaluates
    a single job-staff pairing and returns a list of ``CriterionResult``
    objects, one per criterion in the group.
    """

    async def score_assignment(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> list[CriterionResult]:
        """Score a job-staff assignment for this group's criteria."""
        ...


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _CriterionConfig:
    """Internal representation of a single criterion's configuration.

    Loaded from the ``scheduling_criteria_config`` database table and
    cached in memory for the lifetime of the evaluator (or until cache
    expires).
    """

    __slots__ = (
        "config_json",
        "criterion_group",
        "criterion_name",
        "criterion_number",
        "is_enabled",
        "is_hard_constraint",
        "weight",
    )

    def __init__(
        self,
        criterion_number: int,
        criterion_name: str,
        criterion_group: str,
        weight: int,
        is_hard_constraint: bool,
        is_enabled: bool,
        config_json: dict[str, Any] | None,
    ) -> None:
        self.criterion_number = criterion_number
        self.criterion_name = criterion_name
        self.criterion_group = criterion_group
        self.weight = weight
        self.is_hard_constraint = is_hard_constraint
        self.is_enabled = is_enabled
        self.config_json = config_json or {}


def _c(
    n: int,
    name: str,
    group: str,
    w: int,
    *,
    hard: bool = False,
) -> dict[str, Any]:
    """Build a default criterion definition dict."""
    return {
        "n": n,
        "name": name,
        "group": group,
        "w": w,
        "hard": hard,
    }


# Default criteria definitions used when the DB has no rows yet.
_DEFAULT_CRITERIA: list[dict[str, Any]] = [
    # Geographic (1-5)
    _c(1, "Resource-to-job proximity", "geographic", 80),
    _c(2, "Intra-route drive time", "geographic", 70),
    _c(3, "Service zone boundaries", "geographic", 60),
    _c(4, "Real-time traffic", "geographic", 50),
    _c(5, "Job site access constraints", "geographic", 90, hard=True),
    # Resource (6-10)
    _c(6, "Skill/certification match", "resource", 100, hard=True),
    _c(7, "Equipment on truck", "resource", 100, hard=True),
    _c(8, "Resource availability windows", "resource", 100, hard=True),
    _c(9, "Workload balance", "resource", 60),
    _c(10, "Performance history", "resource", 40),
    # Customer/Job (11-15)
    _c(11, "Customer time-window preferences", "customer_job", 70),
    _c(12, "Job type duration estimates", "customer_job", 50),
    _c(13, "Job priority level", "customer_job", 90),
    _c(14, "Customer lifetime value", "customer_job", 40),
    _c(15, "Customer-resource relationship", "customer_job", 50),
    # Capacity/Demand (16-20)
    _c(16, "Daily capacity utilization", "capacity_demand", 60),
    _c(17, "Weekly demand forecast", "capacity_demand", 40),
    _c(18, "Seasonal peak windows", "capacity_demand", 50),
    _c(19, "Cancellation probability", "capacity_demand", 30),
    _c(20, "Pipeline/backlog pressure", "capacity_demand", 50),
    # Business Rules (21-25)
    _c(21, "Compliance deadlines", "business_rules", 95, hard=True),
    _c(22, "Revenue per resource-hour", "business_rules", 60),
    _c(23, "SLA commitments", "business_rules", 95, hard=True),
    _c(24, "Overtime cost threshold", "business_rules", 50),
    _c(25, "Seasonal pricing signals", "business_rules", 40),
    # Predictive (26-30)
    _c(26, "Weather forecast impact", "predictive", 70),
    _c(27, "Predicted job complexity", "predictive", 50),
    _c(28, "Lead conversion timing", "predictive", 30),
    _c(29, "Resource start location", "predictive", 60),
    _c(30, "Cross-job dependencies", "predictive", 90, hard=True),
]

# Number of criteria the engine evaluates.
TOTAL_CRITERIA = 30

# Cache TTL for criteria config (seconds).
_CONFIG_CACHE_TTL_SECONDS = 300  # 5 minutes


class CriteriaEvaluator(LoggerMixin):
    """30-criteria scoring engine for AI-powered scheduling.

    Evaluates job-staff assignments against all 30 decision criteria by
    delegating to 6 scorer modules and aggregating weighted scores.
    Wraps the existing ``ConstraintChecker`` for hard constraint
    validation.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    def __init__(
        self,
        session: AsyncSession,
        config: SchedulingConfig | None = None,
        *,
        scorers: dict[str, ScorerProtocol] | None = None,
    ) -> None:
        """Initialise the evaluator.

        Args:
            session: Async SQLAlchemy session for DB access.
            config: Optional runtime configuration overrides for
                criteria weights and thresholds. When ``None``,
                defaults are loaded from the
                ``scheduling_criteria_config`` table.
            scorers: Optional mapping of scorer group names to scorer
                instances. Keys should be ``geographic``, ``resource``,
                ``customer_job``, ``capacity_demand``,
                ``business_rules``, ``predictive``. Scorers not
                provided will be skipped gracefully (a neutral score
                is returned for their criteria).
        """
        super().__init__()
        self._session = session
        self._config_overrides = config
        self._scorers: dict[str, ScorerProtocol] = scorers or {}
        self._constraint_checker = ConstraintChecker()

        # In-memory cache for criteria config loaded from DB.
        self._criteria_cache: dict[int, _CriterionConfig] | None = None
        self._cache_loaded_at: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate_assignment(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> CriteriaScore:
        """Score a single job-staff assignment against all 30 criteria.

        Delegates to each registered scorer module, collects
        per-criterion results, and aggregates into a weighted composite
        score.

        Args:
            job: The job to evaluate.
            staff: The candidate staff member.
            context: Scheduling context (date, weather, traffic,
                backlog).

        Returns:
            ``CriteriaScore`` with total weighted score,
            hard-violation count, and per-criterion breakdown.
        """
        self.log_started(
            "evaluate_assignment",
            job_id=str(job.id),
            staff_id=str(staff.id),
        )

        try:
            criteria_config = await self._load_criteria_config()
            criterion_results = await self._score_all_criteria(
                job,
                staff,
                context,
                criteria_config,
            )
            total_score = self._aggregate_scores(criterion_results)
            hard_violations = sum(
                1 for r in criterion_results if r.is_hard and not r.is_satisfied
            )
        except Exception as exc:
            self.log_failed(
                "evaluate_assignment",
                error=exc,
                job_id=str(job.id),
                staff_id=str(staff.id),
            )
            raise
        else:
            result = CriteriaScore(
                total_score=total_score,
                hard_violations=hard_violations,
                criteria_scores=criterion_results,
            )
            self.log_completed(
                "evaluate_assignment",
                job_id=str(job.id),
                staff_id=str(staff.id),
                total_score=total_score,
                hard_violations=hard_violations,
            )
            return result

    async def evaluate_schedule(
        self,
        solution: ScheduleSolution,
        context: SchedulingContext,
    ) -> ScheduleEvaluation:
        """Score an entire schedule against all 30 criteria.

        Iterates over every assignment in the solution, evaluates each
        job-staff pairing, and produces an aggregate evaluation with
        per-criterion averages and alert messages for violations.

        Args:
            solution: The complete schedule solution to evaluate.
            context: Scheduling context.

        Returns:
            ``ScheduleEvaluation`` with aggregate score,
            hard-violation count, per-criterion breakdown, and alert
            strings.
        """
        self.log_started(
            "evaluate_schedule",
            schedule_date=str(solution.schedule_date),
            assignment_count=len(solution.assignments),
        )

        try:
            total_hard_violations = 0
            assignment_scores: list[float] = []
            alerts: list[str] = []

            for assignment in solution.assignments:
                for job in assignment.jobs:
                    score = await self.evaluate_assignment(
                        job,
                        assignment.staff,
                        context,
                    )
                    assignment_scores.append(score.total_score)
                    total_hard_violations += score.hard_violations

                    # Collect alerts for hard-constraint violations.
                    alerts.extend(
                        f"[Criterion {cr.criterion_number}] "
                        f"{cr.criterion_name}: {cr.explanation}"
                        for cr in score.criteria_scores
                        if cr.is_hard and not cr.is_satisfied
                    )

            # Aggregate per-criterion averages.
            all_criterion_results = self._aggregate_criterion_averages()

            total_score = (
                sum(assignment_scores) / len(assignment_scores)
                if assignment_scores
                else 0.0
            )
        except Exception as exc:
            self.log_failed(
                "evaluate_schedule",
                error=exc,
                schedule_date=str(solution.schedule_date),
            )
            raise
        else:
            result = ScheduleEvaluation(
                schedule_date=solution.schedule_date,
                total_score=round(total_score, 2),
                hard_violations=total_hard_violations,
                criteria_scores=all_criterion_results,
                alerts=alerts,
            )
            self.log_completed(
                "evaluate_schedule",
                schedule_date=str(solution.schedule_date),
                total_score=result.total_score,
                hard_violations=total_hard_violations,
                alert_count=len(alerts),
            )
            return result

    async def rank_candidates(
        self,
        job: ScheduleJob,
        candidates: list[ScheduleStaff],
        context: SchedulingContext,
    ) -> list[RankedCandidate]:
        """Rank staff candidates for a job by composite criteria score.

        Evaluates each candidate against the job and returns a sorted
        list (highest score first). Candidates with hard-constraint
        violations are ranked below those without.

        Args:
            job: The job to assign.
            candidates: List of candidate staff members.
            context: Scheduling context.

        Returns:
            Sorted list of ``RankedCandidate`` objects, best fit first.
        """
        self.log_started(
            "rank_candidates",
            job_id=str(job.id),
            candidate_count=len(candidates),
        )

        try:
            ranked: list[RankedCandidate] = []

            for staff in candidates:
                score = await self.evaluate_assignment(
                    job,
                    staff,
                    context,
                )
                ranked.append(
                    RankedCandidate(
                        staff_id=staff.id,
                        name=staff.name,
                        composite_score=score.total_score,
                        criterion_breakdown=score.criteria_scores,
                    ),
                )

            # Sort: fewest hard violations first, then highest score.
            ranked.sort(
                key=lambda r: (
                    sum(
                        1
                        for cr in r.criterion_breakdown
                        if cr.is_hard and not cr.is_satisfied
                    ),
                    -r.composite_score,
                ),
            )
        except Exception as exc:
            self.log_failed(
                "rank_candidates",
                error=exc,
                job_id=str(job.id),
            )
            raise
        else:
            self.log_completed(
                "rank_candidates",
                job_id=str(job.id),
                candidate_count=len(candidates),
                top_score=(ranked[0].composite_score if ranked else 0.0),
            )
            return ranked

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    async def _load_criteria_config(
        self,
    ) -> dict[int, _CriterionConfig]:
        """Load criteria configuration from the database with caching.

        Results are cached in memory for
        ``_CONFIG_CACHE_TTL_SECONDS``. If the DB table is empty,
        built-in defaults are used. Runtime overrides from
        ``SchedulingConfig`` are applied on top.

        Returns:
            Mapping of criterion number (1-30) to its configuration.
        """
        now = time_mod.monotonic()
        if (
            self._criteria_cache is not None
            and (now - self._cache_loaded_at) < _CONFIG_CACHE_TTL_SECONDS
        ):
            return self._criteria_cache

        self.log_started("load_criteria_config")

        try:
            stmt = select(SchedulingCriteriaConfig).order_by(
                SchedulingCriteriaConfig.criterion_number,
            )
            result = await self._session.execute(stmt)
            rows = result.scalars().all()

            config_map: dict[int, _CriterionConfig] = {}

            if rows:
                for row in rows:
                    config_map[row.criterion_number] = _CriterionConfig(
                        criterion_number=row.criterion_number,
                        criterion_name=row.criterion_name,
                        criterion_group=row.criterion_group,
                        weight=row.weight,
                        is_hard_constraint=row.is_hard_constraint,
                        is_enabled=row.is_enabled,
                        config_json=row.config_json,
                    )
            else:
                self.logger.warning(
                    "scheduling.criteriaevaluator.load_criteria_config_fallback",
                    reason="No criteria rows in DB, using defaults",
                )
                for d in _DEFAULT_CRITERIA:
                    config_map[d["n"]] = _CriterionConfig(
                        criterion_number=d["n"],
                        criterion_name=d["name"],
                        criterion_group=d["group"],
                        weight=d["w"],
                        is_hard_constraint=d["hard"],
                        is_enabled=True,
                        config_json=None,
                    )

            # Apply runtime overrides from SchedulingConfig.
            if self._config_overrides and self._config_overrides.criteria_weights:
                for cnum, weight in self._config_overrides.criteria_weights.items():
                    if cnum in config_map:
                        config_map[cnum].weight = weight

            self._criteria_cache = config_map
            self._cache_loaded_at = now
        except Exception as exc:
            self.log_failed("load_criteria_config", error=exc)
            raise
        else:
            self.log_completed(
                "load_criteria_config",
                criteria_count=len(config_map),
            )
            return config_map

    # ------------------------------------------------------------------
    # Scoring internals
    # ------------------------------------------------------------------

    async def _score_all_criteria(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        criteria_config: dict[int, _CriterionConfig],
    ) -> list[CriterionResult]:
        """Collect scores from all registered scorers.

        For each scorer group, delegates to the scorer's
        ``score_assignment`` method. Criteria belonging to groups
        without a registered scorer receive a neutral default score
        (50).

        Returns:
            List of ``CriterionResult`` objects, one per enabled
            criterion.
        """
        results: list[CriterionResult] = []

        # Map criterion groups to their number ranges.
        group_ranges: dict[str, tuple[int, int]] = {
            "geographic": (1, 5),
            "resource": (6, 10),
            "customer_job": (11, 15),
            "capacity_demand": (16, 20),
            "business_rules": (21, 25),
            "predictive": (26, 30),
        }

        for group_name, (start, end) in group_ranges.items():
            scorer = self._scorers.get(group_name)

            if scorer is not None:
                try:
                    group_results = await scorer.score_assignment(
                        job,
                        staff,
                        context,
                        criteria_config,
                    )
                    results.extend(group_results)
                except Exception as exc:
                    self.log_failed(
                        "score_criteria_group",
                        error=exc,
                        group=group_name,
                    )
                    results.extend(
                        self._neutral_results(
                            start,
                            end,
                            criteria_config,
                        ),
                    )
            else:
                results.extend(
                    self._neutral_results(
                        start,
                        end,
                        criteria_config,
                    ),
                )

        return results

    def _neutral_results(
        self,
        start: int,
        end: int,
        criteria_config: dict[int, _CriterionConfig],
    ) -> list[CriterionResult]:
        """Generate neutral (score=50) results for a criteria range.

        Used when a scorer module is not yet registered or fails.
        """
        results: list[CriterionResult] = []
        for n in range(start, end + 1):
            cfg = criteria_config.get(n)
            if cfg and not cfg.is_enabled:
                continue
            results.append(
                CriterionResult(
                    criterion_number=n,
                    criterion_name=(cfg.criterion_name if cfg else f"Criterion {n}"),
                    score=50.0,
                    weight=cfg.weight if cfg else 50,
                    is_hard=(cfg.is_hard_constraint if cfg else False),
                    is_satisfied=True,
                    explanation=("Scorer not available — neutral score applied"),
                ),
            )
        return results

    def _aggregate_scores(
        self,
        criterion_results: list[CriterionResult],
    ) -> float:
        """Aggregate weighted criterion scores into a composite.

        The composite score is the weighted average of all criterion
        scores: ``sum(score_i * weight_i) / sum(weight_i)``.

        Hard-constraint violations impose a heavy penalty: each
        unsatisfied hard constraint subtracts 100 points from the
        composite (clamped to 0 at the floor).

        Args:
            criterion_results: Per-criterion evaluation results.

        Returns:
            Composite score as a float (0-100 range, may be 0 if
            hard constraints are violated).
        """
        if not criterion_results:
            return 0.0

        total_weighted = 0.0
        total_weight = 0

        for cr in criterion_results:
            total_weighted += cr.score * cr.weight
            total_weight += cr.weight

        if total_weight == 0:
            return 0.0

        base_score = total_weighted / total_weight

        # Penalise hard-constraint violations.
        hard_violation_count = sum(
            1 for cr in criterion_results if cr.is_hard and not cr.is_satisfied
        )
        penalty = hard_violation_count * 100.0

        return round(max(0.0, base_score - penalty), 2)

    def _aggregate_criterion_averages(
        self,
    ) -> list[CriterionResult]:
        """Build per-criterion summary results using cached config.

        Produces one ``CriterionResult`` per criterion number using
        the cached config. Actual per-assignment scores are computed
        in ``evaluate_schedule`` via ``evaluate_assignment``; this
        method provides the summary row.

        Returns an empty list if config is not yet loaded.
        """
        if self._criteria_cache is None:
            return []

        results: list[CriterionResult] = []
        for n in range(1, TOTAL_CRITERIA + 1):
            cfg = self._criteria_cache.get(n)
            if cfg is None or not cfg.is_enabled:
                continue
            results.append(
                CriterionResult(
                    criterion_number=n,
                    criterion_name=cfg.criterion_name,
                    score=50.0,
                    weight=cfg.weight,
                    is_hard=cfg.is_hard_constraint,
                    is_satisfied=True,
                    explanation="Aggregate placeholder",
                ),
            )
        return results

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate_cache(self) -> None:
        """Force-clear the in-memory criteria config cache.

        Useful after an admin updates criteria weights at runtime.
        """
        self._criteria_cache = None
        self._cache_loaded_at = 0.0
        self.logger.info(
            "scheduling.criteriaevaluator.cache_invalidated",
        )
