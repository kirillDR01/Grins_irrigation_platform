"""
Notification API endpoints.

Provides endpoints for triggering appointment notifications.

Validates: CRM Gap Closure Req 39.6
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.services.notification_service import NotificationService

router = APIRouter()


class NotificationEndpoints(LoggerMixin):
    """Notification API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = NotificationEndpoints()


# =============================================================================
# POST /api/v1/notifications/appointment/{id}/day-of - Day-of reminder (Req 39)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/appointment/{appointment_id}/day-of",
    summary="Trigger day-of appointment reminder",
    description=(
        "Trigger day-of reminders for today's appointments. "
        "Normally called by the daily background job at 7AM CT."
    ),
)
async def trigger_day_of_reminders(
    appointment_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, object]:
    """Trigger day-of appointment reminders.

    Validates: Requirement 39.6
    """
    _endpoints.log_started(
        "trigger_day_of_reminders",
        appointment_id=str(appointment_id),
    )

    notification_service = NotificationService()

    try:
        sent_count = await notification_service.send_day_of_reminders(session)
    except Exception as e:
        _endpoints.log_failed(
            "trigger_day_of_reminders",
            error=e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send day-of reminders: {e!s}",
        ) from e

    _endpoints.log_completed(
        "trigger_day_of_reminders",
        sent_count=sent_count,
    )

    return {
        "sent_count": sent_count,
        "appointment_id": str(appointment_id),
        "message": f"Day-of reminders sent: {sent_count}",
    }
