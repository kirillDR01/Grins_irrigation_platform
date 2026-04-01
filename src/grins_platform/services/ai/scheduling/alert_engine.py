"""
AlertEngine service for autonomous alert and suggestion generation.

Scans schedule state and generates critical alerts (red) for conflicts
and optimization suggestions (green) for improvements. Deduplicates
against existing active alerts and persists new ones to the database.

Validates: Requirements 11.1-11.5, 12.1-12.5, 23.4, 32.4
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.scheduling_alert import SchedulingAlert
from grins_platform.schemas.ai_scheduling import AlertCandidate, ResolutionOption

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AlertEngine(LoggerMixin):
    """Autonomous alert and suggestion generator.

    Scans current schedule state for conflicts (red alerts) and
    optimization opportunities (green suggestions). Each detector
    and generator produces ``AlertCandidate`` objects which are
    deduplicated against existing active alerts before persistence.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the alert engine.

        Args:
            session: Async database session for data access.
        """
        super().__init__()
        self._session = session

    # ------------------------------------------------------------------
    # Main scan entry point
    # ------------------------------------------------------------------

    async def scan_and_generate(
        self,
        schedule_date: date,
    ) -> list[SchedulingAlert]:
        """Scan schedule state and generate alerts/suggestions.

        Runs all 5 alert detectors and 5 suggestion generators,
        deduplicates candidates against existing active alerts,
        persists new alerts, and returns the persisted models.

        Args:
            schedule_date: The date to scan for conflicts and
                optimisation opportunities.

        Returns:
            List of newly persisted ``SchedulingAlert`` instances.
        """
        self.log_started("scan_and_generate", schedule_date=str(schedule_date))

        # Placeholder assignment / job data — will be wired to real
        # queries against appointments + jobs tables in a later task.
        assignments: list[dict[str, Any]] = []
        jobs: list[dict[str, Any]] = []
        open_slots: list[dict[str, Any]] = []

        # Collect candidates from all detectors and generators.
        candidates: list[AlertCandidate] = []

        # --- Red / critical alert detectors ---
        candidates.extend(await self._detect_double_bookings(assignments))
        candidates.extend(await self._detect_skill_mismatches(assignments))
        candidates.extend(await self._detect_sla_risks(jobs))
        candidates.extend(await self._detect_resource_behind(assignments))
        candidates.extend(
            await self._detect_weather_impacts(schedule_date, jobs),
        )

        # --- Green / suggestion generators ---
        candidates.extend(await self._suggest_route_swaps(assignments))
        candidates.extend(await self._suggest_utilization_fills(assignments))
        candidates.extend(await self._suggest_customer_preference(assignments))
        candidates.extend(await self._suggest_overtime_avoidance(assignments))
        candidates.extend(await self._suggest_high_revenue_fills(open_slots))

        # Deduplicate and persist.
        new_alerts = await self._deduplicate_and_persist(
            candidates,
            schedule_date,
        )

        self.log_completed(
            "scan_and_generate",
            schedule_date=str(schedule_date),
            total_candidates=len(candidates),
            new_alerts=len(new_alerts),
        )
        return new_alerts

    # ------------------------------------------------------------------
    # Alert detectors (red / critical)
    # ------------------------------------------------------------------

    async def _detect_double_bookings(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find overlapping time windows on the same resource.

        Args:
            assignments: List of assignment dicts with resource_id,
                job_id, start, end keys.

        Returns:
            Alert candidates for any detected double-bookings.
        """
        candidates: list[AlertCandidate] = []

        # Group assignments by resource.
        by_resource: dict[str, list[dict[str, Any]]] = {}
        for a in assignments:
            rid = str(a.get("resource_id", ""))
            by_resource.setdefault(rid, []).append(a)

        for rid, res_assignments in by_resource.items():
            sorted_a = sorted(res_assignments, key=lambda x: x.get("start", ""))
            for i in range(len(sorted_a) - 1):
                current_end = sorted_a[i].get("end", "")
                next_start = sorted_a[i + 1].get("start", "")
                if current_end > next_start:
                    job_ids = [
                        UUID(str(sorted_a[i].get("job_id", ""))),
                        UUID(str(sorted_a[i + 1].get("job_id", ""))),
                    ]
                    candidates.append(
                        AlertCandidate(
                            alert_type="double_booking",
                            severity="critical",
                            title="Double-Booking Conflict",
                            description=(
                                f"Resource {rid} has overlapping jobs "
                                f"at {current_end}/{next_start}."
                            ),
                            affected_job_ids=job_ids,
                            affected_staff_ids=[UUID(rid)],
                            criteria_triggered=[1, 8],
                            resolution_options=[
                                ResolutionOption(
                                    action="reassign",
                                    label="Reassign one job",
                                    description="Move one job to another resource.",
                                    parameters={},
                                ),
                                ResolutionOption(
                                    action="shift_time",
                                    label="Shift by 30 min",
                                    description="Shift one job by 30 minutes.",
                                    parameters={"shift_minutes": 30},
                                ),
                            ],
                        ),
                    )
        return candidates

    async def _detect_skill_mismatches(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find jobs assigned to uncertified resources.

        Args:
            assignments: List of assignment dicts with resource_id,
                job_id, required_skills, resource_skills keys.

        Returns:
            Alert candidates for any detected skill mismatches.
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            required = set(a.get("required_skills", []))
            held = set(a.get("resource_skills", []))
            missing = required - held
            if missing:
                candidates.append(
                    AlertCandidate(
                        alert_type="skill_mismatch",
                        severity="critical",
                        title="Skill Mismatch",
                        description=(
                            f"Resource {a.get('resource_id')} lacks "
                            f"skills: {', '.join(sorted(missing))}."
                        ),
                        affected_job_ids=[UUID(str(a.get("job_id", "")))],
                        affected_staff_ids=[UUID(str(a.get("resource_id", "")))],
                        criteria_triggered=[6],
                        resolution_options=[
                            ResolutionOption(
                                action="swap_resource",
                                label="Swap to certified resource",
                                description="Reassign to a certified resource.",
                                parameters={},
                            ),
                        ],
                    ),
                )
        return candidates

    async def _detect_sla_risks(
        self,
        jobs: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find SLA deadlines expiring before the scheduled date.

        Args:
            jobs: List of job dicts with job_id, sla_deadline,
                scheduled_date keys.

        Returns:
            Alert candidates for any SLA deadline risks.
        """
        candidates: list[AlertCandidate] = []
        for j in jobs:
            sla = j.get("sla_deadline")
            scheduled = j.get("scheduled_date")
            if sla and scheduled and str(scheduled) > str(sla):
                candidates.append(
                    AlertCandidate(
                        alert_type="sla_risk",
                        severity="critical",
                        title="SLA Deadline at Risk",
                        description=(
                            f"Job {j.get('job_id')} SLA deadline "
                            f"{sla} is before scheduled date {scheduled}."
                        ),
                        affected_job_ids=[UUID(str(j.get("job_id", "")))],
                        criteria_triggered=[23],
                        resolution_options=[
                            ResolutionOption(
                                action="force_schedule",
                                label="Force-schedule today",
                                description="Move job to today to meet SLA.",
                                parameters={},
                            ),
                            ResolutionOption(
                                action="override_sla",
                                label="Accept SLA miss",
                                description="Override and accept the SLA miss.",
                                parameters={},
                            ),
                        ],
                    ),
                )
        return candidates

    async def _detect_resource_behind(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find resources 40+ minutes behind schedule.

        Args:
            assignments: List of assignment dicts with resource_id,
                job_id, expected_time, actual_time keys.

        Returns:
            Alert candidates for resources running behind.
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            delay = int(a.get("delay_minutes", 0))
            if delay >= 40:
                candidates.append(
                    AlertCandidate(
                        alert_type="resource_behind",
                        severity="critical",
                        title="Resource Running Behind",
                        description=(
                            f"Resource {a.get('resource_id')} is "
                            f"{delay} minutes behind schedule."
                        ),
                        affected_job_ids=[UUID(str(a.get("job_id", "")))],
                        affected_staff_ids=[UUID(str(a.get("resource_id", "")))],
                        criteria_triggered=[8],
                        resolution_options=[
                            ResolutionOption(
                                action="absorb_delay",
                                label="Absorb delay",
                                description="Keep current route, update ETAs.",
                                parameters={},
                            ),
                            ResolutionOption(
                                action="move_last_job",
                                label="Move last job",
                                description="Move last job to another resource.",
                                parameters={},
                            ),
                        ],
                    ),
                )
        return candidates

    async def _detect_weather_impacts(
        self,
        schedule_date: date,
        jobs: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find outdoor jobs on severe weather days.

        Args:
            schedule_date: The date to check weather for.
            jobs: List of job dicts with job_id, is_outdoor keys.

        Returns:
            Alert candidates for weather-impacted outdoor jobs.
        """
        # Placeholder: weather data will come from external service.
        severe_weather = False  # Will be wired to Weather API later.
        if not severe_weather:
            return []

        candidates: list[AlertCandidate] = []
        outdoor_job_ids = [
            UUID(str(j.get("job_id", "")))
            for j in jobs
            if j.get("is_outdoor", False)
        ]
        if outdoor_job_ids:
            candidates.append(
                AlertCandidate(
                    alert_type="severe_weather",
                    severity="critical",
                    title="Severe Weather Impact",
                    description=(
                        f"Severe weather forecast for {schedule_date}. "
                        f"{len(outdoor_job_ids)} outdoor job(s) affected."
                    ),
                    affected_job_ids=outdoor_job_ids,
                    criteria_triggered=[26],
                    resolution_options=[
                        ResolutionOption(
                            action="batch_reschedule",
                            label="Batch reschedule outdoor jobs",
                            description="Move all outdoor jobs to next clear day.",
                            parameters={},
                        ),
                    ],
                ),
            )
        return candidates

    # ------------------------------------------------------------------
    # Suggestion generators (green)
    # ------------------------------------------------------------------

    async def _suggest_route_swaps(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find job swaps that reduce combined drive time.

        Args:
            assignments: List of assignment dicts with resource_id,
                job_id, drive_time_minutes keys.

        Returns:
            Suggestion candidates for beneficial route swaps.
        """
        candidates: list[AlertCandidate] = []
        # Group by resource for pairwise comparison.
        by_resource: dict[str, list[dict[str, Any]]] = {}
        for a in assignments:
            rid = str(a.get("resource_id", ""))
            by_resource.setdefault(rid, []).append(a)

        resource_ids = list(by_resource.keys())
        for i in range(len(resource_ids)):
            for j in range(i + 1, len(resource_ids)):
                r1, r2 = resource_ids[i], resource_ids[j]
                jobs_r1 = by_resource[r1]
                jobs_r2 = by_resource[r2]
                # Stub: real implementation would compute drive-time
                # savings for each possible swap pair.
                if jobs_r1 and jobs_r2:
                    current_drive = sum(
                        int(x.get("drive_time_minutes", 0)) for x in jobs_r1
                    ) + sum(
                        int(x.get("drive_time_minutes", 0)) for x in jobs_r2
                    )
                    # Placeholder — actual swap analysis deferred.
                    if current_drive > 120:
                        candidates.append(
                            AlertCandidate(
                                alert_type="route_swap",
                                severity="suggestion",
                                title="Route Swap Opportunity",
                                description=(
                                    f"Swapping jobs between {r1} and {r2} "
                                    f"may reduce combined drive time."
                                ),
                                affected_staff_ids=[UUID(r1), UUID(r2)],
                                criteria_triggered=[1, 2],
                                resolution_options=[
                                    ResolutionOption(
                                        action="accept_swap",
                                        label="Accept swap",
                                        description="Execute the proposed route swap.",
                                        parameters={
                                            "resource_a": r1,
                                            "resource_b": r2,
                                        },
                                    ),
                                ],
                            ),
                        )
        return candidates

    async def _suggest_utilization_fills(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find resources with 2+ hour gaps and matching backlog.

        Args:
            assignments: List of assignment dicts with resource_id,
                total_minutes, available_minutes keys.

        Returns:
            Suggestion candidates for filling utilization gaps.
        """
        candidates: list[AlertCandidate] = []
        by_resource: dict[str, dict[str, Any]] = {}
        for a in assignments:
            rid = str(a.get("resource_id", ""))
            if rid not in by_resource:
                by_resource[rid] = {
                    "total_minutes": 0,
                    "available_minutes": int(a.get("available_minutes", 480)),
                }
            by_resource[rid]["total_minutes"] += int(
                a.get("job_duration_minutes", 0),
            ) + int(a.get("drive_time_minutes", 0))

        for rid, info in by_resource.items():
            gap = info["available_minutes"] - info["total_minutes"]
            if gap >= 120:
                candidates.append(
                    AlertCandidate(
                        alert_type="underutilized",
                        severity="suggestion",
                        title="Underutilized Resource",
                        description=(
                            f"Resource {rid} has {gap} minutes of "
                            f"unused capacity."
                        ),
                        affected_staff_ids=[UUID(rid)],
                        criteria_triggered=[9, 16],
                        resolution_options=[
                            ResolutionOption(
                                action="fill_gap",
                                label="Fill with backlog jobs",
                                description="Assign matching backlog jobs.",
                                parameters={"gap_minutes": gap},
                            ),
                        ],
                    ),
                )
        return candidates

    async def _suggest_customer_preference(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find dissatisfaction feedback and recommend alternatives.

        Args:
            assignments: List of assignment dicts with resource_id,
                job_id, customer_satisfaction keys.

        Returns:
            Suggestion candidates for customer preference issues.
        """
        candidates: list[AlertCandidate] = []
        for a in assignments:
            satisfaction = a.get("customer_satisfaction")
            if satisfaction is not None and float(satisfaction) < 3.0:
                candidates.append(
                    AlertCandidate(
                        alert_type="customer_preference",
                        severity="suggestion",
                        title="Customer Prefers Different Resource",
                        description=(
                            f"Customer gave resource {a.get('resource_id')} "
                            f"a {satisfaction}-star rating on a previous visit."
                        ),
                        affected_job_ids=[UUID(str(a.get("job_id", "")))],
                        affected_staff_ids=[UUID(str(a.get("resource_id", "")))],
                        criteria_triggered=[15],
                        resolution_options=[
                            ResolutionOption(
                                action="reassign",
                                label="Reassign to preferred resource",
                                description="Swap to a higher-rated resource.",
                                parameters={},
                            ),
                        ],
                    ),
                )
        return candidates

    async def _suggest_overtime_avoidance(
        self,
        assignments: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find low-priority jobs shiftable to avoid overtime.

        Args:
            assignments: List of assignment dicts with resource_id,
                job_id, total_minutes, overtime_threshold keys.

        Returns:
            Suggestion candidates for overtime avoidance.
        """
        candidates: list[AlertCandidate] = []
        by_resource: dict[str, dict[str, Any]] = {}
        for a in assignments:
            rid = str(a.get("resource_id", ""))
            if rid not in by_resource:
                by_resource[rid] = {
                    "total_minutes": 0,
                    "overtime_threshold": int(
                        a.get("overtime_threshold", 480),
                    ),
                    "low_priority_jobs": [],
                }
            by_resource[rid]["total_minutes"] += int(
                a.get("job_duration_minutes", 0),
            ) + int(a.get("drive_time_minutes", 0))
            priority = a.get("priority", "standard")
            if priority in ("standard", "flexible"):
                by_resource[rid]["low_priority_jobs"].append(a)

        for rid, info in by_resource.items():
            if info["total_minutes"] > info["overtime_threshold"]:
                for lp_job in info["low_priority_jobs"]:
                    candidates.append(
                        AlertCandidate(
                            alert_type="overtime_avoidable",
                            severity="suggestion",
                            title="Overtime Avoidable",
                            description=(
                                f"Shifting job {lp_job.get('job_id')} from "
                                f"resource {rid} would avoid overtime."
                            ),
                            affected_job_ids=[
                                UUID(str(lp_job.get("job_id", ""))),
                            ],
                            affected_staff_ids=[UUID(rid)],
                            criteria_triggered=[24],
                            resolution_options=[
                                ResolutionOption(
                                    action="shift_job",
                                    label="Move to another day",
                                    description="Shift this job to avoid overtime.",
                                    parameters={},
                                ),
                            ],
                        ),
                    )
                    break  # One suggestion per resource is enough.
        return candidates

    async def _suggest_high_revenue_fills(
        self,
        open_slots: list[dict[str, Any]],
    ) -> list[AlertCandidate]:
        """Find high-revenue jobs matching open slots.

        Args:
            open_slots: List of open slot dicts with resource_id,
                slot_start, slot_end, available_skills keys.

        Returns:
            Suggestion candidates for high-revenue slot fills.
        """
        # Stub: real implementation queries backlog for
        # high-revenue jobs matching the slot's skills/time.
        return [
            AlertCandidate(
                alert_type="high_revenue",
                severity="suggestion",
                title="High-Revenue Job Available",
                description=(
                    f"Open slot for resource "
                    f"{slot.get('resource_id')} could be filled "
                    f"with a high-revenue backlog job."
                ),
                affected_staff_ids=[
                    UUID(str(slot.get("resource_id", ""))),
                ],
                criteria_triggered=[22, 13],
                resolution_options=[
                    ResolutionOption(
                        action="auto_schedule",
                        label="Auto-schedule top job",
                        description=(
                            "Assign the highest-revenue "
                            "matching job."
                        ),
                        parameters={},
                    ),
                ],
            )
            for slot in open_slots
        ]

    # ------------------------------------------------------------------
    # Deduplication and persistence
    # ------------------------------------------------------------------

    async def _deduplicate_and_persist(
        self,
        candidates: list[AlertCandidate],
        schedule_date: date,
    ) -> list[SchedulingAlert]:
        """Deduplicate candidates and persist new alerts.

        Deduplication key: (alert_type, affected_job_ids, schedule_date).

        Args:
            candidates: Raw alert candidates from detectors/generators.
            schedule_date: The schedule date for these alerts.

        Returns:
            List of newly persisted ``SchedulingAlert`` instances.
        """
        if not candidates:
            return []

        # Load existing active alerts for this date.
        stmt = select(SchedulingAlert).where(
            SchedulingAlert.schedule_date == schedule_date,
            SchedulingAlert.status == "active",
        )
        result = await self._session.execute(stmt)
        existing = result.scalars().all()

        existing_keys: set[tuple[str, str, str]] = set()
        for alert in existing:
            job_ids_key = str(sorted(alert.affected_job_ids or []))
            existing_keys.add(
                (alert.alert_type, job_ids_key, str(alert.schedule_date)),
            )

        new_alerts: list[SchedulingAlert] = []
        for candidate in candidates:
            job_ids_key = str(sorted(str(jid) for jid in candidate.affected_job_ids))
            dedup_key = (candidate.alert_type, job_ids_key, str(schedule_date))
            if dedup_key in existing_keys:
                continue

            alert = SchedulingAlert(
                alert_type=candidate.alert_type,
                severity=candidate.severity,
                title=candidate.title,
                description=candidate.description,
                affected_job_ids=[str(jid) for jid in candidate.affected_job_ids],
                affected_staff_ids=[str(sid) for sid in candidate.affected_staff_ids],
                criteria_triggered=candidate.criteria_triggered,
                resolution_options=[
                    opt.model_dump() for opt in candidate.resolution_options
                ],
                status="active",
                schedule_date=schedule_date,
            )
            self._session.add(alert)
            new_alerts.append(alert)

            # Mark as seen for further dedup within this batch.
            existing_keys.add(dedup_key)

            self.logger.info(
                "scheduling.alertengine.alert_created",
                alert_type=candidate.alert_type,
                severity=candidate.severity,
                title=candidate.title,
                schedule_date=str(schedule_date),
            )

        if new_alerts:
            await self._session.flush()

        return new_alerts
