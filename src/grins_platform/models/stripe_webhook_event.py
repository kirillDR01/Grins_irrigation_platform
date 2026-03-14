"""StripeWebhookEvent model for tracking Stripe webhook event processing.

Validates: Requirements 7.1
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from grins_platform.database import Base


class StripeWebhookEvent(Base):
    """Tracks Stripe webhook events for idempotent processing.

    Attributes:
        id: Unique identifier
        stripe_event_id: Stripe's unique event ID (unique constraint)
        event_type: Stripe event type (e.g., checkout.session.completed)
        processing_status: Current processing status
        error_message: Error details if processing failed
        event_data: Full event payload as JSONB
        processed_at: When the event was processed

    Validates: Requirements 7.1
    """

    __tablename__ = "stripe_webhook_events"
    __table_args__ = (
        Index("ix_stripe_webhook_events_stripe_event_id", "stripe_event_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    stripe_event_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<StripeWebhookEvent(id={self.id}, "
            f"stripe_event_id='{self.stripe_event_id}', "
            f"type='{self.event_type}', "
            f"status='{self.processing_status}')>"
        )
