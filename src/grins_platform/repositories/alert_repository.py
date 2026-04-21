"""Alert repository for database operations.

Provides persistence for admin-facing :class:`Alert` rows used by the
dashboard to surface noteworthy events (for example, a customer SMS
cancellation).

Validates: bughunt 2026-04-16 finding H-5
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

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

    async def get(self, alert_id: UUID) -> Alert | None:
        """Fetch a single :class:`Alert` row by primary key.

        Args:
            alert_id: Alert UUID.

        Returns:
            The Alert or None if no row matches.
        """
        self.log_started("get", alert_id=str(alert_id))
        stmt = select(Alert).where(Alert.id == alert_id).limit(1)
        result = await self.session.execute(stmt)
        row: Alert | None = result.scalar_one_or_none()
        self.log_completed("get", found=row is not None)
        return row

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

    async def list_unacknowledged_by_type(
        self,
        alert_type: str,
        limit: int = 100,
    ) -> list[Alert]:
        """Return unacknowledged alerts filtered by :attr:`Alert.type`.

        Args:
            alert_type: Alert type string (e.g. ``"informal_opt_out"``).
            limit: Maximum number of rows to return (default 100).

        Returns:
            List of matching :class:`Alert` rows in ascending created_at order.
        """
        self.log_started(
            "list_unacknowledged_by_type",
            alert_type=alert_type,
            limit=limit,
        )
        stmt = (
            select(Alert)
            .where(
                Alert.type == alert_type,
                Alert.acknowledged_at.is_(None),
            )
            .order_by(Alert.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        alerts = list(result.scalars().all())
        self.log_completed(
            "list_unacknowledged_by_type",
            alert_type=alert_type,
            count=len(alerts),
        )
        return alerts

    async def acknowledge(self, alert_id: UUID) -> Alert | None:
        """Mark an alert as acknowledged.

        Idempotent: if the row is already acknowledged, the existing
        ``acknowledged_at`` is preserved and returned unchanged.

        Args:
            alert_id: Alert UUID.

        Returns:
            The refreshed :class:`Alert` row, or None if no row matches.
        """
        self.log_started("acknowledge", alert_id=str(alert_id))
        row = await self.get(alert_id)
        if row is None:
            self.log_completed("acknowledge", alert_id=str(alert_id), found=False)
            return None
        if row.acknowledged_at is not None:
            self.log_completed(
                "acknowledge",
                alert_id=str(alert_id),
                already_acknowledged=True,
            )
            return row
        row.acknowledged_at = datetime.now(tz=timezone.utc)
        await self.session.flush()
        await self.session.refresh(row)
        self.log_completed(
            "acknowledge",
            alert_id=str(alert_id),
            acknowledged_at=row.acknowledged_at.isoformat(),
        )
        return row
