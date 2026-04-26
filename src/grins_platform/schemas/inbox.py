"""Pydantic schemas for the unified SMS inbox queue (gap-16 v0).

The inbox surfaces inbound replies that span four heterogeneous source
tables (``job_confirmation_responses``, ``reschedule_requests``,
``campaign_responses``, ``communications``) so admins can triage
orphan / unrecognized / informal-opt-out replies without context-switching
across multiple admin pages.

v0 is read-only — triage actions (link, archive, reply) are deferred to
v1. The frontend renders this as a fourth queue card on ``/schedule``
alongside the existing reschedule-requests and no-reply-review queues.

Validates: scheduling-gaps gap-16.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

InboxTriageStatus = Literal["pending", "handled", "dismissed"]
InboxSourceTable = Literal[
    "job_confirmation_responses",
    "reschedule_requests",
    "campaign_responses",
    "communications",
]
InboxFilterToken = Literal[
    "all",
    "needs_triage",
    "orphans",
    "unrecognized",
    "opt_outs",
    "archived",
]


class InboxItem(BaseModel):
    """A single inbound row projected for the unified inbox view."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Source-table primary key")
    source_table: InboxSourceTable = Field(
        ...,
        description="Origin table for this row",
    )
    triage_status: InboxTriageStatus = Field(
        ...,
        description="Computed triage bucket (pending / handled / dismissed)",
    )
    received_at: datetime = Field(
        ...,
        description="Canonical timestamp the inbound row was received",
    )
    body: str = Field(..., description="Raw / parsed body text")
    from_phone: str | None = Field(
        default=None,
        description="Sender phone (E.164 or provider canonical form)",
    )
    customer_id: UUID | None = Field(
        default=None,
        description="Linked customer if known (NULL = orphan)",
    )
    customer_name: str | None = Field(
        default=None,
        description="Linked customer's display name when known",
    )
    appointment_id: UUID | None = Field(
        default=None,
        description="Linked appointment if known",
    )
    parsed_keyword: str | None = Field(
        default=None,
        description="Y / R / C / option key parsed from body, if any",
    )
    status: str | None = Field(
        default=None,
        description="Raw status label from the source table",
    )


class InboxFilterCounts(BaseModel):
    """Counts per filter-pill so the UI can label each pill in real time."""

    all: int = Field(..., ge=0)
    needs_triage: int = Field(..., ge=0)
    orphans: int = Field(..., ge=0)
    unrecognized: int = Field(..., ge=0)
    opt_outs: int = Field(..., ge=0)
    archived: int = Field(..., ge=0)


class InboxListResponse(BaseModel):
    """Paginated inbox response with cursor-based pagination."""

    items: list[InboxItem] = Field(
        default_factory=list,
        description="Inbox items in descending received_at order",
    )
    next_cursor: str | None = Field(
        default=None,
        description="Opaque base64-encoded cursor for the next page",
    )
    has_more: bool = Field(
        ...,
        description="True if more items are available beyond this page",
    )
    counts: InboxFilterCounts = Field(
        ...,
        description="Per-filter counts for the queue header pills",
    )
