"""
Tests for DashboardService.

This module contains unit tests for the DashboardService class,
testing dashboard metrics, request volume, schedule overview,
and payment status functionality.

Validates: Admin Dashboard Requirements 1.6
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus, JobStatus
from grins_platform.schemas.dashboard import (
    DashboardMetrics,
    JobsByStatusResponse,
    PaymentStatusOverview,
    RequestVolumeMetrics,
    ScheduleOverview,
    TodayScheduleResponse,
)
from grins_platform.services.dashboard_service import DashboardService

if TYPE_CHECKING:
    from unittest.mock import Mock


@pytest.fixture
def mock_customer_repository() -> Mock:
    """Create mock customer repository."""
    repo = MagicMock()
    repo.count_all = AsyncMock(return_value=100)
    repo.count_active = AsyncMock(return_value=75)
    return repo


@pytest.fixture
def mock_job_repository() -> Mock:
    """Create mock job repository."""
    repo = MagicMock()
    repo.count_by_status = AsyncMock(
        return_value={
            JobStatus.REQUESTED.value: 10,
            JobStatus.APPROVED.value: 5,
            JobStatus.SCHEDULED.value: 8,
            JobStatus.IN_PROGRESS.value: 3,
            JobStatus.COMPLETED.value: 50,
            JobStatus.CLOSED.value: 20,
            JobStatus.CANCELLED.value: 2,
        },
    )
    repo.count_by_day = AsyncMock(
        return_value={
            date.today(): 5,
            date.today() - timedelta(days=1): 3,
            date.today() - timedelta(days=2): 7,
        },
    )
    repo.count_by_category = AsyncMock(
        return_value={
            "ready_to_schedule": 15,
            "requires_estimate": 8,
        },
    )
    repo.count_by_source = AsyncMock(
        return_value={
            "website": 10,
            "referral": 8,
            "google": 5,
        },
    )
    return repo


@pytest.fixture
def mock_staff_repository() -> Mock:
    """Create mock staff repository."""
    repo = MagicMock()
    repo.count_active = AsyncMock(return_value=5)
    repo.count_available = AsyncMock(return_value=3)
    return repo


@pytest.fixture
def mock_appointment_repository() -> Mock:
    """Create mock appointment repository."""
    repo = MagicMock()
    repo.count_by_date = AsyncMock(return_value=12)

    # Create mock appointments for schedule overview
    mock_staff = MagicMock()
    mock_staff.name = "John Doe"

    mock_appointment1 = MagicMock()
    mock_appointment1.id = uuid4()
    mock_appointment1.status = AppointmentStatus.SCHEDULED.value
    mock_appointment1.staff = mock_staff
    mock_appointment1.get_duration_minutes = MagicMock(return_value=60)

    mock_appointment2 = MagicMock()
    mock_appointment2.id = uuid4()
    mock_appointment2.status = AppointmentStatus.COMPLETED.value
    mock_appointment2.staff = mock_staff
    mock_appointment2.get_duration_minutes = MagicMock(return_value=90)

    repo.get_daily_schedule = AsyncMock(
        return_value=[mock_appointment1, mock_appointment2],
    )
    return repo


@pytest.fixture
def dashboard_service(
    mock_customer_repository: Mock,
    mock_job_repository: Mock,
    mock_staff_repository: Mock,
    mock_appointment_repository: Mock,
) -> DashboardService:
    """Create DashboardService with mocked repositories."""
    return DashboardService(
        customer_repository=mock_customer_repository,
        job_repository=mock_job_repository,
        staff_repository=mock_staff_repository,
        appointment_repository=mock_appointment_repository,
    )


@pytest.mark.unit
class TestDashboardServiceGetOverviewMetrics:
    """Tests for DashboardService.get_overview_metrics method."""

    @pytest.mark.asyncio
    async def test_get_overview_metrics_returns_dashboard_metrics(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that get_overview_metrics returns DashboardMetrics."""
        result = await dashboard_service.get_overview_metrics()

        assert isinstance(result, DashboardMetrics)

    @pytest.mark.asyncio
    async def test_get_overview_metrics_includes_customer_counts(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that metrics include customer counts."""
        result = await dashboard_service.get_overview_metrics()

        assert result.total_customers == 100
        assert result.active_customers == 75

    @pytest.mark.asyncio
    async def test_get_overview_metrics_includes_jobs_by_status(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that metrics include jobs by status."""
        result = await dashboard_service.get_overview_metrics()

        assert JobStatus.REQUESTED.value in result.jobs_by_status
        assert result.jobs_by_status[JobStatus.REQUESTED.value] == 10
        assert result.jobs_by_status[JobStatus.COMPLETED.value] == 50

    @pytest.mark.asyncio
    async def test_get_overview_metrics_includes_today_appointments(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that metrics include today's appointment count."""
        result = await dashboard_service.get_overview_metrics()

        assert result.today_appointments == 12

    @pytest.mark.asyncio
    async def test_get_overview_metrics_includes_staff_counts(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that metrics include staff counts."""
        result = await dashboard_service.get_overview_metrics()

        assert result.total_staff == 5
        assert result.available_staff == 3


@pytest.mark.unit
class TestDashboardServiceGetRequestVolume:
    """Tests for DashboardService.get_request_volume method."""

    @pytest.mark.asyncio
    async def test_get_request_volume_returns_metrics(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that get_request_volume returns RequestVolumeMetrics."""
        result = await dashboard_service.get_request_volume(period_days=30)

        assert isinstance(result, RequestVolumeMetrics)

    @pytest.mark.asyncio
    async def test_get_request_volume_includes_period_dates(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that metrics include period start and end dates."""
        result = await dashboard_service.get_request_volume(period_days=30)

        assert result.period_end == date.today()
        assert result.period_start == date.today() - timedelta(days=30)

    @pytest.mark.asyncio
    async def test_get_request_volume_calculates_total(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that total requests is calculated correctly."""
        result = await dashboard_service.get_request_volume(period_days=30)

        # 5 + 3 + 7 = 15 from mock data
        assert result.total_requests == 15

    @pytest.mark.asyncio
    async def test_get_request_volume_calculates_average(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that average daily requests is calculated correctly."""
        result = await dashboard_service.get_request_volume(period_days=30)

        # 15 total / 30 days = 0.5
        assert result.average_daily_requests == 0.5

    @pytest.mark.asyncio
    async def test_get_request_volume_includes_by_category(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that metrics include requests by category."""
        result = await dashboard_service.get_request_volume(period_days=30)

        assert "ready_to_schedule" in result.requests_by_category
        assert result.requests_by_category["ready_to_schedule"] == 15

    @pytest.mark.asyncio
    async def test_get_request_volume_includes_by_source(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that metrics include requests by source."""
        result = await dashboard_service.get_request_volume(period_days=30)

        assert "website" in result.requests_by_source
        assert result.requests_by_source["website"] == 10


@pytest.mark.unit
class TestDashboardServiceGetScheduleOverview:
    """Tests for DashboardService.get_schedule_overview method."""

    @pytest.mark.asyncio
    async def test_get_schedule_overview_returns_overview(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that get_schedule_overview returns ScheduleOverview."""
        result = await dashboard_service.get_schedule_overview()

        assert isinstance(result, ScheduleOverview)

    @pytest.mark.asyncio
    async def test_get_schedule_overview_uses_today_by_default(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that schedule overview defaults to today."""
        result = await dashboard_service.get_schedule_overview()

        assert result.schedule_date == date.today()

    @pytest.mark.asyncio
    async def test_get_schedule_overview_uses_specified_date(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that schedule overview uses specified date."""
        target_date = date.today() + timedelta(days=1)
        result = await dashboard_service.get_schedule_overview(
            schedule_date=target_date,
        )

        assert result.schedule_date == target_date

    @pytest.mark.asyncio
    async def test_get_schedule_overview_counts_appointments(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that overview counts total appointments."""
        result = await dashboard_service.get_schedule_overview()

        assert result.total_appointments == 2

    @pytest.mark.asyncio
    async def test_get_schedule_overview_groups_by_status(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that overview groups appointments by status."""
        result = await dashboard_service.get_schedule_overview()

        assert AppointmentStatus.SCHEDULED.value in result.appointments_by_status
        assert result.appointments_by_status[AppointmentStatus.SCHEDULED.value] == 1
        assert result.appointments_by_status[AppointmentStatus.COMPLETED.value] == 1

    @pytest.mark.asyncio
    async def test_get_schedule_overview_groups_by_staff(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that overview groups appointments by staff."""
        result = await dashboard_service.get_schedule_overview()

        assert "John Doe" in result.appointments_by_staff
        assert result.appointments_by_staff["John Doe"] == 2

    @pytest.mark.asyncio
    async def test_get_schedule_overview_calculates_total_minutes(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that overview calculates total scheduled minutes."""
        result = await dashboard_service.get_schedule_overview()

        # 60 + 90 = 150 minutes from mock data
        assert result.total_scheduled_minutes == 150


@pytest.mark.unit
class TestDashboardServiceGetPaymentStatus:
    """Tests for DashboardService.get_payment_status method."""

    @pytest.mark.asyncio
    async def test_get_payment_status_returns_overview(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that get_payment_status returns PaymentStatusOverview."""
        result = await dashboard_service.get_payment_status()

        assert isinstance(result, PaymentStatusOverview)

    @pytest.mark.asyncio
    async def test_get_payment_status_returns_placeholder_data(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test payment status returns placeholder data (invoices not implemented)."""
        result = await dashboard_service.get_payment_status()

        # Placeholder values until invoice system is implemented
        assert result.total_invoices == 0
        assert result.pending_invoices == 0
        assert result.paid_invoices == 0
        assert result.overdue_invoices == 0


@pytest.mark.unit
class TestDashboardServiceGetJobsByStatus:
    """Tests for DashboardService.get_jobs_by_status method."""

    @pytest.mark.asyncio
    async def test_get_jobs_by_status_returns_response(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that get_jobs_by_status returns JobsByStatusResponse."""
        result = await dashboard_service.get_jobs_by_status()

        assert isinstance(result, JobsByStatusResponse)

    @pytest.mark.asyncio
    async def test_get_jobs_by_status_includes_all_statuses(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that response includes counts for all statuses."""
        result = await dashboard_service.get_jobs_by_status()

        assert result.requested == 10
        assert result.approved == 5
        assert result.scheduled == 8
        assert result.in_progress == 3
        assert result.completed == 50
        assert result.closed == 20
        assert result.cancelled == 2


@pytest.mark.unit
class TestDashboardServiceGetTodaySchedule:
    """Tests for DashboardService.get_today_schedule method."""

    @pytest.mark.asyncio
    async def test_get_today_schedule_returns_response(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that get_today_schedule returns TodayScheduleResponse."""
        result = await dashboard_service.get_today_schedule()

        assert isinstance(result, TodayScheduleResponse)

    @pytest.mark.asyncio
    async def test_get_today_schedule_uses_today_date(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that today schedule uses today's date."""
        result = await dashboard_service.get_today_schedule()

        assert result.schedule_date == date.today()

    @pytest.mark.asyncio
    async def test_get_today_schedule_counts_by_status(
        self,
        dashboard_service: DashboardService,
    ) -> None:
        """Test that today schedule counts appointments by status."""
        result = await dashboard_service.get_today_schedule()

        assert result.total_appointments == 2
        assert result.completed_appointments == 1
        assert result.upcoming_appointments == 1  # scheduled counts as upcoming
        assert result.in_progress_appointments == 0
        assert result.cancelled_appointments == 0
