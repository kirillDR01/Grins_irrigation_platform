"""Webhook processed-log repository for fallback-dedup persistence.

Backs the Gap 07 (7.B) DB-fallback dedup path: when Redis is
unavailable, the inbound CallRail webhook route consults this
repository to answer "has this provider message id been processed
before?" and marks successful processing durably.

Validates: Gap 07 — Webhook Security & Dedup (7.B)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from grins_platform.log_config import LoggerMixin
from grins_platform.models.webhook_processed_log import WebhookProcessedLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WebhookProcessedLogRepository(LoggerMixin):
    """Repository for :class:`WebhookProcessedLog` database operations.

    Mirrors :class:`grins_platform.repositories.alert_repository.AlertRepository`:
    takes an :class:`AsyncSession` in the constructor, inherits structured
    logging from :class:`LoggerMixin`, and performs all I/O through the
    injected session.

    Validates: Gap 07 — Webhook Security & Dedup (7.B)
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations.
        """
        super().__init__()
        self.session = session

    async def exists(self, provider: str, provider_message_id: str) -> bool:
        """Return True if a row already records this provider message id.

        Args:
            provider: Provider slug (e.g. ``"callrail"``).
            provider_message_id: Provider-supplied stable message id.

        Returns:
            True if a matching row exists; False otherwise.
        """
        self.log_started(
            "exists",
            provider=provider,
            provider_message_id=provider_message_id,
        )
        stmt = (
            select(WebhookProcessedLog.id)
            .where(
                WebhookProcessedLog.provider == provider,
                WebhookProcessedLog.provider_message_id == provider_message_id,
            )
            .limit(1)
        )
        row = await self.session.scalar(stmt)
        found = row is not None
        self.log_completed("exists", found=found)
        return found

    async def mark_processed(
        self,
        provider: str,
        provider_message_id: str,
    ) -> None:
        """Durably record that this provider message id was processed.

        Race-safe under concurrent webhook deliveries: uses
        ``INSERT ... ON CONFLICT DO NOTHING`` on the composite unique
        constraint ``(provider, provider_message_id)``.

        Args:
            provider: Provider slug.
            provider_message_id: Provider-supplied stable message id.
        """
        self.log_started(
            "mark_processed",
            provider=provider,
            provider_message_id=provider_message_id,
        )
        stmt = (
            pg_insert(WebhookProcessedLog)
            .values(
                provider=provider,
                provider_message_id=provider_message_id,
            )
            .on_conflict_do_nothing(
                index_elements=["provider", "provider_message_id"],
            )
        )
        _ = await self.session.execute(stmt)
        await self.session.flush()
        self.log_completed("mark_processed")

    async def prune_older_than(self, days: int) -> int:
        """Delete rows whose ``created_at`` is older than ``days`` days.

        Args:
            days: Age threshold in days.

        Returns:
            Number of rows deleted.
        """
        self.log_started("prune_older_than", days=days)
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        stmt = delete(WebhookProcessedLog).where(
            WebhookProcessedLog.created_at < cutoff,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        deleted = int(getattr(result, "rowcount", 0) or 0)
        self.log_completed("prune_older_than", deleted=deleted)
        return deleted
