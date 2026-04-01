"""
Scheduling alerts and change requests API endpoints.

Provides alert listing, resolution, dismissal, and change request
management for the AI scheduling system.

Validates: Requirements 11.1-11.5, 12.1-12.5, 13.1-13.10, 15.1-15.10
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.change_request import ChangeRequest
from grins_platform.models.scheduling_alert import SchedulingAlert
from grins_platform.schemas.ai_scheduling import (
    ApproveChangeRequest,
    ChangeRequestResponse,
    DenyChangeRequest,
    DismissAlertRequest,
    ResolveAlertRequest,
    SchedulingAlertResponse,
)
from grins_platform.services.ai.scheduling.change_request_service import (
    ChangeRequestService,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/alerts", tags=["scheduling-alerts"])


class AlertsEndpoints(LoggerMixin):
    """Scheduling alerts endpoints."""

    DOMAIN = "api"


endpoints = AlertsEndpoints()


@router.get(  # type: ignore[misc,untyped-decorator]
    "/",
    response_model=list[SchedulingAlertResponse],
)
async def list_alerts(
    current_user: CurrentActiveUser,
    alert_type: str | None = Query(default=None, description="Filter by alert type"),
    severity: str | None = Query(default=None, description="Filter by severity"),
    schedule_date: date | None = Query(
        default=None,
        description="Filter by schedule date",
    ),
    alert_status: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status (active, resolved, dismissed)",
    ),
    session: AsyncSession = Depends(get_db_session),
) -> list[SchedulingAlertResponse]:
    """List active alerts and suggestions.

    Supports filtering by type, severity, schedule_date, and status.

    GET /api/v1/alerts/

    Validates: Requirements 11.1-11.5, 12.1-12.5
    """
    endpoints.log_started(
        "list_alerts",
        user_id=str(current_user.id),
        alert_type=alert_type,
        severity=severity,
    )

    try:
        stmt = select(SchedulingAlert).order_by(SchedulingAlert.created_at.desc())

        if alert_type is not None:
            stmt = stmt.where(SchedulingAlert.alert_type == alert_type)
        if severity is not None:
            stmt = stmt.where(SchedulingAlert.severity == severity)
        if schedule_date is not None:
            stmt = stmt.where(SchedulingAlert.schedule_date == schedule_date)
        if alert_status is not None:
            stmt = stmt.where(SchedulingAlert.status == alert_status)

        result = await session.execute(stmt)
        alerts = result.scalars().all()

        response_list = [
            SchedulingAlertResponse(
                id=alert.id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                title=alert.title,
                description=alert.description,
                affected_job_ids=alert.affected_job_ids,
                affected_staff_ids=alert.affected_staff_ids,
                criteria_triggered=alert.criteria_triggered,
                resolution_options=alert.resolution_options or [],
                status=alert.status,
                schedule_date=alert.schedule_date,
                created_at=alert.created_at,
            )
            for alert in alerts
        ]
    except Exception as e:
        endpoints.log_failed("list_alerts", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list alerts: {e!s}",
        ) from e
    else:
        endpoints.log_completed("list_alerts", count=len(response_list))
        return response_list


@router.post(  # type: ignore[misc,untyped-decorator]
    "/{alert_id}/resolve",
    response_model=SchedulingAlertResponse,
)
async def resolve_alert(
    alert_id: UUID,
    request: ResolveAlertRequest,
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db_session),
) -> SchedulingAlertResponse:
    """Resolve an alert with a chosen action.

    POST /api/v1/alerts/{alert_id}/resolve

    Validates: Requirements 13.1-13.10
    """
    endpoints.log_started(
        "resolve_alert",
        alert_id=str(alert_id),
        action=request.action,
        user_id=str(current_user.id),
    )

    stmt = select(SchedulingAlert).where(SchedulingAlert.id == alert_id)
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    try:
        alert.status = "resolved"
        alert.resolved_by = current_user.id
        alert.resolved_action = request.action
        alert.resolved_at = datetime.now(tz=timezone.utc)
        await session.flush()

        response = SchedulingAlertResponse(
            id=alert.id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            affected_job_ids=alert.affected_job_ids,
            affected_staff_ids=alert.affected_staff_ids,
            criteria_triggered=alert.criteria_triggered,
            resolution_options=alert.resolution_options or [],
            status=alert.status,
            schedule_date=alert.schedule_date,
            created_at=alert.created_at,
        )
    except Exception as e:
        endpoints.log_failed("resolve_alert", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {e!s}",
        ) from e
    else:
        endpoints.log_completed("resolve_alert", alert_id=str(alert_id))
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/{alert_id}/dismiss",
    response_model=SchedulingAlertResponse,
)
async def dismiss_alert(
    alert_id: UUID,
    request: DismissAlertRequest,
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db_session),
) -> SchedulingAlertResponse:
    """Dismiss a suggestion.

    POST /api/v1/alerts/{alert_id}/dismiss

    Validates: Requirements 12.1-12.5
    """
    endpoints.log_started(
        "dismiss_alert",
        alert_id=str(alert_id),
        user_id=str(current_user.id),
    )

    stmt = select(SchedulingAlert).where(SchedulingAlert.id == alert_id)
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    try:
        alert.status = "dismissed"
        alert.resolved_by = current_user.id
        alert.resolved_action = f"dismissed: {request.reason or 'no reason'}"
        alert.resolved_at = datetime.now(tz=timezone.utc)
        await session.flush()

        response = SchedulingAlertResponse(
            id=alert.id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            affected_job_ids=alert.affected_job_ids,
            affected_staff_ids=alert.affected_staff_ids,
            criteria_triggered=alert.criteria_triggered,
            resolution_options=alert.resolution_options or [],
            status=alert.status,
            schedule_date=alert.schedule_date,
            created_at=alert.created_at,
        )
    except Exception as e:
        endpoints.log_failed("dismiss_alert", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss alert: {e!s}",
        ) from e
    else:
        endpoints.log_completed("dismiss_alert", alert_id=str(alert_id))
        return response


@router.get(  # type: ignore[misc,untyped-decorator]
    "/change-requests",
    response_model=list[ChangeRequestResponse],
)
async def list_change_requests(
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db_session),
) -> list[ChangeRequestResponse]:
    """List pending change requests for admin review.

    GET /api/v1/alerts/change-requests

    Validates: Requirements 2.4, 15.3-15.10
    """
    endpoints.log_started("list_change_requests", user_id=str(current_user.id))

    try:
        stmt = (
            select(ChangeRequest)
            .where(ChangeRequest.status == "pending")
            .order_by(ChangeRequest.created_at.desc())
        )
        result = await session.execute(stmt)
        requests = result.scalars().all()

        response_list = [
            ChangeRequestResponse.model_validate(cr) for cr in requests
        ]
    except Exception as e:
        endpoints.log_failed("list_change_requests", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list change requests: {e!s}",
        ) from e
    else:
        endpoints.log_completed("list_change_requests", count=len(response_list))
        return response_list


@router.post(  # type: ignore[misc,untyped-decorator]
    "/change-requests/{request_id}/approve",
    response_model=dict[str, Any],
)
async def approve_change_request(
    request_id: UUID,
    request: ApproveChangeRequest,
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Approve a change request.

    POST /api/v1/alerts/change-requests/{request_id}/approve

    Validates: Requirements 2.4, 13.5-13.10
    """
    endpoints.log_started(
        "approve_change_request",
        request_id=str(request_id),
        user_id=str(current_user.id),
    )

    try:
        service = ChangeRequestService(session)
        result = await service.approve_request(
            request_id=request_id,
            admin_id=current_user.id,
            admin_notes=request.admin_notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        endpoints.log_failed("approve_change_request", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve change request: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "approve_change_request",
            request_id=str(request_id),
        )
        return result


@router.post(  # type: ignore[misc,untyped-decorator]
    "/change-requests/{request_id}/deny",
    response_model=dict[str, Any],
)
async def deny_change_request(
    request_id: UUID,
    request: DenyChangeRequest,
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Deny a change request.

    POST /api/v1/alerts/change-requests/{request_id}/deny

    Validates: Requirements 2.4, 13.5-13.10
    """
    endpoints.log_started(
        "deny_change_request",
        request_id=str(request_id),
        user_id=str(current_user.id),
    )

    try:
        service = ChangeRequestService(session)
        result = await service.deny_request(
            request_id=request_id,
            admin_id=current_user.id,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        endpoints.log_failed("deny_change_request", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deny change request: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "deny_change_request",
            request_id=str(request_id),
        )
        return result
