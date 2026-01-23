"""
Dashboard API endpoints.

This module provides REST API endpoints for dashboard metrics and overview
including metrics, request volume, schedule overview, and payment status.

Validates: Admin Dashboard Requirements 1.6
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from grins_platform.api.v1.dependencies import get_dashboard_service
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.dashboard import (
    DashboardMetrics,
    JobsByStatusResponse,
    PaymentStatusOverview,
    RequestVolumeMetrics,
    ScheduleOverview,
    TodayScheduleResponse,
)
from grins_platform.services.dashboard_service import (
    DashboardService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class DashboardEndpoints(LoggerMixin):
    """Dashboard API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = DashboardEndpoints()


# =============================================================================
# GET /api/v1/dashboard/metrics - Get Dashboard Metrics
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/metrics",
    response_model=DashboardMetrics,
    summary="Get dashboard metrics",
    description="Get overall dashboard metrics including customer counts, "
    "job status summary, appointments, and staff availability.",
)
async def get_dashboard_metrics(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardMetrics:
    """Get overall dashboard metrics.

    Validates: Admin Dashboard Requirement 1.6
    """
    _endpoints.log_started("get_dashboard_metrics")

    result = await service.get_overview_metrics()

    _endpoints.log_completed(
        "get_dashboard_metrics",
        total_customers=result.total_customers,
        today_appointments=result.today_appointments,
    )
    return result


# =============================================================================
# GET /api/v1/dashboard/requests - Get Request Volume Metrics
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/requests",
    response_model=RequestVolumeMetrics,
    summary="Get request volume metrics",
    description="Get job request volume metrics for a specified period.",
)
async def get_request_volume(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    period_days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to look back (1-365)",
    ),
) -> RequestVolumeMetrics:
    """Get request volume metrics for a period.

    Validates: Admin Dashboard Requirement 1.6
    """
    _endpoints.log_started("get_request_volume", period_days=period_days)

    result = await service.get_request_volume(period_days=period_days)

    _endpoints.log_completed(
        "get_request_volume",
        total_requests=result.total_requests,
        average_daily=result.average_daily_requests,
    )
    return result


# =============================================================================
# GET /api/v1/dashboard/schedule - Get Schedule Overview
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/schedule",
    response_model=ScheduleOverview,
    summary="Get schedule overview",
    description="Get schedule overview for a specific date including "
    "appointment counts and staff utilization.",
)
async def get_schedule_overview(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    schedule_date: date | None = Query(
        default=None,
        description="Date to get overview for (defaults to today)",
    ),
) -> ScheduleOverview:
    """Get schedule overview for a specific date.

    Validates: Admin Dashboard Requirement 1.6
    """
    target_date = schedule_date or date.today()
    _endpoints.log_started("get_schedule_overview", date=str(target_date))

    result = await service.get_schedule_overview(schedule_date=target_date)

    _endpoints.log_completed(
        "get_schedule_overview",
        total_appointments=result.total_appointments,
        total_minutes=result.total_scheduled_minutes,
    )
    return result


# =============================================================================
# GET /api/v1/dashboard/payments - Get Payment Status Overview
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/payments",
    response_model=PaymentStatusOverview,
    summary="Get payment status overview",
    description="Get payment status overview including invoice counts and amounts.",
)
async def get_payment_status(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> PaymentStatusOverview:
    """Get payment status overview.

    Note: Returns placeholder data until invoice system is implemented.

    Validates: Admin Dashboard Requirement 1.6
    """
    _endpoints.log_started("get_payment_status")

    result = await service.get_payment_status()

    _endpoints.log_completed(
        "get_payment_status",
        total_invoices=result.total_invoices,
        pending_invoices=result.pending_invoices,
    )
    return result


# =============================================================================
# GET /api/v1/dashboard/jobs-by-status - Get Jobs Count by Status
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/jobs-by-status",
    response_model=JobsByStatusResponse,
    summary="Get jobs count by status",
    description="Get count of jobs grouped by their current status.",
)
async def get_jobs_by_status(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> JobsByStatusResponse:
    """Get jobs count grouped by status.

    Validates: Admin Dashboard Requirement 1.6
    """
    _endpoints.log_started("get_jobs_by_status")

    result = await service.get_jobs_by_status()

    _endpoints.log_completed("get_jobs_by_status")
    return result


# =============================================================================
# GET /api/v1/dashboard/today-schedule - Get Today's Schedule Summary
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/today-schedule",
    response_model=TodayScheduleResponse,
    summary="Get today's schedule summary",
    description="Get summary of today's appointments by status.",
)
async def get_today_schedule(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> TodayScheduleResponse:
    """Get today's schedule summary.

    Validates: Admin Dashboard Requirement 1.6
    """
    _endpoints.log_started("get_today_schedule")

    result = await service.get_today_schedule()

    _endpoints.log_completed(
        "get_today_schedule",
        total=result.total_appointments,
        completed=result.completed_appointments,
        upcoming=result.upcoming_appointments,
    )
    return result
