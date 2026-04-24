"""CustomerTag repository for database operations.

Validates: Requirements 12.4, 12.5
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.customer_tag import CustomerTag

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CustomerTagRepository(LoggerMixin):
    """Repository for customer tag database operations.

    Validates: Requirements 12.4, 12.5
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def get_by_customer_id(self, customer_id: UUID) -> list[CustomerTag]:
        """Return all tags for a customer ordered by created_at.

        Args:
            customer_id: Customer UUID

        Returns:
            List of CustomerTag instances
        """
        self.log_started("get_by_customer_id", customer_id=str(customer_id))
        stmt = (
            select(CustomerTag)
            .where(CustomerTag.customer_id == customer_id)
            .order_by(CustomerTag.created_at)
        )
        result = await self.session.execute(stmt)
        tags = list(result.scalars().all())
        self.log_completed("get_by_customer_id", count=len(tags))
        return tags

    async def create(
        self,
        customer_id: UUID,
        label: str,
        tone: str = "neutral",
        source: str = "manual",
    ) -> CustomerTag:
        """Create a new customer tag.

        Args:
            customer_id: Customer UUID
            label: Tag label (max 32 chars)
            tone: Visual tone variant
            source: Tag source (manual/system)

        Returns:
            Created CustomerTag instance
        """
        self.log_started("create", customer_id=str(customer_id), label=label)
        tag = CustomerTag(
            customer_id=customer_id,
            label=label,
            tone=tone,
            source=source,
        )
        self.session.add(tag)
        await self.session.flush()
        await self.session.refresh(tag)
        self.log_completed("create", tag_id=str(tag.id))
        return tag

    async def delete_by_ids(self, tag_ids: list[UUID]) -> int:
        """Delete tags by their IDs.

        Args:
            tag_ids: List of tag UUIDs to delete

        Returns:
            Number of rows deleted
        """
        if not tag_ids:
            return 0
        self.log_started("delete_by_ids", count=len(tag_ids))
        stmt = delete(CustomerTag).where(CustomerTag.id.in_(tag_ids))
        result = await self.session.execute(stmt)
        deleted: int = getattr(result, "rowcount", 0) or 0
        self.log_completed("delete_by_ids", deleted=deleted)
        return deleted

    async def get_by_customer_and_label(
        self, customer_id: UUID, label: str
    ) -> CustomerTag | None:
        """Find a tag by customer and label (for duplicate detection).

        Args:
            customer_id: Customer UUID
            label: Tag label

        Returns:
            CustomerTag or None
        """
        self.log_started(
            "get_by_customer_and_label",
            customer_id=str(customer_id),
            label=label,
        )
        stmt = select(CustomerTag).where(
            CustomerTag.customer_id == customer_id,
            CustomerTag.label == label,
        )
        result = await self.session.execute(stmt)
        tag: CustomerTag | None = result.scalar_one_or_none()
        self.log_completed("get_by_customer_and_label", found=tag is not None)
        return tag
