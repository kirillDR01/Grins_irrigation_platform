"""
BusinessRulesScorer - criteria 21-25 for AI scheduling.

Evaluates business rules and compliance constraints for job-staff assignments:
  21. Compliance deadlines (hard constraint)
  22. Revenue per resource-hour (soft)
  23. Contract/SLA commitments (hard constraint)
  24. Overtime cost threshold (soft)
  25. Seasonal pricing signals (soft)

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

from __future__ import annotations

from datetime import date, datetime
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

# Criterion 21 — compliance deadlines
_COMPLIANCE_URGENCY_DAYS = 7  # urgency note if within 7 days

# Criterion 22 — revenue per resource-hour
_REVENUE_HIGH_PER_HOUR = 100.0  # score 100 at ≥$100/hr
_REVENUE_LOW_PER_HOUR = 20.0  # score 0 at ≤$20/hr

# Criterion 24 — overtime
_OVERTIME_DEFAULT_THRESHOLD_MINUTES = 480  # 8-hour default shift

# Criterion 25 — seasonal pricing
_PRICING_FULL_PRICE_PEAK_SCORE = 100.0
_PRICING_FLEXIBLE_OFFPEAK_SCORE = 100.0
_PRICING_FLEXIBLE_PEAK_SCORE = 40.0


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


def _parse_date(value: Any) -> date | None:  # noqa: ANN401
    """Parse a date value from various formats.

    Accepts ``datetime.date``, ``datetime.datetime``, or ISO date
    strings (``YYYY-MM-DD``).
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None
    return None


# ---------------------------------------------------------------------------
# BusinessRulesScorer
# ---------------------------------------------------------------------------


