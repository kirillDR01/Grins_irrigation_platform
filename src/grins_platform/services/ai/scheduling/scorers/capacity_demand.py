"""
CapacityDemandScorer - criteria 16-20 for AI scheduling.

Evaluates capacity utilization and demand signals for job-staff assignments:
  16. Daily capacity utilization (soft)
  17. Weekly demand forecast (soft)
  18. Seasonal peak windows (soft)
  19. Cancellation/no-show probability (soft)
  20. Pipeline/backlog pressure (soft)

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
"""

from __future__ import annotations

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

# Criterion 16 — daily capacity utilization
_UTILIZATION_SWEET_LOW = 60.0  # below this = underutilization
_UTILIZATION_SWEET_HIGH = 90.0  # above this = overbooking risk

# Criterion 19 — cancellation probability
_CANCEL_PROB_BEST = 0.05  # ≤5% → score 100
_CANCEL_PROB_WORST = 0.50  # ≥50% → score 0

# Criterion 20 — backlog aging thresholds (days)
_BACKLOG_AGE_BEST = 0.0  # brand-new job → score 0 (no urgency)
_BACKLOG_AGE_WORST = 30.0  # 30+ days old → score 100 (max urgency)


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
# CapacityDemandScorer
# ---------------------------------------------------------------------------


