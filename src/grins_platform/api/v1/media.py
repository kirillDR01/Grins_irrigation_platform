"""Media library API endpoints.

Provides CRUD for media library items (photos, videos, documents).

Validates: CRM Gap Closure Req 49.2, 49.3
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    MediaType,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.repositories.media_repository import MediaRepository
from grins_platform.schemas.media import MediaCreate, MediaResponse
from grins_platform.services.media_service import (
    MediaNotFoundError,
    MediaService,
    MediaValidationError,
)

router = APIRouter()


class _MediaEndpoints(LoggerMixin):
    """Media API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _MediaEndpoints()


async def _get_media_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MediaService:
    """Get MediaService dependency."""
    repo = MediaRepository(session)
    return MediaService(media_repository=repo)


@router.post(
    "",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create media item",
    description="Create a new media library item.",
)
async def create_media(
    data: MediaCreate,
    _current_user: CurrentActiveUser,
    service: Annotated[MediaService, Depends(_get_media_service)],
) -> MediaResponse:
    """Create a new media library item.

    Validates: CRM Gap Closure Req 49.2
    """
    _endpoints.log_started("create_media", file_name=data.file_name)
    try:
        result = await service.create(data)
    except MediaValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed("create_media", media_id=str(result.id))
        return result


@router.get(
    "",
    response_model=dict[str, Any],
    summary="List media items",
    description="List media items with pagination and filters.",
)
async def list_media(
    _current_user: CurrentActiveUser,
    service: Annotated[MediaService, Depends(_get_media_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    media_type: MediaType | None = Query(default=None, description="Filter by type"),
    category: str | None = Query(default=None, description="Filter by category"),
) -> dict[str, Any]:
    """List media items with pagination.

    Validates: CRM Gap Closure Req 49.3
    """
    _endpoints.log_started("list_media", page=page)
    items, total = await service.list_items(
        page=page,
        page_size=page_size,
        media_type=media_type.value if media_type else None,
        category=category,
    )
    _endpoints.log_completed("list_media", count=len(items), total=total)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{media_id}",
    response_model=MediaResponse,
    summary="Get media item by ID",
)
async def get_media(
    media_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[MediaService, Depends(_get_media_service)],
) -> MediaResponse:
    """Get a single media item by ID."""
    _endpoints.log_started("get_media", media_id=str(media_id))
    try:
        result = await service.get_by_id(media_id)
    except MediaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed("get_media", media_id=str(media_id))
        return result


@router.delete(
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete media item",
)
async def delete_media(
    media_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[MediaService, Depends(_get_media_service)],
) -> None:
    """Delete a media item by ID."""
    _endpoints.log_started("delete_media", media_id=str(media_id))
    try:
        await service.delete(media_id)
        _endpoints.log_completed("delete_media", media_id=str(media_id))
    except MediaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
