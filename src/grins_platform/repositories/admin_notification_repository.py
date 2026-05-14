"""AdminNotification repository for in-app admin inbox.

Provides persistence for :class:`AdminNotification` rows used by the
top-nav bell + dropdown so admin users can see estimate decisions,
appointment cancellations, and late reschedule attempts even when the
original SMS/email channel was missed.

Validates: Cluster H §5.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.admin_notification import AdminNotification

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AdminNotificationRepository(LoggerMixin):
    """Repository for :class:`AdminNotification` database operations.

    Mirrors :class:`AlertRepository` — takes an :class:`AsyncSession`,
    exposes structured-logging wrappers via :class:`LoggerMixin`, and
    performs all I/O through the injected session.

    Validates: Cluster H §5.
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(
        self,
        notification: AdminNotification,
    ) -> AdminNotification:
        """Persist a new :class:`AdminNotification` row.

        Args:
            notification: Fully-populated :class:`AdminNotification` to persist.

        Returns:
            The refreshed AdminNotification (server-side defaults applied).
        """
        self.log_started(
            "create",
            event_type=notification.event_type,
            subject_resource_type=notification.subject_resource_type,
        )

        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)

        self.log_completed("create", notification_id=str(notification.id))
        return notification

    async def list_recent(self, limit: int = 20) -> list[AdminNotification]:
        """Return the newest-first list of notifications.

        Args:
            limit: Maximum number of rows to return (default 20).

        Returns:
            List of :class:`AdminNotification` rows ordered by
            ``created_at`` descending.
        """
        self.log_started("list_recent", limit=limit)
        stmt = (
            select(AdminNotification)
            .order_by(AdminNotification.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        self.log_completed("list_recent", count=len(rows))
        return rows

    async def count_unread(self) -> int:
        """Return the count of notifications with ``read_at IS NULL``."""
        self.log_started("count_unread")
        stmt = (
            select(func.count())
            .select_from(AdminNotification)
            .where(AdminNotification.read_at.is_(None))
        )
        count = int((await self.session.execute(stmt)).scalar_one())
        self.log_completed("count_unread", count=count)
        return count

    async def mark_read(
        self,
        notification_id: UUID,
    ) -> AdminNotification | None:
        """Mark a notification as read; idempotent.

        Returns the updated row, or ``None`` if no row was updated (either
        the id is unknown, or the row is already read).
        """
        self.log_started("mark_read", notification_id=str(notification_id))
        stmt = (
            update(AdminNotification)
            .where(
                AdminNotification.id == notification_id,
                AdminNotification.read_at.is_(None),
            )
            .values(read_at=func.now())
            .returning(AdminNotification)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        await self.session.flush()
        self.log_completed(
            "mark_read",
            notification_id=str(notification_id),
            updated=row is not None,
        )
        return row
