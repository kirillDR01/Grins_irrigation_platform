"""Pydantic schemas for media library.

Validates: CRM Gap Closure Req 49.2, 49.3
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.models.enums import MediaType


class MediaCreate(BaseModel):
    """Schema for creating a media library item.

    Validates: CRM Gap Closure Req 49.2, 75.1, 75.2
    """

    file_key: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="S3 object key",
    )
    file_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original file name",
    )
    file_size: int = Field(..., gt=0, description="File size in bytes")
    content_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="MIME content type",
    )
    media_type: MediaType = Field(..., description="Media type classification")
    category: str | None = Field(
        default=None,
        max_length=50,
        description="Media category",
    )
    caption: str | None = Field(
        default=None,
        max_length=1000,
        description="Media caption",
    )
    is_public: bool = Field(
        default=False,
        description="Whether publicly accessible",
    )


class MediaResponse(BaseModel):
    """Schema for media library item response.

    Validates: CRM Gap Closure Req 49.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Media item UUID")
    file_key: str = Field(..., description="S3 object key")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")
    media_type: MediaType = Field(..., description="Media type classification")
    category: str | None = Field(default=None, description="Media category")
    caption: str | None = Field(default=None, description="Media caption")
    is_public: bool = Field(..., description="Whether publicly accessible")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")
