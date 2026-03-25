"""Pydantic schemas for marketing campaigns.

Validates: CRM Gap Closure Req 45.3, 45.5, 75.1, 75.2
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.models.enums import CampaignStatus, CampaignType


class CampaignCreate(BaseModel):
    """Schema for creating a campaign.

    Validates: CRM Gap Closure Req 45.3, 75.1, 75.2
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Campaign name",
    )
    campaign_type: CampaignType = Field(..., description="Campaign type")
    target_audience: dict[str, Any] | None = Field(
        default=None,
        description="Audience filter criteria",
    )
    subject: str | None = Field(
        default=None,
        max_length=200,
        description="Email subject line",
    )
    body: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Message body",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Scheduled send time",
    )


class CampaignResponse(BaseModel):
    """Schema for campaign response.

    Validates: CRM Gap Closure Req 45.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Campaign UUID")
    name: str = Field(..., description="Campaign name")
    campaign_type: CampaignType = Field(..., description="Campaign type")
    status: CampaignStatus = Field(..., description="Campaign status")
    target_audience: dict[str, Any] | None = Field(
        default=None,
        description="Audience filter criteria",
    )
    subject: str | None = Field(default=None, description="Email subject line")
    body: str = Field(..., description="Message body")
    scheduled_at: datetime | None = Field(
        default=None,
        description="Scheduled send time",
    )
    sent_at: datetime | None = Field(default=None, description="Actual send time")
    created_by: UUID | None = Field(
        default=None,
        description="Staff who created the campaign",
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")


class CampaignRecipientResponse(BaseModel):
    """Schema for campaign recipient response.

    Validates: CRM Gap Closure Req 45.5
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Recipient record UUID")
    campaign_id: UUID = Field(..., description="Campaign UUID")
    customer_id: UUID | None = Field(default=None, description="Customer UUID")
    lead_id: UUID | None = Field(default=None, description="Lead UUID")
    channel: str = Field(..., max_length=20, description="Delivery channel")
    delivery_status: str = Field(
        ...,
        max_length=20,
        description="Delivery status",
    )
    sent_at: datetime | None = Field(default=None, description="Send timestamp")
    error_message: str | None = Field(
        default=None,
        max_length=1000,
        description="Error details if failed",
    )
    created_at: datetime = Field(..., description="Record creation timestamp")


class CampaignSendResult(BaseModel):
    """Result of sending a campaign.

    Validates: CRM Gap Closure Req 45.5
    """

    campaign_id: UUID = Field(..., description="Campaign UUID")
    total_recipients: int = Field(..., ge=0, description="Total recipients")
    sent: int = Field(..., ge=0, description="Successfully sent")
    skipped: int = Field(..., ge=0, description="Skipped (no consent)")
    failed: int = Field(..., ge=0, description="Failed to send")


class CampaignStats(BaseModel):
    """Campaign delivery statistics.

    Validates: CRM Gap Closure Req 45.5
    """

    campaign_id: UUID = Field(..., description="Campaign UUID")
    total: int = Field(..., ge=0, description="Total recipients")
    sent: int = Field(..., ge=0, description="Sent count")
    delivered: int = Field(..., ge=0, description="Delivered count")
    failed: int = Field(..., ge=0, description="Failed count")
    bounced: int = Field(..., ge=0, description="Bounced count")
    opted_out: int = Field(..., ge=0, description="Opted out count")
