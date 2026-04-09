"""Pydantic schemas for marketing campaigns.

Validates: CRM Gap Closure Req 45.3, 45.5, 75.1, 75.2
Validates: CallRail SMS Requirements 13.2, 13.3, 13.4, 13.5, 13.7, 25
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grins_platform.models.enums import CampaignStatus, CampaignType
from grins_platform.schemas.campaign_response import PollOption

# --- Target Audience Filter Models (Requirement 13) ---


class CustomerAudienceFilter(BaseModel):
    """Filter criteria for customer audience source.

    Validates: Requirements 13.2, 13.3
    """

    sms_opt_in: bool | None = Field(
        default=None,
        description="Filter by SMS opt-in status",
    )
    ids_include: list[UUID] | None = Field(
        default=None,
        description="Explicit customer IDs to include",
    )
    cities: list[str] | None = Field(
        default=None,
        description="Filter by property city",
    )
    last_service_between: tuple[date, date] | None = Field(
        default=None,
        description="Date range (start, end) for last service",
    )
    tags_include: list[str] | None = Field(
        default=None,
        description="Customer tags to include",
    )
    lead_source: str | None = Field(
        default=None,
        description="Filter by lead source",
    )
    is_active: bool | None = Field(
        default=None,
        description="Filter by active status",
    )
    no_appointment_in_days: int | None = Field(
        default=None,
        ge=1,
        description="No appointment in N days",
    )


class LeadAudienceFilter(BaseModel):
    """Filter criteria for lead audience source.

    Validates: Requirements 13.4
    """

    sms_consent: bool | None = Field(
        default=None,
        description="Filter by SMS consent status",
    )
    ids_include: list[UUID] | None = Field(
        default=None,
        description="Explicit lead IDs to include",
    )
    statuses: list[str] | None = Field(
        default=None,
        description="Lead statuses (new, contacted, qualified)",
    )
    lead_source: str | None = Field(
        default=None,
        description="Filter by lead source",
    )
    intake_tag: str | None = Field(
        default=None,
        description="Filter by intake tag",
    )
    action_tags_include: list[str] | None = Field(
        default=None,
        description="Action tags to include",
    )
    cities: list[str] | None = Field(
        default=None,
        description="Filter by city",
    )
    created_between: tuple[date, date] | None = Field(
        default=None,
        description="Date range (start, end) for lead creation",
    )


class AdHocRecipientPayload(BaseModel):
    """A single normalized ad-hoc recipient (persisted inline in target_audience).

    These rows are parsed from the CSV upload and embedded in the campaign's
    ``target_audience.ad_hoc.recipients`` so preview/send no longer depend on
    a TTL-bound Redis cache.

    Validates: Requirements 13.5, 35
    """

    phone: str = Field(..., description="Phone number in E.164 format")
    first_name: str | None = Field(default=None, description="Optional first name")
    last_name: str | None = Field(default=None, description="Optional last name")


class AdHocAudienceFilter(BaseModel):
    """Filter criteria for ad-hoc CSV audience source.

    Validates: Requirements 13.5, 25
    """

    csv_upload_id: UUID | None = Field(
        default=None,
        description="Staged CSV upload ID (audit reference)",
    )
    recipients: list[AdHocRecipientPayload] | None = Field(
        default=None,
        description=(
            "Inline parsed CSV recipients. Preferred over csv_upload_id; "
            "embedded directly in target_audience so send-time doesn't "
            "depend on Redis staging."
        ),
    )
    staff_attestation_confirmed: bool = Field(
        default=False,
        description="Staff confirmed consent attestation",
    )
    attestation_text_shown: str = Field(
        default="",
        description="Verbatim attestation text displayed to staff",
    )
    attestation_version: str = Field(
        default="CSV_ATTESTATION_V1",
        description="Attestation form version",
    )


class TargetAudience(BaseModel):
    """Composed target audience with three additive sources.

    Validates: Requirements 13.2, 13.3, 13.4, 13.5, 13.7
    """

    customers: CustomerAudienceFilter | None = Field(
        default=None,
        description="Customer audience filters",
    )
    leads: LeadAudienceFilter | None = Field(
        default=None,
        description="Lead audience filters",
    )
    ad_hoc: AdHocAudienceFilter | None = Field(
        default=None,
        description="Ad-hoc CSV audience filters",
    )


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
    target_audience: TargetAudience | dict[str, Any] | None = Field(
        default=None,
        description="Audience filter criteria (structured or legacy dict)",
    )
    subject: str | None = Field(
        default=None,
        max_length=200,
        description="Email subject line",
    )
    body: str = Field(
        default="",
        max_length=10000,
        description=(
            "Message body. Empty string allowed on draft create; "
            "must be non-empty at send time."
        ),
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Scheduled send time",
    )
    poll_options: list[PollOption] | None = Field(
        default=None,
        description="2-5 numbered scheduling options for poll campaigns",
    )

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def validate_poll_options(self) -> "CampaignCreate":
        opts = self.poll_options
        if opts is not None:
            if not (2 <= len(opts) <= 5):
                msg = "poll_options must contain 2-5 entries"
                raise ValueError(msg)
            expected = [str(i) for i in range(1, len(opts) + 1)]
            if [o.key for o in opts] != expected:
                msg = "poll_options keys must be sequential starting from '1'"
                raise ValueError(msg)
        return self


class CampaignUpdate(BaseModel):
    """Schema for updating a draft campaign.

    All fields optional; only provided fields are applied.
    Only campaigns in DRAFT status may be updated.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Campaign name",
    )
    target_audience: TargetAudience | dict[str, Any] | None = Field(
        default=None,
        description="Audience filter criteria (structured or legacy dict)",
    )
    subject: str | None = Field(
        default=None,
        max_length=200,
        description="Email subject line",
    )
    body: str | None = Field(
        default=None,
        max_length=10000,
        description="Message body",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Scheduled send time",
    )
    poll_options: list[PollOption] | None = Field(
        default=None,
        description="2-5 numbered scheduling options for poll campaigns",
    )

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def validate_poll_options(self) -> "CampaignUpdate":
        opts = self.poll_options
        if opts is not None:
            if not (2 <= len(opts) <= 5):
                msg = "poll_options must contain 2-5 entries"
                raise ValueError(msg)
            expected = [str(i) for i in range(1, len(opts) + 1)]
            if [o.key for o in opts] != expected:
                msg = "poll_options keys must be sequential starting from '1'"
                raise ValueError(msg)
        return self


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
    poll_options: list[PollOption] | None = Field(
        default=None,
        description="Poll scheduling options (null for non-poll campaigns)",
    )


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
    recipient_name: str | None = Field(default=None, description="Customer or lead name")
    recipient_phone: str | None = Field(default=None, description="Customer or lead phone")

    @model_validator(mode="before")
    @classmethod
    def populate_recipient_info(cls, data: Any) -> Any:
        """Pull name/phone from loaded customer/lead relationships."""
        if hasattr(data, "customer") and data.customer:
            c = data.customer
            first = getattr(c, "first_name", "") or ""
            last = getattr(c, "last_name", "") or ""
            data.recipient_name = f"{first} {last}".strip() or None
            data.recipient_phone = getattr(c, "phone", None)
        elif hasattr(data, "lead") and data.lead:
            data.recipient_name = getattr(data.lead, "name", None)
            data.recipient_phone = getattr(data.lead, "phone", None)
        return data


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
    pending: int = Field(default=0, ge=0, description="Pending count")
    sending: int = Field(default=0, ge=0, description="Currently sending count")
    sent: int = Field(..., ge=0, description="Sent count")
    delivered: int = Field(..., ge=0, description="Delivered count")
    failed: int = Field(..., ge=0, description="Failed count")
    bounced: int = Field(..., ge=0, description="Bounced count")
    opted_out: int = Field(..., ge=0, description="Opted out count")


