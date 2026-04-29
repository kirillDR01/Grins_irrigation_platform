"""
ResourceScorer - criteria 6-10 for AI scheduling.

Evaluates resource capability and capacity constraints for job-staff assignments:
  6. Skill/certification match (hard constraint)
  7. Equipment on truck (hard constraint)
  8. Resource availability windows (hard constraint)
  9. Workload balance (soft)
  10. Performance history (soft)

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import CriterionResult

if TYPE_CHECKING:
    from grins_platform.schemas.ai_scheduling import SchedulingContext
    from grins_platform.services.ai.scheduling.criteria_evaluator import (
        _CriterionConfig,
    )
    from grins_platform.services.schedule_domain import (
        ScheduleJob,
        ScheduleStaff,
    )


# ---------------------------------------------------------------------------
# Scoring thresholds
# ---------------------------------------------------------------------------

# Criterion 9 — workload balance
_WORKLOAD_BEST_STDDEV = 0.0  # score 100 at perfect balance
_WORKLOAD_WORST_STDDEV = 120.0  # score 0 at ≥120 min std-dev

# Criterion 10 — performance history weights
_PERF_WEIGHT_SCORE = 0.50
_PERF_WEIGHT_CALLBACK = 0.25
_PERF_WEIGHT_SATISFACTION = 0.25


def _linear_score(
    value: float,
    best: float,
    worst: float,
) -> float:
    """Linearly interpolate a score between 100 (best) and 0 (worst).

    Values at or below *best* yield 100; values at or above *worst*
    yield 0.
    """
    if value <= best:
        return 100.0
    if value >= worst:
        return 0.0
    return 100.0 * (1.0 - (value - best) / (worst - best))


# ---------------------------------------------------------------------------
# ResourceScorer
# ---------------------------------------------------------------------------


class ResourceScorer(LoggerMixin):
    """Score resource capability / capacity criteria 6-10.

    Implements the ``ScorerProtocol`` expected by ``CriteriaEvaluator``.
    """

    DOMAIN = "scheduling"

    # ------------------------------------------------------------------
    # ScorerProtocol entry point
    # ------------------------------------------------------------------

    async def score_assignment(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> list[CriterionResult]:
        """Score a job-staff assignment for resource criteria 6-10.

        Args:
            job: The job being evaluated.
            staff: The candidate staff member.
            context: Scheduling context (date, weather, traffic, backlog).
            config: Per-criterion configuration (weights, hard/soft).

        Returns:
            List of ``CriterionResult`` objects for criteria 6-10.
        """
        self.log_started(
            "score_assignment",
            job_id=str(job.id),
            staff_id=str(staff.id),
        )

        results: list[CriterionResult] = []

        try:
            results.append(
                await self._score_skill_certification(job, staff, context, config),
            )
            results.append(
                await self._score_equipment_on_truck(job, staff, context, config),
            )
            results.append(
                await self._score_availability_windows(job, staff, context, config),
            )
            results.append(
                await self._score_workload_balance(job, staff, context, config),
            )
            results.append(
                await self._score_performance_history(job, staff, context, config),
            )
        except Exception as exc:
            self.log_failed(
                "score_assignment",
                error=exc,
                job_id=str(job.id),
                staff_id=str(staff.id),
            )
            raise
        else:
            self.log_completed(
                "score_assignment",
                job_id=str(job.id),
                staff_id=str(staff.id),
                criteria_count=len(results),
            )

        return results

    # ------------------------------------------------------------------
    # Criterion 6 — Skill/certification match (HARD)
    # ------------------------------------------------------------------

    async def _score_skill_certification(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 6: Skill/certification match.

        Verify job's required skill tags against resource's
        certifications.  Uses ``staff.assigned_equipment`` as a proxy
        for skill tags alongside certification data from context.

        Score 100 if all required skills matched, 0 if any missing.
        ``is_satisfied=False`` if missing a required certification.
        This is a **hard constraint**.
        """
        cfg = config.get(6)
        weight = cfg.weight if cfg else 100
        is_hard = cfg.is_hard_constraint if cfg else True  # default hard

        # Gather required skills from the job
        required_skills = self._get_required_skills(job, context)

        # Gather staff certifications from context
        staff_certs = self._get_staff_certifications(staff, context)

        # No required skills — fully satisfied
        if not required_skills:
            return CriterionResult(
                criterion_number=6,
                criterion_name="Skill/certification match",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No specific skill requirements for this job.",
            )

        # Check for missing certifications
        missing = [s for s in required_skills if s not in staff_certs]

        if missing:
            return CriterionResult(
                criterion_number=6,
                criterion_name="Skill/certification match",
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(
                    f"Missing required certifications: {', '.join(missing)}. "
                    f"Staff has: {', '.join(staff_certs) if staff_certs else 'none'}."
                ),
            )

        return CriterionResult(
            criterion_number=6,
            criterion_name="Skill/certification match",
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"All {len(required_skills)} required skills matched: "
                f"{', '.join(required_skills)}."
            ),
        )

    # ------------------------------------------------------------------
    # Criterion 7 — Equipment on truck (HARD)
    # ------------------------------------------------------------------

    async def _score_equipment_on_truck(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 7: Equipment on truck.

        Verify resource's truck carries required equipment.  Uses
        ``staff.assigned_equipment`` and ``resource_truck_inventory``
        data from context.

        Score 100 if all equipment available, 0 if any missing.
        ``is_satisfied=False`` if missing required equipment.
        This is a **hard constraint**.
        """
        cfg = config.get(7)
        weight = cfg.weight if cfg else 100
        is_hard = cfg.is_hard_constraint if cfg else True  # default hard

        required_equipment = job.equipment_required

        # No equipment requirements — fully satisfied
        if not required_equipment:
            return CriterionResult(
                criterion_number=7,
                criterion_name="Equipment on truck",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No specific equipment required for this job.",
            )

        # Gather available equipment from staff + truck inventory
        available_equipment = self._get_available_equipment(staff, context)

        # Check for missing equipment
        missing = [e for e in required_equipment if e not in available_equipment]

        if missing:
            return CriterionResult(
                criterion_number=7,
                criterion_name="Equipment on truck",
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(
                    f"Missing required equipment: "
                    f"{', '.join(missing)}. "
                    f"Available: "
                    f"{', '.join(available_equipment) or 'none'}."
                ),
            )

        return CriterionResult(
            criterion_number=7,
            criterion_name="Equipment on truck",
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"All {len(required_equipment)} required equipment items "
                f"available on truck."
            ),
        )

    # ------------------------------------------------------------------
    # Criterion 8 — Resource availability windows (HARD)
    # ------------------------------------------------------------------

    async def _score_availability_windows(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 8: Resource availability windows.

        Check shift start/end, PTO, training blocks from
        ``StaffAvailability``.  Uses context to get availability data.

        Score 100 if job fits within availability, 0 if outside.
        ``is_satisfied=False`` if scheduled outside available hours.
        This is a **hard constraint**.
        """
        cfg = config.get(8)
        weight = cfg.weight if cfg else 100
        is_hard = cfg.is_hard_constraint if cfg else True  # default hard

        availability = self._get_staff_availability(staff, context)

        # No availability data — use staff defaults from ScheduleStaff
        if availability is None:
            return self._check_default_availability(
                job,
                staff,
                weight,
                is_hard,
            )

        # Staff explicitly marked unavailable (PTO, training, etc.)
        if not availability.get("is_available", True):
            reason = availability.get("notes", "unavailable")
            return CriterionResult(
                criterion_number=8,
                criterion_name="Resource availability windows",
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(f"Staff is unavailable on this date: {reason}."),
            )

        # Check if job's preferred time fits within the availability window
        shift_start = availability.get("start_time")
        shift_end = availability.get("end_time")

        if shift_start is not None and shift_end is not None:
            job_start = job.preferred_time_start

            if job_start is not None and (
                job_start < shift_start or job_start >= shift_end
            ):
                start_fmt = (
                    shift_start.strftime("%H:%M")
                    if hasattr(shift_start, "strftime")
                    else str(shift_start)
                )
                end_fmt = (
                    shift_end.strftime("%H:%M")
                    if hasattr(shift_end, "strftime")
                    else str(shift_end)
                )
                job_fmt = (
                    job_start.strftime("%H:%M")
                    if hasattr(job_start, "strftime")
                    else str(job_start)
                )
                return CriterionResult(
                    criterion_number=8,
                    criterion_name="Resource availability windows",
                    score=0.0,
                    weight=weight,
                    is_hard=is_hard,
                    is_satisfied=False,
                    explanation=(
                        f"Job start {job_fmt} is outside staff shift "
                        f"{start_fmt}-{end_fmt}."
                    ),
                )

        return CriterionResult(
            criterion_number=8,
            criterion_name="Resource availability windows",
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation="Job fits within staff availability window.",
        )

    # ------------------------------------------------------------------
    # Criterion 9 — Workload balance (soft)
    # ------------------------------------------------------------------

    async def _score_workload_balance(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 9: Workload balance.

        Calculate standard deviation of job-hours across resources.
        Uses context to get all resources' current workloads.

        Score 100 if adding this job keeps workload balanced,
        decreasing as imbalance grows.
        """
        cfg = config.get(9)
        weight = cfg.weight if cfg else 60
        is_hard = cfg.is_hard_constraint if cfg else False

        workloads = self._get_resource_workloads(context)

        # No workload data — neutral score
        if not workloads:
            return CriterionResult(
                criterion_number=9,
                criterion_name="Workload balance",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Workload data unavailable — neutral score applied."),
            )

        # Simulate adding this job to the staff's workload
        staff_key = str(staff.id)
        simulated = dict(workloads)
        simulated[staff_key] = simulated.get(staff_key, 0.0) + job.duration_minutes

        # Calculate standard deviation of workloads
        values = list(simulated.values())
        if len(values) < 2:
            # Only one resource — perfect balance by definition
            return CriterionResult(
                criterion_number=9,
                criterion_name="Workload balance",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="Single resource — workload balance is trivial.",
            )

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        stddev = math.sqrt(variance)

        score = _linear_score(stddev, _WORKLOAD_BEST_STDDEV, _WORKLOAD_WORST_STDDEV)

        explanation = (
            f"Workload std-dev {stddev:.0f} min across {len(values)} resources "
            f"(after adding {job.duration_minutes} min to this resource). "
            f"Score {score:.0f}/100 "
            f"(100 at {_WORKLOAD_BEST_STDDEV:.0f} min, "
            f"0 at ≥{_WORKLOAD_WORST_STDDEV:.0f} min)."
        )

        return CriterionResult(
            criterion_number=9,
            criterion_name="Workload balance",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 10 — Performance history (soft)
    # ------------------------------------------------------------------

    async def _score_performance_history(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 10: Performance history.

        Score based on ``staff.performance_score``,
        ``callback_rate``, ``avg_satisfaction``.  Match
        high-complexity jobs to top performers.

        Score = weighted average of performance metrics (0-100).
        """
        cfg = config.get(10)
        weight = cfg.weight if cfg else 40
        is_hard = cfg.is_hard_constraint if cfg else False

        perf_data = self._get_performance_data(staff, context)

        # No performance data — neutral score
        if perf_data is None:
            return CriterionResult(
                criterion_number=10,
                criterion_name="Performance history",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Performance data unavailable — neutral score applied."),
            )

        perf_score = perf_data.get("performance_score", 50.0)
        callback_rate = perf_data.get("callback_rate", 0.0)
        avg_satisfaction = perf_data.get("avg_satisfaction", 50.0)

        # Normalize callback_rate: lower is better (0% = 100 score,
        # 20%+ = 0 score).  Invert so it contributes positively.
        callback_score = max(0.0, 100.0 - (callback_rate * 500.0))

        # Weighted average of the three metrics
        composite = (
            _PERF_WEIGHT_SCORE * perf_score
            + _PERF_WEIGHT_CALLBACK * callback_score
            + _PERF_WEIGHT_SATISFACTION * avg_satisfaction
        )

        # Clamp to 0-100
        composite = max(0.0, min(100.0, composite))

        # Boost score for high-complexity jobs matched to top performers
        job_complexity = self._get_job_complexity(job, context)
        if job_complexity is not None and job_complexity > 0.7 and composite >= 80.0:
            # Top performer on complex job — small bonus (capped at 100)
            composite = min(100.0, composite + 5.0)

        explanation = (
            f"Performance score {perf_score:.0f}, "
            f"callback rate {callback_rate:.1%}, "
            f"satisfaction {avg_satisfaction:.0f}. "
            f"Composite {composite:.0f}/100."
        )

        if job_complexity is not None and job_complexity > 0.7:
            explanation += f" High-complexity job ({job_complexity:.2f}) " + (
                "matched to top performer."
                if composite >= 80.0
                else "may benefit from a stronger performer."
            )

        return CriterionResult(
            criterion_number=10,
            criterion_name="Performance history",
            score=round(composite, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _get_required_skills(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> list[str]:
        """Extract required skill tags for a job.

        Looks for ``context.backlog["required_skills"]`` keyed by job
        id, or derives from ``job.service_type`` and
        ``job.equipment_required``.
        """
        # Try context first
        if context.backlog is not None:
            skills_map: dict[str, Any] = context.backlog.get(
                "required_skills",
                {},
            )
            if isinstance(skills_map, dict):
                job_skills = skills_map.get(str(job.id))
                if isinstance(job_skills, list) and job_skills:
                    return [str(s) for s in job_skills]

        # Derive from service_type and equipment
        derived: list[str] = []
        if job.service_type:
            derived.append(job.service_type)
        if job.equipment_required:
            derived.extend(job.equipment_required)
        return derived

    def _get_staff_certifications(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> set[str]:
        """Gather staff certifications from context and staff data.

        Looks for ``context.backlog["staff_certifications"]`` keyed by
        staff id.  Falls back to ``staff.assigned_equipment`` as a
        proxy for capabilities.
        """
        certs: set[str] = set()

        # From context
        if context.backlog is not None:
            cert_map: dict[str, Any] = context.backlog.get(
                "staff_certifications",
                {},
            )
            if isinstance(cert_map, dict):
                staff_certs = cert_map.get(str(staff.id))
                if isinstance(staff_certs, list):
                    certs.update(str(c) for c in staff_certs)

        # From staff's assigned equipment (proxy for capabilities)
        if staff.assigned_equipment:
            certs.update(staff.assigned_equipment)

        return certs

    def _get_available_equipment(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> set[str]:
        """Gather available equipment from staff and truck inventory.

        Combines ``staff.assigned_equipment`` with
        ``context.backlog["resource_truck_inventory"]`` keyed by
        staff id.
        """
        equipment: set[str] = set()

        # From staff's assigned equipment
        if staff.assigned_equipment:
            equipment.update(staff.assigned_equipment)

        # From truck inventory in context
        if context.backlog is not None:
            inventory: dict[str, Any] = context.backlog.get(
                "resource_truck_inventory",
                {},
            )
            if isinstance(inventory, dict):
                staff_inventory = inventory.get(str(staff.id))
                if isinstance(staff_inventory, list):
                    for item in staff_inventory:
                        if isinstance(item, dict):
                            name = item.get("part_name")
                            qty = item.get("quantity", 0)
                            if name and qty > 0:
                                equipment.add(str(name))
                        elif isinstance(item, str):
                            equipment.add(item)

        return equipment

    def _get_staff_availability(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract staff availability data from context.

        Looks for ``context.backlog["staff_availability"]`` keyed by
        staff id.  Returns a dict with keys: ``is_available``,
        ``start_time``, ``end_time``, ``notes``.
        """
        if context.backlog is None:
            return None

        avail_map = context.backlog.get("staff_availability")
        if not isinstance(avail_map, dict):
            return None

        avail = avail_map.get(str(staff.id))
        if isinstance(avail, dict) and avail:
            return avail
        return None

    def _check_default_availability(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        weight: int,
        is_hard: bool,
    ) -> CriterionResult:
        """Check availability using ScheduleStaff defaults.

        Falls back to ``staff.availability_start`` and
        ``staff.availability_end`` when context data is unavailable.
        """
        job_start = job.preferred_time_start

        if job_start is not None and (
            job_start < staff.availability_start or job_start >= staff.availability_end
        ):
            start_fmt = staff.availability_start.strftime("%H:%M")
            end_fmt = staff.availability_end.strftime("%H:%M")
            job_fmt = job_start.strftime("%H:%M")
            return CriterionResult(
                criterion_number=8,
                criterion_name="Resource availability windows",
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(
                    f"Job start {job_fmt} is outside staff default "
                    f"shift {start_fmt}-{end_fmt}."
                ),
            )

        return CriterionResult(
            criterion_number=8,
            criterion_name="Resource availability windows",
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                "Job fits within staff default availability window "
                f"({staff.availability_start.strftime('%H:%M')}-"
                f"{staff.availability_end.strftime('%H:%M')})."
            ),
        )

    def _get_resource_workloads(
        self,
        context: SchedulingContext,
    ) -> dict[str, float] | None:
        """Extract resource workload data from context.

        Looks for ``context.backlog["resource_workloads"]`` — a dict
        mapping staff id strings to total assigned minutes.
        """
        if context.backlog is None:
            return None

        workloads = context.backlog.get("resource_workloads")
        if isinstance(workloads, dict) and workloads:
            return {str(k): float(v) for k, v in workloads.items()}
        return None

    def _get_performance_data(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> dict[str, float] | None:
        """Extract performance metrics for a staff member.

        Looks for ``context.backlog["staff_performance"]`` keyed by
        staff id.  Returns a dict with keys:
        ``performance_score``, ``callback_rate``,
        ``avg_satisfaction``.
        """
        if context.backlog is not None:
            perf_map = context.backlog.get("staff_performance")
            if isinstance(perf_map, dict):
                perf = perf_map.get(str(staff.id))
                if isinstance(perf, dict) and perf:
                    return {str(k): float(v) for k, v in perf.items()}

        return None

    def _get_job_complexity(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> float | None:
        """Extract predicted job complexity from context.

        Looks for ``context.backlog["job_complexity"]`` keyed by job
        id.  Returns a float 0.0-1.0 or ``None``.
        """
        if context.backlog is None:
            return None

        complexity_map = context.backlog.get("job_complexity")
        if isinstance(complexity_map, dict):
            value = complexity_map.get(str(job.id))
            if value is not None:
                try:
                    return max(0.0, min(1.0, float(value)))
                except (TypeError, ValueError):
                    return None
        return None
