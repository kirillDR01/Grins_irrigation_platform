"""Communications API endpoints.

Provides listing and addressing of inbound communications.

Validates: CRM Gap Closure Req 4.2, 4.4
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.communication_repository import (
    CommunicationRepository,
)
from grins_platform.schemas.communication import (
    CommunicationResponse,
)

router = APIRouter()


class _CommunicationsEndpoints(LoggerMixin):
    """Communications API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _CommunicationsEndpoints()


@router.get(
    "",
    response_model=dict[str, Any],
    summary="List communications",
    description="List inbound communications with pagination.",
)
async def list_communications(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    addressed: bool | None = Query(
        default=None,
        description="Filter by addressed status",
    ),
) -> dict[str, Any]:
    """List inbound communications.

    Validates: CRM Gap Closure Req 4.2
    """
    _endpoints.log_started("list_communications", page=page)
    repo = CommunicationRepository(session)
    comms, total = await repo.list_with_filters(
        page=page,
        page_size=page_size,
        addressed=addressed,
    )
    items = [CommunicationResponse.model_validate(c) for c in comms]
    _endpoints.log_completed("list_communications", count=len(items), total=total)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch(
    "/{communication_id}/address",
    response_model=CommunicationResponse,
    summary="Mark communication as addressed",
    description="Mark an inbound communication as addressed.",
)
async def address_communication(
    communication_id: UUID,
    current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CommunicationResponse:
    """Mark a communication as addressed.

    Validates: CRM Gap Closure Req 4.4
    """
    _endpoints.log_started(
        "address_communication",
        communication_id=str(communication_id),
    )
    repo = CommunicationRepository(session)
    comm = await repo.mark_addressed(
        communication_id,
        addressed_by=current_user.id,
    )
    if not comm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Communication not found: {communication_id}",
        )
    _endpoints.log_completed(
        "address_communication",
        communication_id=str(communication_id),
    )
    return CommunicationResponse.model_validate(comm)