class CapacityDemandScorer(LoggerMixin):
    """Score capacity and demand criteria 16-20.

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
        """Score a job-staff assignment for capacity/demand criteria 16-20.

        Args:
            job: The job being evaluated.
            staff: The candidate staff member.
            context: Scheduling context (date, weather, traffic, backlog).
            config: Per-criterion configuration (weights, hard/soft).

        Returns:
            List of ``CriterionResult`` objects for criteria 16-20.
        """
        self.log_started(
            "score_assignment",
            job_id=str(job.id),
            staff_id=str(staff.id),
        )

        results: list[CriterionResult] = []

        try:
            results.append(
                await self._score_daily_capacity_utilization(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_weekly_demand_forecast(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_seasonal_peak_windows(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_cancellation_probability(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_pipeline_backlog_pressure(
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
    # Criterion 16 — Daily capacity utilization
    # ------------------------------------------------------------------

    async def _score_daily_capacity_utilization(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 16: Daily capacity utilization.

        Calculate (assigned job minutes + drive minutes) / available
        minutes x 100.  Flag >90% as overbooking risk (score
        decreasing) and <60% as underutilization (score decreasing).
        Sweet spot 60-90% = score 100.

        Uses ``context.backlog["daily_capacity"]`` keyed by staff id
        for current utilization data.
        """
        cfg = config.get(16)
        weight = cfg.weight if cfg else 60
        is_hard = cfg.is_hard_constraint if cfg else False

        capacity_data = self._get_daily_capacity(staff, context)

        # No capacity data — neutral score
        if capacity_data is None:
            return CriterionResult(
                criterion_number=16,
                criterion_name="Daily capacity utilization",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Daily capacity data unavailable — neutral score applied."
                ),
            )

        assigned_minutes = capacity_data.get("assigned_minutes", 0.0)
        drive_minutes = capacity_data.get("drive_minutes", 0.0)
        available_minutes = capacity_data.get("available_minutes", 0.0)

        try:
            assigned_minutes = float(assigned_minutes)
            drive_minutes = float(drive_minutes)
            available_minutes = float(available_minutes)
        except (TypeError, ValueError):
            return CriterionResult(
                criterion_number=16,
                criterion_name="Daily capacity utilization",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Daily capacity data invalid — neutral score applied."),
            )

        if available_minutes <= 0:
            return CriterionResult(
                criterion_number=16,
                criterion_name="Daily capacity utilization",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("No available minutes reported — neutral score applied."),
            )

        # Simulate adding this job to the utilization
        new_assigned = assigned_minutes + job.duration_minutes
        utilization_pct = (new_assigned + drive_minutes) / available_minutes * 100.0

        # Score based on utilization band
        if _UTILIZATION_SWEET_LOW <= utilization_pct <= _UTILIZATION_SWEET_HIGH:
            # Sweet spot — perfect score
            score = 100.0
            band = "optimal"
        elif utilization_pct > _UTILIZATION_SWEET_HIGH:
            # Overbooking risk — score decreases from 100 at 90% to 0 at 110%
            overshoot = utilization_pct - _UTILIZATION_SWEET_HIGH
            score = max(0.0, 100.0 - (overshoot / 20.0) * 100.0)
            band = "overbooking risk"
        else:
            # Underutilization — score decreases from 100 at 60% to 0 at 0%
            score = max(0.0, (utilization_pct / _UTILIZATION_SWEET_LOW) * 100.0)
            band = "underutilization"

        explanation = (
            f"Utilization {utilization_pct:.0f}% "
            f"({new_assigned:.0f} assigned + {drive_minutes:.0f} drive "
            f"/ {available_minutes:.0f} available). "
            f"Band: {band}. "
            f"Score {score:.0f}/100 "
            f"(sweet spot {_UTILIZATION_SWEET_LOW:.0f}-"
            f"{_UTILIZATION_SWEET_HIGH:.0f}%)."
        )

        return CriterionResult(
            criterion_number=16,
            criterion_name="Daily capacity utilization",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 17 — Weekly demand forecast
    # ------------------------------------------------------------------

    async def _score_weekly_demand_forecast(
        self,
        job: ScheduleJob,  # noqa: ARG002
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 17: Weekly demand forecast.

        Predict job volume for 2-8 weeks based on historical patterns.
        Score based on how well current scheduling density matches
        the forecast — high forecast with low density = higher score
        (incentivize filling), low forecast with high density = lower
        score (avoid overscheduling).

        Uses ``context.backlog["demand_forecast"]`` for forecast data.
        Neutral 50 if no forecast data.
        """
        cfg = config.get(17)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        forecast_data = self._get_demand_forecast(context)

        # No forecast data — neutral score
        if forecast_data is None:
            return CriterionResult(
                criterion_number=17,
                criterion_name="Weekly demand forecast",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Demand forecast data unavailable — neutral score applied."
                ),
            )

        predicted_jobs = forecast_data.get("predicted_jobs")
        current_scheduled = forecast_data.get("current_scheduled")
        capacity_total = forecast_data.get("capacity_total")

        # Validate data
        try:
            predicted_jobs = (
                float(predicted_jobs) if predicted_jobs is not None else None
            )
            current_scheduled = (
                float(current_scheduled) if current_scheduled is not None else None
            )
            capacity_total = (
                float(capacity_total) if capacity_total is not None else None
            )
        except (TypeError, ValueError):
            return CriterionResult(
                criterion_number=17,
                criterion_name="Weekly demand forecast",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Demand forecast data invalid — neutral score applied."),
            )

        if predicted_jobs is None or predicted_jobs <= 0:
            return CriterionResult(
                criterion_number=17,
                criterion_name="Weekly demand forecast",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "No predicted job volume available — neutral score applied."
                ),
            )

        # Calculate scheduling density ratio
        if capacity_total is not None and capacity_total > 0:
            # How full is the schedule relative to forecast demand?
            scheduled_count = (
                current_scheduled if current_scheduled is not None else 0.0
            )
            fill_ratio = scheduled_count / predicted_jobs

            # Score: 100 if fill ratio is around 0.7-0.9 (well-matched)
            # Lower if underfilled (incentivize scheduling)
            # Lower if overfilled (risk of overbooking)
            if 0.7 <= fill_ratio <= 0.9:
                score = 100.0
                match_desc = "well-matched to forecast"
            elif fill_ratio < 0.7:
                # Underfilled — higher score to incentivize scheduling
                score = 70.0 + (fill_ratio / 0.7) * 30.0
                match_desc = "below forecast — scheduling encouraged"
            else:
                # Overfilled — lower score
                overshoot = fill_ratio - 0.9
                score = max(0.0, 100.0 - (overshoot / 0.5) * 100.0)
                match_desc = "above forecast — overbooking risk"
        else:
            # No capacity data — use simple ratio
            score = 70.0
            fill_ratio = 0.0
            match_desc = "limited forecast data"

        explanation = (
            f"Forecast: {predicted_jobs:.0f} predicted jobs. "
            f"Currently scheduled: "
            f"{current_scheduled:.0f if current_scheduled is not None else 'unknown'}. "
            f"Fill ratio: {fill_ratio:.1%}. "
            f"Status: {match_desc}. "
            f"Score {score:.0f}/100."
        )

        return CriterionResult(
            criterion_number=17,
            criterion_name="Weekly demand forecast",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 18 — Seasonal peak windows
    # ------------------------------------------------------------------

    async def _score_seasonal_peak_windows(
        self,
        job: ScheduleJob,  # noqa: ARG002
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 18: Seasonal peak windows.

        Detect spring opening / fall closing rush periods.  Score
        higher during peak periods to prioritize scheduling density.

        Uses ``context.backlog["seasonal_data"]`` for peak window
        info.  Neutral 50 if no seasonal data.
        """
        cfg = config.get(18)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        seasonal_data = self._get_seasonal_data(context)

        # No seasonal data — neutral score
        if seasonal_data is None:
            return CriterionResult(
                criterion_number=18,
                criterion_name="Seasonal peak windows",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Seasonal data unavailable — neutral score applied."),
            )

        is_peak = seasonal_data.get("is_peak_period", False)
        peak_type = seasonal_data.get("peak_type")
        intensity = seasonal_data.get("intensity")

        # Validate intensity
        try:
            intensity_val = float(intensity) if intensity is not None else None
        except (TypeError, ValueError):
            intensity_val = None

        if not is_peak:
            # Off-peak — moderate score (scheduling is normal priority)
            return CriterionResult(
                criterion_number=18,
                criterion_name="Seasonal peak windows",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Not currently in a seasonal peak window "
                    "— normal scheduling priority."
                ),
            )

        # Peak period — score higher to prioritize scheduling density
        if intensity_val is not None:
            # Intensity 0.0-1.0 maps to score 60-100
            score = 60.0 + (min(1.0, max(0.0, intensity_val)) * 40.0)
        else:
            # Peak but no intensity data — default high score
            score = 80.0

        peak_label = str(peak_type) if peak_type else "seasonal"

        explanation = (
            f"Currently in {peak_label} peak period. "
            + (f"Intensity {intensity_val:.0%}. " if intensity_val is not None else "")
            + "Scheduling density prioritized. "
            + f"Score {score:.0f}/100."
        )

        return CriterionResult(
            criterion_number=18,
            criterion_name="Seasonal peak windows",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 19 — Cancellation/no-show probability
    # ------------------------------------------------------------------

    async def _score_cancellation_probability(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 19: Cancellation/no-show probability.

        ML model prediction based on customer history, weather,
        day-of-week.  Low probability = high score (reliable job),
        high probability = lower score.

        Score 100 for <5% probability, linearly decreasing to 0
        at >50%.

        Uses ``context.backlog["cancellation_probability"]`` keyed
        by job id.
        """
        cfg = config.get(19)
        weight = cfg.weight if cfg else 40
        is_hard = cfg.is_hard_constraint if cfg else False

        cancel_prob = self._get_cancellation_probability(job, context)

        # No cancellation data — neutral score
        if cancel_prob is None:
            return CriterionResult(
                criterion_number=19,
                criterion_name="Cancellation/no-show probability",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Cancellation probability data unavailable — neutral score applied."
                ),
            )

        # Clamp probability to 0.0-1.0
        prob = max(0.0, min(1.0, cancel_prob))

        # Score: 100 at ≤5%, linearly decreasing to 0 at ≥50%
        score = _linear_score(prob, _CANCEL_PROB_BEST, _CANCEL_PROB_WORST)

        if prob <= _CANCEL_PROB_BEST:
            risk_label = "very low"
        elif prob <= 0.15:
            risk_label = "low"
        elif prob <= 0.30:
            risk_label = "moderate"
        elif prob <= _CANCEL_PROB_WORST:
            risk_label = "high"
        else:
            risk_label = "very high"

        explanation = (
            f"Cancellation probability {prob:.0%} ({risk_label} risk). "
            f"Score {score:.0f}/100 "
            f"(100 at ≤{_CANCEL_PROB_BEST:.0%}, "
            f"0 at ≥{_CANCEL_PROB_WORST:.0%})."
        )

        return CriterionResult(
            criterion_number=19,
            criterion_name="Cancellation/no-show probability",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 20 — Pipeline/backlog pressure
    # ------------------------------------------------------------------

    async def _score_pipeline_backlog_pressure(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 20: Pipeline/backlog pressure.

        Track unscheduled jobs count and aging.  Higher backlog
        pressure = higher score for scheduling this job (incentivize
        clearing backlog).  Score based on job aging: older jobs
        score higher.

        Uses ``context.backlog["backlog_stats"]`` for queue size
        and aging data.
        """
        cfg = config.get(20)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        backlog_stats = self._get_backlog_stats(context)

        # No backlog data — neutral score
        if backlog_stats is None:
            return CriterionResult(
                criterion_number=20,
                criterion_name="Pipeline/backlog pressure",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Backlog data unavailable — neutral score applied."),
            )

        queue_size = backlog_stats.get("queue_size")
        job_age_days = backlog_stats.get("job_age_days")
        avg_age_days = backlog_stats.get("avg_age_days")

        # Get this specific job's age if available
        job_ages = backlog_stats.get("job_ages")
        if isinstance(job_ages, dict):
            specific_age = job_ages.get(str(job.id))
            if specific_age is not None:
                try:
                    job_age_days = float(specific_age)
                except (TypeError, ValueError):
                    self.logger.debug(
                        "scheduling.capacitydemandscorer.invalid_job_age",
                        job_id=str(job.id),
                        value=str(specific_age),
                    )

        # Validate data
        try:
            queue_size_val = int(queue_size) if queue_size is not None else None
            job_age_val = float(job_age_days) if job_age_days is not None else None
            avg_age_val = float(avg_age_days) if avg_age_days is not None else None
        except (TypeError, ValueError):
            return CriterionResult(
                criterion_number=20,
                criterion_name="Pipeline/backlog pressure",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Backlog data invalid — neutral score applied."),
            )

        # Score primarily based on job aging (older = higher priority)
        if job_age_val is not None:
            # Invert the linear score: older jobs get HIGHER scores
            # 0 days old → score ~0 (low urgency)
            # 30+ days old → score 100 (max urgency)
            age_score = min(
                100.0,
                max(0.0, (job_age_val / _BACKLOG_AGE_WORST) * 100.0),
            )
        elif avg_age_val is not None:
            # Use average age as fallback
            age_score = min(
                100.0,
                max(0.0, (avg_age_val / _BACKLOG_AGE_WORST) * 100.0),
            )
        else:
            age_score = 50.0

        # Boost score if queue is large (more pressure to schedule)
        if queue_size_val is not None and queue_size_val > 0:
            # Queue size bonus: +10 at 20+ jobs, +20 at 50+ jobs
            queue_bonus = min(20.0, (queue_size_val / 50.0) * 20.0)
            score = min(100.0, age_score + queue_bonus)
        else:
            score = age_score

        # Build explanation
        parts: list[str] = []
        if job_age_val is not None:
            parts.append(f"Job age: {job_age_val:.0f} days")
        elif avg_age_val is not None:
            parts.append(f"Avg backlog age: {avg_age_val:.0f} days")
        if queue_size_val is not None:
            parts.append(f"Queue size: {queue_size_val} jobs")

        explanation = (
            (". ".join(parts) + ". " if parts else "")
            + f"Backlog pressure score {score:.0f}/100 "
            + "(older/larger backlog = higher priority)."
        )

        return CriterionResult(
            criterion_number=20,
            criterion_name="Pipeline/backlog pressure",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _get_daily_capacity(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract daily capacity utilization data from context.

        Looks for ``context.backlog["daily_capacity"]`` keyed by
        staff id.  Returns a dict with keys: ``assigned_minutes``,
        ``drive_minutes``, ``available_minutes``.
        """
        if context.backlog is None:
            return None

        capacity_map = context.backlog.get("daily_capacity")
        if not isinstance(capacity_map, dict):
            return None

        data = capacity_map.get(str(staff.id))
        if isinstance(data, dict) and data:
            return data
        return None

    def _get_demand_forecast(
        self,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract weekly demand forecast data from context.

        Looks for ``context.backlog["demand_forecast"]``.  Returns
        a dict with keys: ``predicted_jobs``, ``current_scheduled``,
        ``capacity_total``.
        """
        if context.backlog is None:
            return None

        forecast = context.backlog.get("demand_forecast")
        if isinstance(forecast, dict) and forecast:
            return forecast
        return None

    def _get_seasonal_data(
        self,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract seasonal peak window data from context.

        Looks for ``context.backlog["seasonal_data"]``.  Returns
        a dict with keys: ``is_peak_period``, ``peak_type``,
        ``intensity``.
        """
        if context.backlog is None:
            return None

        seasonal = context.backlog.get("seasonal_data")
        if isinstance(seasonal, dict) and seasonal:
            return seasonal
        return None

    def _get_cancellation_probability(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> float | None:
        """Extract cancellation/no-show probability for a job.

        Looks for ``context.backlog["cancellation_probability"]``
        keyed by job id.  Returns a float 0.0-1.0 or ``None``.
        """
        if context.backlog is None:
            return None

        prob_map = context.backlog.get("cancellation_probability")
        if not isinstance(prob_map, dict):
            return None

        value = prob_map.get(str(job.id))
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                self.logger.debug(
                    "scheduling.capacitydemandscorer.invalid_cancel_prob",
                    job_id=str(job.id),
                    value=str(value),
                )
        return None

    def _get_backlog_stats(
        self,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract pipeline/backlog pressure data from context.

        Looks for ``context.backlog["backlog_stats"]``.  Returns
        a dict with keys: ``queue_size``, ``job_age_days``,
        ``avg_age_days``, ``job_ages`` (dict keyed by job id).
        """
        if context.backlog is None:
            return None

        stats = context.backlog.get("backlog_stats")
        if isinstance(stats, dict) and stats:
            return stats
        return None
