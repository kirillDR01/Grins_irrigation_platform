"""
Lead Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for lead-related API operations,
including public form submission, admin CRUD, conversion to customer,
and query parameters.

Validates: Requirement 1.1-1.11, 5.1-5.5, 7.1-7.6
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from grins_platform.models.enums import (
    IntakeTag,
    LeadSituation,
    LeadSourceExtended,
    LeadStatus,
)
from grins_platform.schemas.customer import normalize_phone


def strip_html_tags(text: str) -> str:
    """Strip HTML tags from text to prevent stored XSS.

    Args:
        text: Input string potentially containing HTML tags

    Returns:
        String with all HTML tags removed

    Validates: Requirement 1.11, 12.4
    """
    return re.sub(r"<[^>]+>", "", text).strip()


class LeadSubmission(BaseModel):
    """Schema for public form submission.

    Validates: Requirement 1
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Full name",
    )
    phone: str = Field(
        ...,
        min_length=7,
        max_length=20,
        description="Phone number",
    )
    zip_code: str | None = Field(
        default=None,
        max_length=10,
        description="5-digit zip code (optional — extracted from address if omitted)",
    )
    situation: LeadSituation = Field(
        ...,
        description="Service situation from dropdown",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Optional email address",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional notes",
    )
    source_site: str = Field(
        default="residential",
        max_length=100,
        description="Source site identifier",
    )
    city: str | None = Field(
        default=None,
        max_length=100,
        description="City",
    )
    state: str | None = Field(
        default=None,
        max_length=2,
        description="State abbreviation",
    )
    address: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Street address",
    )
    lead_source: LeadSourceExtended | None = Field(
        default=None,
        description="Lead source channel (defaults to WEBSITE)",
    )
    source_detail: str | None = Field(
        default=None,
        max_length=255,
        description="Additional source context",
    )
    intake_tag: IntakeTag | None = Field(
        default=None,
        description="Intake routing tag (defaults to SCHEDULE for website)",
    )
    website: str | None = Field(
        default=None,
        description="Honeypot field — must be empty",
    )
    sms_consent: bool = Field(
        default=False,
        description="SMS consent from form",
    )
    terms_accepted: bool = Field(
        default=False,
        description="Terms of service accepted",
    )
    email_marketing_consent: bool = Field(
        default=False,
        description="Email marketing consent",
    )
    page_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Source page URL",
    )
    customer_type: str | None = Field(
        default=None,
        max_length=20,
        description="Customer type: new or existing",
    )
    property_type: str | None = Field(
        default=None,
        max_length=20,
        description="Property type: RESIDENTIAL or COMMERCIAL",
    )
    consent_ip: str | None = Field(
        default=None,
        description="IP address at time of consent",
    )
    consent_user_agent: str | None = Field(
        default=None,
        description="User agent at time of consent",
    )
    consent_language_version: str | None = Field(
        default=None,
        description="Consent language version identifier",
    )

    @field_validator("phone")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Normalize phone to 10 digits.

        Validates: Requirement 1.2, 1.3
        """
        return normalize_phone(v)

    @field_validator("zip_code")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_zip_code(cls, v: str | None) -> str | None:
        """Validate 5-digit zip code.

        Validates: Requirement 1.4
        """
        if v is None:
            return None
        digits = "".join(filter(str.isdigit, v))
        if len(digits) != 5:
            msg = "Zip code must be exactly 5 digits"
            raise ValueError(msg)
        return digits

    @field_validator("name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Strip HTML tags and whitespace from name.

        Validates: Requirement 1.11
        """
        return strip_html_tags(v)

    @field_validator("address")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_address(cls, v: str) -> str:
        """Strip HTML tags and whitespace from address.

        Validates: Requirement 1.11
        """
        sanitized = strip_html_tags(v)
        if not sanitized:
            msg = "Address must not be empty"
            raise ValueError(msg)
        return sanitized

    @field_validator("notes")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        """Strip HTML tags from notes if provided.

        Validates: Requirement 1.11
        """
        if v is None:
            return None
        sanitized = strip_html_tags(v)
        return sanitized if sanitized else None


class LeadSubmissionResponse(BaseModel):
    """Response for public lead submission.

    Validates: Requirement 1.1
    """

    success: bool = True
    message: str = "Thank you! We'll reach out within 1-2 business days."
    lead_id: UUID | None = None


