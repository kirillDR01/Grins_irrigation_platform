"""Media library repository for database operations.

CRUD + filtered browsing by category/type.

Validates: CRM Gap Closure Req 49.2, 49.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.media_library import MediaLibraryItem

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class MediaRepository(LoggerMixin):
    """Repository for media library database operations.

    Validates: CRM Gap Closure Req 49.2, 49.3
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(self, **kwargs: Any) -> MediaLibraryItem:
        """Create a new media library item.

        Args:
            **kwargs: Media item field values

        Returns:
            Created MediaLibraryItem instance
        """
        self.log_started("create")

        item = MediaLibraryItem(**kwargs)
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)

        self.log_completed("create", media_id=str(item.id))
        return item

    async def get_by_id(self, media_id: UUID) -> MediaLibraryItem | None:
        """Get a media item by ID.

        Args:
            media_id: Media item UUID

        Returns:
            MediaLibraryItem or None if not found
        """
        self.log_started("get_by_id", media_id=str(media_id))

        stmt = select(MediaLibraryItem).where(MediaLibraryItem.id == media_id)
        result = await self.session.execute(stmt)
        item: MediaLibraryItem | None = result.scalar_one_or_none()

        self.log_completed("get_by_id", found=item is not None)
        return item

    async def update(
        self,
        media_id: UUID,
        **kwargs: Any,
    ) -> MediaLibraryItem | None:
        """Update a media library item.

        Args:
            media_id: Media item UUID
            **kwargs: Fields to update

        Returns:
            Updated MediaLibraryItem or None if not found
        """
        self.log_started("update", media_id=str(media_id))

        item = await self.get_by_id(media_id)
        if not item:
            self.log_completed("update", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)

        await self.session.flush()
        await self.session.refresh(item)

        self.log_completed("update", media_id=str(item.id))
        return item

    async def delete(self, media_id: UUID) -> bool:
        """Delete a media library item.

        Args:
            media_id: Media item UUID

        Returns:
            True if deleted, False if not found
        """
        self.log_started("delete", media_id=str(media_id))

        item = await self.get_by_id(media_id)
        if not item:
            self.log_completed("delete", found=False)
            return False

        await self.session.delete(item)
        await self.session.flush()

        self.log_completed("delete", media_id=str(media_id))
        return True

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        media_type: str | None = None,
        category: str | None = None,
        is_public: bool | None = None,
    ) -> tuple[list[MediaLibraryItem], int]:
        """List media items with filtering and pagination.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            media_type: Filter by media type (photo, video, testimonial)
            category: Filter by category
            is_public: Filter by public visibility

        Returns:
            Tuple of (list of media items, total count)

        Validates: CRM Gap Closure Req 49.2, 49.3
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        base_query = select(MediaLibraryItem)
        count_query = select(func.count(MediaLibraryItem.id))

        if media_type is not None:
            base_query = base_query.where(MediaLibraryItem.media_type == media_type)
            count_query = count_query.where(MediaLibraryItem.media_type == media_type)

        if category is not None:
            base_query = base_query.where(MediaLibraryItem.category == category)
            count_query = count_query.where(MediaLibraryItem.category == category)

        if is_public is not None:
            base_query = base_query.where(MediaLibraryItem.is_public == is_public)
            count_query = count_query.where(MediaLibraryItem.is_public == is_public)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(MediaLibraryItem.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(items), total=total)
        return items, total

    async def get_categories(self) -> list[str]:
        """Get all distinct media categories.

        Returns:
            List of category strings
        """
        self.log_started("get_categories")

        stmt = (
            select(MediaLibraryItem.category)
            .where(MediaLibraryItem.category.isnot(None))
            .distinct()
            .order_by(MediaLibraryItem.category.asc())
        )

        result = await self.session.execute(stmt)
        categories = [str(row[0]) for row in result.all()]

        self.log_completed("get_categories", count=len(categories))
        return categories
