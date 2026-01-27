"""SMS-related Pydantic schemas.

This module defines schemas for SMS communication including
send requests, webhook payloads, and communications queue.

Validates: AI Assistant Requirements 15.8, 15.9, 15.10
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from grins_platform.schemas.ai import MessageType


class SMSSendRequest(BaseModel):
    """Request to send an SMS message."""

    customer_id: UUID
    phone: str = Field(..., min_length=10, max_length=20)
    message: str = Field(..., min_length=1, max_length=1600)
    message_type: MessageType
    sms_opt_in: bool = False
    job_id: UUID | None = None
    appointment_id: UUID | None = None


class SMSSendResponse(BaseModel):
    """Response from sending an SMS."""

    success: bool
    message_id: UUID
    twilio_sid: str | None = None
    status: str


class SMSWebhookPayload(BaseModel):
    """Payload from Twilio webhook."""

    message_sid: str = Field(..., alias="MessageSid")
    message_status: str = Field(..., alias="MessageStatus")
    to: str = Field(..., alias="To")
    from_: str = Field(..., alias="From")
    error_code: str | None = Field(None, alias="ErrorCode")
    error_message: str | None = Field(None, alias="ErrorMessage")

    model_config = {"populate_by_name": True}


class WebhookResponse(BaseModel):
    """Response from webhook processing."""

    action: str
    phone: str | None = None
    message: str | None = None


class CommunicationsQueueItem(BaseModel):
    """An item in the communications queue."""

    id: str
    customer_id: str
    message_type: str
    message_content: str
    recipient_phone: str
    delivery_status: str
    scheduled_for: datetime | None
    created_at: datetime


class CommunicationsQueueResponse(BaseModel):
    """Response with communications queue."""

    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class BulkRecipient(BaseModel):
    """Recipient for bulk SMS."""

    customer_id: UUID
    phone: str
    sms_opt_in: bool = False


class BulkSendRequest(BaseModel):
    """Request to send bulk SMS."""

    recipients: list[BulkRecipient]
    message: str = Field(..., min_length=1, max_length=1600)
    message_type: MessageType


class BulkSendResponse(BaseModel):
    """Response from bulk SMS send."""

    total: int
    success_count: int
    failure_count: int
    results: list[dict[str, Any]]