class LeadUpdate(BaseModel):
    """Schema for admin lead updates.

    Validates: Requirement 5, 48.5
    """

    status: LeadStatus | None = Field(
        default=None,
        description="New status",
    )
    assigned_to: UUID | None = Field(
        default=None,
        description="Staff member UUID",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Updated notes",
    )
    intake_tag: IntakeTag | None = Field(
        default=None,
        description="Intake routing tag",
    )
    city: str | None = Field(
        default=None,
        max_length=100,
        description="City",
    )
    state: str | None = Field(
        default=None,
        max_length=2,
        description="State abbreviation",
    )
    address: str | None = Field(
        default=None,
        max_length=500,
        description="Street address",
    )
    action_tags: list[str] | None = Field(
        default=None,
        description="Action tags for pipeline tracking",
    )

    @field_validator("notes")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        """Strip HTML tags from notes if provided."""
        if v is None:
            return None
        return strip_html_tags(v)


class LeadResponse(BaseModel):
    """Full lead response for admin endpoints.

    Validates: Requirement 5.8, CRM2 Req 9.2, 10.3, 11.2
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    email: str | None
    zip_code: str | None
    city: str | None = None
    state: str | None = None
    address: str | None = None
    action_tags: list[str] | None = None
    situation: LeadSituation
    notes: str | None
    source_site: str
    lead_source: str | None = None
    source_detail: str | None = None
    intake_tag: str | None = None
    customer_type: str | None = None
    property_type: str | None = None
    sms_consent: bool = False
    terms_accepted: bool = False
    email_marketing_consent: bool = False
    status: LeadStatus
    assigned_to: UUID | None
    customer_id: UUID | None
    contacted_at: datetime | None
    converted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # CRM2 fields (Req 9.2, 10.3, 11.2)
    moved_to: str | None = None
    moved_at: datetime | None = None
    last_contacted_at: datetime | None = None
    job_requested: str | None = None

    @field_validator("status", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_status(cls, v: str | LeadStatus) -> LeadStatus:
        """Convert string status to enum if needed."""
        if isinstance(v, str):
            return LeadStatus(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("situation", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_situation(cls, v: str | LeadSituation) -> LeadSituation:
        """Convert string situation to enum if needed."""
        if isinstance(v, str):
            return LeadSituation(v)
        return v  # type: ignore[return-value,unreachable]


class LeadListParams(BaseModel):
    """Query parameters for listing leads.

    Validates: Requirement 5.1-5.5, 45.3, 48.4
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: LeadStatus | None = None
    situation: LeadSituation | None = None
    search: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    lead_source: list[str] | None = None
    intake_tag: str | None = None
    action_tag: str | None = None
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedLeadResponse(BaseModel):
    """Paginated lead list response.

    Validates: Requirement 5.1
    """

    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FromCallSubmission(BaseModel):
    """Schema for admin from-call lead creation.

    Validates: Requirement 45.4, 45.5
    """

    name: str = Field(..., min_length=1, max_length=200, description="Full name")
    phone: str = Field(..., min_length=7, max_length=20, description="Phone number")
    email: EmailStr | None = Field(default=None, description="Optional email")
    address: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Street address",
    )
    zip_code: str | None = Field(
        default=None,
        max_length=10,
        description="Zip code (optional — extracted from address if omitted)",
    )
    situation: LeadSituation = Field(..., description="Service situation")
    notes: str | None = Field(default=None, max_length=1000, description="Notes")
    lead_source: LeadSourceExtended = Field(
        default=LeadSourceExtended.PHONE_CALL,
        description="Lead source (default PHONE_CALL)",
    )
    source_detail: str | None = Field(
        default=None,
        max_length=255,
        description="Source detail (defaults to 'Inbound call')",
    )
    intake_tag: IntakeTag | None = Field(
        default=None,
        description="Intake tag (default NULL for from-call)",
    )

    @field_validator("phone")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Normalize phone to 10 digits."""
        return normalize_phone(v)

    @field_validator("zip_code")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_zip_code(cls, v: str | None) -> str | None:
        """Validate 5-digit zip code."""
        if v is None:
            return None
        digits = "".join(filter(str.isdigit, v))
        if len(digits) != 5:
            msg = "Zip code must be exactly 5 digits"
            raise ValueError(msg)
        return digits

    @field_validator("name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Strip HTML tags."""
        return strip_html_tags(v)

    @field_validator("address")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_address(cls, v: str) -> str:
        """Strip HTML tags and whitespace from address."""
        sanitized = strip_html_tags(v)
        if not sanitized:
            msg = "Address must not be empty"
            raise ValueError(msg)
        return sanitized

    @field_validator("notes")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        """Strip HTML tags from notes."""
        if v is None:
            return None
        sanitized = strip_html_tags(v)
        return sanitized if sanitized else None


