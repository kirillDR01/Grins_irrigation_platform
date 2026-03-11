"""Job generator service for creating seasonal jobs from service agreements.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import JobCategory, JobStatus
from grins_platform.models.job import Job

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

        Args:
            agreement: The service agreement to generate jobs for.

        Returns:
            List of created Job instances.

        Validates: Requirements 9.1-9.7
        """
        tier_name = agreement.tier.name
        tier_slug: str = agreement.tier.slug
        self.log_started(
            "generate_jobs",
            agreement_id=str(agreement.id),
            tier_name=tier_name,
            tier_slug=tier_slug,
        )

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

        now = datetime.now(timezone.utc)
        year = now.year

        jobs: list[Job] = []
        for job_type, description, month_start, month_end in job_specs:
            last_day = calendar.monthrange(year, month_end)[1]
            job = Job(
                customer_id=agreement.customer_id,
                property_id=agreement.property_id,
                service_agreement_id=agreement.id,
                job_type=job_type,
                category=JobCategory.READY_TO_SCHEDULE.value,
                status=JobStatus.APPROVED.value,
                description=description,
                target_start_date=date(year, month_start, 1),
                target_end_date=date(year, month_end, last_day),
                approved_at=now,
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
