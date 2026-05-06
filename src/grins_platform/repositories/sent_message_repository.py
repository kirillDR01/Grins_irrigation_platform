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
        sales_calendar_event_id: UUID | None = None,
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
            sales_calendar_event_id: Optional estimate-visit anchor
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
            sales_calendar_event_id=sales_calendar_event_id,
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
        provider_message_id: str | None = None,
        error_message: str | None = None,
        sent_at: datetime | None = None,
    ) -> SentMessage | None:
        """Update a sent message record.

        Args:
            message_id: The message ID
            delivery_status: New delivery status
            provider_message_id: Provider message ID
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
        if provider_message_id:
            message.provider_message_id = provider_message_id
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
        appointment_id: UUID | None = None,
        sales_calendar_event_id: UUID | None = None,
        *,
        include_superseded: bool = False,
    ) -> list[SentMessage]:
        """Get recent messages for a customer of a specific type.

        Used for duplicate detection. By default excludes rows whose
        ``superseded_at`` is set so a tombstoned send no longer blocks a
        fresh re-send (matches :meth:`list_by_appointment`'s contract).

        Args:
            customer_id: The customer ID
            message_type: Type of message
            hours_back: How many hours back to search
            appointment_id: Optional appointment ID for per-appointment dedupe
            sales_calendar_event_id: Optional sales-event ID for per-event dedupe
            include_superseded: When True, include superseded rows
                (debugging only — production callers leave the default).

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

        conditions = [
            SentMessage.customer_id == customer_id,
            SentMessage.message_type == message_type.value,
            SentMessage.created_at >= cutoff,
        ]
        if appointment_id is not None:
            conditions.append(SentMessage.appointment_id == appointment_id)
        if sales_calendar_event_id is not None:
            conditions.append(
                SentMessage.sales_calendar_event_id == sales_calendar_event_id,
            )
        if not include_superseded:
            conditions.append(SentMessage.superseded_at.is_(None))

        result = await self.session.execute(
            select(SentMessage)
            .where(and_(*conditions))
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

    async def list_by_appointment(
        self,
        appointment_id: UUID,
        include_superseded: bool = False,
    ) -> list[SentMessage]:
        """List outbound messages for an appointment, newest first.

        Args:
            appointment_id: The appointment UUID
            include_superseded: If False (default), filter out rows whose
                ``superseded_at`` is set (stale confirmations).

        Returns:
            Messages ordered by ``sent_at`` desc with ``created_at`` as
            fallback so unsent (pending) rows still appear at the top.
        """
        self.log_started(
            "list_by_appointment",
            appointment_id=str(appointment_id),
        )
        conditions = [SentMessage.appointment_id == appointment_id]
        if not include_superseded:
            conditions.append(SentMessage.superseded_at.is_(None))
        result = await self.session.execute(
            select(SentMessage)
            .where(and_(*conditions))
            .order_by(
                SentMessage.sent_at.desc().nulls_last(),
                SentMessage.created_at.desc(),
            ),
        )
        messages = list(result.scalars().all())
        self.log_completed("list_by_appointment", count=len(messages))
        return messages

    async def list_by_sales_calendar_event(
        self,
        sales_calendar_event_id: UUID,
        include_superseded: bool = False,
    ) -> list[SentMessage]:
        """List outbound messages for a sales calendar event, newest first.

        Mirror of :meth:`list_by_appointment` for the estimate-visit lifecycle.
        """
        self.log_started(
            "list_by_sales_calendar_event",
            sales_calendar_event_id=str(sales_calendar_event_id),
        )
        conditions = [
            SentMessage.sales_calendar_event_id == sales_calendar_event_id,
        ]
        if not include_superseded:
            conditions.append(SentMessage.superseded_at.is_(None))
        result = await self.session.execute(
            select(SentMessage)
            .where(and_(*conditions))
            .order_by(
                SentMessage.sent_at.desc().nulls_last(),
                SentMessage.created_at.desc(),
            ),
        )
        messages = list(result.scalars().all())
        self.log_completed("list_by_sales_calendar_event", count=len(messages))
        return messages

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

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        message_type: str | None = None,
        delivery_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
        customer_id: UUID | None = None,
    ) -> tuple[list[SentMessage], int]:
        """List sent messages with pagination and filters.

        Args:
            page: Page number (1-based).
            page_size: Items per page.
            message_type: Filter by message type.
            delivery_status: Filter by delivery status.
            date_from: Filter from date.
            date_to: Filter to date.
            search: Search in message content.
            customer_id: Filter by customer.

        Returns:
            Tuple of (messages, total count).

        Validates: CRM Gap Closure Req 82.1, 82.2, 82.3
        """
        from sqlalchemy import func as sa_func  # noqa: PLC0415

        self.log_started(
            "list_with_filters",
            page=page,
            page_size=page_size,
        )

        query = select(SentMessage)
        count_query = select(sa_func.count()).select_from(SentMessage)

        # Apply filters
        if message_type:
            query = query.where(SentMessage.message_type == message_type)
            count_query = count_query.where(
                SentMessage.message_type == message_type,
            )
        if delivery_status:
            query = query.where(SentMessage.delivery_status == delivery_status)
            count_query = count_query.where(
                SentMessage.delivery_status == delivery_status,
            )
        if date_from:
            query = query.where(SentMessage.created_at >= date_from)
            count_query = count_query.where(SentMessage.created_at >= date_from)
        if date_to:
            query = query.where(SentMessage.created_at <= date_to)
            count_query = count_query.where(SentMessage.created_at <= date_to)
        if search:
            query = query.where(
                SentMessage.message_content.ilike(f"%{search}%"),
            )
            count_query = count_query.where(
                SentMessage.message_content.ilike(f"%{search}%"),
            )
        if customer_id:
            query = query.where(SentMessage.customer_id == customer_id)
            count_query = count_query.where(
                SentMessage.customer_id == customer_id,
            )

        # Get total count
        count_result = await self.session.execute(count_query)
        total: int = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        query = query.order_by(SentMessage.created_at.desc())
        query = query.limit(page_size).offset(offset)

        result = await self.session.execute(query)
        messages = list(result.scalars().all())

        self.log_completed(
            "list_with_filters",
            count=len(messages),
            total=total,
        )
        return messages, total