class FollowUpQueueItem(BaseModel):
    """A lead in the follow-up queue with computed time_since_created.

    Validates: Requirement 50.1-50.4
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    email: str | None
    situation: LeadSituation
    notes: str | None
    status: LeadStatus
    intake_tag: str | None = None
    created_at: datetime
    time_since_created: float = Field(
        default=0.0,
        description="Hours since lead was created",
    )

    @field_validator("status", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_status(cls, v: str | LeadStatus) -> LeadStatus:
        """Convert string status to enum if needed."""
        if isinstance(v, str):
            return LeadStatus(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("situation", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_situation(cls, v: str | LeadSituation) -> LeadSituation:
        """Convert string situation to enum if needed."""
        if isinstance(v, str):
            return LeadSituation(v)
        return v  # type: ignore[return-value,unreachable]


class PaginatedFollowUpQueueResponse(BaseModel):
    """Paginated follow-up queue response.

    Validates: Requirement 50.1
    """

    items: list[FollowUpQueueItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class LeadConversionRequest(BaseModel):
    """Request body for converting a lead to a customer.

    Validates: Requirement 7
    """

    first_name: str | None = Field(
        default=None,
        max_length=100,
        description="Override auto-split first name",
    )
    last_name: str | None = Field(
        default=None,
        max_length=100,
        description="Override auto-split last name",
    )
    create_job: bool = Field(
        default=True,
        description="Whether to create a job during conversion",
    )
    job_description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional job description override",
    )


class LeadConversionResponse(BaseModel):
    """Response for lead conversion.

    Validates: Requirement 7.6
    """

    success: bool = True
    lead_id: UUID
    customer_id: UUID
    job_id: UUID | None = None
    message: str = "Lead converted successfully"


class LeadSourceCount(BaseModel):
    """Count of leads for a single source.

    Validates: Requirement 61.3
    """

    lead_source: str
    count: int


class LeadMetricsBySourceResponse(BaseModel):
    """Response for lead metrics grouped by source.

    Validates: Requirement 61.3
    """

    items: list[LeadSourceCount]
    total: int
    date_from: datetime
    date_to: datetime


class LeadMoveResponse(BaseModel):
    """Response for lead move-to-jobs or move-to-sales.

    Validates: CRM2 Req 12.1, 12.2, Smoothing Req 6.1, 6.2
    """

    success: bool = True
    lead_id: UUID
    customer_id: UUID | None = None
    job_id: UUID | None = None
    sales_entry_id: UUID | None = None
    message: str
    requires_estimate_warning: bool = False


class BulkOutreachRequest(BaseModel):
    """Request body for bulk lead outreach.

    Validates: Requirement 14.1
    """

    lead_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of lead IDs to contact",
    )
    template: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Message template to send",
    )
    channel: str = Field(
        default="sms",
        pattern="^(sms|email|both)$",
        description="Communication channel: sms, email, or both",
    )


class BulkOutreachSummary(BaseModel):
    """Summary of bulk outreach results.

    Validates: Requirement 14.4
    """

    sent_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total: int = 0


class ManualLeadCreate(BaseModel):
    """Schema for manual lead creation via CRM interface.

    Requires name and phone; all other fields are optional.

    Validates: Requirement 7.2, 7.3
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Full name (required)",
    )
    phone: str = Field(
        ...,
        min_length=7,
        max_length=20,
        description="Phone number (required)",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Optional email address",
    )
    address: str | None = Field(
        default=None,
        max_length=500,
        description="Street address",
    )
    city: str | None = Field(
        default=None,
        max_length=100,
        description="City",
    )
    state: str | None = Field(
        default=None,
        max_length=2,
        description="State abbreviation",
    )
    zip_code: str | None = Field(
        default=None,
        max_length=10,
        description="Zip code",
    )
    situation: LeadSituation = Field(
        default=LeadSituation.EXPLORING,
        description="Lead situation (defaults to exploring)",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional notes",
    )

    @field_validator("phone")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Normalize phone to 10 digits."""
        return normalize_phone(v)

    @field_validator("zip_code")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_zip_code(cls, v: str | None) -> str | None:
        """Validate 5-digit zip code."""
        if v is None:
            return None
        digits = "".join(filter(str.isdigit, v))
        if len(digits) != 5:
            msg = "Zip code must be exactly 5 digits"
            raise ValueError(msg)
        return digits

    @field_validator("name")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Strip HTML tags."""
        return strip_html_tags(v)

    @field_validator("notes")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        """Strip HTML tags from notes."""
        if v is None:
            return None
        sanitized = strip_html_tags(v)
        return sanitized if sanitized else None


class MigrationSummary(BaseModel):
    """Summary of work request migration results.

    Validates: Requirement 19.1
    """

    total_submissions: int = 0
    migrated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = Field(default_factory=list)
