"""Sent Message Repository for tracking SMS communications.

Validates: AI Assistant Requirements 7.8, 7.9, 7.10
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.models.sent_message import SentMessage
from grins_platform.schemas.ai import DeliveryStatus, MessageType


class SentMessageRepository(LoggerMixin):
    """Repository for sent message operations."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(
        self,
        customer_id: UUID,
        message_type: MessageType,
        message_content: str,
        recipient_phone: str,
        job_id: UUID | None = None,
        appointment_id: UUID | None = None,
        scheduled_for: datetime | None = None,
        created_by: UUID | None = None,
    ) -> SentMessage:
        """Create a new sent message record.

        Args:
            customer_id: The customer ID
            message_type: Type of message
            message_content: The message content
            recipient_phone: Phone number to send to
            job_id: Optional job ID
            appointment_id: Optional appointment ID
            scheduled_for: Optional scheduled send time
            created_by: Optional user ID who created the message

        Returns:
            The created message record
        """
        self.log_started(
            "create_message",
            customer_id=str(customer_id),
            message_type=message_type.value,
        )

        status = DeliveryStatus.SCHEDULED if scheduled_for else DeliveryStatus.PENDING

        message = SentMessage(
            customer_id=customer_id,
            job_id=job_id,
            appointment_id=appointment_id,
            message_type=message_type.value,
            message_content=message_content,
            recipient_phone=recipient_phone,
            delivery_status=status.value,
            scheduled_for=scheduled_for,
            created_by=created_by,
        )

        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)

        self.log_completed("create_message", message_id=str(message.id))
        return message

    async def update(
        self,
        message_id: UUID,
        delivery_status: DeliveryStatus | None = None,
        twilio_sid: str | None = None,
        error_message: str | None = None,
        sent_at: datetime | None = None,
    ) -> SentMessage | None:
        """Update a sent message record.

        Args:
            message_id: The message ID
            delivery_status: New delivery status
            twilio_sid: Twilio message SID
            error_message: Error message if failed
            sent_at: When the message was sent

        Returns:
            The updated message or None if not found
        """
        self.log_started("update_message", message_id=str(message_id))

        result = await self.session.execute(
            select(SentMessage).where(SentMessage.id == message_id),
        )
        message: SentMessage | None = result.scalar_one_or_none()

        if not message:
            self.log_rejected("update_message", reason="message_not_found")
            return None

        if delivery_status:
            message.delivery_status = delivery_status.value
        if twilio_sid:
            message.twilio_sid = twilio_sid
        if error_message is not None:
            message.error_message = error_message
        if sent_at:
            message.sent_at = sent_at

        await self.session.flush()
        await self.session.refresh(message)

        self.log_completed("update_message", message_id=str(message_id))
        return message

    async def get_queue_grouped(
        self,
        include_pending: bool = True,
        include_scheduled: bool = True,
        include_sent_today: bool = True,
        include_failed: bool = True,
    ) -> dict[str, list[SentMessage]]:
        """Get messages grouped by status.

        Args:
            include_pending: Include pending messages
            include_scheduled: Include scheduled messages
            include_sent_today: Include messages sent today
            include_failed: Include failed messages

        Returns:
            Dictionary with lists of messages by status
        """
        self.log_started("get_queue_grouped")

        result: dict[str, list[SentMessage]] = {
            "pending": [],
            "scheduled": [],
            "sent_today": [],
            "failed": [],
        }

        if include_pending:
            pending_result = await self.session.execute(
                select(SentMessage)
                .where(SentMessage.delivery_status == DeliveryStatus.PENDING.value)
                .order_by(SentMessage.created_at.desc()),
            )
            result["pending"] = list(pending_result.scalars().all())

        if include_scheduled:
            scheduled_result = await self.session.execute(
                select(SentMessage)
                .where(SentMessage.delivery_status == DeliveryStatus.SCHEDULED.value)
                .order_by(SentMessage.scheduled_for.asc()),
            )
            result["scheduled"] = list(scheduled_result.scalars().all())

        if include_sent_today:
            today_start = datetime.now().replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            sent_result = await self.session.execute(
                select(SentMessage)
                .where(
                    and_(
                        SentMessage.delivery_status.in_(
                            [DeliveryStatus.SENT.value, DeliveryStatus.DELIVERED.value],
                        ),
                        SentMessage.sent_at >= today_start,
                    ),
                )
                .order_by(SentMessage.sent_at.desc()),
            )
            result["sent_today"] = list(sent_result.scalars().all())

        if include_failed:
            failed_result = await self.session.execute(
                select(SentMessage)
                .where(SentMessage.delivery_status == DeliveryStatus.FAILED.value)
                .order_by(SentMessage.created_at.desc()),
            )
            result["failed"] = list(failed_result.scalars().all())

        self.log_completed(
            "get_queue_grouped",
            pending=len(result["pending"]),
            scheduled=len(result["scheduled"]),
            sent_today=len(result["sent_today"]),
            failed=len(result["failed"]),
        )
        return result

    async def get_by_customer_and_type(
        self,
        customer_id: UUID,
        message_type: MessageType,
        hours_back: int = 24,
    ) -> list[SentMessage]:
        """Get recent messages for a customer of a specific type.

        Used for duplicate detection.

        Args:
            customer_id: The customer ID
            message_type: Type of message
            hours_back: How many hours back to search

        Returns:
            List of matching messages
        """
        self.log_started(
            "get_by_customer_and_type",
            customer_id=str(customer_id),
            message_type=message_type.value,
            hours_back=hours_back,
        )

        cutoff = datetime.now() - timedelta(hours=hours_back)

        result = await self.session.execute(
            select(SentMessage)
            .where(
                and_(
                    SentMessage.customer_id == customer_id,
                    SentMessage.message_type == message_type.value,
                    SentMessage.created_at >= cutoff,
                ),
            )
            .order_by(SentMessage.created_at.desc()),
        )
        messages = list(result.scalars().all())

        self.log_completed("get_by_customer_and_type", count=len(messages))
        return messages

    async def get_by_id(self, message_id: UUID) -> SentMessage | None:
        """Get a message by ID.

        Args:
            message_id: The message ID

        Returns:
            The message or None if not found
        """
        result = await self.session.execute(
            select(SentMessage).where(SentMessage.id == message_id),
        )
        message: SentMessage | None = result.scalar_one_or_none()
        return message

    async def delete(self, message_id: UUID) -> bool:
        """Delete a message (only if pending or scheduled).

        Args:
            message_id: The message ID

        Returns:
            True if deleted, False if not found or not deletable
        """
        self.log_started("delete_message", message_id=str(message_id))

        message = await self.get_by_id(message_id)
        if not message:
            self.log_rejected("delete_message", reason="message_not_found")
            return False

        if message.delivery_status not in [
            DeliveryStatus.PENDING.value,
            DeliveryStatus.SCHEDULED.value,
        ]:
            self.log_rejected(
                "delete_message",
                reason="cannot_delete_sent_message",
                status=message.delivery_status,
            )
            return False

        await self.session.delete(message)
        await self.session.flush()

        self.log_completed("delete_message", message_id=str(message_id))
        return True

    async def get_queue(
        self,
        status: DeliveryStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SentMessage], int]:
        """Get messages with pagination.

        Args:
            status: Filter by delivery status
            limit: Maximum results
            offset: Results to skip

        Returns:
            Tuple of (messages, total count)
        """
        self.log_started("get_queue_paginated", status=status, limit=limit)

        query = select(SentMessage)

        if status:
            query = query.where(SentMessage.delivery_status == status.value)

        # Get total count
        count_query = select(SentMessage)
        if status:
            count_query = count_query.where(
                SentMessage.delivery_status == status.value,
            )
        count_result = await self.session.execute(count_query)
        total = len(count_result.scalars().all())

        # Get paginated results
        query = query.order_by(SentMessage.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        messages = list(result.scalars().all())

        self.log_completed("get_queue_paginated", count=len(messages), total=total)
        return messages, total
