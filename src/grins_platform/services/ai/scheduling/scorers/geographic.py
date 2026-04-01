"""
GeographicScorer — criteria 1-5 for AI scheduling.

Scores geographic factors: proximity, intra-route drive time,
service zone boundaries, real-time traffic, and job site access.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 31.2, 31.3
"""

from __future__ import annotations

import math
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import CriterionResult, SchedulingContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class GeographicScorer(LoggerMixin):
    """Scores geographic criteria 1-5 for job-staff assignments."""

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
        """Score a geographic criterion for a job-staff pair."""
        method_map: dict[int, Callable[..., Coroutine[Any, Any, CriterionResult]]] = {
            1: self._score_proximity,
            2: self._score_intra_route_drive_time,
            3: self._score_zone_boundaries,
            4: self._score_traffic,
            5: self._score_access_constraints,
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
            explanation="Unknown geographic criterion",
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

    async def _score_proximity(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 1: Resource-to-job proximity.

        Score based on haversine distance. Closer = higher score.
        Score = max(0, 100 - (distance_km * 5)).
        """
        name = config.get("criterion_name", "Resource-to-Job Proximity")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        job_lat = job.get("latitude") or job.get("lat")
        job_lng = job.get("longitude") or job.get("lng")
        staff_lat = staff.get("latitude") or staff.get("lat")
        staff_lng = staff.get("longitude") or staff.get("lng")

        if not all(
            v is not None for v in [job_lat, job_lng, staff_lat, staff_lng]
        ):
            return CriterionResult(
                criterion_number=1,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="Missing coordinates; neutral score",
            )

        # Guaranteed non-None after the all() check above
        assert staff_lat is not None
        assert staff_lng is not None
        assert job_lat is not None
        assert job_lng is not None
        distance_km = self._haversine_km(
            float(staff_lat),
            float(staff_lng),
            float(job_lat),
            float(job_lng),
        )
        raw_score = max(0.0, 100.0 - (distance_km * 5.0))

        return CriterionResult(
            criterion_number=1,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Distance {distance_km:.1f} km → score {raw_score:.1f}"
            ),
        )

    async def _score_intra_route_drive_time(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 2: Intra-route drive time.

        Total cumulative drive time across daily route.
        Score = max(0, 100 - (total_minutes / 4)).
        """
        name = config.get("criterion_name", "Intra-Route Drive Time")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        total_drive_minutes = float(
            staff.get("total_drive_minutes", 0)
            or staff.get("route_drive_minutes", 0),
        )
        raw_score = max(0.0, 100.0 - (total_drive_minutes / 4.0))

        return CriterionResult(
            criterion_number=2,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Total drive {total_drive_minutes:.0f} min → "
                f"score {raw_score:.1f}"
            ),
        )

    async def _score_zone_boundaries(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 3: Service zone boundaries.

        In-zone = 100, out-of-zone = 30.
        """
        name = config.get("criterion_name", "Service Zone Boundaries")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        job_zone = job.get("service_zone_id")
        staff_zone = staff.get("service_zone_id")

        if not job_zone or not staff_zone:
            return CriterionResult(
                criterion_number=3,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No zone data; neutral score",
            )

        in_zone = str(job_zone) == str(staff_zone)
        raw_score = 100.0 if in_zone else 30.0

        return CriterionResult(
            criterion_number=3,
            criterion_name=name,
            score=raw_score,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                "In-zone match" if in_zone else "Out-of-zone assignment"
            ),
        )

    async def _score_traffic(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 4: Real-time traffic overlay.

        If traffic data available, adjust score. Fallback: 50 (neutral).
        """
        name = config.get("criterion_name", "Real-Time Traffic")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        traffic = context.traffic or {}
        congestion = traffic.get("congestion_factor")

        if congestion is None:
            return CriterionResult(
                criterion_number=4,
                criterion_name=name,
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No traffic data; neutral score",
            )

        factor = float(congestion)
        raw_score = max(0.0, 100.0 - (factor * 50.0))

        return CriterionResult(
            criterion_number=4,
            criterion_name=name,
            score=round(raw_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Traffic congestion factor {factor:.2f} → "
                f"score {raw_score:.1f}"
            ),
        )

    async def _score_access_constraints(
        self,
        config: dict[str, Any],
        job: dict[str, Any],
        staff: dict[str, Any],
        context: SchedulingContext,
    ) -> CriterionResult:
        """Criterion 5: Job site access constraints.

        Check gate codes, HOA hours. Constraints met = 100,
        violated = 0.
        """
        name = config.get("criterion_name", "Job Site Access Constraints")
        weight = config.get("weight", 50)
        is_hard = config.get("is_hard_constraint", False)

        access = job.get("access_constraints") or {}
        if not access:
            return CriterionResult(
                criterion_number=5,
                criterion_name=name,
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No access constraints",
            )

        violations: list[str] = []

        gate_code = access.get("gate_code")
        if gate_code and not staff.get("has_gate_codes", True):
            violations.append("Missing gate code access")

        hoa_start = access.get("hoa_start_hour")
        hoa_end = access.get("hoa_end_hour")
        slot_hour = job.get("scheduled_hour")
        if (
            hoa_start is not None
            and hoa_end is not None
            and slot_hour is not None
            and not (int(hoa_start) <= int(slot_hour) < int(hoa_end))
        ):
            violations.append(
                f"Outside HOA hours ({hoa_start}-{hoa_end})",
            )

        if violations:
            return CriterionResult(
                criterion_number=5,
                criterion_name=name,
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=f"Access violations: {', '.join(violations)}",
            )

        return CriterionResult(
            criterion_number=5,
            criterion_name=name,
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation="All access constraints satisfied",
        )
