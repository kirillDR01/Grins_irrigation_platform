"""
Dashboard service for metrics and overview operations.

This module provides the DashboardService class for all dashboard-related
business operations including metrics, request volume, schedule overview,
and payment status.

Validates: Admin Dashboard Requirements 1.6
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import AppointmentStatus, JobStatus
from grins_platform.schemas.dashboard import (
    DashboardMetrics,
    JobsByStatusResponse,
    PaymentStatusOverview,
    RequestVolumeMetrics,
    ScheduleOverview,
    TodayScheduleResponse,
)

if TYPE_CHECKING:
    from grins_platform.repositories.appointment_repository import (
        AppointmentRepository,
    )
    from grins_platform.repositories.customer_repository import CustomerRepository
    from grins_platform.repositories.job_repository import JobRepository
    from grins_platform.repositories.staff_repository import StaffRepository


class DashboardService(LoggerMixin):
    """Service for dashboard metrics and overview operations.

    This class handles all business logic for dashboard metrics including
    customer counts, job status summaries, appointment overviews, and
    staff availability.

    Attributes:
        customer_repository: CustomerRepository for customer data
        job_repository: JobRepository for job data
        staff_repository: StaffRepository for staff data
        appointment_repository: AppointmentRepository for appointment data

    Validates: Admin Dashboard Requirements 1.6
    """

    DOMAIN = "dashboard"

    def __init__(
        self,
        customer_repository: CustomerRepository,
        job_repository: JobRepository,
        staff_repository: StaffRepository,
        appointment_repository: AppointmentRepository,
    ) -> None:
        """Initialize service with repositories.

        Args:
            customer_repository: CustomerRepository for customer data
            job_repository: JobRepository for job data
            staff_repository: StaffRepository for staff data
            appointment_repository: AppointmentRepository for appointment data
        """
        super().__init__()
        self.customer_repository = customer_repository
        self.job_repository = job_repository
        self.staff_repository = staff_repository
        self.appointment_repository = appointment_repository

    async def get_overview_metrics(self) -> DashboardMetrics:
        """Get overall dashboard metrics.

        Returns:
            DashboardMetrics with customer counts, job status, appointments, staff

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("get_overview_metrics")

        # Get customer counts
        total_customers = await self.customer_repository.count_all()
        active_customers = await self.customer_repository.count_active()

        # Get jobs by status
        jobs_by_status = await self._get_jobs_by_status_dict()

        # Get today's appointments count
        today = date.today()
        today_appointments = await self.appointment_repository.count_by_date(today)

        # Get staff counts
        total_staff = await self.staff_repository.count_active()
        available_staff = await self.staff_repository.count_available()

        metrics = DashboardMetrics(
            total_customers=total_customers,
            active_customers=active_customers,
            jobs_by_status=jobs_by_status,
            today_appointments=today_appointments,
            available_staff=available_staff,
            total_staff=total_staff,
        )

        self.log_completed(
            "get_overview_metrics",
            total_customers=total_customers,
            today_appointments=today_appointments,
        )
        return metrics

    async def get_request_volume(
        self,
        period_days: int = 30,
    ) -> RequestVolumeMetrics:
        """Get request volume metrics for a period.

        Args:
            period_days: Number of days to look back (default 30)

        Returns:
            RequestVolumeMetrics with request counts and breakdowns

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("get_request_volume", period_days=period_days)

        period_end = date.today()
        period_start = period_end - timedelta(days=period_days)

        # Get requests by day
        requests_by_day_raw = await self.job_repository.count_by_day(
            period_start,
            period_end,
        )
        # Convert date keys to ISO format strings
        requests_by_day: dict[str, int] = {
            d.isoformat(): count for d, count in requests_by_day_raw.items()
        }

        # Get requests by category
        requests_by_category = await self.job_repository.count_by_category(
            period_start,
            period_end,
        )

        # Get requests by source
        requests_by_source = await self.job_repository.count_by_source(
            period_start,
            period_end,
        )

        # Calculate totals
        total_requests = sum(requests_by_day.values())
        average_daily = total_requests / period_days if period_days > 0 else 0.0

        metrics = RequestVolumeMetrics(
            period_start=period_start,
            period_end=period_end,
            total_requests=total_requests,
            requests_by_day=requests_by_day,
            requests_by_category=requests_by_category,
            requests_by_source=requests_by_source,
            average_daily_requests=round(average_daily, 2),
        )

        self.log_completed(
            "get_request_volume",
            total_requests=total_requests,
            average_daily=average_daily,
        )
        return metrics

    async def get_schedule_overview(
        self,
        schedule_date: date | None = None,
    ) -> ScheduleOverview:
        """Get schedule overview for a specific date.

        Args:
            schedule_date: Date to get overview for (default today)

        Returns:
            ScheduleOverview with appointment counts and staff utilization

        Validates: Admin Dashboard Requirement 1.6
        """
        target_date = schedule_date or date.today()
        self.log_started("get_schedule_overview", date=str(target_date))

        # Get appointments for the date
        appointments = await self.appointment_repository.get_daily_schedule(
            target_date,
            include_relationships=True,
        )

        # Count by status
        appointments_by_status: dict[str, int] = {}
        for apt in appointments:
            status = apt.status
            appointments_by_status[status] = appointments_by_status.get(status, 0) + 1

        # Count by staff
        appointments_by_staff: dict[str, int] = {}
        staff_minutes: dict[str, int] = {}
        for apt in appointments:
            staff_name = apt.staff.name if apt.staff else "Unassigned"
            appointments_by_staff[staff_name] = (
                appointments_by_staff.get(staff_name, 0) + 1
            )
            duration = apt.get_duration_minutes()
            staff_minutes[staff_name] = staff_minutes.get(staff_name, 0) + duration

        # Calculate total scheduled minutes
        total_minutes = sum(apt.get_duration_minutes() for apt in appointments)

        # Calculate staff utilization (assuming 8-hour workday = 480 minutes)
        workday_minutes = 480
        staff_utilization: dict[str, float] = {}
        for staff_name, minutes in staff_minutes.items():
            utilization = (minutes / workday_minutes) * 100
            staff_utilization[staff_name] = round(min(utilization, 100.0), 1)

        overview = ScheduleOverview(
            schedule_date=target_date,
            total_appointments=len(appointments),
            appointments_by_status=appointments_by_status,
            appointments_by_staff=appointments_by_staff,
            total_scheduled_minutes=total_minutes,
            staff_utilization=staff_utilization,
        )

        self.log_completed(
            "get_schedule_overview",
            total_appointments=len(appointments),
            total_minutes=total_minutes,
        )
        return overview

    async def get_payment_status(self) -> PaymentStatusOverview:
        """Get payment status overview.

        Note: This is a placeholder implementation since invoices are not
        yet implemented. Returns mock data for now.

        Returns:
            PaymentStatusOverview with invoice counts and amounts

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("get_payment_status")

        # TODO: Implement when invoice repository is available
        # For now, return placeholder data
        overview = PaymentStatusOverview(
            total_invoices=0,
            pending_invoices=0,
            paid_invoices=0,
            overdue_invoices=0,
            total_pending_amount=0.0,
            total_overdue_amount=0.0,
            average_days_to_payment=0.0,
        )

        self.log_completed("get_payment_status")
        return overview

    async def get_jobs_by_status(self) -> JobsByStatusResponse:
        """Get job counts grouped by status.

        Returns:
            JobsByStatusResponse with counts for each status

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("get_jobs_by_status")

        jobs_dict = await self._get_jobs_by_status_dict()

        response = JobsByStatusResponse(
            requested=jobs_dict.get(JobStatus.REQUESTED.value, 0),
            approved=jobs_dict.get(JobStatus.APPROVED.value, 0),
            scheduled=jobs_dict.get(JobStatus.SCHEDULED.value, 0),
            in_progress=jobs_dict.get(JobStatus.IN_PROGRESS.value, 0),
            completed=jobs_dict.get(JobStatus.COMPLETED.value, 0),
            closed=jobs_dict.get(JobStatus.CLOSED.value, 0),
            cancelled=jobs_dict.get(JobStatus.CANCELLED.value, 0),
        )

        self.log_completed("get_jobs_by_status")
        return response

    async def get_today_schedule(self) -> TodayScheduleResponse:
        """Get today's schedule summary.

        Returns:
            TodayScheduleResponse with appointment counts by status

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("get_today_schedule")

        today = date.today()
        appointments = await self.appointment_repository.get_daily_schedule(today)

        # Count by status
        completed = 0
        in_progress = 0
        upcoming = 0
        cancelled = 0

        for apt in appointments:
            if apt.status == AppointmentStatus.COMPLETED.value:
                completed += 1
            elif apt.status == AppointmentStatus.IN_PROGRESS.value:
                in_progress += 1
            elif apt.status == AppointmentStatus.CANCELLED.value:
                cancelled += 1
            else:
                # scheduled, confirmed count as upcoming
                upcoming += 1

        response = TodayScheduleResponse(
            schedule_date=today,
            total_appointments=len(appointments),
            completed_appointments=completed,
            in_progress_appointments=in_progress,
            upcoming_appointments=upcoming,
            cancelled_appointments=cancelled,
        )

        self.log_completed(
            "get_today_schedule",
            total=len(appointments),
            completed=completed,
            upcoming=upcoming,
        )
        return response

    async def _get_jobs_by_status_dict(self) -> dict[str, int]:
        """Get jobs count by status as a dictionary.

        Returns:
            Dictionary mapping status string to count
        """
        return await self.job_repository.count_by_status()
