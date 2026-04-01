"""
PredictiveScorer — criteria 26-30 for AI scheduling.

Scores predictive factors: weather forecast impact, predicted job
complexity, lead-to-job conversion timing, resource location at
shift start, and cross-job dependency chains.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""

from __future__ import annotations

import math
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import CriterionResult, SchedulingContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PredictiveScorer(LoggerMixin):
    """Scores predictive criteria 26-30 for job-staff assignments."""

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
        """Score a predictive criterion for a job-staff pair."""
        method_map: dict[int, Callable[..., Coroutine[Any, Any, CriterionResult]]] = {
            26: self._score_weather_impact,
            27: self._score_predicted_complexity,
            28: self._score_lead_conversion,
            29: self._score_shift_start_location,
            30: self._score_dependency_chain,
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
            explanation="Unknown predictive criterion",
        )


    @staticmethod
    def _haversine_km(
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:
        """Calculate haversine distance in kilometres."""
        r = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lng = math.radians(lng2 - lng1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lng / 2) ** 2
        )
        return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    async def _score_weather_impact(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 26: Weather forecast impact.

        Outdoor job + bad weather = 0, indoor = 100,
        outdoor + good weather = 80.
        """
        name = config.get("criterion_name", "Weather Forecast Impact")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        is_outdoor = bool(job.get("is_outdoor", False))
        weather = context.weather or {}
        condition = str(weather.get("condition", "")).lower()

        bad_conditions = {"rain", "storm", "freeze", "snow", "ice", "severe"}

        if not is_outdoor:
            return CriterionResult(
                criterion_number=26,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="Indoor job; weather not a factor",
            )

        if not condition:
            return CriterionResult(
                criterion_number=26,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No weather data; neutral score",
            )

        is_bad = any(bc in condition for bc in bad_conditions)
        if is_bad:
            return CriterionResult(
                criterion_number=26,
                criterion_name=name,
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=(
                    f"Outdoor job with bad weather: {condition}"
                ),
            )

        return CriterionResult(
            criterion_number=26,
            criterion_name=name,
            score=80.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=f"Outdoor job, weather OK: {condition}",
        )

    async def _score_predicted_complexity(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 27: Predicted job complexity.

        Well-matched time slot = 100. Uses predicted_complexity.
        """
        name = config.get("criterion_name", "Predicted Job Complexity")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        complexity = job.get("predicted_complexity")
        if complexity is None:
            return CriterionResult(
                criterion_number=27,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No complexity prediction; neutral score",
            )

        c_val = float(complexity)
        slot_min = float(job.get("slot_duration_minutes", 0))
        est_min = float(job.get("estimated_duration_minutes", 60))

        if slot_min <= 0:
            slot_min = est_min

        needed = est_min * c_val
        if slot_min <= 0:
            raw_score = 50.0
        else:
            ratio = needed / slot_min
            if 0.8 <= ratio <= 1.2:
                raw_score = 100.0
            else:
                deviation = abs(1.0 - ratio)
                raw_score = max(0.0, 100.0 - (deviation * 100.0))

        return CriterionResult(
            criterion_number=27,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Complexity {c_val:.2f}, slot fit → "
                f"score {raw_score:.1f}"
            ),
        )

    async def _score_lead_conversion(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 28: Lead-to-job conversion timing.

        Placeholder. Hot lead = 80, cold = 50.
        """
        name = config.get("criterion_name", "Lead-to-Job Conversion Timing")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        lead_temp = str(job.get("lead_temperature", "")).lower()

        temp_map: dict[str, float] = {
            "hot": 80.0,
            "warm": 65.0,
            "cold": 50.0,
        }
        raw_score = temp_map.get(lead_temp, 50.0)

        return CriterionResult(
            criterion_number=28,
            criterion_name=name,
            score=raw_score,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Lead temperature '{lead_temp or 'unknown'}' → "
                f"score {raw_score:.0f}"
            ),
        )

    async def _score_shift_start_location(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 29: Resource location at shift start.

        Use default_start_lat/lng for first-job routing.
        Close = 100.
        """
        name = config.get(
            "criterion_name",
            "Resource Location at Shift Start",
        )
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        start_lat = staff.get("default_start_lat")
        start_lng = staff.get("default_start_lng")
        job_lat = job.get("latitude") or job.get("lat")
        job_lng = job.get("longitude") or job.get("lng")

        if not all(
            v is not None
            for v in [start_lat, start_lng, job_lat, job_lng]
        ):
            return CriterionResult(
                criterion_number=29,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="Missing location data; neutral score",
            )

        # Guaranteed non-None after the all() check above
        assert start_lat is not None
        assert start_lng is not None
        assert job_lat is not None
        assert job_lng is not None
        distance_km = self._haversine_km(
            float(start_lat),
            float(start_lng),
            float(job_lat),
            float(job_lng),
        )
        raw_score = max(0.0, 100.0 - (distance_km * 5.0))

        return CriterionResult(
            criterion_number=29,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Start-to-job distance {distance_km:.1f} km → "
                f"score {raw_score:.1f}"
            ),
        )

    async def _score_dependency_chain(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 30: Cross-job dependency chains (HARD).

        Prerequisite complete = 100/satisfied,
        not complete = 0/not satisfied.
        """
        name = config.get(
            "criterion_name",
            "Cross-Job Dependency Chains",
        )
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", True)

        depends_on = job.get("depends_on_job_id")
        if not depends_on:
            return CriterionResult(
                criterion_number=30,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No dependency; satisfied",
            )

        prereq_status = str(
            job.get("prerequisite_status", "unknown"),
        ).lower()
        completed_statuses = {"completed", "done", "finished"}

        if prereq_status in completed_statuses:
            return CriterionResult(
                criterion_number=30,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Prerequisite job {depends_on} completed"
                ),
            )

        return CriterionResult(
            criterion_number=30,
            criterion_name=name,
            score=0.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=False,
            explanation=(
                f"Prerequisite job {depends_on} not completed "
                f"(status: {prereq_status})"
            ),
        )
