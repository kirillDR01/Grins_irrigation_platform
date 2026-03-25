"""Audit log API endpoint.

Provides paginated, filterable audit log retrieval.

Validates: CRM Gap Closure Req 74.3
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.audit import AuditLogFilters
from grins_platform.services.audit_service import AuditService

router = APIRouter()


class _AuditEndpoints(LoggerMixin):
    """Audit API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _AuditEndpoints()


@router.get(
    "",
    response_model=dict[str, Any],
    summary="Get audit log",
    description="Paginated audit log with optional filters.",
)
async def get_audit_log(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    actor_id: UUID | None = Query(default=None, description="Filter by actor"),
    action: str | None = Query(default=None, description="Filter by action"),
    resource_type: str | None = Query(
        default=None,
        description="Filter by resource type",
    ),
    date_from: datetime | None = Query(default=None, description="Filter from date"),
    date_to: datetime | None = Query(default=None, description="Filter to date"),
) -> dict[str, Any]:
    """Get paginated audit log.

    Validates: CRM Gap Closure Req 74.3
    """
    _endpoints.log_started("get_audit_log", page=page)

    filters = AuditLogFilters(
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
    )

    svc = AuditService()
    result = await svc.get_audit_log(session, filters)

    _endpoints.log_completed(
        "get_audit_log",
        count=len(result["items"]),
        total=result["total"],
    )
    return result
