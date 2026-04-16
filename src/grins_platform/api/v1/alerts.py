"""Alerts API endpoint.

Exposes admin-facing :class:`Alert` rows (e.g. customer SMS
cancellations) to the dashboard.

Validates: bughunt 2026-04-16 finding H-5
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    ManagerOrAdminUser,  # noqa: TC001 - runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.alert_repository import AlertRepository
from grins_platform.schemas.alert import AlertListResponse, AlertResponse

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

    Validates: bughunt 2026-04-16 finding H-5
    """
    _endpoints.log_started("list_alerts", acknowledged=acknowledged, limit=limit)

    repo = AlertRepository(session=session)

    if acknowledged:
        # Acknowledged-alert listing isn't implemented yet; return empty.
        alerts: list[AlertResponse] = []
        total = 0
    else:
        rows = await repo.list_unacknowledged(limit=limit)
        alerts = [AlertResponse.model_validate(row) for row in rows]
        total = len(alerts)

    _endpoints.log_completed("list_alerts", count=total)
    return AlertListResponse(items=alerts, total=total)
