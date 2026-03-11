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
    zip_code: str = Field(
        ...,
        min_length=5,
        max_length=10,
        description="5-digit zip code",
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
    email_marketing_consent: bool = Field(
        default=False,
        description="Email marketing consent",
    )
    page_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Source page URL",
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
    def validate_zip_code(cls, v: str) -> str:
        """Validate 5-digit zip code.

        Validates: Requirement 1.4
        """
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
    message: str = "Thank you! We'll be in touch within 24 hours."
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

    @field_validator("notes")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        """Strip HTML tags from notes if provided."""
        if v is None:
            return None
        return strip_html_tags(v)


class LeadResponse(BaseModel):
    """Full lead response for admin endpoints.

    Validates: Requirement 5.8
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    email: str | None
    zip_code: str | None
    situation: LeadSituation
    notes: str | None
    source_site: str
    lead_source: str | None = None
    source_detail: str | None = None
    intake_tag: str | None = None
    sms_consent: bool = False
    terms_accepted: bool = False
    status: LeadStatus
    assigned_to: UUID | None
    customer_id: UUID | None
    contacted_at: datetime | None
    converted_at: datetime | None
    created_at: datetime
    updated_at: datetime

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
    zip_code: str = Field(..., min_length=5, max_length=10, description="Zip code")
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
    def validate_zip_code(cls, v: str) -> str:
        """Validate 5-digit zip code."""
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
