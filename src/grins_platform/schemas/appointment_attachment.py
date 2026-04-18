"""
Appointment attachment Pydantic schemas for request/response validation.

This module defines Pydantic schemas for appointment file attachment
operations, including upload responses and list responses.

Validates: april-16th-fixes-enhancements Requirement 6
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttachmentUploadResponse(BaseModel):
    """Response schema for an uploaded appointment attachment.

    Validates: Requirement 10.5
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique attachment identifier")
    appointment_id: UUID = Field(..., description="Associated appointment ID")
    appointment_type: str = Field(
        ...,
        description="Appointment type: job or estimate",
    )
    file_key: str = Field(..., description="S3 object key for the file")
    file_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    uploaded_by: UUID = Field(..., description="Staff ID of the uploader")
    created_at: datetime = Field(..., description="Upload timestamp")
    presigned_url: str | None = Field(
        default=None,
        description="Pre-signed download URL (temporary)",
    )


class AttachmentListResponse(BaseModel):
    """Response schema for listing appointment attachments.

    Validates: Requirement 10.5
    """

    items: list[AttachmentUploadResponse] = Field(
        ...,
        description="List of attachment records",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of attachments for this appointment",
    )
