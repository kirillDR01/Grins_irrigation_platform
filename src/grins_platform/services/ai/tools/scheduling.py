"""Scheduling tools for AI assistant.

Validates: AI Assistant Requirements 4.1-4.9
"""

from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.job import Job
from grins_platform.models.staff import Staff


class SchedulingTools(LoggerMixin):
    """Tools for schedule generation and management."""

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.session = session

    async def get_pending_jobs(
        self,
        target_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get jobs pending scheduling.

        Args:
            target_date: Optional date filter

        Returns:
            List of pending jobs with details
        """
        self.log_started("get_pending_jobs", target_date=str(target_date))

        stmt = (
            select(Job)
            .options(selectinload(Job.customer), selectinload(Job.job_property))
            .where(Job.is_deleted == False)  # noqa: E712
            .where(Job.category == "ready_to_schedule")
            .where(Job.status.in_(["approved", "requested"]))
        )
        result = await self.session.execute(stmt)
        job_models = result.scalars().all()

        jobs = [
            {
                "id": str(j.id),
                "customer_name": j.customer.full_name if j.customer else "Unknown",
                "address": j.job_property.address if j.job_property else None,
                "city": j.job_property.city if j.job_property else None,
                "job_type": j.job_type,
                "estimated_duration": j.estimated_duration_minutes or 60,
                "priority_level": j.priority_level,
            }
            for j in job_models
        ]

        self.log_completed("get_pending_jobs", count=len(jobs))
        return jobs

    async def get_staff_availability(
        self,
        target_date: date,
    ) -> list[dict[str, Any]]:
        """Get staff availability for a date.

        Args:
            target_date: Date to check availability

        Returns:
            List of staff with availability windows
        """
        self.log_started("get_staff_availability", target_date=str(target_date))

        stmt = (
            select(Staff)
            .where(Staff.is_active == True)  # noqa: E712
            .where(Staff.is_available == True)  # noqa: E712
        )
        result = await self.session.execute(stmt)
        staff_models = result.scalars().all()

        staff = [
            {
                "id": str(s.id),
                "name": s.name,
                "role": s.role,
                "skill_level": s.skill_level,
                "start_lat": (
                    float(s.default_start_lat) if s.default_start_lat else None
                ),
                "start_lng": (
                    float(s.default_start_lng) if s.default_start_lng else None
                ),
            }
            for s in staff_models
        ]

        self.log_completed("get_staff_availability", count=len(staff))
        return staff

    async def generate_schedule(
        self,
        target_date: date,
        job_ids: list[UUID] | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Generate optimized schedule for a date.

        Args:
            target_date: Date to generate schedule for
            job_ids: Optional specific job IDs to schedule

        Returns:
            Generated schedule with assignments
        """
        self.log_started("generate_schedule", target_date=str(target_date))

        # Get pending jobs
        jobs = await self.get_pending_jobs(target_date)

        # Get staff availability
        staff = await self.get_staff_availability(target_date)

        # Generate schedule with batching
        schedule = self._batch_and_assign(jobs, staff, target_date)

        self.log_completed(
            "generate_schedule",
            slot_count=len(schedule.get("slots", [])),
        )
        return schedule

    def _batch_and_assign(
        self,
        jobs: list[dict[str, Any]],
        staff: list[dict[str, Any]],
        target_date: date,
    ) -> dict[str, Any]:
        """Batch jobs by location and type, then assign to staff.

        Args:
            jobs: List of jobs to schedule
            staff: Available staff
            target_date: Target date

        Returns:
            Schedule with batched assignments
        """
        # Group jobs by city for geographic batching
        by_city: dict[str, list[dict[str, Any]]] = {}
        for job in jobs:
            city = job.get("city", "Unknown")
            if city not in by_city:
                by_city[city] = []
            by_city[city].append(job)

        # Within each city, group by job type
        batched_jobs: list[dict[str, Any]] = []
        for city_jobs in by_city.values():
            by_type: dict[str, list[dict[str, Any]]] = {}
            for job in city_jobs:
                job_type = job.get("job_type", "other")
                if job_type not in by_type:
                    by_type[job_type] = []
                by_type[job_type].append(job)

            for type_jobs in by_type.values():
                batched_jobs.extend(type_jobs)

        # Create schedule slots
        slots: list[dict[str, Any]] = []
        current_time = datetime.combine(target_date, time(8, 0))

        for job in batched_jobs:
            duration = job.get("estimated_duration", 60)
            end_time = current_time + timedelta(minutes=duration)

            slots.append(
                {
                    "job_id": job.get("id"),
                    "start_time": current_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "staff_id": staff[0].get("id") if staff else None,
                    "city": job.get("city"),
                    "job_type": job.get("job_type"),
                },
            )

            # Add travel buffer
            current_time = end_time + timedelta(minutes=15)

        return {
            "date": target_date.isoformat(),
            "slots": slots,
            "total_jobs": len(slots),
            "cities_covered": list(by_city.keys()),
        }
