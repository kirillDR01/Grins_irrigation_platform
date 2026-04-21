"""Alerts API endpoint.

Exposes admin-facing :class:`Alert` rows (e.g. customer SMS
cancellations) to the dashboard.

Validates: bughunt 2026-04-16 finding H-5, Gap 06 opt-out management.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    ManagerOrAdminUser,  # noqa: TC001 - runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import AlertType
from grins_platform.repositories.alert_repository import AlertRepository
from grins_platform.schemas.alert import AlertListResponse, AlertResponse
from grins_platform.services.sms_service import SMSService

router = APIRouter(prefix="/alerts", tags=["alerts"])


class _AlertEndpoints(LoggerMixin):
    """Alert API endpoint handlers with structured logging."""

    DOMAIN = "api"


_endpoints = _AlertEndpoints()


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List admin alerts",
    description=(
        "Return admin-facing alerts (e.g. customer SMS cancellations). "
        "Defaults to unacknowledged only."
    ),
)
async def list_alerts(
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    acknowledged: bool = Query(
        default=False,
        description=(
            "If False (default), only unacknowledged alerts are returned. "
            "Acknowledged alerts are not currently exposed via this "
            "endpoint — pass True only once the acknowledge workflow is "
            "implemented."
        ),
    ),
    type: str | None = Query(  # noqa: A002
        default=None,
        description=(
            "Optional alert type filter (e.g. 'informal_opt_out'). When "
            "provided, only unacknowledged alerts of that type are returned."
        ),
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of alerts to return",
    ),
) -> AlertListResponse:
    """Return admin alerts.

    Only unacknowledged alerts are returned. The ``acknowledged`` query
    parameter is accepted for forward-compat with an eventual dismissal
    workflow, but passing ``True`` currently yields an empty list.

    Validates: bughunt 2026-04-16 finding H-5, Gap 06 (type filter).
    """
    _endpoints.log_started(
        "list_alerts",
        acknowledged=acknowledged,
        type=type,
        limit=limit,
    )

    repo = AlertRepository(session=session)

    if acknowledged:
        # Acknowledged-alert listing isn't implemented yet; return empty.
        alerts: list[AlertResponse] = []
        total = 0
    elif type is not None:
        rows = await repo.list_unacknowledged_by_type(
            alert_type=type,
            limit=limit,
        )
        alerts = [AlertResponse.model_validate(row) for row in rows]
        total = len(alerts)
    else:
        rows = await repo.list_unacknowledged(limit=limit)
        alerts = [AlertResponse.model_validate(row) for row in rows]
        total = len(alerts)

    _endpoints.log_completed("list_alerts", count=total)
    return AlertListResponse(items=alerts, total=total)


@router.post(
    "/{alert_id}/confirm-opt-out",
    response_model=AlertResponse,
    summary="Admin-confirm an informal opt-out alert",
    description=(
        "Admin workflow for an unacknowledged INFORMAL_OPT_OUT alert: "
        "writes an SmsConsentRecord(opt_out_method='admin_confirmed_informal'), "
        "acknowledges the alert, sends the opt-out confirmation SMS, and "
        "emits both `sms.informal_opt_out.confirmed` and "
        "`sms.consent.hard_stop_received` audit events."
    ),
)
async def confirm_informal_opt_out(
    current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    alert_id: Annotated[UUID, Path(..., description="Alert UUID")],
) -> AlertResponse:
    """Confirm an informal opt-out alert.

    Returns the updated :class:`AlertResponse` (now with
    ``acknowledged_at`` set).
    """
    _endpoints.log_started(
        "confirm_informal_opt_out",
        alert_id=str(alert_id),
        actor_id=str(current_user.id) if current_user else None,
    )

    repo = AlertRepository(session=session)
    alert = await repo.get(alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    if alert.type != AlertType.INFORMAL_OPT_OUT.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Alert {alert_id} has type={alert.type}; only "
                "informal_opt_out alerts can be confirmed via this route."
            ),
        )
    if alert.acknowledged_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alert {alert_id} is already acknowledged.",
        )
    if alert.entity_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Alert is not attached to a customer; link the phone to a "
                "customer before confirming the opt-out."
            ),
        )

    sms_service = SMSService(session)
    try:
        acknowledged = await sms_service.confirm_informal_opt_out(
            alert_id,
            actor_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    _endpoints.log_completed(
        "confirm_informal_opt_out",
        alert_id=str(alert_id),
    )
    return AlertResponse.model_validate(acknowledged)


@router.post(
    "/{alert_id}/dismiss",
    response_model=AlertResponse,
    summary="Dismiss an admin alert without writing consent",
    description=(
        "Acknowledges the alert (primarily informal_opt_out) without "
        "writing any SmsConsentRecord. Emits `sms.informal_opt_out.dismissed` "
        "for informal_opt_out alerts."
    ),
)
async def dismiss_alert(
    current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    alert_id: Annotated[UUID, Path(..., description="Alert UUID")],
) -> AlertResponse:
    """Dismiss an alert. Only informal_opt_out supported for now."""
    _endpoints.log_started(
        "dismiss_alert",
        alert_id=str(alert_id),
        actor_id=str(current_user.id) if current_user else None,
    )

    repo = AlertRepository(session=session)
    alert = await repo.get(alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    if alert.type != AlertType.INFORMAL_OPT_OUT.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Dismissal of alert type '{alert.type}' is not supported."
            ),
        )
    if alert.acknowledged_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alert {alert_id} is already acknowledged.",
        )

    sms_service = SMSService(session)
    try:
        acknowledged = await sms_service.dismiss_informal_opt_out(
            alert_id,
            actor_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    _endpoints.log_completed("dismiss_alert", alert_id=str(alert_id))
    return AlertResponse.model_validate(acknowledged)
