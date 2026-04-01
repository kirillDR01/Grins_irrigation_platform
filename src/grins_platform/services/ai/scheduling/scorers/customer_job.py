"""
CustomerJobScorer — criteria 11-15 for AI scheduling.

Scores customer/job factors: time-window preferences, duration
estimates, job priority, customer lifetime value, and
customer-resource relationship history.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import CriterionResult, SchedulingContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CustomerJobScorer(LoggerMixin):
    """Scores customer/job criteria 11-15 for job-staff assignments."""

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
        """Score a customer/job criterion for a job-staff pair."""
        method_map: dict[int, Callable[..., Coroutine[Any, Any, CriterionResult]]] = {
            11: self._score_time_window,
            12: self._score_duration_estimate,
            13: self._score_priority,
            14: self._score_clv,
            15: self._score_relationship,
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
            explanation="Unknown customer/job criterion",
        )


    async def _score_time_window(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 11: Customer time-window preferences.

        Hard if time_window_is_hard. Match = 100,
        mismatch = 0 (hard) or 30 (soft).
        """
        name = config.get("criterion_name", "Customer Time-Window Preferences")
        weight = config.get("weight", 50)

        customer = job.get("customer", {})
        pref = customer.get("time_window_preference")
        is_hard_pref = bool(customer.get("time_window_is_hard", False))
        is_hard = is_hard_pref or config.get("is_hard_constraint", False)

        if not pref:
            return CriterionResult(
                criterion_number=11,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No time-window preference",
            )

        slot = job.get("time_slot", "").lower()
        pref_lower = pref.lower()

        matched = pref_lower in slot or slot in pref_lower
        if not matched and pref_lower in ("am", "morning"):
            hour = job.get("scheduled_hour")
            if hour is not None:
                matched = int(hour) < 12
        elif not matched and pref_lower in ("pm", "afternoon"):
            hour = job.get("scheduled_hour")
            if hour is not None:
                matched = int(hour) >= 12

        if matched:
            return CriterionResult(
                criterion_number=11,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=f"Time window '{pref}' matched",
            )

        return CriterionResult(
            criterion_number=11,
            criterion_name=name,
            score=0.0 if is_hard else 30.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=not is_hard,
            explanation=(
                f"Time window '{pref}' not matched"
                f" ({'hard' if is_hard else 'soft'} constraint)"
            ),
        )

    async def _score_duration_estimate(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 12: Job type duration estimates.

        Compare estimated vs predicted complexity.
        Well-matched = 100, over/under = lower.
        """
        name = config.get("criterion_name", "Job Type Duration Estimates")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        estimated = job.get("estimated_duration_minutes")
        predicted = job.get("predicted_complexity")

        if estimated is None:
            return CriterionResult(
                criterion_number=12,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No duration estimate; neutral score",
            )

        est = float(estimated)
        if predicted is not None:
            adjusted = est * float(predicted)
            slot_minutes = float(job.get("slot_duration_minutes", est))
            if slot_minutes <= 0:
                slot_minutes = est
            ratio = adjusted / slot_minutes if slot_minutes > 0 else 1.0
            deviation = abs(1.0 - ratio)
            raw_score = max(0.0, 100.0 - (deviation * 100.0))
        else:
            raw_score = 75.0

        return CriterionResult(
            criterion_number=12,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=f"Duration fit → score {raw_score:.1f}",
        )

    async def _score_priority(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 13: Job priority level.

        emergency=100, VIP=80, standard=50, flexible=30.
        """
        name = config.get("criterion_name", "Job Priority Level")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        priority_map: dict[str, float] = {
            "emergency": 100.0,
            "vip": 80.0,
            "standard": 50.0,
            "flexible": 30.0,
        }

        priority = str(job.get("priority", "standard")).lower()
        raw_score = priority_map.get(priority, 50.0)

        return CriterionResult(
            criterion_number=13,
            criterion_name=name,
            score=raw_score,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=f"Priority '{priority}' → score {raw_score:.0f}",
        )

    async def _score_clv(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 14: Customer lifetime value.

        Normalize clv_score to 0-100.
        """
        name = config.get("criterion_name", "Customer Lifetime Value")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        customer = job.get("customer", {})
        clv = customer.get("clv_score")

        if clv is None:
            return CriterionResult(
                criterion_number=14,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No CLV data; neutral score",
            )

        raw_score = max(0.0, min(100.0, float(clv)))

        return CriterionResult(
            criterion_number=14,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=f"CLV score {clv} → {raw_score:.1f}",
        )

    async def _score_relationship(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 15: Customer-resource relationship.

        preferred_resource_id match = 100, no preference = 50.
        """
        name = config.get(
            "criterion_name",
            "Customer-Resource Relationship",
        )
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        customer = job.get("customer", {})
        preferred = customer.get("preferred_resource_id")

        if not preferred:
            return CriterionResult(
                criterion_number=15,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No preferred resource; neutral score",
            )

        staff_id = staff.get("id")
        matched = str(preferred) == str(staff_id)

        return CriterionResult(
            criterion_number=15,
            criterion_name=name,
            score=100.0 if matched else 30.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                "Preferred resource match"
                if matched
                else "Not preferred resource"
            ),
        )
