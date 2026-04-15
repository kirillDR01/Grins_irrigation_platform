"""Job generator service for creating seasonal jobs from service agreements.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 30.3, 30.4, 30.5
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import JobCategory, JobStatus
from grins_platform.models.job import Job
from grins_platform.utils.week_alignment import align_to_week

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.service_agreement import ServiceAgreement

# Tier name → list of (job_type, description, month_start, month_end)
# For monthly visits, we expand May-Sep individually.
_ESSENTIAL_JOBS: list[tuple[str, str, int, int]] = [
    ("spring_startup", "Spring system activation and inspection", 4, 4),
    ("fall_winterization", "Fall system winterization and blowout", 10, 10),
]

_PROFESSIONAL_JOBS: list[tuple[str, str, int, int]] = [
    ("spring_startup", "Spring system activation and inspection", 4, 4),
    ("mid_season_inspection", "Mid-season system inspection and adjustment", 7, 7),
    ("fall_winterization", "Fall system winterization and blowout", 10, 10),
]

_PREMIUM_JOBS: list[tuple[str, str, int, int]] = [
    ("spring_startup", "Spring system activation and inspection", 4, 4),
    ("monthly_visit", "Monthly system check and adjustment", 5, 5),
    ("monthly_visit", "Monthly system check and adjustment", 6, 6),
    ("monthly_visit", "Monthly system check and adjustment", 7, 7),
    ("monthly_visit", "Monthly system check and adjustment", 8, 8),
    ("monthly_visit", "Monthly system check and adjustment", 9, 9),
    ("fall_winterization", "Fall system winterization and blowout", 10, 10),
]

_WINTERIZATION_ONLY_JOBS: list[tuple[str, str, int, int]] = [
    ("fall_winterization", "Fall system winterization and blowout", 10, 10),
]

_TIER_JOB_MAP: dict[str, list[tuple[str, str, int, int]]] = {
    "Essential": _ESSENTIAL_JOBS,
    "Professional": _PROFESSIONAL_JOBS,
    "Premium": _PREMIUM_JOBS,
}

_TIER_PRIORITY_MAP: dict[str, int] = {
    "Essential": 0,
    "Professional": 1,
    "Premium": 2,
}


class JobGenerator(LoggerMixin):
    """Generates seasonal jobs for a service agreement based on its tier.

    Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
    """

    DOMAIN = "agreements"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.session = session

    async def generate_jobs(self, agreement: ServiceAgreement) -> list[Job]:
        """Generate seasonal jobs based on the agreement's tier.

        Essential: 2 jobs (Spring Startup Apr, Fall Winterization Oct)
        Professional: 3 jobs (Spring Apr, Mid-Season Jul, Fall Oct)
        Premium: 7 jobs (Spring Apr, Monthly May-Sep, Fall Oct)

        All jobs created with status=APPROVED, category=READY_TO_SCHEDULE,
        linked via service_agreement_id and customer_id.

        When the agreement has service_week_preferences, each job's date
        range is set to the customer-selected Monday-Sunday week instead
        of the default calendar-month range.

        Args:
            agreement: The service agreement to generate jobs for.

        Returns:
            List of created Job instances.

        Validates: Requirements 9.1-9.7, 30.3, 30.4, 30.5
        """
        tier_name = agreement.tier.name
        tier_slug: str = agreement.tier.slug

        # Winterization-only tiers detected by slug prefix
        if tier_slug.startswith("winterization-only-"):
            job_specs: list[tuple[str, str, int, int]] | None = _WINTERIZATION_ONLY_JOBS
        else:
            job_specs = _TIER_JOB_MAP.get(tier_name)

        if not job_specs:
            self.log_failed(
                "generate_jobs",
                error=ValueError(f"Unknown tier name: {tier_name}"),
            )
            msg = f"Unknown tier name: {tier_name}"
            raise ValueError(msg)

        if tier_slug.startswith("winterization-only-"):
            priority = 0
        else:
            priority = _TIER_PRIORITY_MAP.get(tier_name, 0)

        # Read week preferences (Req 30.4, 30.5)
        week_prefs: dict[str, Any] = agreement.service_week_preferences or {}

        self.log_started(
            "generate_jobs",
            agreement_id=str(agreement.id),
            tier_name=tier_name,
            tier_slug=tier_slug,
            priority=priority,
            has_week_prefs=bool(week_prefs),
        )

        now = datetime.now(timezone.utc)
        year = now.year
        current_month = now.month

        jobs: list[Job] = []
        for job_type, description, month_start, month_end in job_specs:
            start, end = self._resolve_dates(
                job_type,
                month_start,
                month_end,
                year,
                week_prefs,
                current_month=current_month,
            )
            job = Job(
                customer_id=agreement.customer_id,
                property_id=agreement.property_id,
                service_agreement_id=agreement.id,
                job_type=job_type,
                category=JobCategory.READY_TO_SCHEDULE.value,
                status=JobStatus.TO_BE_SCHEDULED.value,
                description=description,
                priority_level=priority,
                target_start_date=start,
                target_end_date=end,
                requested_at=now,
            )
            self.session.add(job)
            jobs.append(job)

        await self.session.flush()
        for job in jobs:
            await self.session.refresh(job)

        self.log_completed(
            "generate_jobs",
            agreement_id=str(agreement.id),
            job_count=len(jobs),
        )
        return jobs

    @staticmethod
    def _resolve_dates(
        job_type: str,
        month_start: int,
        month_end: int,
        year: int,
        week_prefs: dict[str, Any],
        *,
        current_month: int | None = None,
    ) -> tuple[date, date]:
        """Resolve target start/end dates for a job.

        If a matching week preference exists (ISO Monday string keyed by
        job_type or job_type_{month} for monthly visits), use align_to_week
        to produce a Monday-Sunday range. Otherwise fall back to the
        calendar-month default.

        When no week preference is set and the generator's base ``year``
        would put the job in the past (onboarding in November, Spring
        Startup scheduled in April — bughunt M-4), roll the year forward
        so the job lands in the next season instead of silently back-dating.

        Validates: Requirements 30.4, 30.5; bughunt M-4.
        """
        # Try month-qualified key first (e.g. monthly_visit_5), then plain
        candidates = [f"{job_type}_{month_start}", job_type]
        for key in candidates:
            pref_monday_iso = week_prefs.get(key)
            if pref_monday_iso and isinstance(pref_monday_iso, str):
                try:
                    pref_date = date.fromisoformat(pref_monday_iso)
                    return align_to_week(pref_date)
                except ValueError:  # noqa: S110
                    pass  # invalid ISO date, fall through

        # bughunt M-4: if we're already past the job's start month, the
        # upcoming occurrence is next year's. Without this, onboarding a
        # Professional tier in November would create a Spring Startup job
        # dated for April of the current (past) year.
        effective_year = year
        if current_month is not None and month_start < current_month:
            effective_year = year + 1

        # Default: full calendar-month range
        last_day = calendar.monthrange(effective_year, month_end)[1]
        return (
            date(effective_year, month_start, 1),
            date(effective_year, month_end, last_day),
        )
