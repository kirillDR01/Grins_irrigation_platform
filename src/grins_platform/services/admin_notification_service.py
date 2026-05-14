"""AdminNotificationService — fire-and-forget admin inbox writer.

Provides a single :meth:`record` entry point for upstream services (estimate
service, notification service) to persist an in-app admin notification
row. All exceptions are caught and logged — admin notification rows must
NEVER block the originating customer action (estimate approval, SMS
cancellation, etc.). Mirrors the catch-and-swallow discipline at
:meth:`NotificationService.send_admin_cancellation_alert`.

Validates: Cluster H §5.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.models.admin_notification import AdminNotification
from grins_platform.models.enums import (
    AdminNotificationEventType,  # noqa: TC001 — used at runtime via .value
)
from grins_platform.repositories.admin_notification_repository import (
    AdminNotificationRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AdminNotificationService(LoggerMixin):
    """Service that writes :class:`AdminNotification` rows.

    Single public method: :meth:`record`. Always swallows DB errors and
    logs them via :meth:`log_failed`. Does not commit; the caller's
    session handles transaction lifecycle.

    Validates: Cluster H §5.
    """

    DOMAIN = "admin_notification_service"

    async def record(
        self,
        *,
        event_type: AdminNotificationEventType,
        subject_resource_type: str,
        subject_resource_id: UUID,
        summary: str,
        actor_user_id: UUID | None,
        db: AsyncSession,
    ) -> None:
        """Persist an admin notification row. Never raises.

        Args:
            event_type: One of :class:`AdminNotificationEventType`.
            subject_resource_type: Logical entity type
                (e.g. ``"estimate"``, ``"appointment"``).
            subject_resource_id: UUID of the referenced entity.
            summary: Short human-readable summary (≤280 chars).
            actor_user_id: Staff UUID who triggered the event, or ``None``
                for portal-driven events (e.g. customer approve via portal).
            db: Active database session.
        """
        self.log_started(
            "record",
            event_type=event_type.value,
            subject_resource_type=subject_resource_type,
            subject_resource_id=str(subject_resource_id),
        )

        try:
            repo = AdminNotificationRepository(db)
            await repo.create(
                AdminNotification(
                    event_type=event_type.value,
                    subject_resource_type=subject_resource_type,
                    subject_resource_id=subject_resource_id,
                    summary=summary,
                    actor_user_id=actor_user_id,
                ),
            )
        except Exception as exc:
            # Per spec: never re-raise. Log and continue.
            self.log_failed(
                "record",
                error=exc,
                event_type=event_type.value,
                subject_resource_type=subject_resource_type,
                subject_resource_id=str(subject_resource_id),
            )
            return

        self.log_completed(
            "record",
            event_type=event_type.value,
            subject_resource_id=str(subject_resource_id),
        )
