"""Alerts API endpoint.

Exposes admin-facing :class:`Alert` rows (e.g. customer SMS
cancellations) to the dashboard.

Validates: bughunt 2026-04-16 finding H-5, Gap 06 opt-out management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
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
from grins_platform.schemas.alert import (
    AlertCountsResponse,
    AlertListResponse,
    AlertResponse,
)
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
            "If True, acknowledged alerts are returned (history view)."
        ),
    ),
    type: str | None = Query(  # noqa: A002
        default=None,
        description=(
            "Single-type filter (back-compat). For multi-type filtering, "
            "use the repeatable ``alert_type`` query param."
        ),
    ),
    alert_type: list[str] | None = Query(
        default=None,
        description=(
            "Repeatable alert type filter (e.g. "
            "?alert_type=pending_reschedule_request"
            "&alert_type=informal_opt_out)."
        ),
    ),
    severity: list[str] | None = Query(
        default=None,
        description="Repeatable severity filter (info / warning / error).",
    ),
    since: datetime | None = Query(
        default=None,
        description=(
            "Acknowledged-history only: return rows whose "
            "acknowledged_at >= since (ISO 8601)."
        ),
    ),
    sort: Literal["created_at_asc", "created_at_desc"] = Query(
        default="created_at_desc",
        description="Sort order on created_at (default: newest first).",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Pagination offset.",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of alerts to return.",
    ),
) -> AlertListResponse:
    """Return admin alerts.

    Validates: bughunt 2026-04-16 finding H-5, Gap 06 (type filter),
               scheduling-gaps gap-14 (multi-type/severity, acknowledged
               history, offset+sort).
    """
    _endpoints.log_started(
        "list_alerts",
        acknowledged=acknowledged,
        single_type=type,
        types_count=len(alert_type) if alert_type else 0,
        severities_count=len(severity) if severity else 0,
        offset=offset,
        limit=limit,
        sort=sort,
    )

    # Merge the legacy single-`type` and the new repeatable `alert_type`
    # query params into one normalized list (back-compat with Gap 06
    # callers that still pass ?type=informal_opt_out).
    types_filter: list[str] | None
    if alert_type:
        types_filter = list(alert_type)
        if type is not None and type not in types_filter:
            types_filter.append(type)
    elif type is not None:
        types_filter = [type]
    else:
        types_filter = None

    repo = AlertRepository(session=session)

    if acknowledged:
        rows = await repo.list_acknowledged(
            limit=limit,
            offset=offset,
            since=since,
            types=types_filter,
            severities=severity,
            sort=sort,
        )
    else:
        rows = await repo.list_unacknowledged_filtered(
            types=types_filter,
            severities=severity,
            offset=offset,
            limit=limit,
            sort=sort,
        )

    alerts = [AlertResponse.model_validate(row) for row in rows]
    total = len(alerts)

    _endpoints.log_completed("list_alerts", count=total)
    return AlertListResponse(items=alerts, total=total)


@router.get(
    "/counts",
    response_model=AlertCountsResponse,
    summary="Per-type counts of unacknowledged admin alerts",
    description=(
        "Returns a map of ``AlertType`` → count of unacknowledged rows. "
        "Types with zero open rows are present with value 0 so the "
        "dashboard cards do not need to special-case missing keys."
    ),
)
async def get_alert_counts(
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AlertCountsResponse:
    """Return per-type counts of unacknowledged alerts.

    Validates: scheduling-gaps gap-14 (dashboard alert-counts feed).
    """
    _endpoints.log_started("alert_counts")

    repo = AlertRepository(session=session)
    raw_counts = await repo.count_unacknowledged_by_type()

    # Backfill all known AlertType values with zero so the FE can render
    # cards without conditional defaults.
    counts: dict[str, int] = {
        member.value: raw_counts.get(member.value, 0) for member in AlertType
    }
    # Preserve any unknown keys that future writers might emit (forward-compat).
    counts.update(
        {key: value for key, value in raw_counts.items() if key not in counts},
    )
    total = sum(counts.values())

    _endpoints.log_completed("alert_counts", total=total)
    return AlertCountsResponse(counts=counts, total=total)


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an admin alert (idempotent)",
    description=(
        "Generic acknowledge endpoint. Idempotent — if the alert is "
        "already acknowledged, the existing acknowledged_at is returned "
        "unchanged. Distinct from /confirm-opt-out and /dismiss, which "
        "carry side effects specific to informal_opt_out."
    ),
)
async def acknowledge_alert(
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    alert_id: Annotated[UUID, Path(..., description="Alert UUID")],
) -> AlertResponse:
    """Acknowledge an admin alert.

    Validates: scheduling-gaps gap-14 (manual ack from generic alerts UI).
    """
    _endpoints.log_started("acknowledge_alert", alert_id=str(alert_id))

    repo = AlertRepository(session=session)
    acknowledged = await repo.acknowledge(alert_id)
    if acknowledged is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    _endpoints.log_completed("acknowledge_alert", alert_id=str(alert_id))
    return AlertResponse.model_validate(acknowledged)  # type: ignore[no-any-return]


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
            detail=(f"Dismissal of alert type '{alert.type}' is not supported."),
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
