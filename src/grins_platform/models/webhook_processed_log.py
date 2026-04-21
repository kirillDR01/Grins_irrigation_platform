"""Webhook processed-log model for durable fallback dedup.

A :class:`WebhookProcessedLog` row records that a specific provider
webhook message id was processed. The webhook route consults this
table when Redis is unavailable, turning the Redis-primary dedup path
into a fail-open-to-DB path (see Gap 07 — Webhook Security & Dedup).

Rows older than the pruning window (30 days by default) are deleted by
a daily background job.

Validates: Gap 07 — Webhook Security & Dedup (7.B)
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from grins_platform.database import Base


class WebhookProcessedLog(Base):
    """Durable dedup record for processed inbound webhooks.

    Attributes:
        id: Unique identifier (UUID).
        provider: Webhook provider slug (e.g. ``"callrail"``).
        provider_message_id: Provider-supplied stable message id
            (for CallRail this is ``resource_id``).
        created_at: Insertion time (tz-aware UTC); indexed for pruning.

    Validates: Gap 07 — Webhook Security & Dedup (7.B)
    """

    __tablename__ = "webhook_processed_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_message_id",
            name="uq_webhook_processed_logs_provider_msgid",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of the log row."""
        return (
            f"<WebhookProcessedLog(id={self.id}, provider='{self.provider}', "
            f"provider_message_id='{self.provider_message_id}')>"
        )
