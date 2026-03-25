"""
Lead attachment Pydantic schemas for request/response validation.

Validates: CRM Gap Closure Req 15.2, 15.3, 15.4
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LeadAttachmentResponse(BaseModel):
    """Response schema for a lead attachment.

    Validates: Requirement 15.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    file_key: str
    file_name: str
    file_size: int
    content_type: str
    attachment_type: str
    download_url: str | None = Field(
        default=None,
        description="Pre-signed download URL",
    )
    created_at: datetime


class LeadAttachmentListResponse(BaseModel):
    """Response schema for listing lead attachments.

    Validates: Requirement 15.3
    """

    items: list[LeadAttachmentResponse]
    total: int
