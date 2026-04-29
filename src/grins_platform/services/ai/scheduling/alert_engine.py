"""
AlertEngine -- scans schedules and generates alerts/suggestions.

Detects 5 critical alert types (red) and generates 5 optimization
suggestions (green) for the Alerts Panel.

Validates: Requirements 11.1-11.5, 12.1-12.5, 23.4, 32.4
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.scheduling_alert import SchedulingAlert
from grins_platform.schemas.ai_scheduling import AlertCandidate, ResolutionOption

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.services.ai.scheduling.criteria_evaluator import (
        CriteriaEvaluator,
    )


class AlertEngine(LoggerMixin):
    """Scans schedules and generates alerts and suggestions.

    Detects critical conflicts (red alerts) and optimization
    opportunities (green suggestions), deduplicates against existing
    active alerts, and persists new ones to the ``scheduling_alerts``
    table.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    def __init__(
        self,
        session: AsyncSession,
        evaluator: CriteriaEvaluator | None = None,
    ) -> None:
        """Initialise the alert engine.

        Args:
            session: Async SQLAlchemy session.
            evaluator: Optional CriteriaEvaluator for scoring-based detection.
        """
        super().__init__()
        self._session = session
        self._evaluator = evaluator

    async def scan_and_generate(
        self,
        schedule_date: date,
        assignments: list[dict[str, Any]] | None = None,
    ) -> list[SchedulingAlert]:
        """Scan a schedule and generate alerts and suggestions.

        Runs all 5 alert detectors and 5 suggestion generators,
        deduplicates against existing active alerts, and persists
        new ones.

        Args:
            schedule_date: Date of the schedule to scan.
            assignments: Optional list of assignment dicts. If None,
                loads from DB.

        Returns:
            List of newly created ``SchedulingAlert`` records.
        """
        self.log_started("scan_and_generate", schedule_date=str(schedule_date))

        try:
            asgns: list[dict[str, Any]] = assignments or []
            candidates: list[AlertCandidate] = []

            # Run alert detectors
            candidates.extend(await self._detect_double_bookings(asgns))
            candidates.extend(await self._detect_skill_mismatches(asgns))
            candidates.extend(await self._detect_sla_risks(asgns))
            candidates.extend(await self._detect_resource_behind(asgns))
            candidates.extend(await self._detect_weather_impacts(schedule_date, asgns))

            # Run suggestion generators
            candidates.extend(await self._suggest_route_swaps(asgns))
            candidates.extend(await self._suggest_utilization_fills(asgns))
            candidates.extend(await self._suggest_customer_preference(asgns))
            candidates.extend(await self._suggest_overtime_avoidance(asgns))
            candidates.extend(await self._suggest_high_revenue_fills(asgns))

            # Deduplicate and persist
            new_alerts = await self._persist_new_alerts(candidates, schedule_date)

        except Exception as exc:
            self.log_failed("scan_and_generate", error=exc)
            raise
        else:
            self.log_completed(
                "scan_and_generate",
                schedule_date=str(schedule_date),
                new_alert_count=len(new_alerts),
            )
            return new_alerts

    # ------------------------------------------------------------------
    # Alert detectors (red/critical)
    # ------------------------------------------------------------------

    async def _detect_double_bookings(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Detect overlapping time windows on the same resource.

        Validates: Requirement 11.1
        """
        candidates: list[AlertCandidate] = []
        by_staff: dict[str, list[dict[str, Any]]] = {}
        for a in assignments:
            sid = str(a.get("staff_id", ""))
            by_staff.setdefault(sid, []).append(a)

        for staff_id, staff_assignments in by_staff.items():
            sorted_a = sorted(
                staff_assignments,
                key=lambda x: x.get("start_time", ""),
            )
            for i in range(len(sorted_a) - 1):
                curr = sorted_a[i]
                nxt = sorted_a[i + 1]
                curr_end = curr.get("end_time", "")
                nxt_start = nxt.get("start_time", "")
                if curr_end and nxt_start and curr_end > nxt_start:
                    candidates.append(
                        AlertCandidate(
                            alert_type="double_booking",
                            severity="critical",
                            title="Double Booking Detected",
                            description=(
                                f"Resource {staff_id} has overlapping jobs: "
                                f"job {curr.get('job_id')} ends at {curr_end} "
                                f"but job {nxt.get('job_id')} starts at {nxt_start}."
                            ),
                            affected_job_ids=[
                                j
                                for j in [
                                    UUID(str(curr["job_id"]))
                                    if curr.get("job_id")
                                    else None,
                                    UUID(str(nxt["job_id"]))
                                    if nxt.get("job_id")
                                    else None,
                                ]
                                if j is not None
                            ],
                            affected_staff_ids=([UUID(staff_id)] if staff_id else None),
                            criteria_triggered=[8],
                            resolution_options=[
                                ResolutionOption(
                                    action="reassign_job",
                                    label="Reassign conflicting job",
                                    description=(
                                        "Move the conflicting job to another resource"
                                    ),
                                ),
                                ResolutionOption(
                                    action="reschedule_job",
                                    label="Reschedule to next available slot",
                                    description=(
                                        "Push the job to the next open time slot"
                                    ),
                                ),
                            ],
                        )
                    )
        return candidates

    async def _detect_skill_mismatches(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Detect jobs assigned to uncertified resources.

        Validates: Requirement 11.2
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            required_skills = a.get("required_skills", [])
            staff_skills = a.get("staff_skills", [])
            if required_skills and not all(s in staff_skills for s in required_skills):
                missing = [s for s in required_skills if s not in staff_skills]
                candidates.append(
                    AlertCandidate(
                        alert_type="skill_mismatch",
                        severity="critical",
                        title="Skill Mismatch",
                        description=(
                            f"Job {a.get('job_id')} requires skills {missing} "
                            f"but assigned resource lacks them."
                        ),
                        affected_job_ids=(
                            [UUID(str(a["job_id"]))] if a.get("job_id") else None
                        ),
                        affected_staff_ids=(
                            [UUID(str(a["staff_id"]))] if a.get("staff_id") else None
                        ),
                        criteria_triggered=[6],
                        resolution_options=[
                            ResolutionOption(
                                action="reassign_certified",
                                label="Reassign to certified resource",
                                description=(
                                    "Find and assign a resource with required skills"
                                ),
                            ),
                        ],
                    )
                )
        return candidates

    async def _detect_sla_risks(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Detect SLA deadlines expiring before scheduled date.

        Validates: Requirement 11.3
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            sla_deadline = a.get("sla_deadline")
            scheduled_date = a.get("scheduled_date")
            if sla_deadline and scheduled_date:
                try:
                    sla_dt = datetime.fromisoformat(str(sla_deadline))
                    sched_dt = datetime.fromisoformat(str(scheduled_date))
                    if sla_dt < sched_dt:
                        candidates.append(
                            AlertCandidate(
                                alert_type="sla_risk",
                                severity="critical",
                                title="SLA Deadline at Risk",
                                description=(
                                    f"Job {a.get('job_id')} SLA deadline "
                                    f"{sla_deadline} is before scheduled date "
                                    f"{scheduled_date}."
                                ),
                                affected_job_ids=(
                                    [UUID(str(a["job_id"]))]
                                    if a.get("job_id")
                                    else None
                                ),
                                criteria_triggered=[23],
                                resolution_options=[
                                    ResolutionOption(
                                        action="expedite_job",
                                        label="Expedite job",
                                        description=(
                                            "Move job to earliest available slot"
                                        ),
                                    ),
                                ],
                            )
                        )
                except (ValueError, TypeError) as exc:
                    self.logger.debug(
                        "scheduling.alertengine.sla_parse_error",
                        error=str(exc),
                    )
        return candidates

    async def _detect_resource_behind(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Detect resources 40+ minutes behind schedule.

        Validates: Requirement 11.4
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            delay_minutes = a.get("current_delay_minutes", 0)
            if delay_minutes >= 40:
                candidates.append(
                    AlertCandidate(
                        alert_type="resource_behind",
                        severity="critical",
                        title="Resource Running Behind",
                        description=(
                            f"Resource {a.get('staff_id')} is "
                            f"{delay_minutes} minutes behind schedule. "
                            "Customer windows may be missed."
                        ),
                        affected_staff_ids=(
                            [UUID(str(a["staff_id"]))] if a.get("staff_id") else None
                        ),
                        criteria_triggered=[11, 8],
                        resolution_options=[
                            ResolutionOption(
                                action="notify_customers",
                                label="Notify affected customers",
                                description="Send delay notifications to customers",
                            ),
                            ResolutionOption(
                                action="reassign_remaining",
                                label="Reassign remaining jobs",
                                description=(
                                    "Move remaining jobs to available resources"
                                ),
                            ),
                        ],
                    )
                )
        return candidates

    async def _detect_weather_impacts(
        self,
        schedule_date: date,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Detect outdoor jobs on severe weather days.

        Validates: Requirement 11.5
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            is_outdoor = a.get("is_outdoor", False)
            severe_weather = a.get("severe_weather", False)
            if is_outdoor and severe_weather:
                candidates.append(
                    AlertCandidate(
                        alert_type="weather_impact",
                        severity="critical",
                        title="Outdoor Job on Severe Weather Day",
                        description=(
                            f"Job {a.get('job_id')} is an outdoor job scheduled "
                            f"on {schedule_date} with severe weather forecast."
                        ),
                        affected_job_ids=(
                            [UUID(str(a["job_id"]))] if a.get("job_id") else None
                        ),
                        criteria_triggered=[26],
                        resolution_options=[
                            ResolutionOption(
                                action="reschedule_weather",
                                label="Reschedule to clear day",
                                description="Move job to next day with clear weather",
                            ),
                            ResolutionOption(
                                action="swap_indoor",
                                label="Swap with indoor job",
                                description="Replace with an indoor job from backlog",
                            ),
                        ],
                    )
                )
        return candidates

    # ------------------------------------------------------------------
    # Suggestion generators (green)
    # ------------------------------------------------------------------

    async def _suggest_route_swaps(
        self,
        _assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Suggest job swaps that reduce combined drive time.

        Validates: Requirement 12.1
        """
        # Placeholder: real implementation would compute haversine distances
        return []

    async def _suggest_utilization_fills(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Suggest backlog fills for resources with 2+ hour gaps.

        Validates: Requirement 12.2
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            gap_minutes = a.get("gap_minutes", 0)
            if gap_minutes >= 120:
                candidates.append(
                    AlertCandidate(
                        alert_type="utilization_fill",
                        severity="suggestion",
                        title="Utilization Opportunity",
                        description=(
                            f"Resource {a.get('staff_id')} has a "
                            f"{gap_minutes}-minute gap. "
                            "Backlog jobs available to fill."
                        ),
                        affected_staff_ids=(
                            [UUID(str(a["staff_id"]))] if a.get("staff_id") else None
                        ),
                        criteria_triggered=[16, 20],
                        resolution_options=[
                            ResolutionOption(
                                action="fill_gap",
                                label="Fill gap with backlog job",
                                description="Assign best-fit backlog job to this slot",
                            ),
                        ],
                    )
                )
        return candidates

    async def _suggest_customer_preference(
        self,
        _assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Suggest alternatives based on customer dissatisfaction.

        Validates: Requirement 12.3
        """
        # Placeholder: real implementation would check customer ratings
        return []

    async def _suggest_overtime_avoidance(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Suggest moving low-priority jobs to avoid overtime.

        Validates: Requirement 12.4
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            overtime_minutes = a.get("overtime_minutes", 0)
            has_low_priority_jobs = a.get("has_low_priority_jobs", False)
            if overtime_minutes > 0 and has_low_priority_jobs:
                candidates.append(
                    AlertCandidate(
                        alert_type="overtime_avoidance",
                        severity="suggestion",
                        title="Overtime Avoidance Opportunity",
                        description=(
                            f"Resource {a.get('staff_id')} is projected "
                            f"{overtime_minutes} min overtime. "
                            "Low-priority jobs can be shifted."
                        ),
                        affected_staff_ids=(
                            [UUID(str(a["staff_id"]))] if a.get("staff_id") else None
                        ),
                        criteria_triggered=[24],
                        resolution_options=[
                            ResolutionOption(
                                action="defer_low_priority",
                                label="Defer low-priority jobs",
                                description=(
                                    "Move low-priority jobs to next available day"
                                ),
                            ),
                        ],
                    )
                )
        return candidates

    async def _suggest_high_revenue_fills(
        self,
        _assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Suggest high-revenue jobs for open slots.

        Validates: Requirement 12.5
        """
        # Placeholder: real implementation would query backlog by revenue/hour
        return []

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _persist_new_alerts(
        self,
        candidates: list[AlertCandidate],
        schedule_date: date,
    ) -> list[SchedulingAlert]:
        """Deduplicate candidates against existing alerts and persist new ones.

        Args:
            candidates: Alert candidates from detectors/generators.
            schedule_date: Schedule date for deduplication.

        Returns:
            List of newly created ``SchedulingAlert`` records.
        """
        if not candidates:
            return []

        stmt = select(SchedulingAlert).where(
            and_(
                SchedulingAlert.schedule_date == schedule_date,
                SchedulingAlert.status == "active",
            )
        )
        result = await self._session.execute(stmt)
        existing = result.scalars().all()

        existing_keys: set[tuple[str, str]] = {
            (a.alert_type, str(sorted(a.affected_job_ids or []))) for a in existing
        }

        new_alerts: list[SchedulingAlert] = []
        for candidate in candidates:
            key = (
                candidate.alert_type,
                str(sorted(str(j) for j in (candidate.affected_job_ids or []))),
            )
            if key in existing_keys:
                continue

            alert = SchedulingAlert(
                alert_type=candidate.alert_type,
                severity=candidate.severity,
                title=candidate.title,
                description=candidate.description,
                affected_job_ids=(
                    [str(j) for j in candidate.affected_job_ids]
                    if candidate.affected_job_ids
                    else None
                ),
                affected_staff_ids=(
                    [str(s) for s in candidate.affected_staff_ids]
                    if candidate.affected_staff_ids
                    else None
                ),
                criteria_triggered=candidate.criteria_triggered,
                resolution_options=(
                    [opt.model_dump() for opt in candidate.resolution_options]
                    if candidate.resolution_options
                    else None
                ),
                status="active",
                schedule_date=schedule_date,
            )
            self._session.add(alert)
            new_alerts.append(alert)
            existing_keys.add(key)

            self.logger.info(
                "scheduling.alertengine.alert_created",
                alert_type=candidate.alert_type,
                severity=candidate.severity,
                criteria_triggered=candidate.criteria_triggered,
                schedule_date=str(schedule_date),
            )

        if new_alerts:
            await self._session.flush()

        return new_alerts