class CampaignSendAcceptedResponse(BaseModel):
    """Response from async campaign send enqueue (HTTP 202).

    Validates: Requirements 8.4, 31, 41
    """

    campaign_id: UUID = Field(..., description="Campaign UUID")
    total_recipients: int = Field(
        ...,
        ge=0,
        description="Recipients enqueued for background delivery",
    )
    status: str = "sending"
    message: str = "Campaign recipients enqueued for background delivery"


class CampaignCancelResult(BaseModel):
    """Result of cancelling a campaign.

    Validates: Requirement 28, 37
    """

    campaign_id: UUID = Field(..., description="Campaign UUID")
    cancelled_recipients: int = Field(
        ...,
        ge=0,
        description="Number of pending recipients cancelled",
    )


class CampaignRetryResult(BaseModel):
    """Result of retrying failed campaign recipients.

    Validates: Requirement 37
    """

    campaign_id: UUID = Field(..., description="Campaign UUID")
    retried_recipients: int = Field(
        ...,
        ge=0,
        description="Number of new pending rows created from failed recipients",
    )


class RateLimitInfo(BaseModel):
    """Rate limit state snapshot from CallRail headers."""

    hourly_allowed: int = Field(default=0, description="Hourly limit")
    hourly_used: int = Field(default=0, description="Hourly used")
    hourly_remaining: int = Field(
        default=0,
        description="Hourly remaining",
    )
    daily_allowed: int = Field(default=0, description="Daily limit")
    daily_used: int = Field(default=0, description="Daily used")
    daily_remaining: int = Field(
        default=0,
        description="Daily remaining",
    )


