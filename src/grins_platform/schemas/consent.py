"""Pydantic schemas for SMS consent status and history.

Validates: Gap 06 — Opt-Out Management & Visibility.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConsentStatusResponse(BaseModel):
    """Derived consent status for a customer.

    Exposes the fields frontend surfaces need to render the OptOutBadge
    and disable outbound SMS actions: whether the customer is currently
    opted out, by what method, when, and whether an informal-opt-out
    alert is pending admin review.
    """

    model_config = ConfigDict(from_attributes=True)

    customer_id: UUID = Field(..., description="Customer UUID")
    phone: str | None = Field(
        default=None,
        description="Customer's primary phone (E.164 when available)",
    )
    is_opted_out: bool = Field(
        ...,
        description=(
            "True when the most recent consent record has consent_given=False "
            "or a hard-STOP row exists for any of the customer's phones."
        ),
    )
    opt_out_method: str | None = Field(
        default=None,
        description=(
            "How the opt-out was recorded: text_stop, "
            "admin_confirmed_informal, or any other consent_method value."
        ),
    )
    opt_out_timestamp: datetime | None = Field(
        default=None,
        description="When the opt-out was recorded (tz-aware UTC)",
    )
    pending_informal_opt_out_alert_id: UUID | None = Field(
        default=None,
        description=(
            "UUID of an unacknowledged INFORMAL_OPT_OUT alert for the "
            "customer, or null. Drives the 'pending' badge variant."
        ),
    )


class ConsentHistoryEntry(BaseModel):
    """A single SmsConsentRecord row rendered for the history timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Consent record UUID")
    consent_given: bool = Field(
        ...,
        description="True if this row grants consent; False if it revokes it.",
    )
    consent_type: str = Field(
        ...,
        description="marketing / transactional / operational",
    )
    consent_method: str = Field(
        ...,
        description="Method by which consent was obtained or revoked",
    )
    consent_timestamp: datetime = Field(
        ...,
        description="When the consent event occurred (tz-aware UTC)",
    )
    opt_out_method: str | None = Field(
        default=None,
        description="Set when this row records an opt-out, else null",
    )
    opt_out_timestamp: datetime | None = Field(
        default=None,
        description="When the opt-out was recorded, if applicable",
    )
    created_by_staff_id: UUID | None = Field(
        default=None,
        description="Staff actor who wrote this row, if admin-initiated",
    )
    consent_language_shown: str = Field(
        ...,
        description="Verbatim attestation / message body captured with the row",
    )


class ConsentHistoryResponse(BaseModel):
    """Paginated chronological list of consent events for a customer."""

    items: list[ConsentHistoryEntry] = Field(
        default_factory=list,
        description="Consent events in descending consent_timestamp order",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Number of rows returned (bounded by the query limit)",
    )
