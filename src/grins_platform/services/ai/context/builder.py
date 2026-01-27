"""Context Builder for AI prompts.

Builds context from business data for AI prompts.

Validates: AI Assistant Requirements 3.1-3.7, 4.1-4.5, 5.1-5.5
"""

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.customer import Customer
from grins_platform.models.job import Job
from grins_platform.models.staff import Staff


class ContextBuilder(LoggerMixin):
    """Builds context for AI prompts from business data."""

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.session = session

    async def build_scheduling_context(
        self,
        target_date: date,
        job_ids: list[UUID] | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Build context for schedule generation.

        Args:
            target_date: Date to generate schedule for
            job_ids: Optional list of specific job IDs

        Returns:
            Context dictionary for AI prompt
        """
        self.log_started("build_scheduling_context", target_date=str(target_date))

        context = {
            "target_date": target_date.isoformat(),
            "day_of_week": target_date.strftime("%A"),
            "jobs": [],
            "staff": [],
            "constraints": {
                "work_hours": {"start": "08:00", "end": "18:00"},
                "max_jobs_per_staff": 10,
                "travel_buffer_minutes": 15,
            },
        }

        self.log_completed("build_scheduling_context", job_count=len(context["jobs"]))
        return context

    async def build_categorization_context(
        self,
        job_description: str,
        customer_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build context for job categorization.

        Args:
            job_description: Description of the job
            customer_history: Optional customer service history

        Returns:
            Context dictionary for AI prompt
        """
        self.log_started("build_categorization_context")

        context = {
            "job_description": job_description,
            "customer_history": customer_history or [],
            "categories": {
                "ready_to_schedule": "Standard service, no estimate needed",
                "requires_estimate": "Complex work requiring site visit",
                "urgent": "Emergency repair needed",
                "follow_up": "Follow-up from previous work",
            },
        }

        self.log_completed("build_categorization_context")
        return context

    async def build_communication_context(
        self,
        customer_id: UUID,
        message_type: str,
        appointment_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Build context for communication drafting.

        Args:
            customer_id: Customer ID
            message_type: Type of message to draft
            appointment_id: Optional appointment ID

        Returns:
            Context dictionary for AI prompt
        """
        self.log_started(
            "build_communication_context",
            customer_id=str(customer_id),
            message_type=message_type,
        )

        context = {
            "customer_id": str(customer_id),
            "message_type": message_type,
            "appointment_id": str(appointment_id) if appointment_id else None,
            "business_info": {
                "name": "Grin's Irrigation",
                "phone": "(612) 555-0100",
                "service_area": "Twin Cities Metro",
            },
            "templates": {
                "confirmation": "Your appointment is confirmed for {date} at {time}.",
                "reminder": "Reminder: Your appointment is tomorrow at {time}.",
                "on_the_way": "Your technician is on the way, arriving in ~{eta}.",
            },
        }

        self.log_completed("build_communication_context")
        return context

    async def build_estimate_context(
        self,
        job_id: UUID,
        property_details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build context for estimate generation.

        Args:
            job_id: Job ID
            property_details: Optional property details

        Returns:
            Context dictionary for AI prompt
        """
        self.log_started("build_estimate_context", job_id=str(job_id))

        context = {
            "job_id": str(job_id),
            "property_details": property_details or {},
            "pricing": {
                "startup_per_zone": 15.0,
                "winterization_per_zone": 20.0,
                "head_replacement": 50.0,
                "diagnostic_fee": 100.0,
                "hourly_rate": 85.0,
            },
            "labor_estimates": {
                "startup": {"base_minutes": 30, "per_zone_minutes": 5},
                "winterization": {"base_minutes": 30, "per_zone_minutes": 5},
                "repair": {"base_minutes": 60},
            },
        }

        self.log_completed("build_estimate_context")
        return context

    async def build_query_context(
        self,
        query: str,
        date_range: tuple[date, date] | None = None,
    ) -> dict[str, Any]:
        """Build context for business query answering.

        Args:
            query: User's business query
            date_range: Optional date range for data

        Returns:
            Context dictionary for AI prompt
        """
        self.log_started("build_query_context", query_length=len(query))

        if date_range:
            start_date, end_date = date_range
        else:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

        # Fetch real business data from the database
        business_data = await self._fetch_business_summary(start_date, end_date)

        context = {
            "query": query,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "current_time": datetime.now().isoformat(),
            "today": date.today().isoformat(),
            "business_data": business_data,
        }

        self.log_completed("build_query_context")
        return context

    async def _fetch_business_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Fetch a summary of business data for AI context.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary with business summary data
        """
        today = date.today()

        # Count customers
        customer_count_stmt = select(func.count()).select_from(Customer)
        customer_result = await self.session.execute(customer_count_stmt)
        total_customers = customer_result.scalar() or 0

        # Count jobs by status
        job_status_stmt = (
            select(Job.status, func.count())
            .where(Job.is_deleted == False)  # noqa: E712
            .group_by(Job.status)
        )
        job_status_result = await self.session.execute(job_status_stmt)
        jobs_by_status = dict(job_status_result.all())

        # Count today's appointments
        today_appointments_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.scheduled_date == today)
        )
        today_appointments_result = await self.session.execute(today_appointments_stmt)
        today_appointments = today_appointments_result.scalar() or 0

        # Count today's appointments by status
        today_status_stmt = (
            select(Appointment.status, func.count())
            .where(Appointment.scheduled_date == today)
            .group_by(Appointment.status)
        )
        today_status_result = await self.session.execute(today_status_stmt)
        today_by_status = dict(today_status_result.all())

        # Count appointments in date range
        range_appointments_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.scheduled_date >= start_date)
            .where(Appointment.scheduled_date <= end_date)
        )
        range_appointments_result = await self.session.execute(range_appointments_stmt)
        range_appointments = range_appointments_result.scalar() or 0

        # Count staff
        staff_count_stmt = (
            select(func.count())
            .select_from(Staff)
            .where(Staff.is_active == True)  # noqa: E712
        )
        staff_result = await self.session.execute(staff_count_stmt)
        total_staff = staff_result.scalar() or 0

        # Get jobs scheduled for today (via appointments)
        scheduled_jobs_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.scheduled_date == today)
            .where(Appointment.status == "scheduled")
        )
        scheduled_jobs_result = await self.session.execute(scheduled_jobs_stmt)
        scheduled_today = scheduled_jobs_result.scalar() or 0

        # Get completed jobs today
        completed_today_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.scheduled_date == today)
            .where(Appointment.status == "completed")
        )
        completed_today_result = await self.session.execute(completed_today_stmt)
        completed_today = completed_today_result.scalar() or 0

        # Get in-progress jobs today
        in_progress_today_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.scheduled_date == today)
            .where(Appointment.status == "in_progress")
        )
        in_progress_today_result = await self.session.execute(in_progress_today_stmt)
        in_progress_today = in_progress_today_result.scalar() or 0

        return {
            "customers": {
                "total": total_customers,
            },
            "jobs": {
                "by_status": jobs_by_status,
                "total_pending": (
                    jobs_by_status.get("requested", 0) +
                    jobs_by_status.get("approved", 0)
                ),
                "total_scheduled": jobs_by_status.get("scheduled", 0),
                "total_completed": jobs_by_status.get("completed", 0),
                "total_in_progress": jobs_by_status.get("in_progress", 0),
            },
            "appointments": {
                "today": {
                    "total": today_appointments,
                    "scheduled": scheduled_today,
                    "completed": completed_today,
                    "in_progress": in_progress_today,
                    "by_status": today_by_status,
                },
                "date_range": {
                    "total": range_appointments,
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            },
            "staff": {
                "total_active": total_staff,
            },
        }
