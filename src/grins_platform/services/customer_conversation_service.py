"""Customer conversation aggregator (gap-13).

Aggregates a single customer's inbound and outbound message history
across four heterogeneous source tables into a chronological stream:

- ``sent_messages``               — outbound (SMS, email, etc.)
- ``job_confirmation_responses``  — inbound Y/R/C confirmation replies
- ``campaign_responses``          — inbound poll / campaign replies
                                    (may be orphaned via phone fallback)
- ``communications``              — inbound free-text / general inbox

Implementation note (verified 2026-04-26): SQL ``UNION ALL`` was
rejected because the four tables' column shapes diverge meaningfully
(``raw_reply_body`` vs ``content`` vs ``message_content``, different
keyword/status/parsed columns). Casting to a uniform tuple inside SQL
is fragile, so the service issues 4 parallel ``select`` queries via
``asyncio.gather`` and merges in Python with ``heapq.merge``. This
plays well with the existing per-table FK indexes.

Performance contract: <150 ms p95 at 500 cumulative items per customer.

Validates: scheduling-gaps gap-13 (CustomerMessages tab inbound).
"""

from __future__ import annotations

import asyncio
import base64
import heapq
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, or_, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.campaign_response import CampaignResponse
from grins_platform.models.communication import Communication
from grins_platform.models.customer import Customer
from grins_platform.models.job_confirmation import JobConfirmationResponse
from grins_platform.models.sent_message import SentMessage
from grins_platform.schemas.customer_conversation import (
    ConversationChannel,
    ConversationDirection,
    ConversationItem,
    ConversationResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


@dataclass(order=True)
class _Cursor:
    """Composite cursor for descending-timestamp pagination.

    Ordering key is ``(-timestamp_epoch, source_table, source_id)`` so
    Python's natural sort yields newest-first. The cursor is opaque to
    clients and round-trips as base64-encoded JSON.
    """

    timestamp: datetime = field(compare=False)
    source_table: str
    source_id: str

    def encode(self) -> str:
        payload = {
            "ts": self.timestamp.isoformat(),
            "tbl": self.source_table,
            "id": self.source_id,
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @classmethod
    def decode(cls, value: str) -> _Cursor | None:
        try:
            raw = base64.urlsafe_b64decode(value.encode("ascii"))
            payload = json.loads(raw.decode("utf-8"))
            return cls(
                timestamp=datetime.fromisoformat(payload["ts"]),
                source_table=str(payload["tbl"]),
                source_id=str(payload["id"]),
            )
        except (ValueError, KeyError, TypeError):
            return None


def _sort_key(item: ConversationItem) -> tuple[Any, ...]:
    # Descending timestamp; ties broken by (source_table, id) for stability.
    return (-item.timestamp.timestamp(), item.source_table, str(item.id))


class CustomerConversationService(LoggerMixin):
    """List a customer's inbound + outbound message history."""

    DOMAIN = "customer_conversation"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def list_conversation(
        self,
        customer_id: UUID,
        cursor: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> ConversationResponse:
        """Return a single page of the merged conversation stream.

        ``cursor`` encodes the last item of the previous page; when
        present, results are filtered to items strictly older than the
        cursor (or equal-timestamp items with a lower (table, id) tuple
        — the natural python tuple ordering).

        Note: phone-number history is best-effort. If a customer's
        ``phone`` has changed, orphan ``campaign_responses`` matched by
        ``from_phone`` will only match the *current* phone — older
        inbound rows tied to a stale phone will not appear here. v1
        improvement candidate.
        """
        clamped_limit = max(1, min(limit, _MAX_LIMIT))
        decoded_cursor = _Cursor.decode(cursor) if cursor else None
        self.log_started(
            "list_conversation",
            customer_id=str(customer_id),
            limit=clamped_limit,
            has_cursor=cursor is not None,
        )

        # Resolve customer phone for orphan campaign_response fallback.
        phone_row = await self.session.execute(
            select(Customer.phone).where(Customer.id == customer_id)
        )
        customer_phone = phone_row.scalar_one_or_none()

        per_source_limit = clamped_limit + 1
        sent, confirmations, campaign_replies, comms = await asyncio.gather(
            self._fetch_sent_messages(customer_id, per_source_limit),
            self._fetch_confirmation_responses(customer_id, per_source_limit),
            self._fetch_campaign_responses(
                customer_id, customer_phone, per_source_limit
            ),
            self._fetch_communications(customer_id, per_source_limit),
        )

        # Merge into a single descending stream, dropping anything older
        # than the cursor.
        cursor_key = (
            (
                -decoded_cursor.timestamp.timestamp(),
                decoded_cursor.source_table,
                decoded_cursor.source_id,
            )
            if decoded_cursor is not None
            else None
        )
        merged: list[ConversationItem] = []
        for item in heapq.merge(
            sent, confirmations, campaign_replies, comms, key=_sort_key
        ):
            if cursor_key is not None and _sort_key(item) <= cursor_key:
                continue
            merged.append(item)
            if len(merged) >= clamped_limit + 1:
                break

        has_more = len(merged) > clamped_limit
        page = merged[:clamped_limit]
        next_cursor: str | None = None
        if has_more and page:
            tail = page[-1]
            next_cursor = _Cursor(
                timestamp=tail.timestamp,
                source_table=tail.source_table,
                source_id=str(tail.id),
            ).encode()

        self.log_completed(
            "list_conversation",
            customer_id=str(customer_id),
            count=len(page),
            has_more=has_more,
        )
        return ConversationResponse(
            items=page,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def _fetch_sent_messages(
        self,
        customer_id: UUID,
        limit: int,
    ) -> list[ConversationItem]:
        stmt = (
            select(SentMessage)
            .where(SentMessage.customer_id == customer_id)
            .order_by(
                SentMessage.sent_at.desc().nulls_last(),
                SentMessage.created_at.desc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        items: list[ConversationItem] = []
        for row in rows:
            channel = self._classify_outbound_channel(row.message_type)
            timestamp = row.sent_at or row.created_at
            items.append(
                ConversationItem(
                    id=row.id,
                    source_table="sent_messages",
                    direction="outbound",
                    channel=channel,
                    timestamp=timestamp,
                    body=row.message_content,
                    status=row.delivery_status,
                    parsed_keyword=None,
                    appointment_id=row.appointment_id,
                    from_phone=None,
                    to_phone=row.recipient_phone,
                    message_type=row.message_type,
                )
            )
        return items

    async def _fetch_confirmation_responses(
        self,
        customer_id: UUID,
        limit: int,
    ) -> list[ConversationItem]:
        stmt = (
            select(JobConfirmationResponse)
            .where(JobConfirmationResponse.customer_id == customer_id)
            .order_by(JobConfirmationResponse.received_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            ConversationItem(
                id=row.id,
                source_table="job_confirmation_responses",
                direction="inbound",
                channel="sms",
                timestamp=row.received_at,
                body=row.raw_reply_body,
                status=row.status,
                parsed_keyword=row.reply_keyword,
                appointment_id=row.appointment_id,
                from_phone=row.from_phone,
                to_phone=None,
                message_type=None,
            )
            for row in rows
        ]

    async def _fetch_campaign_responses(
        self,
        customer_id: UUID,
        customer_phone: str | None,
        limit: int,
    ) -> list[ConversationItem]:
        # Orphan fallback: rows where customer_id is NULL but the inbound
        # phone matches the customer's current phone. Best-effort — phone
        # history is not tracked.
        clauses = [CampaignResponse.customer_id == customer_id]
        if customer_phone:
            clauses.append(
                and_(
                    CampaignResponse.customer_id.is_(None),
                    CampaignResponse.phone == customer_phone,
                )
            )
        where_clause = or_(*clauses) if len(clauses) > 1 else clauses[0]
        stmt = (
            select(CampaignResponse)
            .where(where_clause)
            .order_by(CampaignResponse.received_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            ConversationItem(
                id=row.id,
                source_table="campaign_responses",
                direction="inbound",
                channel="sms",
                timestamp=row.received_at,
                body=row.raw_reply_body,
                status=row.status,
                parsed_keyword=row.selected_option_key,
                appointment_id=None,
                from_phone=row.phone,
                to_phone=None,
                message_type=None,
            )
            for row in rows
        ]

    async def _fetch_communications(
        self,
        customer_id: UUID,
        limit: int,
    ) -> list[ConversationItem]:
        stmt = (
            select(Communication)
            .where(Communication.customer_id == customer_id)
            .order_by(Communication.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        items: list[ConversationItem] = []
        for row in rows:
            direction: ConversationDirection = (
                "inbound" if row.direction == "inbound" else "outbound"
            )
            channel = self._classify_communication_channel(row.channel)
            items.append(
                ConversationItem(
                    id=row.id,
                    source_table="communications",
                    direction=direction,
                    channel=channel,
                    timestamp=row.created_at,
                    body=row.content,
                    status="addressed" if row.addressed else None,
                    parsed_keyword=None,
                    appointment_id=None,
                    from_phone=None,
                    to_phone=None,
                    message_type=None,
                )
            )
        return items

    @staticmethod
    def _classify_outbound_channel(message_type: str) -> ConversationChannel:
        token = (message_type or "").lower()
        if "email" in token:
            return "email"
        if "phone" in token or "voice" in token or "call" in token:
            return "phone"
        return "sms"

    @staticmethod
    def _classify_communication_channel(channel: str) -> ConversationChannel:
        token = (channel or "").lower()
        if token == "sms":
            return "sms"
        if token == "email":
            return "email"
        if token == "phone":
            return "phone"
        return "other"
