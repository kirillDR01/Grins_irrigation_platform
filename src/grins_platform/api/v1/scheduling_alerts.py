"""Scheduling alerts and change requests API endpoints.

Provides endpoints for listing, resolving, and dismissing AI-generated
scheduling alerts and suggestions, and for managing resource-initiated
change requests.

Note: A generic ``alerts.py`` router already exists at
``api/v1/alerts.py`` (prefix ``/alerts``) for SMS-cancellation alerts.
This module uses prefix ``/scheduling-alerts`` to avoid collision.

Validates: Requirements 11.1-11.5, 12.1-12.5, 13.1-13.10,
           15.1-15.10
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002 - runtime for FastAPI DI

from grins_platform.api.v1.auth_dependencies import (
    AdminUser,  # noqa: TC001 - runtime for FastAPI DI
    CurrentActiveUser,  # noqa: TC001 - runtime for FastAPI DI
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
    ResolutionOption,
    ResolveAlertRequest,
    SchedulingAlertResponse,
)
from grins_platform.services.ai.scheduling.change_request_service import (
    ChangeRequestService,
)

router = APIRouter(prefix="/scheduling-alerts", tags=["scheduling-alerts"])


class SchedulingAlertsEndpoints(LoggerMixin):
    """Scheduling alerts endpoint logger."""

    DOMAIN = "api"


_log = SchedulingAlertsEndpoints()


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_change_request_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChangeRequestService:
    """Provide a ChangeRequestService bound to the request session."""
    return ChangeRequestService(session)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _alert_to_response(alert: SchedulingAlert) -> SchedulingAlertResponse:
    """Convert a SchedulingAlert ORM object to the response schema."""
    resolution_options: list[ResolutionOption] | None = None
    if alert.resolution_options:
        resolution_options = [
            ResolutionOption(
                action=opt.get("action", ""),
                label=opt.get("label", ""),
                description=opt.get("description", ""),
                parameters=opt.get("parameters"),
            )
            for opt in alert.resolution_options
        ]

    return SchedulingAlertResponse(
        id=alert.id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        affected_job_ids=[UUID(j) for j in (alert.affected_job_ids or [])],
        affected_staff_ids=[UUID(s) for s in (alert.affected_staff_ids or [])],
        criteria_triggered=alert.criteria_triggered,
        resolution_options=resolution_options,
        status=alert.status,
        schedule_date=alert.schedule_date,
        created_at=alert.created_at,
    )


def _cr_to_response(cr: ChangeRequest) -> ChangeRequestResponse:
    """Convert a ChangeRequest ORM object to the response schema."""
    return ChangeRequestResponse(
        id=cr.id,
        resource_id=cr.resource_id,
        request_type=cr.request_type,
        details=cr.details,
        affected_job_id=cr.affected_job_id,
        recommended_action=cr.recommended_action,
        status=cr.status,
        created_at=cr.created_at,
    )


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------


@router.get(  # type: ignore[misc,untyped-decorator]
    "/",
    response_model=list[SchedulingAlertResponse],
    summary="List active scheduling alerts and suggestions",
)
async def list_alerts(
    current_user: CurrentActiveUser,  # noqa: ARG001
    session: Annotated[AsyncSession, Depends(get_db_session)],
    alert_type: str | None = Query(default=None, description="Filter by alert type"),
    severity: str | None = Query(
        default=None, description="Filter by severity (critical/suggestion)"
    ),
    schedule_date: date | None = Query(
        default=None, description="Filter by schedule date"
    ),
    alert_status: str | None = Query(
        default="active", alias="status", description="Filter by status"
    ),
) -> list[SchedulingAlertResponse]:
    """List scheduling alerts and suggestions.

    Returns alerts (red/critical) first, then suggestions (green).

    GET /api/v1/scheduling-alerts/

    Validates: Requirements 11.1-11.5, 12.1-12.5
    """
    _log.log_started("list_alerts")

    try:
        conditions = []
        if alert_type is not None:
            conditions.append(SchedulingAlert.alert_type == alert_type)
        if severity is not None:
            conditions.append(SchedulingAlert.severity == severity)
        if schedule_date is not None:
            conditions.append(SchedulingAlert.schedule_date == schedule_date)
        if alert_status is not None:
            conditions.append(SchedulingAlert.status == alert_status)

        # Bug 8 fix: SchedulingAlert.severity.desc() sorts lexicographically
        # ("suggestion" > "critical"), which inverted the intended priority.
        # Use a CASE expression so critical alerts always rank first.
        severity_priority = case(
            (SchedulingAlert.severity == "critical", 0),
            (SchedulingAlert.severity == "suggestion", 1),
            else_=2,
        )
        stmt = select(SchedulingAlert).order_by(
            severity_priority,
            SchedulingAlert.created_at.desc(),
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await session.execute(stmt)
        alerts = result.scalars().all()
    except Exception as exc:
        _log.log_failed("list_alerts", error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load alerts: {exc!s}",
        ) from exc
    else:
        _log.log_completed("list_alerts", count=len(alerts))
        return [_alert_to_response(a) for a in alerts]


@router.post(  # type: ignore[misc,untyped-decorator]
    "/{alert_id}/resolve",
    response_model=SchedulingAlertResponse,
    summary="Resolve a scheduling alert",
)
async def resolve_alert(
    alert_id: UUID,
    request: ResolveAlertRequest,
    current_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SchedulingAlertResponse:
    """Resolve a scheduling alert with the chosen action.

    POST /api/v1/scheduling-alerts/{id}/resolve

    Validates: Requirements 11.1, 13.1-13.5
    """
    _log.log_started(
        "resolve_alert",
        alert_id=str(alert_id),
        resolution_action=request.action,
        admin_id=str(current_user.id),
    )

    try:
        stmt = select(SchedulingAlert).where(SchedulingAlert.id == alert_id)
        result = await session.execute(stmt)
        alert = result.scalar_one_or_none()

        if alert is None:
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found.",
            )

        if alert.status != "active":
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Alert {alert_id} is already {alert.status}.",
            )

        alert.status = "resolved"
        alert.resolved_by = current_user.id
        alert.resolved_action = request.action
        alert.resolved_at = datetime.now(tz=timezone.utc)
        await session.flush()
    except HTTPException:
        raise
    except Exception as exc:
        _log.log_failed("resolve_alert", error=exc, alert_id=str(alert_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {exc!s}",
        ) from exc
    else:
        _log.log_completed("resolve_alert", alert_id=str(alert_id))
        return _alert_to_response(alert)


@router.post(  # type: ignore[misc,untyped-decorator]
    "/{alert_id}/dismiss",
    response_model=SchedulingAlertResponse,
    summary="Dismiss a scheduling suggestion",
)
async def dismiss_alert(
    alert_id: UUID,
    request: DismissAlertRequest,  # noqa: ARG001
    current_user: CurrentActiveUser,  # noqa: ARG001
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SchedulingAlertResponse:
    """Dismiss a scheduling suggestion.

    POST /api/v1/scheduling-alerts/{id}/dismiss

    Validates: Requirements 12.1, 13.6-13.10
    """
    _log.log_started("dismiss_alert", alert_id=str(alert_id))

    try:
        stmt = select(SchedulingAlert).where(SchedulingAlert.id == alert_id)
        result = await session.execute(stmt)
        alert = result.scalar_one_or_none()

        if alert is None:
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found.",
            )

        if alert.status != "active":
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Alert {alert_id} is already {alert.status}.",
            )

        if alert.severity != "suggestion":
            _log.log_rejected(
                "dismiss_alert",
                reason="non_suggestion_severity",
                alert_id=str(alert_id),
                severity=alert.severity,
            )
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Only suggestions can be dismissed; "
                    "resolve critical alerts via /resolve."
                ),
            )

        alert.status = "dismissed"
        await session.flush()
    except HTTPException:
        raise
    except Exception as exc:
        _log.log_failed("dismiss_alert", error=exc, alert_id=str(alert_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss alert: {exc!s}",
        ) from exc
    else:
        _log.log_completed("dismiss_alert", alert_id=str(alert_id))
        return _alert_to_response(alert)


# ---------------------------------------------------------------------------
# Change request endpoints
# ---------------------------------------------------------------------------


@router.get(  # type: ignore[misc,untyped-decorator]
    "/change-requests",
    response_model=list[ChangeRequestResponse],
    summary="List pending change requests",
)
async def list_change_requests(
    current_user: AdminUser,  # noqa: ARG001
    session: Annotated[AsyncSession, Depends(get_db_session)],
    cr_status: str | None = Query(
        default="pending", alias="status", description="Filter by status"
    ),
) -> list[ChangeRequestResponse]:
    """List resource-initiated change requests for admin review.

    GET /api/v1/scheduling-alerts/change-requests

    Validates: Requirements 15.3, 15.6, 15.7, 15.10
    """
    _log.log_started("list_change_requests")

    try:
        stmt = select(ChangeRequest).order_by(ChangeRequest.created_at.desc())
        if cr_status is not None:
            stmt = stmt.where(ChangeRequest.status == cr_status)

        result = await session.execute(stmt)
        requests = result.scalars().all()
    except Exception as exc:
        _log.log_failed("list_change_requests", error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load change requests: {exc!s}",
        ) from exc
    else:
        _log.log_completed("list_change_requests", count=len(requests))
        return [_cr_to_response(cr) for cr in requests]


@router.post(  # type: ignore[misc,untyped-decorator]
    "/change-requests/{request_id}/approve",
    response_model=ChangeRequestResponse,
    summary="Approve a change request",
)
async def approve_change_request(
    request_id: UUID,
    body: ApproveChangeRequest,
    current_user: AdminUser,
    svc: Annotated[ChangeRequestService, Depends(get_change_request_service)],
) -> ChangeRequestResponse:
    """Approve a resource change request and execute the action.

    POST /api/v1/scheduling-alerts/change-requests/{id}/approve

    Validates: Requirements 2.4, 15.6, 15.7
    """
    _log.log_started(
        "approve_change_request",
        request_id=str(request_id),
        admin_id=str(current_user.id),
    )

    try:
        result = await svc.approve_request(
            request_id=request_id,
            admin_id=current_user.id,
            admin_notes=body.admin_notes,
        )
    except Exception as exc:
        _log.log_failed("approve_change_request", error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve change request: {exc!s}",
        ) from exc

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.message,
        )

    if result.change_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found.",
        )

    _log.log_completed("approve_change_request", request_id=str(request_id))
    return _cr_to_response(result.change_request)


@router.post(  # type: ignore[misc,untyped-decorator]
    "/change-requests/{request_id}/deny",
    response_model=ChangeRequestResponse,
    summary="Deny a change request",
)
async def deny_change_request(
    request_id: UUID,
    body: DenyChangeRequest,
    current_user: AdminUser,
    svc: Annotated[ChangeRequestService, Depends(get_change_request_service)],
) -> ChangeRequestResponse:
    """Deny a resource change request with a reason.

    POST /api/v1/scheduling-alerts/change-requests/{id}/deny

    Validates: Requirements 2.4, 15.6, 15.7
    """
    _log.log_started(
        "deny_change_request",
        request_id=str(request_id),
        admin_id=str(current_user.id),
    )

    try:
        result = await svc.deny_request(
            request_id=request_id,
            admin_id=current_user.id,
            reason=body.reason,
        )
    except Exception as exc:
        _log.log_failed("deny_change_request", error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deny change request: {exc!s}",
        ) from exc

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.message,
        )

    if result.change_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found.",
        )

    _log.log_completed("deny_change_request", request_id=str(request_id))
    return _cr_to_response(result.change_request)
