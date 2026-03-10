"""Repository for Stripe webhook event operations.

Validates: Requirements 7.1, 7.2, 7.3
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.models.stripe_webhook_event import StripeWebhookEvent


class StripeWebhookEventRepository(LoggerMixin):
    """Repository for Stripe webhook event deduplication and tracking."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def get_by_stripe_event_id(
        self,
        stripe_event_id: str,
    ) -> StripeWebhookEvent | None:
        """Look up a webhook event by Stripe's event ID.

        Args:
            stripe_event_id: The unique event ID from Stripe.

        Returns:
            The event record or None if not found.
        """
        self.log_started("get_by_stripe_event_id", stripe_event_id=stripe_event_id)
        result = await self.session.execute(
            select(StripeWebhookEvent).where(
                StripeWebhookEvent.stripe_event_id == stripe_event_id,
            ),
        )
        event: StripeWebhookEvent | None = result.scalar_one_or_none()
        self.log_completed("get_by_stripe_event_id", found=event is not None)
        return event

    async def create_event_record(
        self,
        stripe_event_id: str,
        event_type: str,
        event_data: dict[str, Any] | None = None,
        processing_status: str = "pending",
    ) -> StripeWebhookEvent:
        """Create a new webhook event record.

        Args:
            stripe_event_id: Stripe's unique event ID.
            event_type: The Stripe event type (e.g. checkout.session.completed).
            event_data: Full event payload.
            processing_status: Initial processing status.

        Returns:
            The created event record.
        """
        self.log_started(
            "create_event_record",
            stripe_event_id=stripe_event_id,
            event_type=event_type,
        )
        event = StripeWebhookEvent(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            event_data=event_data,
            processing_status=processing_status,
        )
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        self.log_completed("create_event_record", event_id=str(event.id))
        return event

    async def mark_processed(self, event: StripeWebhookEvent) -> None:
        """Mark an event as successfully processed.

        Args:
            event: The webhook event record to update.
        """
        event.processing_status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def mark_failed(
        self,
        event: StripeWebhookEvent,
        error_message: str,
    ) -> None:
        """Mark an event as failed with an error message.

        Args:
            event: The webhook event record to update.
            error_message: Description of the failure.
        """
        event.processing_status = "failed"
        event.error_message = error_message
        event.processed_at = datetime.now(timezone.utc)
        await self.session.flush()
