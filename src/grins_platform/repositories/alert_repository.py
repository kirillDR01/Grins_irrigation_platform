"""Alert repository for database operations.

Provides persistence for admin-facing :class:`Alert` rows used by the
dashboard to surface noteworthy events (for example, a customer SMS
cancellation).

Validates: bughunt 2026-04-16 finding H-5
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.alert import Alert

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AlertRepository(LoggerMixin):
    """Repository for :class:`Alert` database operations.

    Mirrors the pattern used by sibling repositories
    (e.g. :class:`AuditLogRepository`) — takes an :class:`AsyncSession`,
    exposes structured-logging wrappers via :class:`LoggerMixin`, and
    performs all I/O through the injected session.

    Validates: bughunt 2026-04-16 finding H-5
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations.
        """
        super().__init__()
        self.session = session

    async def create(self, alert: Alert) -> Alert:
        """Persist a new :class:`Alert` row.

        Args:
            alert: Fully-populated :class:`Alert` instance to persist.

        Returns:
            The refreshed Alert instance (server-side defaults applied).
        """
        self.log_started(
            "create",
            alert_type=alert.type,
            severity=alert.severity,
            entity_type=alert.entity_type,
            entity_id=str(alert.entity_id),
        )

        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)

        self.log_completed("create", alert_id=str(alert.id))
        return alert

    async def list_unacknowledged(self, limit: int = 100) -> list[Alert]:
        """Return the oldest-first list of unacknowledged alerts.

        Args:
            limit: Maximum number of rows to return (default 100).

        Returns:
            List of :class:`Alert` rows where :attr:`Alert.acknowledged_at`
            is NULL, ordered by :attr:`Alert.created_at` ascending.
        """
        self.log_started("list_unacknowledged", limit=limit)

        stmt = (
            select(Alert)
            .where(Alert.acknowledged_at.is_(None))
            .order_by(Alert.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        alerts = list(result.scalars().all())

        self.log_completed("list_unacknowledged", count=len(alerts))
        return alerts
