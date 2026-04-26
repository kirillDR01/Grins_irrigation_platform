"""Pydantic schemas for the per-customer conversation view.

Validates: scheduling-gaps gap-13 (CustomerMessages tab is outbound-only).

The conversation view UNIONs four heterogeneous inbound/outbound sources
(``sent_messages``, ``job_confirmation_responses``, ``campaign_responses``,
``communications``) into a single chronological stream. Each row is
projected into a ``ConversationItem`` with a stable shape so the UI can
render paired in/out chat-style messages without per-source rendering
branches.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ConversationDirection = Literal["inbound", "outbound"]
ConversationChannel = Literal["sms", "email", "phone", "other"]
ConversationSourceTable = Literal[
    "sent_messages",
    "job_confirmation_responses",
    "campaign_responses",
    "communications",
]


class ConversationItem(BaseModel):
    """A single inbound or outbound message in the conversation stream.

    The shape unifies the four source tables: outbound rows come from
    ``sent_messages``; inbound rows come from one of the three inbound
    tables. ``parsed_keyword`` is set only for ``job_confirmation_responses``
    where the SMS service has identified a Y/R/C-style keyword.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Source-table primary key")
    source_table: ConversationSourceTable = Field(
        ...,
        description="Origin table for this row",
    )
    direction: ConversationDirection = Field(..., description="inbound or outbound")
    channel: ConversationChannel = Field(
        ...,
        description="Transport channel — sms / email / phone / other",
    )
    timestamp: datetime = Field(
        ...,
        description=(
            "Canonical timestamp used for chronological ordering "
            "(sent_at fallback to created_at for outbound; received_at "
            "for inbound)"
        ),
    )
    body: str = Field(..., description="Message body / content")
    status: str | None = Field(
        default=None,
        description=(
            "Delivery / processing status (outbound: sent/delivered/failed; "
            "inbound: parsed/needs_review/orphan/etc.)"
        ),
    )
    parsed_keyword: str | None = Field(
        default=None,
        description="Y/R/C-style keyword if parsed from inbound body",
    )
    appointment_id: UUID | None = Field(
        default=None,
        description="Linked appointment if known",
    )
    from_phone: str | None = Field(
        default=None,
        description="Sender phone (inbound only)",
    )
    to_phone: str | None = Field(
        default=None,
        description="Recipient phone (outbound only)",
    )
    message_type: str | None = Field(
        default=None,
        description=(
            "Outbound message_type (e.g. appointment_confirmation) or null for inbound"
        ),
    )


class ConversationResponse(BaseModel):
    """Paginated conversation response with cursor-based pagination."""

    items: list[ConversationItem] = Field(
        default_factory=list,
        description="Conversation items in descending timestamp order",
    )
    next_cursor: str | None = Field(
        default=None,
        description=(
            "Opaque base64-encoded cursor for the next page; null when no "
            "more items exist"
        ),
    )
    has_more: bool = Field(
        ...,
        description="True if more items are available beyond this page",
    )
