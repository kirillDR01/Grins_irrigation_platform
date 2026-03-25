"""Sent messages API endpoints.

Provides paginated outbound notification history.

Validates: CRM Gap Closure Req 82.1, 82.2, 82.3
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.schemas.sent_message import (
    SentMessageListResponse,
    SentMessageResponse,
)

router = APIRouter()


class _SentMessageEndpoints(LoggerMixin):
    """Sent message API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _SentMessageEndpoints()


@router.get(
    "",
    response_model=SentMessageListResponse,
    summary="List sent messages",
    description="Paginated outbound notification history with filters.",
)
async def list_sent_messages(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    message_type: str | None = Query(
        default=None,
        description="Filter by message type",
    ),
    delivery_status: str | None = Query(
        default=None,
        description="Filter by delivery status",
    ),
    date_from: datetime | None = Query(default=None, description="Filter from date"),
    date_to: datetime | None = Query(default=None, description="Filter to date"),
    search: str | None = Query(default=None, description="Search content"),
) -> SentMessageListResponse:
    """List sent messages with pagination and filters.

    Validates: CRM Gap Closure Req 82.1, 82.2
    """
    _endpoints.log_started("list_sent_messages", page=page)

    repo = SentMessageRepository(session)
    messages, total = await repo.list_with_filters(
        page=page,
        page_size=page_size,
        message_type=message_type,
        delivery_status=delivery_status,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )

    items = [SentMessageResponse.model_validate(m) for m in messages]
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    _endpoints.log_completed("list_sent_messages", count=len(items), total=total)
    return SentMessageListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
