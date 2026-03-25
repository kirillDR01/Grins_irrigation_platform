"""Pydantic schemas for communication management.

Validates: CRM Gap Closure Req 4.2, 4.4, 5.2, 6.2, 75.1, 75.2
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.models.enums import CommunicationChannel, CommunicationDirection


class CommunicationCreate(BaseModel):
    """Schema for creating a communication record.

    Validates: CRM Gap Closure Req 4.4, 75.1, 75.2
    """

    customer_id: UUID = Field(..., description="Customer UUID")
    channel: CommunicationChannel = Field(..., description="Communication channel")
    direction: CommunicationDirection = Field(
        ...,
        description="Inbound or outbound",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Message content",
    )


class CommunicationUpdate(BaseModel):
    """Schema for addressing a communication (mark as addressed).

    Validates: CRM Gap Closure Req 5.2, 6.2
    """

    addressed: bool = Field(default=True, description="Mark as addressed")


class CommunicationResponse(BaseModel):
    """Schema for communication response.

    Validates: CRM Gap Closure Req 4.2, 4.4
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Communication UUID")
    customer_id: UUID = Field(..., description="Customer UUID")
    channel: CommunicationChannel = Field(..., description="Communication channel")
    direction: CommunicationDirection = Field(
        ...,
        description="Inbound or outbound",
    )
    content: str = Field(..., description="Message content")
    addressed: bool = Field(..., description="Whether addressed")
    addressed_at: datetime | None = Field(
        default=None,
        description="When addressed",
    )
    addressed_by: UUID | None = Field(
        default=None,
        description="Staff who addressed",
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")


class UnaddressedCountResponse(BaseModel):
    """Schema for unaddressed communication count.

    Validates: CRM Gap Closure Req 4.2
    """

    count: int = Field(..., ge=0, description="Number of unaddressed communications")
