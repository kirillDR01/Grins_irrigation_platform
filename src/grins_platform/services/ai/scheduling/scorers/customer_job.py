"""
CustomerJobScorer - criteria 11-15 for AI scheduling.

Evaluates customer preferences and job attributes for job-staff assignments:
  11. Customer time-window preferences (soft/hard depending on config)
  12. Job type duration estimates (soft)
  13. Job priority level (soft)
  14. Customer lifetime value (CLV) (soft)
  15. Customer-resource relationship history (soft)

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

from datetime import datetime, time
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
# Scoring constants
# ---------------------------------------------------------------------------

# Criterion 11 — time-window preferences
_TIME_WINDOW_EXACT_SCORE = 100  # within preferred window
_TIME_WINDOW_CLOSE_MINUTES = 30  # "close" threshold
_TIME_WINDOW_FAR_MINUTES = 120  # "far" threshold

# Criterion 12 — duration estimates
_DURATION_COMPLEXITY_MULTIPLIER_LOW = 0.8  # complexity < 0.3
_DURATION_COMPLEXITY_MULTIPLIER_HIGH = 1.5  # complexity > 0.7

# Criterion 13 — priority level scores
_PRIORITY_SCORES: dict[str, float] = {
    "emergency": 100.0,
    "vip": 80.0,
    "standard": 60.0,
    "flexible": 40.0,
}
# Numeric priority mapping (from Job model: 0=normal, 1=high, 2=urgent, 3=emergency)
_NUMERIC_PRIORITY_SCORES: dict[int, float] = {
    3: 100.0,  # emergency
    2: 80.0,  # urgent / VIP
    1: 60.0,  # high / standard
    0: 40.0,  # normal / flexible
}

# Criterion 14 — CLV percentile thresholds
_CLV_HIGH_PERCENTILE = 80  # top 20% → score 100
_CLV_LOW_PERCENTILE = 20  # bottom 20% → score 20

# Criterion 15 — relationship history
_RELATIONSHIP_PREFERRED_SCORE = 100.0
_RELATIONSHIP_FIVE_STAR_SCORE = 80.0
_RELATIONSHIP_NEUTRAL_SCORE = 50.0


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


def _try_parse_time(value: str, fmt: str) -> time | None:
    """Attempt to parse a time string with the given format.

    Returns the parsed ``time`` or ``None`` on failure.
    """
    try:
        return datetime.strptime(value, fmt).time()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# CustomerJobScorer
# ---------------------------------------------------------------------------


class CustomerJobScorer(LoggerMixin):
    """Score customer/job attribute criteria 11-15.

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
        """Score a job-staff assignment for customer/job criteria 11-15.

        Args:
            job: The job being evaluated.
            staff: The candidate staff member.
            context: Scheduling context (date, weather, traffic, backlog).
            config: Per-criterion configuration (weights, hard/soft).

        Returns:
            List of ``CriterionResult`` objects for criteria 11-15.
        """
        self.log_started(
            "score_assignment",
            job_id=str(job.id),
            staff_id=str(staff.id),
        )

        results: list[CriterionResult] = []

        try:
            results.append(
                await self._score_time_window_preferences(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_duration_estimates(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_priority_level(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_customer_lifetime_value(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_relationship_history(
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
    # Criterion 11 — Customer time-window preferences
    # ------------------------------------------------------------------

    async def _score_time_window_preferences(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 11: Customer time-window preferences.

        Check customer-requested AM/PM or specific-hour windows.
        If ``time_window_is_hard=True``, treat as a hard constraint
        (score 0, ``is_satisfied=False`` if violated).  If soft,
        score 100 if within preference, 50-80 if close, lower if
        far off.

        Uses ``context.backlog["customer_preferences"]`` keyed by
        job id for time window data.
        """
        cfg = config.get(11)
        weight = cfg.weight if cfg else 70
        # Default to soft; may be overridden by customer preference data
        is_hard = cfg.is_hard_constraint if cfg else False

        prefs = self._get_customer_preferences(job, context)

        # No preference data — neutral score
        if not prefs:
            return CriterionResult(
                criterion_number=11,
                criterion_name="Customer time-window preferences",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "No customer time-window preference data available "
                    "— neutral score applied."
                ),
            )

        # Extract preference details
        pref_start = self._parse_time(prefs.get("preferred_start"))
        pref_end = self._parse_time(prefs.get("preferred_end"))
        time_window_is_hard = bool(prefs.get("time_window_is_hard", False))

        # Override hard constraint flag from customer preference
        if time_window_is_hard:
            is_hard = True

        # No parseable time window — neutral score
        if pref_start is None or pref_end is None:
            return CriterionResult(
                criterion_number=11,
                criterion_name="Customer time-window preferences",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Customer preference data incomplete — neutral score applied."
                ),
            )

        # Check job's scheduled/preferred time against the window
        job_time = job.preferred_time_start

        if job_time is None:
            return CriterionResult(
                criterion_number=11,
                criterion_name="Customer time-window preferences",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Customer prefers "
                    f"{pref_start.strftime('%H:%M')}-"
                    f"{pref_end.strftime('%H:%M')}. "
                    f"No job time set yet — neutral score applied."
                ),
            )

        # Calculate how far the job time is from the preferred window
        job_minutes = job_time.hour * 60 + job_time.minute
        pref_start_minutes = pref_start.hour * 60 + pref_start.minute
        pref_end_minutes = pref_end.hour * 60 + pref_end.minute

        # Within the preferred window
        if pref_start_minutes <= job_minutes <= pref_end_minutes:
            return CriterionResult(
                criterion_number=11,
                criterion_name="Customer time-window preferences",
                score=float(_TIME_WINDOW_EXACT_SCORE),
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Job time {job_time.strftime('%H:%M')} is within "
                    f"customer preference "
                    f"{pref_start.strftime('%H:%M')}-"
                    f"{pref_end.strftime('%H:%M')}. "
                    f"Score {_TIME_WINDOW_EXACT_SCORE}/100."
                ),
            )

        # Calculate distance from the nearest edge of the window
        if job_minutes < pref_start_minutes:
            distance_minutes = pref_start_minutes - job_minutes
        else:
            distance_minutes = job_minutes - pref_end_minutes

        # Hard constraint violation
        if time_window_is_hard:
            return CriterionResult(
                criterion_number=11,
                criterion_name="Customer time-window preferences",
                score=0.0,
                weight=weight,
                is_hard=True,
                is_satisfied=False,
                explanation=(
                    f"HARD CONSTRAINT VIOLATION: Job time "
                    f"{job_time.strftime('%H:%M')} is "
                    f"{distance_minutes} min outside customer's "
                    f"required window "
                    f"{pref_start.strftime('%H:%M')}-"
                    f"{pref_end.strftime('%H:%M')}."
                ),
            )

        # Soft constraint — score based on distance
        score = _linear_score(
            float(distance_minutes),
            float(_TIME_WINDOW_CLOSE_MINUTES),
            float(_TIME_WINDOW_FAR_MINUTES),
        )
        # Ensure minimum score of 50 for "close" misses
        if distance_minutes <= _TIME_WINDOW_CLOSE_MINUTES:
            score = max(score, 80.0)
        elif distance_minutes <= _TIME_WINDOW_FAR_MINUTES:
            score = max(score, 50.0)

        return CriterionResult(
            criterion_number=11,
            criterion_name="Customer time-window preferences",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Job time {job_time.strftime('%H:%M')} is "
                f"{distance_minutes} min outside preferred window "
                f"{pref_start.strftime('%H:%M')}-"
                f"{pref_end.strftime('%H:%M')}. "
                f"Score {score:.0f}/100."
            ),
        )

    # ------------------------------------------------------------------
    # Criterion 12 — Job type duration estimates
    # ------------------------------------------------------------------

    async def _score_duration_estimates(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 12: Job type duration estimates.

        Use the job's template default duration adjusted by
        ``predicted_complexity`` from context.  Score based on how
        well the allocated time slot matches the estimated duration.

        Score 100 if slot >= estimated duration, decreasing if the
        slot is too short.
        """
        cfg = config.get(12)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        # Get predicted complexity from context
        predicted_complexity = self._get_predicted_complexity(job, context)

        # Base duration from the job template
        base_duration = float(job.duration_minutes)

        # Adjust duration by complexity
        if predicted_complexity is not None:
            if predicted_complexity > 0.7:
                multiplier = _DURATION_COMPLEXITY_MULTIPLIER_HIGH
                estimated_duration = base_duration * multiplier
            elif predicted_complexity < 0.3:
                estimated_duration = base_duration * _DURATION_COMPLEXITY_MULTIPLIER_LOW
            else:
                # Linear interpolation between low and high multipliers
                t = (predicted_complexity - 0.3) / 0.4
                multiplier = _DURATION_COMPLEXITY_MULTIPLIER_LOW + t * (
                    _DURATION_COMPLEXITY_MULTIPLIER_HIGH
                    - _DURATION_COMPLEXITY_MULTIPLIER_LOW
                )
                estimated_duration = base_duration * multiplier
        else:
            estimated_duration = base_duration

        # The allocated slot is the job's duration_minutes (template default)
        allocated_slot = float(job.duration_minutes)

        # Score: 100 if slot >= estimated, decreasing if too short
        if allocated_slot >= estimated_duration:
            score = 100.0
            fit_description = "adequate"
        else:
            # How much of the estimated duration is covered
            coverage_ratio = allocated_slot / estimated_duration
            score = max(0.0, coverage_ratio * 100.0)
            fit_description = "insufficient"

        complexity_note = ""
        if predicted_complexity is not None:
            complexity_note = (
                f" Predicted complexity {predicted_complexity:.2f} "
                f"adjusts estimate to {estimated_duration:.0f} min."
            )

        explanation = (
            f"Base duration {base_duration:.0f} min.{complexity_note} "
            f"Allocated slot {allocated_slot:.0f} min is {fit_description}. "
            f"Score {score:.0f}/100."
        )

        return CriterionResult(
            criterion_number=12,
            criterion_name="Job type duration estimates",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 13 — Job priority level
    # ------------------------------------------------------------------

    async def _score_priority_level(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 13: Job priority level.

        Emergency > VIP > standard > flexible ordering.
        Score 100 for emergency, 80 for VIP, 60 for standard,
        40 for flexible.

        Uses ``job.priority`` (numeric) or context data for
        string-based priority labels.
        """
        cfg = config.get(13)
        weight = cfg.weight if cfg else 90
        is_hard = cfg.is_hard_constraint if cfg else False

        # Try string-based priority from context first
        priority_label = self._get_priority_label(job, context)

        if priority_label is not None:
            label_lower = priority_label.lower()
            score = _PRIORITY_SCORES.get(label_lower, 60.0)
            explanation = (
                f"Job priority '{priority_label}'. "
                f"Score {score:.0f}/100 "
                f"(emergency=100, VIP=80, standard=60, flexible=40)."
            )
        else:
            # Fall back to numeric priority from ScheduleJob
            numeric_priority = job.priority
            score = _NUMERIC_PRIORITY_SCORES.get(numeric_priority, 60.0)
            priority_name = {
                3: "emergency",
                2: "urgent/VIP",
                1: "high/standard",
                0: "normal/flexible",
            }.get(numeric_priority, f"level {numeric_priority}")
            explanation = (
                f"Job numeric priority {numeric_priority} "
                f"({priority_name}). "
                f"Score {score:.0f}/100 "
                f"(3=100, 2=80, 1=60, 0=40)."
            )

        return CriterionResult(
            criterion_number=13,
            criterion_name="Job priority level",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 14 — Customer lifetime value (CLV)
    # ------------------------------------------------------------------

    async def _score_customer_lifetime_value(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 14: Customer lifetime value (CLV).

        Use ``context.backlog["customer_clv"]`` keyed by job id.
        Score proportional to CLV percentile (high CLV = higher
        score).  Used for tie-breaking during high-demand periods.
        """
        cfg = config.get(14)
        weight = cfg.weight if cfg else 40
        is_hard = cfg.is_hard_constraint if cfg else False

        clv_data = self._get_customer_clv(job, context)

        # No CLV data — neutral score
        if clv_data is None:
            return CriterionResult(
                criterion_number=14,
                criterion_name="Customer lifetime value",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Customer CLV data unavailable — neutral score applied."),
            )

        clv_score = clv_data.get("clv_score")
        clv_percentile = clv_data.get("clv_percentile")

        # If we have a percentile, use it directly
        if clv_percentile is not None:
            try:
                percentile = float(clv_percentile)
                # Map percentile (0-100) to score (20-100)
                score = 20.0 + (percentile / 100.0) * 80.0
                explanation = (
                    f"Customer CLV percentile {percentile:.0f}%. "
                    f"Score {score:.0f}/100 "
                    f"(top 20% → 100, bottom 20% → 36)."
                )
            except (TypeError, ValueError):
                score = 50.0
                explanation = (
                    "Customer CLV percentile data invalid — neutral score applied."
                )
        elif clv_score is not None:
            # Use raw CLV score — normalize to 0-100 range
            try:
                raw_score = float(clv_score)
                # Clamp to 0-100 range
                score = max(0.0, min(100.0, raw_score))
                explanation = (
                    f"Customer CLV score {raw_score:.0f}. Score {score:.0f}/100."
                )
            except (TypeError, ValueError):
                score = 50.0
                explanation = "Customer CLV score data invalid — neutral score applied."
        else:
            score = 50.0
            explanation = "Customer CLV data incomplete — neutral score applied."

        return CriterionResult(
            criterion_number=14,
            criterion_name="Customer lifetime value",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 15 — Customer-resource relationship history
    # ------------------------------------------------------------------

    async def _score_relationship_history(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 15: Customer-resource relationship history.

        Prefer pairings where customer rated resource 5 stars or
        requested by name.

        Check ``context.backlog["preferred_resource"]`` for explicit
        preferences and ``context.backlog["customer_resource_history"]``
        for past ratings.

        Score 100 if preferred match, 80 if 5-star history,
        50 neutral.
        """
        cfg = config.get(15)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        # Check for explicit preferred resource match
        preferred_resource_id = self._get_preferred_resource(job, context)

        if preferred_resource_id is not None and str(preferred_resource_id) == str(
            staff.id,
        ):
            return CriterionResult(
                criterion_number=15,
                criterion_name="Customer-resource relationship",
                score=_RELATIONSHIP_PREFERRED_SCORE,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Customer explicitly requested this resource. "
                    f"Score {_RELATIONSHIP_PREFERRED_SCORE:.0f}/100."
                ),
            )

        # Check past rating history
        history = self._get_customer_resource_history(job, staff, context)

        if history is not None:
            avg_rating = history.get("avg_rating")
            if avg_rating is not None:
                try:
                    rating = float(avg_rating)
                    if rating >= 5.0:
                        return CriterionResult(
                            criterion_number=15,
                            criterion_name="Customer-resource relationship",
                            score=_RELATIONSHIP_FIVE_STAR_SCORE,
                            weight=weight,
                            is_hard=is_hard,
                            is_satisfied=True,
                            explanation=(
                                f"Customer rated this resource "
                                f"{rating:.1f}/5 stars. "
                                f"Score "
                                f"{_RELATIONSHIP_FIVE_STAR_SCORE:.0f}/100."
                            ),
                        )
                    if rating >= 4.0:
                        # Good but not perfect — score between 50 and 80
                        score = 50.0 + (rating - 4.0) * 30.0
                        return CriterionResult(
                            criterion_number=15,
                            criterion_name="Customer-resource relationship",
                            score=round(score, 2),
                            weight=weight,
                            is_hard=is_hard,
                            is_satisfied=True,
                            explanation=(
                                f"Customer rated this resource "
                                f"{rating:.1f}/5 stars. "
                                f"Score {score:.0f}/100."
                            ),
                        )
                    # Below 4 stars — score proportional to rating
                    score = max(20.0, (rating / 5.0) * 50.0)
                    return CriterionResult(
                        criterion_number=15,
                        criterion_name="Customer-resource relationship",
                        score=round(score, 2),
                        weight=weight,
                        is_hard=is_hard,
                        is_satisfied=True,
                        explanation=(
                            f"Customer rated this resource "
                            f"{rating:.1f}/5 stars. "
                            f"Score {score:.0f}/100."
                        ),
                    )
                except (TypeError, ValueError):
                    self.logger.debug(
                        "scheduling.customerjobscorer.invalid_rating",
                        job_id=str(job.id),
                        staff_id=str(staff.id),
                    )

        # No relationship data — neutral score
        return CriterionResult(
            criterion_number=15,
            criterion_name="Customer-resource relationship",
            score=_RELATIONSHIP_NEUTRAL_SCORE,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                "No customer-resource relationship history available "
                f"— neutral score {_RELATIONSHIP_NEUTRAL_SCORE:.0f}/100."
            ),
        )

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _get_customer_preferences(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract customer time-window preferences from context.

        Looks for ``context.backlog["customer_preferences"]`` keyed
        by job id.  Returns a dict with optional keys:
        ``preferred_start``, ``preferred_end``,
        ``time_window_is_hard``.
        """
        if context.backlog is None:
            return None

        prefs = context.backlog.get("customer_preferences")
        if not isinstance(prefs, dict):
            return None

        job_prefs = prefs.get(str(job.id))
        if isinstance(job_prefs, dict) and job_prefs:
            return job_prefs
        return None

    def _get_predicted_complexity(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> float | None:
        """Extract predicted job complexity from context.

        Looks for ``context.backlog["predicted_complexity"]`` keyed
        by job id.  Returns a float 0.0-1.0 or ``None``.
        """
        if context.backlog is None:
            return None

        complexity_map = context.backlog.get("predicted_complexity")
        if isinstance(complexity_map, dict):
            value = complexity_map.get(str(job.id))
            if value is not None:
                try:
                    return max(0.0, min(1.0, float(value)))
                except (TypeError, ValueError):
                    return None
        return None

    def _get_priority_label(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> str | None:
        """Extract string-based priority label from context.

        Looks for ``context.backlog["job_priority_labels"]`` keyed
        by job id.  Returns a string like ``"emergency"``,
        ``"vip"``, ``"standard"``, ``"flexible"`` or ``None``.
        """
        if context.backlog is None:
            return None

        labels = context.backlog.get("job_priority_labels")
        if isinstance(labels, dict):
            label = labels.get(str(job.id))
            if isinstance(label, str) and label:
                return label
        return None

    def _get_customer_clv(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract customer CLV data from context.

        Looks for ``context.backlog["customer_clv"]`` keyed by job
        id.  Returns a dict with optional keys: ``clv_score``,
        ``clv_percentile``.
        """
        if context.backlog is None:
            return None

        clv_map = context.backlog.get("customer_clv")
        if not isinstance(clv_map, dict):
            return None

        clv_data = clv_map.get(str(job.id))
        if isinstance(clv_data, dict) and clv_data:
            return clv_data
        return None

    def _get_preferred_resource(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> str | None:
        """Extract preferred resource ID for a job's customer.

        Looks for ``context.backlog["preferred_resource"]`` keyed by
        job id.  Returns the preferred staff id string or ``None``.
        """
        if context.backlog is None:
            return None

        pref_map = context.backlog.get("preferred_resource")
        if isinstance(pref_map, dict):
            value = pref_map.get(str(job.id))
            if value is not None:
                return str(value)
        return None

    def _get_customer_resource_history(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract customer-resource relationship history from context.

        Looks for ``context.backlog["customer_resource_history"]``
        keyed by ``"{job_id}:{staff_id}"``.  Returns a dict with
        optional keys: ``avg_rating``, ``job_count``,
        ``last_service_date``.
        """
        if context.backlog is None:
            return None

        history_map = context.backlog.get("customer_resource_history")
        if not isinstance(history_map, dict):
            return None

        key = f"{job.id}:{staff.id}"
        history = history_map.get(key)
        if isinstance(history, dict) and history:
            return history
        return None

    @staticmethod
    def _parse_time(value: Any) -> time | None:  # noqa: ANN401
        """Parse a time value from various formats.

        Accepts ``datetime.time``, ISO time strings (``HH:MM``,
        ``HH:MM:SS``), or ``datetime.datetime`` objects.
        """
        if isinstance(value, time):
            return value
        if isinstance(value, datetime):
            return value.time()
        if isinstance(value, str):
            for fmt in ("%H:%M", "%H:%M:%S"):
                parsed = _try_parse_time(value, fmt)
                if parsed is not None:
                    return parsed
        return None
