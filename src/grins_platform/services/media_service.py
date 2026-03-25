"""Media library service for CRUD operations on media items.

Provides: create, read, update, delete, and filtered listing
of media library items with file type validation.

Validates: CRM Gap Closure Req 49.2, 49.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import MediaType
from grins_platform.schemas.media import MediaCreate, MediaResponse

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.repositories.media_repository import (
        MediaRepository,
    )

# Allowed content types per media type
ALLOWED_CONTENT_TYPES: dict[MediaType, set[str]] = {
    MediaType.IMAGE: {
        "image/jpeg",
        "image/png",
        "image/heic",
        "image/heif",
    },
    MediaType.VIDEO: {
        "video/mp4",
        "video/quicktime",
    },
    MediaType.DOCUMENT: {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}

# Max file size: 50MB for media library (Req 49.5)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class MediaValidationError(Exception):
    """Raised when media file validation fails."""

    def __init__(
        self,
        message: str = "Media validation failed",
    ) -> None:
        self.message = message
        super().__init__(self.message)


class MediaNotFoundError(Exception):
    """Raised when a media item is not found."""

    def __init__(self, media_id: str = "") -> None:
        self.message = f"Media item not found: {media_id}"
        super().__init__(self.message)


class MediaService(LoggerMixin):
    """Service for media library CRUD operations.

    Validates: CRM Gap Closure Req 49.2, 49.3
    """

    DOMAIN = "media"

    def __init__(
        self,
        media_repository: MediaRepository,
    ) -> None:
        """Initialize MediaService.

        Args:
            media_repository: Repository for media DB operations.
        """
        super().__init__()
        self.media_repo = media_repository

    # ------------------------------------------------------------------ #
    # validate_media -- internal helper
    # ------------------------------------------------------------------ #

    def _validate_media(self, data: MediaCreate) -> None:
        """Validate media file type and size.

        Args:
            data: MediaCreate schema with file metadata.

        Raises:
            MediaValidationError: If validation fails.
        """
        if data.file_size > MAX_FILE_SIZE_BYTES:
            self.log_rejected(
                "validate_media",
                reason="file_too_large",
                file_size=data.file_size,
                max_size=MAX_FILE_SIZE_BYTES,
            )
            msg = (
                f"File size {data.file_size} exceeds "
                f"maximum of {MAX_FILE_SIZE_BYTES} bytes"
            )
            raise MediaValidationError(msg)

        allowed = ALLOWED_CONTENT_TYPES.get(
            data.media_type,
            set(),
        )
        if data.content_type not in allowed:
            self.log_rejected(
                "validate_media",
                reason="invalid_content_type",
                content_type=data.content_type,
                media_type=data.media_type.value,
            )
            msg = (
                f"Content type '{data.content_type}' not "
                f"allowed for '{data.media_type.value}'. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )
            raise MediaValidationError(msg)

    # ------------------------------------------------------------------ #
    # create -- Req 49.2
    # ------------------------------------------------------------------ #

    async def create(self, data: MediaCreate) -> MediaResponse:
        """Create a new media library item.

        Args:
            data: MediaCreate schema with file metadata.

        Returns:
            MediaResponse for the created item.

        Raises:
            MediaValidationError: If file validation fails.

        Validates: Req 49.2
        """
        self.log_started(
            "create",
            file_name=data.file_name,
            media_type=data.media_type.value,
        )

        try:
            self._validate_media(data)

            item = await self.media_repo.create(
                file_key=data.file_key,
                file_name=data.file_name,
                file_size=data.file_size,
                content_type=data.content_type,
                media_type=data.media_type.value,
                category=data.category,
                caption=data.caption,
                is_public=data.is_public,
            )

            response = MediaResponse.model_validate(item)
            self.log_completed(
                "create",
                media_id=str(item.id),
            )
        except MediaValidationError:
            raise
        except Exception as e:
            self.log_failed("create", error=e)
            raise
        else:
            return response

    # ------------------------------------------------------------------ #
    # get_by_id -- Req 49.3
    # ------------------------------------------------------------------ #

    async def get_by_id(self, media_id: UUID) -> MediaResponse:
        """Get a media library item by ID.

        Args:
            media_id: Media item UUID.

        Returns:
            MediaResponse for the item.

        Raises:
            MediaNotFoundError: If item not found.

        Validates: Req 49.3
        """
        self.log_started("get_by_id", media_id=str(media_id))

        item = await self.media_repo.get_by_id(media_id)
        if not item:
            self.log_completed("get_by_id", found=False)
            raise MediaNotFoundError(str(media_id))

        response = MediaResponse.model_validate(item)
        self.log_completed(
            "get_by_id",
            media_id=str(media_id),
        )
        return response

    # ------------------------------------------------------------------ #
    # update -- Req 49.2
    # ------------------------------------------------------------------ #

    async def update(
        self,
        media_id: UUID,
        caption: str | None = None,
        category: str | None = None,
        is_public: bool | None = None,
    ) -> MediaResponse:
        """Update a media library item's metadata.

        Args:
            media_id: Media item UUID.
            caption: New caption (optional).
            category: New category (optional).
            is_public: New public visibility (optional).

        Returns:
            MediaResponse for the updated item.

        Raises:
            MediaNotFoundError: If item not found.

        Validates: Req 49.2
        """
        self.log_started("update", media_id=str(media_id))

        update_fields: dict[str, str | bool] = {}
        if caption is not None:
            update_fields["caption"] = caption
        if category is not None:
            update_fields["category"] = category
        if is_public is not None:
            update_fields["is_public"] = is_public

        item = await self.media_repo.update(
            media_id,
            **update_fields,
        )
        if not item:
            self.log_completed("update", found=False)
            raise MediaNotFoundError(str(media_id))

        response = MediaResponse.model_validate(item)
        self.log_completed(
            "update",
            media_id=str(media_id),
        )
        return response

    # ------------------------------------------------------------------ #
    # delete -- Req 49.2
    # ------------------------------------------------------------------ #

    async def delete(self, media_id: UUID) -> bool:
        """Delete a media library item.

        Args:
            media_id: Media item UUID.

        Returns:
            True if deleted.

        Raises:
            MediaNotFoundError: If item not found.

        Validates: Req 49.2
        """
        self.log_started("delete", media_id=str(media_id))

        deleted = await self.media_repo.delete(media_id)
        if not deleted:
            self.log_completed("delete", found=False)
            raise MediaNotFoundError(str(media_id))

        self.log_completed(
            "delete",
            media_id=str(media_id),
        )
        return True

    # ------------------------------------------------------------------ #
    # list_items -- Req 49.2, 49.3
    # ------------------------------------------------------------------ #

    async def list_items(
        self,
        page: int = 1,
        page_size: int = 20,
        media_type: str | None = None,
        category: str | None = None,
        is_public: bool | None = None,
    ) -> tuple[list[MediaResponse], int]:
        """List media items with filtering and pagination.

        Args:
            page: Page number (1-based).
            page_size: Items per page.
            media_type: Filter by media type.
            category: Filter by category.
            is_public: Filter by public visibility.

        Returns:
            Tuple of (list of MediaResponse, total count).

        Validates: Req 49.2, 49.3
        """
        self.log_started(
            "list_items",
            page=page,
            page_size=page_size,
            media_type=media_type,
            category=category,
        )

        items, total = await self.media_repo.list_with_filters(
            page=page,
            page_size=page_size,
            media_type=media_type,
            category=category,
            is_public=is_public,
        )

        responses = [MediaResponse.model_validate(item) for item in items]

        self.log_completed(
            "list_items",
            count=len(responses),
            total=total,
        )
        return responses, total
