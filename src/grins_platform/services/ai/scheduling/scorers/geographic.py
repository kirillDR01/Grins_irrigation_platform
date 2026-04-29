"""
GeographicScorer - criteria 1-5 for AI scheduling.

Evaluates geographic and logistics constraints for job-staff assignments:
  1. Resource-to-job proximity (haversine / Google Maps drive-time)
  2. Intra-route drive time (cumulative daily route)
  3. Service zone boundaries (in-zone vs cross-zone)
  4. Real-time traffic overlay (Google Maps traffic data)
  5. Job site access constraints (gate codes, HOA, access windows - hard)

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 31.2, 31.3
"""

from __future__ import annotations

from datetime import datetime, time
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

# Criterion 1 — proximity
_PROXIMITY_BEST_MINUTES = 5  # score 100 at ≤5 min
_PROXIMITY_WORST_MINUTES = 60  # score 0 at ≥60 min

# Criterion 2 — intra-route drive time
_ROUTE_BEST_MINUTES = 30  # score 100 at ≤30 min total
_ROUTE_WORST_MINUTES = 180  # score 0 at ≥180 min total

# Criterion 3 — zone scoring
_ZONE_IN_SCORE = 100
_ZONE_CROSS_MIN_SCORE = 50
_ZONE_CROSS_MAX_SCORE = 80


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
# GeographicScorer
# ---------------------------------------------------------------------------


