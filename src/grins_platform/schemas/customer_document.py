"""Pydantic schemas for customer documents.

Validates: CRM Changes Update 2 Req 17.3
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.models.enums import DocumentType


class CustomerDocumentCreate(BaseModel):
    """Metadata for a new customer document upload."""

    file_name: str = Field(min_length=1, max_length=255)
    document_type: DocumentType
    mime_type: str = Field(max_length=100)
    size_bytes: int = Field(gt=0, le=26_214_400)  # 25 MB max


class CustomerDocumentResponse(BaseModel):
    """Customer document response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    sales_entry_id: Optional[UUID] = None
    file_key: str
    file_name: str
    document_type: DocumentType
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    uploaded_by: Optional[UUID] = None
