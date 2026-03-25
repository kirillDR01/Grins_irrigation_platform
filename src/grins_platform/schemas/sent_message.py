"""Pydantic schemas for outbound sent message history.

Validates: CRM Gap Closure Req 82.2, 82.3
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SentMessageResponse(BaseModel):
    """Schema for a sent message record.

    Validates: CRM Gap Closure Req 82.2
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Message UUID")
    customer_id: UUID | None = Field(default=None, description="Customer UUID")
    lead_id: UUID | None = Field(default=None, description="Lead UUID")
    message_type: str = Field(
        ..., max_length=50, description="Message type",
    )
    content: str | None = Field(
        default=None, max_length=5000, description="Message content",
    )
    delivery_status: str | None = Field(
        default=None, max_length=20, description="Delivery status",
    )
    error_message: str | None = Field(
        default=None, max_length=1000, description="Error details if failed",
    )
    sent_at: datetime | None = Field(default=None, description="Send timestamp")
    created_at: datetime = Field(..., description="Record creation timestamp")


class SentMessageListResponse(BaseModel):
    """Paginated sent message list.

    Validates: CRM Gap Closure Req 82.2, 82.3
    """

    items: list[SentMessageResponse] = Field(
        ..., description="List of sent messages",
    )
    total: int = Field(..., ge=0, description="Total matching records")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages")


class SentMessageFilters(BaseModel):
    """Filters for querying sent messages.

    Validates: CRM Gap Closure Req 82.3
    """

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    message_type: str | None = Field(
        default=None, max_length=50, description="Filter by message type",
    )
    delivery_status: str | None = Field(
        default=None, max_length=20, description="Filter by delivery status",
    )
    date_from: datetime | None = Field(
        default=None, description="Filter from date",
    )
    date_to: datetime | None = Field(default=None, description="Filter to date")
    search: str | None = Field(
        default=None, max_length=200, description="Search in content",
    )
