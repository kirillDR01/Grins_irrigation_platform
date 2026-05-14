"""Admin notifications API endpoints.

Powers the top-nav bell + dropdown for admin users. Three routes:

- ``GET /admin/notifications`` — list recent (paged).
- ``GET /admin/notifications/unread-count`` — polled at 30s by the bell.
- ``POST /admin/notifications/{id}/read`` — mark-read, called when the
  user clicks a dropdown row.

Admin-only — gated by :data:`AdminUser`.

Validates: Cluster H §5.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    AdminUser,  # noqa: TC001 - runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.admin_notification_repository import (
    AdminNotificationRepository,
)
from grins_platform.schemas.admin_notification import (
    AdminNotificationListResponse,
    AdminNotificationResponse,
    AdminNotificationUnreadCountResponse,
)

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


class _AdminNotificationEndpoints(LoggerMixin):
    """Admin notification API endpoint handlers with structured logging."""

    DOMAIN = "api"


_endpoints = _AdminNotificationEndpoints()


@router.get(
    "",
    response_model=AdminNotificationListResponse,
    summary="List admin notifications",
    description=(
        "Return the most recent admin notifications, newest-first. "
        "Surfaces the top-nav bell dropdown."
    ),
)
async def list_admin_notifications(
    _current_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of notifications to return (default 20).",
    ),
) -> AdminNotificationListResponse:
    """List recent admin notifications."""
    _endpoints.log_started("list_admin_notifications", limit=limit)
    repo = AdminNotificationRepository(session=session)
    rows = await repo.list_recent(limit=limit)
    items = [AdminNotificationResponse.model_validate(row) for row in rows]
    _endpoints.log_completed("list_admin_notifications", count=len(items))
    return AdminNotificationListResponse(items=items, total=len(items))


@router.get(
    "/unread-count",
    response_model=AdminNotificationUnreadCountResponse,
    summary="Unread notification count",
    description="Return the count of unread admin notifications (polled by bell).",
)
async def admin_notification_unread_count(
    _current_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminNotificationUnreadCountResponse:
    """Return the unread count."""
    _endpoints.log_started("admin_notification_unread_count")
    repo = AdminNotificationRepository(session=session)
    unread = await repo.count_unread()
    _endpoints.log_completed("admin_notification_unread_count", unread=unread)
    return AdminNotificationUnreadCountResponse(unread=unread)


@router.post(
    "/{notification_id}/read",
    response_model=AdminNotificationResponse,
    summary="Mark notification as read",
    description=(
        "Mark a single notification as read. Idempotent at the row level — "
        "returns 404 if the notification doesn't exist OR is already read."
    ),
)
async def mark_admin_notification_read(
    _current_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    notification_id: Annotated[UUID, Path(..., description="Notification UUID")],
) -> AdminNotificationResponse:
    """Mark a notification as read."""
    _endpoints.log_started(
        "mark_admin_notification_read",
        notification_id=str(notification_id),
    )
    repo = AdminNotificationRepository(session=session)
    updated = await repo.mark_read(notification_id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already read.",
        )
    _endpoints.log_completed(
        "mark_admin_notification_read",
        notification_id=str(notification_id),
    )
    return AdminNotificationResponse.model_validate(updated)