class WorkerHealthResponse(BaseModel):
    """Campaign background worker health status.

    Validates: Requirement 32
    """

    last_tick_at: str | None = Field(
        default=None,
        description="ISO timestamp of last worker tick",
    )
    last_tick_duration_ms: int | None = Field(
        default=None,
        description="Duration of last tick in ms",
    )
    last_tick_recipients_processed: int | None = Field(
        default=None,
        description="Recipients processed in last tick",
    )
    pending_count: int = Field(default=0, ge=0, description="Recipients awaiting send")
    sending_count: int = Field(
        default=0,
        ge=0,
        description="Recipients currently sending",
    )
    orphans_recovered_last_hour: int = Field(
        default=0,
        ge=0,
        description="Orphans recovered in last tick",
    )
    rate_limit: RateLimitInfo = Field(
        default_factory=RateLimitInfo,
        description="Current rate limit state",
    )
    status: str = Field(default="unknown", description="healthy or stale")


class CsvRejectedRow(BaseModel):
    """A single rejected row from CSV upload."""

    row_number: int = Field(..., description="1-based row number in CSV")
    phone_raw: str = Field(..., description="Original phone value")
    reason: str = Field(..., description="Rejection reason")


class CsvUploadResult(BaseModel):
    """Response from CSV audience upload endpoint.

    Returns the parsed recipients inline so the frontend can embed them
    directly in the campaign's target_audience. No Redis staging required.

    Validates: Requirement 35
    """

    upload_id: str = Field(..., description="Upload identifier (audit reference)")
    total_rows: int = Field(default=0, ge=0, description="Total data rows parsed")
    matched_customers: int = Field(default=0, ge=0)
    matched_leads: int = Field(default=0, ge=0)
    will_become_ghost_leads: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    duplicates_collapsed: int = Field(default=0, ge=0)
    rejected_rows: list[CsvRejectedRow] = Field(default_factory=list)
    recipients: list[AdHocRecipientPayload] = Field(
        default_factory=list,
        description=(
            "Parsed and normalized recipients. Embed these in "
            "target_audience.ad_hoc.recipients when creating/updating the "
            "campaign draft."
        ),
    )


class AudiencePreviewRecipient(BaseModel):
    """Single recipient in an audience preview."""

    phone_masked: str = Field(..., description="Masked phone (e.g. +1952***3750)")
    source_type: str = Field(..., description="customer, lead, or ad_hoc")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")


class AudiencePreviewResponse(BaseModel):
    """Response from audience preview endpoint.

    Validates: Requirement 13.8
    """

    total: int = Field(..., ge=0, description="Total matched recipients")
    customers_count: int = Field(default=0, ge=0, description="Customer source count")
    leads_count: int = Field(default=0, ge=0, description="Lead source count")
    ad_hoc_count: int = Field(default=0, ge=0, description="Ad-hoc source count")
    matches: list[AudiencePreviewRecipient] = Field(
        default_factory=list,
        description="First 20 matched recipients",
    )
