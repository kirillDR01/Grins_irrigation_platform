"""Pydantic schemas for campaign poll responses.

Validates: Scheduling Poll Req 15.1, 15.2, 15.3
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PollOption(BaseModel):
    """A single scheduling option within a poll campaign.

    Validates: Req 15.1, 15.2
    """

    key: Literal["1", "2", "3", "4", "5"] = Field(
        ...,
        description="Digit key 1-5",
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Human-readable label",
    )
    start_date: date = Field(..., description="Option start date")
    end_date: date = Field(..., description="Option end date")

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def end_date_gte_start_date(self) -> "PollOption":
        if self.end_date < self.start_date:
            msg = "end_date must be >= start_date"
            raise ValueError(msg)
        return self


class CampaignResponseOut(BaseModel):
    """Single campaign response row returned by the API.

    Validates: Req 15.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID | None = None
    sent_message_id: UUID | None = None
    customer_id: UUID | None = None
    lead_id: UUID | None = None
    phone: str
    recipient_name: str | None = None
    recipient_address: str | None = None
    selected_option_key: str | None = None
    selected_option_label: str | None = None
    raw_reply_body: str
    provider_message_id: str | None = None
    status: str
    received_at: datetime
    created_at: datetime


class PaginatedCampaignResponseOut(BaseModel):
    """Paginated list of campaign responses."""

    items: list[CampaignResponseOut] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)


class CampaignResponseBucket(BaseModel):
    """Per-option count bucket in the response summary."""

    option_key: str | None = None
    option_label: str | None = None
    status: str
    count: int = 0


class CampaignResponseSummary(BaseModel):
    """Aggregated response summary for a poll campaign."""

    campaign_id: UUID
    total_sent: int = 0
    total_replied: int = 0
    buckets: list[CampaignResponseBucket] = Field(default_factory=list)


class CampaignResponseCsvRow(BaseModel):
    """A single row in the CSV export."""

    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    selected_option_label: str = ""
    raw_reply: str = ""
    status: str = ""
    address: str = ""
    received_at: str = ""
