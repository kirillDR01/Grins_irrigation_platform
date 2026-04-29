"""
PredictiveScorer - criteria 26-30 for AI scheduling.

Evaluates predictive and forward-looking signals for job-staff assignments:
  26. Weather forecast impact (soft)
  27. Predicted job complexity (soft)
  28. Lead-to-job conversion timing (soft)
  29. Resource location at shift start (soft)
  30. Cross-job dependency chains (hard constraint)

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import CriterionResult
from grins_platform.services.schedule_constraints import haversine_travel_minutes

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

# Criterion 26 — weather impact
_WEATHER_SEVERE_CODES = {
    "thunderstorm",
    "heavy_rain",
    "snow",
    "ice",
    "freeze",
    "blizzard",
}
_WEATHER_MODERATE_CODES = {"rain", "drizzle", "sleet", "fog", "wind"}

# Criterion 27 — predicted complexity
_COMPLEXITY_LOW = 0.3  # ≤0.3 → no extra time needed
_COMPLEXITY_HIGH = 0.8  # ≥0.8 → significant extra time needed

# Criterion 29 — start location proximity
_START_PROXIMITY_BEST_MINUTES = 5  # score 100 at ≤5 min
_START_PROXIMITY_WORST_MINUTES = 45  # score 0 at ≥45 min


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
# PredictiveScorer
# ---------------------------------------------------------------------------


class PredictiveScorer(LoggerMixin):
    """Score predictive and forward-looking criteria 26-30.

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
        """Score a job-staff assignment for predictive criteria 26-30.

        Args:
            job: The job being evaluated.
            staff: The candidate staff member.
            context: Scheduling context (date, weather, traffic, backlog).
            config: Per-criterion configuration (weights, hard/soft).

        Returns:
            List of ``CriterionResult`` objects for criteria 26-30.
        """
        self.log_started(
            "score_assignment",
            job_id=str(job.id),
            staff_id=str(staff.id),
        )

        results: list[CriterionResult] = []

        try:
            results.append(
                await self._score_weather_forecast_impact(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_predicted_job_complexity(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_lead_conversion_timing(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_resource_start_location(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_cross_job_dependencies(
                    job,
                    staff,
                    context,
                    config,
                ),
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
    # Criterion 26 — Weather forecast impact
    # ------------------------------------------------------------------

    async def _score_weather_forecast_impact(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 26: Weather forecast impact.

        Check 7-day forecast and penalize outdoor jobs on rain/freeze
        days.  Indoor jobs are unaffected.  If weather data is
        unavailable, skip criterion (neutral score 50).

        Uses ``context.weather`` for forecast data and
        ``context.backlog["outdoor_jobs"]`` (set of job ids) to
        determine if a job is outdoor.
        """
        cfg = config.get(26)
        weight = cfg.weight if cfg else 60
        is_hard = cfg.is_hard_constraint if cfg else False

        # Determine if job is outdoor
        is_outdoor = self._is_outdoor_job(job, context)

        # Indoor jobs are unaffected by weather
        if not is_outdoor:
            return CriterionResult(
                criterion_number=26,
                criterion_name="Weather forecast impact",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="Indoor job — weather has no impact. Score 100/100.",
            )

        # No weather data — skip criterion (neutral)
        if context.weather is None:
            return CriterionResult(
                criterion_number=26,
                criterion_name="Weather forecast impact",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Weather data unavailable — neutral score applied for outdoor job."
                ),
            )

        weather_condition = self._get_weather_condition(context)
        precipitation_pct = self._get_precipitation_probability(context)

        # Severe weather — heavy penalty for outdoor jobs
        if weather_condition in _WEATHER_SEVERE_CODES:
            score = 0.0
            is_satisfied = not is_hard
            explanation = (
                f"Outdoor job on severe weather day "
                f"({weather_condition}). "
                f"Score 0/100 — recommend rescheduling or indoor backfill."
            )
        elif weather_condition in _WEATHER_MODERATE_CODES:
            # Moderate weather — partial penalty
            score = 40.0
            is_satisfied = True
            explanation = (
                f"Outdoor job on moderate weather day "
                f"({weather_condition}). "
                f"Score 40/100 — consider rescheduling if possible."
            )
        elif precipitation_pct is not None and precipitation_pct >= 0.7:
            # High precipitation probability even without explicit code
            score = 30.0
            is_satisfied = True
            explanation = (
                f"Outdoor job with {precipitation_pct:.0%} precipitation "
                f"probability. Score 30/100."
            )
        elif precipitation_pct is not None and precipitation_pct >= 0.4:
            score = 65.0
            is_satisfied = True
            explanation = (
                f"Outdoor job with {precipitation_pct:.0%} precipitation "
                f"probability. Score 65/100."
            )
        else:
            # Clear/good weather
            score = 100.0
            is_satisfied = True
            explanation = "Outdoor job on clear weather day. Score 100/100."

        return CriterionResult(
            criterion_number=26,
            criterion_name="Weather forecast impact",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=is_satisfied,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 27 — Predicted job complexity
    # ------------------------------------------------------------------

    async def _score_predicted_job_complexity(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 27: Predicted job complexity.

        Use ``Job.predicted_complexity`` (0.0-1.0) from ML model to
        assess whether the scheduled duration is adequate.  High
        complexity jobs need longer time slots.  Score based on
        whether the allocated duration accounts for complexity.

        Uses ``context.backlog["job_complexity"]`` keyed by job id.
        Neutral 50 if no complexity data.
        """
        cfg = config.get(27)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        complexity = self._get_job_complexity(job, context)

        if complexity is None:
            return CriterionResult(
                criterion_number=27,
                criterion_name="Predicted job complexity",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Complexity prediction unavailable — neutral score applied."
                ),
            )

        # Clamp to 0.0-1.0
        complexity = max(0.0, min(1.0, complexity))

        # Check if allocated duration accounts for complexity
        allocated_minutes = job.duration_minutes
        # High complexity jobs need ~50% more time at complexity=1.0
        required_buffer_factor = 1.0 + (complexity * 0.5)
        base_duration = self._get_base_duration(job, context)

        if base_duration is not None and base_duration > 0:
            required_minutes = base_duration * required_buffer_factor
            if allocated_minutes >= required_minutes:
                score = 100.0
                explanation = (
                    f"Complexity {complexity:.2f} — allocated "
                    f"{allocated_minutes} min ≥ required "
                    f"{required_minutes:.0f} min. Score 100/100."
                )
            else:
                # Penalize proportionally to the shortfall
                shortfall_ratio = (
                    required_minutes - allocated_minutes
                ) / required_minutes
                score = max(0.0, 100.0 - (shortfall_ratio * 100.0))
                explanation = (
                    f"Complexity {complexity:.2f} — allocated "
                    f"{allocated_minutes} min < required "
                    f"{required_minutes:.0f} min "
                    f"(shortfall {shortfall_ratio:.0%}). "
                    f"Score {score:.0f}/100."
                )
        else:
            # No base duration — score based on complexity level alone
            # Low complexity = high score, high complexity = lower score
            # (uncertainty about whether slot is adequate)
            score = 100.0 - (complexity * 40.0)
            explanation = (
                f"Complexity {complexity:.2f} — no base duration available. "
                f"Score {score:.0f}/100 (lower complexity = more confidence)."
            )

        return CriterionResult(
            criterion_number=27,
            criterion_name="Predicted job complexity",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 28 — Lead-to-job conversion timing
    # ------------------------------------------------------------------

    async def _score_lead_conversion_timing(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 28: Lead-to-job conversion timing.

        Identify hot leads from pipeline and reserve tentative
        capacity.  Score higher for jobs that originated from hot
        leads to incentivize scheduling them promptly.

        Uses ``context.backlog["lead_conversion"]`` keyed by job id.
        Neutral 50 if no lead data.
        """
        cfg = config.get(28)
        weight = cfg.weight if cfg else 40
        is_hard = cfg.is_hard_constraint if cfg else False

        lead_data = self._get_lead_conversion_data(job, context)

        if lead_data is None:
            return CriterionResult(
                criterion_number=28,
                criterion_name="Lead-to-job conversion timing",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Lead conversion data unavailable — neutral score applied."
                ),
            )

        is_hot_lead = lead_data.get("is_hot_lead", False)
        lead_score = lead_data.get("lead_score")
        days_since_inquiry = lead_data.get("days_since_inquiry")

        try:
            lead_score_val = float(lead_score) if lead_score is not None else None
            days_val = (
                float(days_since_inquiry) if days_since_inquiry is not None else None
            )
        except (TypeError, ValueError):
            lead_score_val = None
            days_val = None

        if is_hot_lead:
            # Hot lead — high score to incentivize prompt scheduling
            base_score = 90.0
            if days_val is not None and days_val > 7:
                # Aging hot lead — slight urgency boost
                base_score = min(100.0, base_score + (days_val - 7) * 1.0)
            score = min(100.0, base_score)
            explanation = (
                "Hot lead — prompt scheduling recommended. "
                + (f"Inquiry {days_val:.0f} days ago. " if days_val is not None else "")
                + f"Score {score:.0f}/100."
            )
        elif lead_score_val is not None:
            # Score based on lead quality (0-100 scale)
            score = 50.0 + (lead_score_val / 100.0) * 50.0
            explanation = f"Lead score {lead_score_val:.0f}/100. Score {score:.0f}/100."
        else:
            # Standard job (not from lead pipeline)
            score = 50.0
            explanation = "Standard job — no lead pipeline data. Score 50/100."

        return CriterionResult(
            criterion_number=28,
            criterion_name="Lead-to-job conversion timing",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 29 — Resource location at shift start
    # ------------------------------------------------------------------

    async def _score_resource_start_location(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 29: Resource location at shift start.

        Determine home/shop/job-site origin for first-job routing.
        Score based on drive time from the resource's actual start
        location to the first job.

        Uses ``context.backlog["staff_start_locations"]`` keyed by
        staff id for override locations (e.g., if staff starts from
        a job site rather than home).  Falls back to
        ``staff.start_location``.
        """
        cfg = config.get(29)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        # Determine effective start location
        start_location = self._get_staff_start_location(staff, context)

        if start_location is None:
            return CriterionResult(
                criterion_number=29,
                criterion_name="Resource location at shift start",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Staff start location unavailable — neutral score applied."
                ),
            )

        # Calculate drive time from start location to job
        try:
            start_lat = float(start_location.get("latitude", 0))
            start_lon = float(start_location.get("longitude", 0))
            job_lat = float(job.location.latitude)
            job_lon = float(job.location.longitude)
        except (TypeError, ValueError, AttributeError):
            return CriterionResult(
                criterion_number=29,
                criterion_name="Resource location at shift start",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Location coordinates invalid — neutral score applied."),
            )

        drive_minutes = float(
            haversine_travel_minutes(
                start_lat,
                start_lon,
                job_lat,
                job_lon,
            ),
        )

        score = _linear_score(
            drive_minutes,
            _START_PROXIMITY_BEST_MINUTES,
            _START_PROXIMITY_WORST_MINUTES,
        )

        start_type = start_location.get("location_type", "home/shop")
        explanation = (
            f"Drive time from {start_type} to first job: "
            f"{drive_minutes:.0f} min. "
            f"Score {score:.0f}/100 "
            f"(100 at ≤{_START_PROXIMITY_BEST_MINUTES} min, "
            f"0 at ≥{_START_PROXIMITY_WORST_MINUTES} min)."
        )

        return CriterionResult(
            criterion_number=29,
            criterion_name="Resource location at shift start",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 30 — Cross-job dependency chains
    # ------------------------------------------------------------------

    async def _score_cross_job_dependencies(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 30: Cross-job dependency chains.

        Check ``Job.depends_on_job_id`` and ``job_phase`` to enforce
        phase sequencing.  This is a hard constraint: a dependent job
        must not be scheduled before its prerequisite completes.

        Uses ``context.backlog["job_dependencies"]`` for dependency
        data and ``context.backlog["scheduled_job_completions"]``
        for prerequisite completion times.
        """
        cfg = config.get(30)
        weight = cfg.weight if cfg else 80
        is_hard = cfg.is_hard_constraint if cfg else True

        dependency_data = self._get_dependency_data(job, context)

        if dependency_data is None:
            # No dependency data — no constraint to enforce
            return CriterionResult(
                criterion_number=30,
                criterion_name="Cross-job dependency chains",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No dependency constraints for this job. Score 100/100.",
            )

        depends_on_job_id = dependency_data.get("depends_on_job_id")
        job_phase = dependency_data.get("job_phase")
        prerequisite_completed = dependency_data.get("prerequisite_completed", False)
        prerequisite_scheduled_before = dependency_data.get(
            "prerequisite_scheduled_before",
            False,
        )

        if depends_on_job_id is None and job_phase is None:
            # No dependency
            return CriterionResult(
                criterion_number=30,
                criterion_name="Cross-job dependency chains",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No dependency constraints for this job. Score 100/100.",
            )

        # Check if prerequisite is satisfied
        if prerequisite_completed:
            score = 100.0
            is_satisfied = True
            explanation = (
                f"Prerequisite job {depends_on_job_id} already completed. "
                f"Dependency satisfied. Score 100/100."
            )
        elif prerequisite_scheduled_before:
            # Prerequisite is scheduled before this job — dependency will be met
            score = 90.0
            is_satisfied = True
            explanation = (
                f"Prerequisite job {depends_on_job_id} scheduled before "
                f"this job. Dependency will be satisfied. Score 90/100."
            )
        elif depends_on_job_id is not None:
            # Prerequisite not completed and not scheduled before — hard violation
            score = 0.0
            is_satisfied = False
            phase_info = f" (phase {job_phase})" if job_phase is not None else ""
            explanation = (
                f"Dependency violation{phase_info}: prerequisite job "
                f"{depends_on_job_id} not yet completed or scheduled before "
                f"this job. Hard constraint violated. Score 0/100."
            )
        else:
            # Phase constraint without explicit dependency
            score = 70.0
            is_satisfied = True
            explanation = (
                f"Job phase {job_phase} — no explicit prerequisite job. Score 70/100."
            )

        return CriterionResult(
            criterion_number=30,
            criterion_name="Cross-job dependency chains",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=is_satisfied,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _is_outdoor_job(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> bool:
        """Determine if a job is outdoor.

        Checks ``context.backlog["outdoor_jobs"]`` (set or list of
        job ids).  Defaults to ``True`` (outdoor) if no data.
        """
        if context.backlog is None:
            return True  # Default: assume outdoor

        outdoor_jobs = context.backlog.get("outdoor_jobs")
        if outdoor_jobs is None:
            return True  # Default: assume outdoor

        job_id_str = str(job.id)
        if isinstance(outdoor_jobs, (set, list)):
            return job_id_str in {str(j) for j in outdoor_jobs}
        if isinstance(outdoor_jobs, dict):
            val = outdoor_jobs.get(job_id_str)
            if val is not None:
                return bool(val)
        return True

    def _get_weather_condition(
        self,
        context: SchedulingContext,
    ) -> str:
        """Extract weather condition code from context.

        Returns a lowercase string like ``"clear"``, ``"rain"``,
        ``"thunderstorm"``, etc.  Returns ``"clear"`` if unavailable.
        """
        if context.weather is None:
            return "clear"

        condition = context.weather.get("condition")
        if isinstance(condition, str):
            return condition.lower().replace(" ", "_")
        return "clear"

    def _get_precipitation_probability(
        self,
        context: SchedulingContext,
    ) -> float | None:
        """Extract precipitation probability from context (0.0-1.0)."""
        if context.weather is None:
            return None

        prob = context.weather.get("precipitation_probability")
        if prob is not None:
            try:
                return max(0.0, min(1.0, float(prob)))
            except (TypeError, ValueError):
                self.logger.debug(
                    "scheduling.predictivescorer.invalid_precipitation_prob",
                    value=str(prob),
                )
        return None

    def _get_job_complexity(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> float | None:
        """Extract predicted complexity for a job (0.0-1.0).

        Looks for ``context.backlog["job_complexity"]`` keyed by
        job id.  Returns a float or ``None``.
        """
        if context.backlog is None:
            return None

        complexity_map = context.backlog.get("job_complexity")
        if not isinstance(complexity_map, dict):
            return None

        value = complexity_map.get(str(job.id))
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                self.logger.debug(
                    "scheduling.predictivescorer.invalid_complexity",
                    job_id=str(job.id),
                    value=str(value),
                )
        return None

    def _get_base_duration(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> float | None:
        """Extract base (template) duration for a job in minutes.

        Looks for ``context.backlog["base_durations"]`` keyed by
        job id.  Falls back to ``job.duration_minutes``.
        """
        if context.backlog is not None:
            duration_map = context.backlog.get("base_durations")
            if isinstance(duration_map, dict):
                value = duration_map.get(str(job.id))
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        self.logger.debug(
                            "scheduling.predictivescorer.invalid_base_duration",
                            job_id=str(job.id),
                            value=str(value),
                        )

        # Fall back to job's own duration
        return float(job.duration_minutes) if job.duration_minutes > 0 else None

    def _get_lead_conversion_data(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract lead conversion data for a job.

        Looks for ``context.backlog["lead_conversion"]`` keyed by
        job id.  Returns a dict with keys: ``is_hot_lead``,
        ``lead_score``, ``days_since_inquiry``.
        """
        if context.backlog is None:
            return None

        lead_map = context.backlog.get("lead_conversion")
        if not isinstance(lead_map, dict):
            return None

        data = lead_map.get(str(job.id))
        if isinstance(data, dict) and data:
            return data
        return None

    def _get_staff_start_location(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract effective start location for a staff member.

        Looks for ``context.backlog["staff_start_locations"]`` keyed
        by staff id.  Falls back to ``staff.start_location``.
        Returns a dict with keys: ``latitude``, ``longitude``,
        ``location_type``.
        """
        if context.backlog is not None:
            location_map = context.backlog.get("staff_start_locations")
            if isinstance(location_map, dict):
                override = location_map.get(str(staff.id))
                if isinstance(override, dict) and override:
                    return override

        # Fall back to staff's default start location
        try:
            return {
                "latitude": float(staff.start_location.latitude),
                "longitude": float(staff.start_location.longitude),
                "location_type": "home/shop",
            }
        except (AttributeError, TypeError, ValueError):
            return None

    def _get_dependency_data(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract dependency chain data for a job.

        Looks for ``context.backlog["job_dependencies"]`` keyed by
        job id.  Returns a dict with keys: ``depends_on_job_id``,
        ``job_phase``, ``prerequisite_completed``,
        ``prerequisite_scheduled_before``.
        """
        if context.backlog is None:
            return None

        dep_map = context.backlog.get("job_dependencies")
        if not isinstance(dep_map, dict):
            return None

        data = dep_map.get(str(job.id))
        if isinstance(data, dict) and data:
            return data
        return None
