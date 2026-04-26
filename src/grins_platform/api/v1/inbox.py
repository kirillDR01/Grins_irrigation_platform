"""Unified inbox API endpoint (gap-16 v0).

Read-only endpoint backing the fourth queue card on ``/schedule``. Accepts
optional ``triage`` filter (``all`` | ``needs_triage`` | ``orphans`` |
``unrecognized`` | ``opt_outs`` | ``archived``) and cursor-based
pagination.

Validates: scheduling-gaps gap-16.
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
from grins_platform.schemas.inbox import InboxListResponse
from grins_platform.services.inbox_service import InboxService

router = APIRouter(prefix="/inbox", tags=["inbox"])


class _InboxEndpoints(LoggerMixin):
    """Inbox API endpoint handlers with structured logging."""

    DOMAIN = "api"


_endpoints = _InboxEndpoints()


@router.get(
    "",
    response_model=InboxListResponse,
    summary="List unified inbox events",
    description=(
        "Return inbound replies merged across job_confirmation_responses, "
        "reschedule_requests, campaign_responses, and communications. "
        "Filterable by triage bucket and cursor-paginated."
    ),
)
async def list_inbox(
    _user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    triage: str | None = Query(
        default=None,
        description=(
            "Triage filter: all | needs_triage | orphans | unrecognized "
            "| opt_outs | archived. Default: all."
        ),
    ),
    cursor: str | None = Query(
        default=None,
        description="Opaque pagination cursor from a prior response",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum items to return per page",
    ),
) -> InboxListResponse:
    """Return one page of unified inbox events.

    Validates: scheduling-gaps gap-16.
    """
    _endpoints.log_started(
        "list_inbox",
        triage=triage,
        limit=limit,
        has_cursor=cursor is not None,
    )
    service = InboxService(session)
    result = await service.list_events(
        triage=triage,
        cursor=cursor,
        limit=limit,
    )
    _endpoints.log_completed(
        "list_inbox",
        count=len(result.items),
        has_more=result.has_more,
    )
    return result