class GeographicScorer(LoggerMixin):
    """Score geographic / logistics criteria 1-5.

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
        """Score a job-staff assignment for geographic criteria 1-5.

        Args:
            job: The job being evaluated.
            staff: The candidate staff member.
            context: Scheduling context (date, weather, traffic, backlog).
            config: Per-criterion configuration (weights, hard/soft).

        Returns:
            List of ``CriterionResult`` objects for criteria 1-5.
        """
        self.log_started(
            "score_assignment",
            job_id=str(job.id),
            staff_id=str(staff.id),
        )

        results: list[CriterionResult] = []

        try:
            results.append(await self._score_proximity(job, staff, context, config))
            results.append(
                await self._score_intra_route_drive_time(job, staff, context, config),
            )
            results.append(
                await self._score_service_zone(job, staff, context, config),
            )
            results.append(
                await self._score_realtime_traffic(job, staff, context, config),
            )
            results.append(
                await self._score_access_constraints(job, staff, context, config),
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
    # Criterion 1 — Resource-to-job proximity
    # ------------------------------------------------------------------

    async def _score_proximity(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 1: Resource-to-job proximity.

        Score based on haversine distance between the resource's start
        location and the job site.  Uses ``haversine_travel_minutes``
        from ``schedule_constraints``.  Falls back from Google Maps
        drive-time when available in context.

        Score 100 for ≤5 min, linearly decreasing to 0 at ≥60 min.
        """
        cfg = config.get(1)
        weight = cfg.weight if cfg else 80
        is_hard = cfg.is_hard_constraint if cfg else False

        # Try Google Maps drive-time from context first
        travel_minutes: float | None = self._get_google_drive_time(
            staff,
            job,
            context,
        )

        if travel_minutes is None:
            # Fallback to haversine
            travel_minutes = float(
                haversine_travel_minutes(
                    float(staff.start_location.latitude),
                    float(staff.start_location.longitude),
                    float(job.location.latitude),
                    float(job.location.longitude),
                ),
            )
            source = "haversine"
        else:
            source = "google_maps"

        score = _linear_score(
            travel_minutes,
            _PROXIMITY_BEST_MINUTES,
            _PROXIMITY_WORST_MINUTES,
        )

        explanation = (
            f"Travel time {travel_minutes:.0f} min ({source}). "
            f"Score {score:.0f}/100 "
            f"(100 at ≤{_PROXIMITY_BEST_MINUTES} min, "
            f"0 at ≥{_PROXIMITY_WORST_MINUTES} min)."
        )

        return CriterionResult(
            criterion_number=1,
            criterion_name="Resource-to-job proximity",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 2 — Intra-route drive time
    # ------------------------------------------------------------------

    async def _score_intra_route_drive_time(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 2: Intra-route drive time.

        Total cumulative drive time across all jobs in the resource's
        daily route.  Uses the resource's current route from context
        (``context.traffic`` may contain ``route_jobs`` keyed by staff
        id).  Score 100 for ≤30 min total, linearly decreasing to 0
        at ≥180 min.
        """
        cfg = config.get(2)
        weight = cfg.weight if cfg else 70
        is_hard = cfg.is_hard_constraint if cfg else False

        route_jobs = self._get_route_jobs(staff, context)

        # Calculate cumulative drive time across the route
        total_drive_minutes = 0.0

        if route_jobs:
            # Drive from staff start to first job
            first = route_jobs[0]
            total_drive_minutes += float(
                haversine_travel_minutes(
                    float(staff.start_location.latitude),
                    float(staff.start_location.longitude),
                    float(first.location.latitude),
                    float(first.location.longitude),
                ),
            )

            # Drive between consecutive jobs
            for i in range(len(route_jobs) - 1):
                j1 = route_jobs[i]
                j2 = route_jobs[i + 1]
                total_drive_minutes += float(
                    haversine_travel_minutes(
                        float(j1.location.latitude),
                        float(j1.location.longitude),
                        float(j2.location.latitude),
                        float(j2.location.longitude),
                    ),
                )

            # Include drive to the new job from the last route job
            last = route_jobs[-1]
            if job.id != last.id:
                total_drive_minutes += float(
                    haversine_travel_minutes(
                        float(last.location.latitude),
                        float(last.location.longitude),
                        float(job.location.latitude),
                        float(job.location.longitude),
                    ),
                )
        else:
            # No existing route — just the drive from start to this job
            total_drive_minutes = float(
                haversine_travel_minutes(
                    float(staff.start_location.latitude),
                    float(staff.start_location.longitude),
                    float(job.location.latitude),
                    float(job.location.longitude),
                ),
            )

        score = _linear_score(
            total_drive_minutes,
            _ROUTE_BEST_MINUTES,
            _ROUTE_WORST_MINUTES,
        )

        explanation = (
            f"Cumulative route drive time {total_drive_minutes:.0f} min "
            f"across {len(route_jobs) + 1} stops. "
            f"Score {score:.0f}/100 "
            f"(100 at ≤{_ROUTE_BEST_MINUTES} min, "
            f"0 at ≥{_ROUTE_WORST_MINUTES} min)."
        )

        return CriterionResult(
            criterion_number=2,
            criterion_name="Intra-route drive time",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 3 — Service zone boundaries
    # ------------------------------------------------------------------

    async def _score_service_zone(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 3: Service zone boundaries.

        Check job location against ``service_zones`` data in context.
        Prefer in-zone resources (score 100).  Allow cross-zone if
        more efficient (score 50-80 based on distance savings).

        If zone data is unavailable, return a neutral score with
        explanation.
        """
        cfg = config.get(3)
        weight = cfg.weight if cfg else 60
        is_hard = cfg.is_hard_constraint if cfg else False

        zones = self._get_service_zones(context)
        staff_zone_id = self._get_staff_zone_id(staff, context)
        job_zone_id = self._find_job_zone(job, zones)

        # No zone data available — neutral score
        if not zones or staff_zone_id is None:
            return CriterionResult(
                criterion_number=3,
                criterion_name="Service zone boundaries",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=("Service zone data unavailable — neutral score applied."),
            )

        # In-zone assignment
        if job_zone_id is not None and job_zone_id == staff_zone_id:
            return CriterionResult(
                criterion_number=3,
                criterion_name="Service zone boundaries",
                score=_ZONE_IN_SCORE,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    f"Job is within staff's assigned zone ({staff_zone_id}). "
                    f"Score {_ZONE_IN_SCORE}/100."
                ),
            )

        # Cross-zone — score 50-80 based on proximity savings
        travel_minutes = float(
            haversine_travel_minutes(
                float(staff.start_location.latitude),
                float(staff.start_location.longitude),
                float(job.location.latitude),
                float(job.location.longitude),
            ),
        )

        # Closer cross-zone jobs get higher scores (up to 80)
        cross_zone_score = _ZONE_CROSS_MIN_SCORE + (
            (_ZONE_CROSS_MAX_SCORE - _ZONE_CROSS_MIN_SCORE)
            * max(0.0, 1.0 - travel_minutes / _PROXIMITY_WORST_MINUTES)
        )
        cross_zone_score = min(cross_zone_score, _ZONE_CROSS_MAX_SCORE)

        zone_label = job_zone_id if job_zone_id else "unknown"
        return CriterionResult(
            criterion_number=3,
            criterion_name="Service zone boundaries",
            score=round(cross_zone_score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=(
                f"Cross-zone assignment: staff zone {staff_zone_id}, "
                f"job zone {zone_label}. "
                f"Travel {travel_minutes:.0f} min. "
                f"Score {cross_zone_score:.0f}/100."
            ),
        )

    # ------------------------------------------------------------------
    # Criterion 4 — Real-time traffic
    # ------------------------------------------------------------------

    async def _score_realtime_traffic(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 4: Real-time traffic.

        Overlay Google Maps traffic data on route calculations and
        adjust ETAs.  If traffic data is unavailable, return a neutral
        score (50) with explanation — this criterion is skipped
        gracefully.
        """
        cfg = config.get(4)
        weight = cfg.weight if cfg else 50
        is_hard = cfg.is_hard_constraint if cfg else False

        traffic_data = self._get_traffic_data(context)

        if traffic_data is None:
            return CriterionResult(
                criterion_number=4,
                criterion_name="Real-time traffic",
                score=50.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation=(
                    "Traffic API unavailable — neutral score applied. "
                    "ETAs based on haversine estimates only."
                ),
            )

        # Extract traffic multiplier for the staff→job route segment
        traffic_multiplier = self._extract_traffic_multiplier(
            staff,
            job,
            traffic_data,
        )

        # Base travel time without traffic
        base_minutes = float(
            haversine_travel_minutes(
                float(staff.start_location.latitude),
                float(staff.start_location.longitude),
                float(job.location.latitude),
                float(job.location.longitude),
            ),
        )

        adjusted_minutes = base_minutes * traffic_multiplier

        # Score: 100 if traffic adds no delay, decreasing as delay grows
        # A multiplier of 1.0 = no delay (score 100)
        # A multiplier of 2.0+ = severe delay (score 0)
        if traffic_multiplier <= 1.0:
            score = 100.0
        elif traffic_multiplier >= 2.0:
            score = 0.0
        else:
            score = 100.0 * (1.0 - (traffic_multiplier - 1.0))

        explanation = (
            f"Traffic multiplier {traffic_multiplier:.2f}x. "
            f"Base {base_minutes:.0f} min → adjusted {adjusted_minutes:.0f} min. "
            f"Score {score:.0f}/100."
        )

        return CriterionResult(
            criterion_number=4,
            criterion_name="Real-time traffic",
            score=round(score, 2),
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Criterion 5 — Job site access constraints (HARD)
    # ------------------------------------------------------------------

    async def _score_access_constraints(
        self,
        job: ScheduleJob,
        staff: ScheduleStaff,  # noqa: ARG002
        context: SchedulingContext,
        config: dict[int, _CriterionConfig],
    ) -> CriterionResult:
        """Criterion 5: Job site access constraints.

        Check gate codes, HOA entry requirements, and construction
        access windows from customer/job data.  This is a **hard
        constraint** — score 0 and ``is_satisfied=False`` if the
        access window doesn't match the scheduled time.

        If no access constraints exist, the criterion is satisfied
        with a perfect score.
        """
        cfg = config.get(5)
        weight = cfg.weight if cfg else 90
        is_hard = cfg.is_hard_constraint if cfg else True  # default hard

        access_info = self._get_access_info(job, context)

        # No access constraints — fully satisfied
        if not access_info:
            return CriterionResult(
                criterion_number=5,
                criterion_name="Job site access constraints",
                score=100.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=True,
                explanation="No access constraints on this job site.",
            )

        # Check access window
        access_start = access_info.get("access_window_start")
        access_end = access_info.get("access_window_end")
        gate_code = access_info.get("gate_code")
        hoa_requirements = access_info.get("hoa_requirements")

        issues: list[str] = []
        has_window_violation = False

        if access_start and access_end:
            # Parse access window times
            window_start = self._parse_time(access_start)
            window_end = self._parse_time(access_end)

            if window_start is not None and window_end is not None:
                # Check if the job's preferred time falls within the
                # access window.  Use the job's preferred_time_start
                # as the scheduled arrival time.
                scheduled_time = job.preferred_time_start

                if scheduled_time is not None:
                    if scheduled_time < window_start or scheduled_time > window_end:
                        has_window_violation = True
                        start_fmt = window_start.strftime("%H:%M")
                        end_fmt = window_end.strftime("%H:%M")
                        sched_fmt = scheduled_time.strftime("%H:%M")
                        msg = (
                            f"Scheduled time {sched_fmt} "
                            f"outside access window "
                            f"{start_fmt}-{end_fmt}"
                        )
                        issues.append(msg)
                else:
                    # No scheduled time yet - note the constraint
                    start_fmt = window_start.strftime("%H:%M")
                    end_fmt = window_end.strftime("%H:%M")
                    msg = (
                        f"Access window {start_fmt}-{end_fmt} "
                        f"must be respected during scheduling"
                    )
                    issues.append(msg)

        # Build notes about other access requirements
        notes: list[str] = []
        if gate_code:
            notes.append(f"Gate code: {gate_code}")
        if hoa_requirements:
            notes.append(f"HOA: {hoa_requirements}")

        if has_window_violation:
            explanation_parts = ["ACCESS VIOLATION: " + "; ".join(issues)]
            if notes:
                explanation_parts.append("Additional: " + ", ".join(notes))
            return CriterionResult(
                criterion_number=5,
                criterion_name="Job site access constraints",
                score=0.0,
                weight=weight,
                is_hard=is_hard,
                is_satisfied=False,
                explanation=". ".join(explanation_parts) + ".",
            )

        # No violation — build explanation with any noted constraints
        explanation_parts = ["Access constraints satisfied"]
        if issues:
            explanation_parts.append("; ".join(issues))
        if notes:
            explanation_parts.append(", ".join(notes))

        return CriterionResult(
            criterion_number=5,
            criterion_name="Job site access constraints",
            score=100.0,
            weight=weight,
            is_hard=is_hard,
            is_satisfied=True,
            explanation=". ".join(explanation_parts) + ".",
        )

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _get_google_drive_time(
        self,
        staff: ScheduleStaff,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> float | None:
        """Extract Google Maps drive-time from context if available.

        Looks for ``context.traffic["drive_times"]`` keyed by
        ``"{staff_id}:{job_id}"``.
        """
        if context.traffic is None:
            return None

        drive_times: dict[str, Any] = context.traffic.get("drive_times", {})
        key = f"{staff.id}:{job.id}"
        value = drive_times.get(key)

        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return None

    def _get_route_jobs(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> list[ScheduleJob]:
        """Get the resource's current daily route from context.

        Looks for ``context.traffic["route_jobs"]`` keyed by staff id.
        Returns an empty list if unavailable.
        """
        if context.traffic is None:
            return []

        route_data: dict[str, Any] = context.traffic.get("route_jobs", {})
        jobs = route_data.get(str(staff.id), [])

        if isinstance(jobs, list):
            # Filter to actual ScheduleJob instances
            from grins_platform.services.schedule_domain import (  # noqa: PLC0415
                ScheduleJob as ScheduleJobType,
            )

            return [j for j in jobs if isinstance(j, ScheduleJobType)]
        return []

    def _get_service_zones(
        self,
        context: SchedulingContext,
    ) -> list[dict[str, Any]]:
        """Extract service zone data from context.

        Looks for ``context.backlog["service_zones"]`` — a list of
        zone dicts with ``id``, ``name``, ``boundary_data``,
        ``assigned_staff_ids``.
        """
        if context.backlog is None:
            return []

        zones = context.backlog.get("service_zones", [])
        if isinstance(zones, list):
            return zones  # type: ignore[return-value]
        return []

    def _get_staff_zone_id(
        self,
        staff: ScheduleStaff,
        context: SchedulingContext,
    ) -> str | None:
        """Determine the staff member's assigned zone.

        Checks ``context.backlog["staff_zones"]`` keyed by staff id,
        or iterates zone ``assigned_staff_ids`` lists.
        """
        if context.backlog is None:
            return None

        # Direct lookup
        staff_zones: dict[str, Any] = context.backlog.get("staff_zones", {})
        zone_id = staff_zones.get(str(staff.id))
        if zone_id is not None:
            return str(zone_id)

        # Search zone assigned_staff_ids
        zones = self._get_service_zones(context)
        for zone in zones:
            assigned = zone.get("assigned_staff_ids", [])
            if isinstance(assigned, list) and str(staff.id) in [
                str(s) for s in assigned
            ]:
                return str(zone.get("id", zone.get("name", "")))

        return None

    def _find_job_zone(
        self,
        job: ScheduleJob,
        zones: list[dict[str, Any]],
    ) -> str | None:
        """Determine which zone a job falls in.

        Uses a simple bounding-box check against zone boundary data.
        Returns the zone id/name or ``None`` if no match.
        """
        if not zones:
            return None

        job_lat = float(job.location.latitude)
        job_lon = float(job.location.longitude)

        for zone in zones:
            boundary = zone.get("boundary_data", {})
            if not isinstance(boundary, dict):
                continue

            # Support bounding-box boundaries
            min_lat = boundary.get("min_lat")
            max_lat = boundary.get("max_lat")
            min_lon = boundary.get("min_lon")
            max_lon = boundary.get("max_lon")

            if min_lat is None or max_lat is None or min_lon is None or max_lon is None:
                continue

            if float(min_lat) <= job_lat <= float(max_lat) and float(
                min_lon
            ) <= job_lon <= float(max_lon):
                return str(zone.get("id", zone.get("name", "")))

        return None

    def _get_traffic_data(
        self,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract traffic data from context.

        Returns ``context.traffic`` if it contains a
        ``traffic_multipliers`` key, otherwise ``None``.
        """
        if context.traffic is None:
            return None

        if "traffic_multipliers" in context.traffic:
            return context.traffic
        return None

    def _extract_traffic_multiplier(
        self,
        staff: ScheduleStaff,
        job: ScheduleJob,
        traffic_data: dict[str, Any],
    ) -> float:
        """Extract the traffic multiplier for a staff→job route.

        Looks for ``traffic_multipliers["{staff_id}:{job_id}"]``.
        Falls back to a global multiplier or 1.0 (no delay).
        """
        multipliers: dict[str, Any] = traffic_data.get(
            "traffic_multipliers",
            {},
        )

        key = f"{staff.id}:{job.id}"
        value = multipliers.get(key)

        if value is not None:
            try:
                return max(0.1, float(value))
            except (TypeError, ValueError):
                self.logger.debug(
                    "scheduling.geographicscorer.invalid_traffic_multiplier",
                    key=key,
                    value=str(value),
                )

        # Global fallback multiplier
        global_mult = multipliers.get("global")
        if global_mult is not None:
            try:
                return max(0.1, float(global_mult))
            except (TypeError, ValueError):
                self.logger.debug(
                    "scheduling.geographicscorer.invalid_global_traffic_multiplier",
                    value=str(global_mult),
                )

        return 1.0

    def _get_access_info(
        self,
        job: ScheduleJob,
        context: SchedulingContext,
    ) -> dict[str, Any] | None:
        """Extract job site access constraint info.

        Looks for ``context.backlog["access_constraints"]`` keyed by
        job id.  Returns a dict with optional keys:
        ``access_window_start``, ``access_window_end``, ``gate_code``,
        ``hoa_requirements``.
        """
        if context.backlog is None:
            return None

        constraints = context.backlog.get("access_constraints")
        if not isinstance(constraints, dict):
            return None

        info = constraints.get(str(job.id))
        if isinstance(info, dict) and info:
            return info
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