class BusinessRulesScorer(LoggerMixin):
    """Score business rules and compliance criteria 21-25.

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
        """Score a job-staff assignment for business rules criteria 21-25.

        Args:
            job: The job being evaluated.
            staff: The candidate staff member.
            context: Scheduling context (date, weather, traffic, backlog).
            config: Per-criterion configuration (weights, hard/soft).

        Returns:
            List of ``CriterionResult`` objects for criteria 21-25.
        """
        self.log_started(
            "score_assignment",
            job_id=str(job.id),
            staff_id=str(staff.id),
        )

        results: list[CriterionResult] = []

        try:
            results.append(
                await self._score_compliance_deadlines(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_revenue_per_resource_hour(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_contract_sla_commitments(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_overtime_cost_threshold(
                    job,
                    staff,
                    context,
                    config,
                ),
            )
            results.append(
                await self._score_seasonal_pricing_signals(
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
    # Criterion 21 — Compliance deadlines (HARD)
    # ------------------------------------------------------------------

    async def _score_compliance_deadlines(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 21: Compliance deadlines.

        Check ``context.backlog["compliance_deadlines"]`` keyed by
        job id for deadline dates (backflow test certification
        expiration, municipal inspection windows, warranty service
        windows).

        Score 0 with ``is_satisfied=False`` if the scheduled date
        is after the compliance deadline.  Score 100 if scheduled
        before the deadline, with an urgency note if within 7 days.
        """
        cfg = config.get(21)
        weight = cfg.weight if cfg else 90
        is_hard = cfg.is_hard_constraint if cfg else True  # default hard

        deadline = self._get_compliance_deadline(job, context)

        # No compliance deadline — fully satisfied
        if deadline is None:
            return CriterionResult(
                criterion_number=21,
                criterion_name="Compliance deadlines",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("No compliance deadline for this job — fully satisfied."),
            )

        scheduled_date = context.schedule_date

        # Deadline violation — scheduled after the compliance deadline
        if scheduled_date > deadline:
            days_past = (scheduled_date - deadline).days
            return CriterionResult(
                criterion_number=21,
                criterion_name="Compliance deadlines",
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(
                    f"COMPLIANCE VIOLATION: Scheduled date "
                    f"{scheduled_date.isoformat()} is {days_past} day(s) "
                    f"past compliance deadline "
                    f"{deadline.isoformat()}."
                ),
            )

        # Scheduled before deadline — check urgency
        days_remaining = (deadline - scheduled_date).days

        if days_remaining <= _COMPLIANCE_URGENCY_DAYS:
            return CriterionResult(
                criterion_number=21,
                criterion_name="Compliance deadlines",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Compliance deadline {deadline.isoformat()} — "
                    f"URGENT: only {days_remaining} day(s) remaining. "
                    f"Scheduled on {scheduled_date.isoformat()}. "
                    f"Score 100/100."
                ),
            )

        return CriterionResult(
            criterion_number=21,
            criterion_name="Compliance deadlines",
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Compliance deadline {deadline.isoformat()} — "
                f"{days_remaining} day(s) remaining. "
                f"Scheduled on {scheduled_date.isoformat()}. "
                f"Score 100/100."
            ),
        )

    # ------------------------------------------------------------------
    # Criterion 22 — Revenue per resource-hour
    # ------------------------------------------------------------------

    async def _score_revenue_per_resource_hour(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 22: Revenue per resource-hour.

        Calculate ``job_revenue / ((job_duration + drive_time) / 60)``
        to get effective revenue per hour including drive time.

        Uses ``context.backlog["job_revenue"]`` keyed by job id for
        revenue data.  Drive time is estimated via haversine from
        the staff's start location to the job site.

        Score 100 for high revenue/hour (≥$100), linearly decreasing
        to 0 at ≤$20/hour.  Neutral 50 if no revenue data.
        """
        cfg = config.get(22)
        weight = cfg.weight if cfg else 60
        is_hard = cfg.is_hard_constraint if cfg else False

        job_revenue = self._get_job_revenue(job, context)

        # No revenue data — neutral score
        if job_revenue is None:
            return CriterionResult(
                criterion_number=22,
                criterion_name="Revenue per resource-hour",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Job revenue data unavailable — neutral score applied."),
            )

        # Calculate drive time from staff start to job site
        drive_time_minutes = float(
            haversine_travel_minutes(
                float(staff.start_location.latitude),
                float(staff.start_location.longitude),
                float(job.location.latitude),
                float(job.location.longitude),
            ),
        )

        # Total resource-hours for this job (duration + drive time)
        total_minutes = float(job.duration_minutes) + drive_time_minutes

        if total_minutes <= 0:
            return CriterionResult(
                criterion_number=22,
                criterion_name="Revenue per resource-hour",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Total job time is zero — neutral score applied."),
            )

        total_hours = total_minutes / 60.0
        revenue_per_hour = job_revenue / total_hours

        # Score: 100 at ≥$100/hr, linearly decreasing to 0 at ≤$20/hr
        # _linear_score gives 100 at best, 0 at worst — we invert
        # because higher revenue = better score
        if revenue_per_hour >= _REVENUE_HIGH_PER_HOUR:
            score = 100.0
        elif revenue_per_hour <= _REVENUE_LOW_PER_HOUR:
            score = 0.0
        else:
            score = (
                (revenue_per_hour - _REVENUE_LOW_PER_HOUR)
                / (_REVENUE_HIGH_PER_HOUR - _REVENUE_LOW_PER_HOUR)
                * 100.0
            )

        explanation = (
            f"Revenue ${job_revenue:.0f} / "
            f"{total_hours:.1f} hrs "
            f"({job.duration_minutes} min job + "
            f"{drive_time_minutes:.0f} min drive) = "
            f"${revenue_per_hour:.0f}/hr. "
            f"Score {score:.0f}/100 "
            f"(100 at ≥${_REVENUE_HIGH_PER_HOUR:.0f}/hr, "
            f"0 at ≤${_REVENUE_LOW_PER_HOUR:.0f}/hr)."
        )

        return CriterionResult(
            criterion_number=22,
            criterion_name="Revenue per resource-hour",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 23 — Contract/SLA commitments (HARD)
    # ------------------------------------------------------------------

    async def _score_contract_sla_commitments(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 23: Contract/SLA commitments.

        Check ``context.backlog["sla_deadlines"]`` keyed by job id
        for SLA deadline dates.  SLA deadlines are hard constraints
        — score 0 with ``is_satisfied=False`` if the SLA deadline
        would be missed.  Score 100 if within SLA, with urgency
        note if tight.
        """
        cfg = config.get(23)
        weight = cfg.weight if cfg else 95
        is_hard = cfg.is_hard_constraint if cfg else True  # default hard

        sla_deadline = self._get_sla_deadline(job, context)

        # No SLA commitment — fully satisfied
        if sla_deadline is None:
            return CriterionResult(
                criterion_number=23,
                criterion_name="Contract/SLA commitments",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("No SLA commitment for this job — fully satisfied."),
            )

        scheduled_date = context.schedule_date

        # SLA violation — scheduled after the SLA deadline
        if scheduled_date > sla_deadline:
            days_past = (scheduled_date - sla_deadline).days
            return CriterionResult(
                criterion_number=23,
                criterion_name="Contract/SLA commitments",
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(
                    f"SLA VIOLATION: Scheduled date "
                    f"{scheduled_date.isoformat()} is {days_past} day(s) "
                    f"past SLA deadline "
                    f"{sla_deadline.isoformat()}."
                ),
            )

        # Within SLA — check how tight
        days_remaining = (sla_deadline - scheduled_date).days

        if days_remaining <= 1:
            urgency_note = "CRITICAL: SLA deadline is tomorrow or today"
        elif days_remaining <= 3:
            urgency_note = f"TIGHT: only {days_remaining} day(s) until SLA deadline"
        elif days_remaining <= _COMPLIANCE_URGENCY_DAYS:
            urgency_note = f"Approaching: {days_remaining} day(s) until SLA deadline"
        else:
            urgency_note = f"{days_remaining} day(s) until SLA deadline"

        return CriterionResult(
            criterion_number=23,
            criterion_name="Contract/SLA commitments",
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"SLA deadline {sla_deadline.isoformat()} — "
                f"{urgency_note}. "
                f"Scheduled on {scheduled_date.isoformat()}. "
                f"Score 100/100."
            ),
        )

    # ------------------------------------------------------------------
    # Criterion 24 — Overtime cost threshold
    # ------------------------------------------------------------------

    async def _score_overtime_cost_threshold(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 24: Overtime cost threshold.

        Check ``context.backlog["overtime_data"]`` keyed by staff id
        for current assigned minutes.  Use the staff's
        ``overtime_threshold_minutes`` from context (or default 480
        min / 8 hours).

        Penalize overtime UNLESS the job's revenue justifies the
        added labor cost.  Score 100 if no overtime, decreasing as
        overtime grows, but restored if revenue justifies it.
        """
        cfg = config.get(24)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        overtime_data = self._get_overtime_data(staff, context)

        # No overtime data — neutral score (assume no overtime)
        if overtime_data is None:
            return CriterionResult(
                criterion_number=24,
                criterion_name="Overtime cost threshold",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("No overtime data available — assuming no overtime risk."),
            )

        current_assigned_minutes = overtime_data.get("assigned_minutes", 0.0)
        overtime_threshold = overtime_data.get(
            "overtime_threshold_minutes",
            _OVERTIME_DEFAULT_THRESHOLD_MINUTES,
        )

        try:
            current_assigned_minutes = float(current_assigned_minutes)
            overtime_threshold = float(overtime_threshold)
        except (TypeError, ValueError):
            return CriterionResult(
                criterion_number=24,
                criterion_name="Overtime cost threshold",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Overtime data invalid — neutral score applied."),
            )

        # Projected total after adding this job
        projected_total = current_assigned_minutes + float(job.duration_minutes)

        # No overtime — perfect score
        if projected_total <= overtime_threshold:
            return CriterionResult(
                criterion_number=24,
                criterion_name="Overtime cost threshold",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Projected {projected_total:.0f} min / "
                    f"{overtime_threshold:.0f} min threshold. "
                    f"No overtime. Score 100/100."
                ),
            )

        # Overtime detected — calculate penalty
        overtime_minutes = projected_total - overtime_threshold

        # Base penalty: score decreases from 100 at 0 OT to 0 at 120 min OT
        base_score = max(0.0, 100.0 - (overtime_minutes / 120.0) * 100.0)

        # Check if job revenue justifies the overtime
        job_revenue = self._get_job_revenue(job, context)

        if job_revenue is not None and job_revenue > 0:
            # Estimate overtime labor cost: assume $50/hr overtime rate
            overtime_hours = overtime_minutes / 60.0
            overtime_cost = overtime_hours * 50.0

            if job_revenue >= overtime_cost * 2.0:
                # Revenue strongly justifies overtime — restore score
                score = max(base_score, 80.0)
                justification = (
                    f"Revenue ${job_revenue:.0f} strongly justifies "
                    f"overtime cost ~${overtime_cost:.0f}"
                )
            elif job_revenue >= overtime_cost:
                # Revenue covers overtime — partial restore
                score = max(base_score, 60.0)
                justification = (
                    f"Revenue ${job_revenue:.0f} covers "
                    f"overtime cost ~${overtime_cost:.0f}"
                )
            else:
                score = base_score
                justification = (
                    f"Revenue ${job_revenue:.0f} does NOT justify "
                    f"overtime cost ~${overtime_cost:.0f}"
                )
        else:
            score = base_score
            justification = "No revenue data to justify overtime"

        explanation = (
            f"Projected {projected_total:.0f} min / "
            f"{overtime_threshold:.0f} min threshold. "
            f"Overtime: {overtime_minutes:.0f} min. "
            f"{justification}. "
            f"Score {score:.0f}/100."
        )

        return CriterionResult(
            criterion_number=24,
            criterion_name="Overtime cost threshold",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 25 — Seasonal pricing signals
    # ------------------------------------------------------------------

    async def _score_seasonal_pricing_signals(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 25: Seasonal pricing signals.

        Steer flexible jobs to off-peak slots, reserve peak slots
        for full-price work.

        Uses ``context.backlog["pricing_signals"]`` for peak/off-peak
        data and job pricing tier.

        Score 100 if job is full-price in a peak slot or flexible
        in an off-peak slot.  Lower score if a flexible/discounted
        job takes a peak slot.
        """
        cfg = config.get(25)
        weight = cfg.weight if cfg else 40
        is_hard = cfg.is_hard_constraint if cfg else False

        pricing_data = self._get_pricing_signals(context)

        # No pricing data — neutral score
        if pricing_data is None:
            return CriterionResult(
                criterion_number=25,
                criterion_name="Seasonal pricing signals",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Pricing signal data unavailable — neutral score applied."
                ),
            )

        is_peak_slot = bool(pricing_data.get("is_peak_slot", False))
        job_pricing = self._get_job_pricing_tier(job, pricing_data)

        is_full_price = job_pricing in ("full_price", "premium")
        is_flexible = job_pricing in ("flexible", "discounted", "off_peak")

        if is_peak_slot:
            if is_full_price:
                # Full-price job in peak slot — ideal
                score = _PRICING_FULL_PRICE_PEAK_SCORE
                explanation = (
                    f"Peak slot with full-price job "
                    f"(pricing tier: {job_pricing}). "
                    f"Ideal match. Score {score:.0f}/100."
                )
            elif is_flexible:
                # Flexible/discounted job in peak slot — suboptimal
                score = _PRICING_FLEXIBLE_PEAK_SCORE
                explanation = (
                    f"Peak slot with flexible/discounted job "
                    f"(pricing tier: {job_pricing}). "
                    f"Reserve peak slots for full-price work. "
                    f"Score {score:.0f}/100."
                )
            else:
                # Standard job in peak slot — acceptable
                score = 70.0
                explanation = (
                    f"Peak slot with standard job "
                    f"(pricing tier: {job_pricing}). "
                    f"Score {score:.0f}/100."
                )
        elif is_flexible:
            # Off-peak: Flexible job in off-peak — ideal
            score = _PRICING_FLEXIBLE_OFFPEAK_SCORE
            explanation = (
                f"Off-peak slot with flexible job "
                f"(pricing tier: {job_pricing}). "
                f"Ideal match. Score {score:.0f}/100."
            )
        elif is_full_price:
            # Off-peak: Full-price job in off-peak — acceptable but not ideal
            score = 70.0
            explanation = (
                f"Off-peak slot with full-price job "
                f"(pricing tier: {job_pricing}). "
                f"Full-price jobs are better in peak slots. "
                f"Score {score:.0f}/100."
            )
        else:
            # Off-peak: Standard job in off-peak — fine
            score = 80.0
            explanation = (
                f"Off-peak slot with standard job "
                f"(pricing tier: {job_pricing}). "
                f"Score {score:.0f}/100."
            )

        return CriterionResult(
            criterion_number=25,
            criterion_name="Seasonal pricing signals",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _get_compliance_deadline(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> date | None:
        """Extract compliance deadline for a job.

        Looks for ``context.backlog["compliance_deadlines"]`` keyed
        by job id.  Returns a ``date`` or ``None``.
        """
        if context.backlog is None:
            return None

        deadlines = context.backlog.get("compliance_deadlines")
        if not isinstance(deadlines, dict):
            return None

        value = deadlines.get(str(job.id))
        if value is None:
            return None

        return _parse_date(value)

    def _get_job_revenue(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> float | None:
        """Extract job revenue from context.

        Looks for ``context.backlog["job_revenue"]`` keyed by job id.
        Returns a float or ``None``.
        """
        if context.backlog is None:
            return None

        revenue_map = context.backlog.get("job_revenue")
        if not isinstance(revenue_map, dict):
            return None

        value = revenue_map.get(str(job.id))
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                self.logger.debug(
                    "scheduling.businessrulesscorer.invalid_revenue",
                    job_id=str(job.id),
                    value=str(value),
                )
        return None

    def _get_sla_deadline(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> date | None:
        """Extract SLA deadline for a job.

        Looks for ``context.backlog["sla_deadlines"]`` keyed by
        job id.  Returns a ``date`` or ``None``.
        """
        if context.backlog is None:
            return None

        deadlines = context.backlog.get("sla_deadlines")
        if not isinstance(deadlines, dict):
            return None

        value = deadlines.get(str(job.id))
        if value is None:
            return None

        return _parse_date(value)

    def _get_overtime_data(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract overtime data for a staff member.

        Looks for ``context.backlog["overtime_data"]`` keyed by
        staff id.  Returns a dict with keys: ``assigned_minutes``,
        ``overtime_threshold_minutes``.
        """
        if context.backlog is None:
            return None

        overtime_map = context.backlog.get("overtime_data")
        if not isinstance(overtime_map, dict):
            return None

        data = overtime_map.get(str(staff.id))
        if isinstance(data, dict) and data:
            return data
        return None

    def _get_pricing_signals(
        self,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract seasonal pricing signal data from context.

        Looks for ``context.backlog["pricing_signals"]``.  Returns
        a dict with keys: ``is_peak_slot``, ``job_pricing_tiers``
        (dict keyed by job id).
        """
        if context.backlog is None:
            return None

        signals = context.backlog.get("pricing_signals")
        if isinstance(signals, dict) and signals:
            return signals
        return None

    def _get_job_pricing_tier(
        self,
        job: ScheduleJob,
        pricing_data: dict[str, Any],
    ) -> str:
        """Determine the pricing tier for a job.

        Looks for ``pricing_data["job_pricing_tiers"]`` keyed by
        job id.  Returns a string like ``"full_price"``,
        ``"flexible"``, ``"discounted"``, ``"premium"``, or
        ``"standard"`` as default.
        """
        tiers = pricing_data.get("job_pricing_tiers")
        if isinstance(tiers, dict):
            tier = tiers.get(str(job.id))
            if isinstance(tier, str) and tier:
                return tier.lower()
        return "standard"
