"""Pydantic schemas for outbound sent message history.

Validates: CRM Gap Closure Req 82.2, 82.3
"""

import contextlib
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class SentMessageResponse(BaseModel):
    """Schema for a sent message record.

    Validates: CRM Gap Closure Req 82.2
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(..., description="Message UUID")
    customer_id: UUID | None = Field(default=None, description="Customer UUID")
    lead_id: UUID | None = Field(default=None, description="Lead UUID")
    message_type: str = Field(
        ...,
        max_length=50,
        description="Message type",
    )
    # The ORM column is ``message_content`` but the frontend (and the rest
    # of this schema's historical consumers) expect ``content``. Accept
    # both aliases on input and serialize as ``content``.
    content: str | None = Field(
        default=None,
        max_length=5000,
        description="Message content",
        validation_alias=AliasChoices("content", "message_content"),
    )
    recipient_phone: str | None = Field(
        default=None,
        max_length=32,
        description="Destination phone (E.164 or provider canonical form)",
    )
    recipient_name: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "Human-readable recipient name resolved from the related "
            "Customer/Lead when available"
        ),
    )
    delivery_status: str | None = Field(
        default=None,
        max_length=20,
        description="Delivery status",
    )
    error_message: str | None = Field(
        default=None,
        max_length=1000,
        description="Error details if failed",
    )
    sent_at: datetime | None = Field(default=None, description="Send timestamp")
    created_at: datetime = Field(..., description="Record creation timestamp")

    @model_validator(mode="before")
    @classmethod
    def _resolve_recipient_name(cls, value: Any) -> Any:  # noqa: ANN401
        """Derive ``recipient_name`` from the loaded Customer/Lead relationship.

        ``SentMessage.customer`` and ``SentMessage.lead`` are both
        ``lazy="selectin"`` on the ORM model, so they're already loaded
        by the time the list endpoint validates each row — no extra
        query is issued here. ``Customer`` stores first/last separately
        while ``Lead`` has a single ``name`` column, so we accept either
        shape. If neither side has a usable name we leave the field
        unset and the UI falls back to a dash.
        """
        # Dicts and None pass through untouched — only ORM rows need patching.
        if value is None or isinstance(value, dict):
            return value

        # Don't clobber an explicit recipient_name if one was already set.
        existing = getattr(value, "recipient_name", None)
        if existing:
            return value

        def _extract_name(rel: object) -> str:
            # Customer: first_name + last_name
            first = (getattr(rel, "first_name", None) or "").strip()
            last = (getattr(rel, "last_name", None) or "").strip()
            joined = f"{first} {last}".strip()
            if joined:
                return joined
            # Lead (and anything else with a single ``name`` column)
            return (getattr(rel, "name", None) or "").strip()

        for rel_name in ("customer", "lead"):
            rel = getattr(value, rel_name, None)
            if rel is None:
                continue
            full = _extract_name(rel)
            if full:
                # Attach as a plain attribute so the subsequent
                # ``from_attributes`` read picks it up. SQLAlchemy allows
                # setting non-mapped attributes on ORM instances without
                # tracking them as dirty.
                with contextlib.suppress(AttributeError):
                    value.recipient_name = full  # type: ignore[attr-defined]
                break

        return value


class SentMessageListResponse(BaseModel):
    """Paginated sent message list.

    Validates: CRM Gap Closure Req 82.2, 82.3
    """

    items: list[SentMessageResponse] = Field(
        ...,
        description="List of sent messages",
    )
    total: int = Field(..., ge=0, description="Total matching records")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages")


class SentMessageFilters(BaseModel):
    """Filters for querying sent messages.

    Validates: CRM Gap Closure Req 82.3
    """

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    message_type: str | None = Field(
        default=None,
        max_length=50,
        description="Filter by message type",
    )
    delivery_status: str | None = Field(
        default=None,
        max_length=20,
        description="Filter by delivery status",
    )
    date_from: datetime | None = Field(
        default=None,
        description="Filter from date",
    )
    date_to: datetime | None = Field(default=None, description="Filter to date")
    search: str | None = Field(
        default=None,
        max_length=200,
        description="Search in content",
    )
