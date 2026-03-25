"""Communication repository for database operations.

CRUD + unaddressed count query + mark addressed.

Validates: CRM Gap Closure Req 4.2, 4.4
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.communication import Communication

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class CommunicationRepository(LoggerMixin):
    """Repository for communication database operations.

    Validates: CRM Gap Closure Req 4.2, 4.4
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(
        self,
        customer_id: UUID,
        channel: str,
        direction: str,
        content: str,
    ) -> Communication:
        """Create a new communication record.

        Args:
            customer_id: Customer UUID
            channel: Communication channel (sms, email, phone)
            direction: Inbound or outbound
            content: Message content

        Returns:
            Created Communication instance
        """
        self.log_started("create", channel=channel, direction=direction)

        communication = Communication(
            customer_id=customer_id,
            channel=channel,
            direction=direction,
            content=content,
        )

        self.session.add(communication)
        await self.session.flush()
        await self.session.refresh(communication)

        self.log_completed("create", communication_id=str(communication.id))
        return communication

    async def get_by_id(self, communication_id: UUID) -> Communication | None:
        """Get a communication by ID.

        Args:
            communication_id: Communication UUID

        Returns:
            Communication instance or None if not found
        """
        self.log_started("get_by_id", communication_id=str(communication_id))

        stmt = select(Communication).where(Communication.id == communication_id)
        result = await self.session.execute(stmt)
        communication: Communication | None = result.scalar_one_or_none()

        self.log_completed(
            "get_by_id",
            found=communication is not None,
        )
        return communication

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        channel: str | None = None,
        addressed: bool | None = None,
    ) -> tuple[list[Communication], int]:
        """List communications with filtering and pagination.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            customer_id: Filter by customer
            channel: Filter by channel
            addressed: Filter by addressed status

        Returns:
            Tuple of (list of communications, total count)
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        base_query = select(Communication)
        count_query = select(func.count(Communication.id))

        if customer_id is not None:
            base_query = base_query.where(Communication.customer_id == customer_id)
            count_query = count_query.where(Communication.customer_id == customer_id)

        if channel is not None:
            base_query = base_query.where(Communication.channel == channel)
            count_query = count_query.where(Communication.channel == channel)

        if addressed is not None:
            base_query = base_query.where(Communication.addressed == addressed)
            count_query = count_query.where(Communication.addressed == addressed)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(Communication.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        communications = list(result.scalars().all())

        self.log_completed(
            "list_with_filters",
            count=len(communications),
            total=total,
        )
        return communications, total

    async def get_unaddressed_count(self) -> int:
        """Get count of unaddressed communications.

        Returns:
            Count of unaddressed communications

        Validates: CRM Gap Closure Req 4.2
        """
        self.log_started("get_unaddressed_count")

        stmt = (
            select(func.count(Communication.id)).where(Communication.addressed == False)  # noqa: E712
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        self.log_completed("get_unaddressed_count", count=count)
        return count

    async def mark_addressed(
        self,
        communication_id: UUID,
        addressed_by: UUID,
    ) -> Communication | None:
        """Mark a communication as addressed.

        Args:
            communication_id: Communication UUID
            addressed_by: Staff UUID who addressed it

        Returns:
            Updated Communication or None if not found

        Validates: CRM Gap Closure Req 4.4
        """
        self.log_started(
            "mark_addressed",
            communication_id=str(communication_id),
        )

        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Communication)
            .where(Communication.id == communication_id)
            .values(
                addressed=True,
                addressed_at=now,
                addressed_by=addressed_by,
            )
            .returning(Communication)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        communication: Communication | None = result.scalar_one_or_none()

        if communication:
            await self.session.refresh(communication)
            self.log_completed(
                "mark_addressed",
                communication_id=str(communication_id),
            )
        else:
            self.log_completed(
                "mark_addressed",
                communication_id=str(communication_id),
                found=False,
            )

        return communication

    async def update(
        self,
        communication_id: UUID,
        **kwargs: Any,
    ) -> Communication | None:
        """Update a communication record.

        Args:
            communication_id: Communication UUID
            **kwargs: Fields to update

        Returns:
            Updated Communication or None if not found
        """
        self.log_started("update", communication_id=str(communication_id))

        communication = await self.get_by_id(communication_id)
        if not communication:
            self.log_completed("update", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(communication, key):
                setattr(communication, key, value)

        await self.session.flush()
        await self.session.refresh(communication)

        self.log_completed("update", communication_id=str(communication.id))
        return communication

    async def delete(self, communication_id: UUID) -> bool:
        """Delete a communication record.

        Args:
            communication_id: Communication UUID

        Returns:
            True if deleted, False if not found
        """
        self.log_started("delete", communication_id=str(communication_id))

        communication = await self.get_by_id(communication_id)
        if not communication:
            self.log_completed("delete", found=False)
            return False

        await self.session.delete(communication)
        await self.session.flush()

        self.log_completed("delete", communication_id=str(communication_id))
        return True
