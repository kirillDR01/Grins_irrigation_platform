"""Unified inbox aggregator (gap-16 v0).

Cross-customer UNION of the four inbound tables, surfaced as a fourth
queue card on ``/schedule``. Mirrors the parallel-gather + ``heapq.merge``
strategy used by ``CustomerConversationService``; the difference is that
filtering is cross-customer and the triage classification is computed
server-side so the UI can render the filter-pill bar with accurate counts.

Sources:

- ``job_confirmation_responses`` — Y/R/C confirmation replies
- ``reschedule_requests``        — derivative of confirmation_responses
                                   but tracked separately so admins can
                                   see which inbound rows opened a queue
                                   item that's still pending resolution
- ``campaign_responses``         — poll / campaign replies (orphan-prone)
- ``communications``             — inbound free-text / general inbox

Performance contract: <250 ms p95 at 30-day window with ~1k inbound rows.

Validates: scheduling-gaps gap-16.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.campaign_response import CampaignResponse
from grins_platform.models.communication import Communication
from grins_platform.models.customer import Customer
from grins_platform.models.job_confirmation import (
    JobConfirmationResponse,
    RescheduleRequest,
)
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.schemas.inbox import (
    InboxFilterCounts,
    InboxItem,
    InboxListResponse,
    InboxSourceTable,
    InboxTriageStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200

# Filter tokens accepted by the API ``triage`` query param.
_FILTER_ALL = "all"
_FILTER_NEEDS_TRIAGE = "needs_triage"
_FILTER_ORPHANS = "orphans"
_FILTER_UNRECOGNIZED = "unrecognized"
_FILTER_OPT_OUTS = "opt_outs"
_FILTER_OPT_INS = "opt_ins"
_FILTER_ARCHIVED = "archived"

# F8: status labels for ``source_table=consent`` rows so the triage
# classifier and filter matcher can reason symbolically about STOP/START
# replies. STOP rows surface as ``opt_out`` (always pending — operator
# should see consent flips); START rows surface as ``opt_in`` (handled —
# informational).
_CONSENT_STATUS_OPT_OUT = "opt_out"
_CONSENT_STATUS_OPT_IN = "opt_in"

# F8 feature gate. When unset / "false", the consent-source UNION is
# skipped — keeps schema rollout risk-free until browser verification
# confirms the SQL plan + chip UX.
_INBOX_SHOW_CONSENT_FLIPS_ENV = "INBOX_SHOW_CONSENT_FLIPS"


def _consent_flips_enabled() -> bool:
    return os.getenv(_INBOX_SHOW_CONSENT_FLIPS_ENV, "false").lower() == "true"


@dataclass
class _Cursor:
    timestamp: datetime
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


def _sort_key(item: InboxItem) -> tuple[Any, ...]:
    return (-item.received_at.timestamp(), item.source_table, str(item.id))


# Per-source HANDLED status sets. Anything outside the set defaults to
# "pending" so unknown / new statuses surface for admin review rather
# than silently disappearing.
_HANDLED_STATUSES: dict[InboxSourceTable, frozenset[str]] = {
    "job_confirmation_responses": frozenset(
        {"parsed", "confirmed", "rescheduled", "cancelled"}
    ),
    "reschedule_requests": frozenset({"resolved", "rejected"}),
    "campaign_responses": frozenset({"parsed"}),
    "communications": frozenset({"addressed"}),
    # F8: standalone START re-opt-ins are informational and land as
    # "handled". Standalone STOP rows are always "pending" — handled in
    # _classify_triage rather than via this set.
    "consent": frozenset({_CONSENT_STATUS_OPT_IN}),
}


def _classify_triage(
    *,
    source_table: InboxSourceTable,
    status: str | None,
    customer_id: UUID | None,
) -> InboxTriageStatus:
    """Compute the triage bucket for a row.

    - ``pending``: row needs admin attention (needs_review / orphan /
      open RescheduleRequest / unaddressed Communication / unknown
      status / standalone STOP).
    - ``handled``: row has been resolved or addressed (incl. standalone
      START re-opt-ins).
    - ``dismissed``: reserved for v1 (manual archive).
    """
    # Communications without a linked customer are always pending —
    # they're orphan inbound that nobody owns yet.
    if source_table == "communications" and customer_id is None:
        return "pending"
    # F8: standalone STOP must always surface for the operator even when
    # the customer record is linked — it represents an active consent
    # withdrawal that someone should acknowledge.
    if source_table == "consent" and (status or "").lower() == _CONSENT_STATUS_OPT_OUT:
        return "pending"
    s = (status or "").lower()
    if s in _HANDLED_STATUSES[source_table]:
        return "handled"
    return "pending"


def _matches_filter(
    *,
    triage: str,
    item: InboxItem,
) -> bool:
    status = (item.status or "").lower()
    is_consent = item.source_table == "consent"
    matchers: dict[str, bool] = {
        "": True,
        _FILTER_ALL: True,
        _FILTER_NEEDS_TRIAGE: item.triage_status == "pending",
        _FILTER_ARCHIVED: item.triage_status == "dismissed",
        _FILTER_ORPHANS: item.customer_id is None or status == "orphan",
        _FILTER_UNRECOGNIZED: status == "needs_review",
        _FILTER_OPT_OUTS: status == "opted_out"
        or (is_consent and status == _CONSENT_STATUS_OPT_OUT),
        _FILTER_OPT_INS: is_consent and status == _CONSENT_STATUS_OPT_IN,
    }
    return matchers.get(triage, True)


class InboxService(LoggerMixin):
    """Read-only unified inbox v0."""

    DOMAIN = "inbox"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def list_events(
        self,
        triage: str | None = None,
        cursor: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> InboxListResponse:
        """Return one page of the unioned inbox stream."""
        clamped_limit = max(1, min(limit, _MAX_LIMIT))
        decoded_cursor = _Cursor.decode(cursor) if cursor else None
        triage_token = (triage or _FILTER_ALL).lower()
        self.log_started(
            "list_events",
            triage=triage_token,
            limit=clamped_limit,
            has_cursor=cursor is not None,
        )

        # Pull a generous per-source slice so the heap merge has enough
        # rows to satisfy the page even after filtering and the cursor
        # discards a prefix. ``per_source_limit`` * 4 sources is a soft
        # upper bound on Python-side work.
        per_source_limit = max(clamped_limit * 2, 100)
        # F8: opt-in/out consent flips are gated behind the
        # INBOX_SHOW_CONSENT_FLIPS env flag so the schema change ships
        # without immediately changing the operator surface.
        if _consent_flips_enabled():
            (
                confirmations,
                reschedules,
                campaigns,
                comms,
                consents,
            ) = await asyncio.gather(
                self._fetch_confirmation_responses(per_source_limit),
                self._fetch_reschedule_requests(per_source_limit),
                self._fetch_campaign_responses(per_source_limit),
                self._fetch_communications(per_source_limit),
                self._fetch_consent_records(per_source_limit),
            )
            batches = (confirmations, reschedules, campaigns, comms, consents)
        else:
            confirmations, reschedules, campaigns, comms = await asyncio.gather(
                self._fetch_confirmation_responses(per_source_limit),
                self._fetch_reschedule_requests(per_source_limit),
                self._fetch_campaign_responses(per_source_limit),
                self._fetch_communications(per_source_limit),
            )
            batches = (confirmations, reschedules, campaigns, comms)

        all_items: list[InboxItem] = []
        for batch in batches:
            all_items.extend(batch)
        all_items.sort(key=_sort_key)

        # Compute filter counts BEFORE applying the active filter so the
        # pill labels reflect the global picture.
        counts = self._compute_counts(all_items)

        cursor_key = (
            (
                -decoded_cursor.timestamp.timestamp(),
                decoded_cursor.source_table,
                decoded_cursor.source_id,
            )
            if decoded_cursor is not None
            else None
        )

        page: list[InboxItem] = []
        for item in all_items:
            if cursor_key is not None and _sort_key(item) <= cursor_key:
                continue
            if not _matches_filter(triage=triage_token, item=item):
                continue
            page.append(item)
            if len(page) >= clamped_limit + 1:
                break

        has_more = len(page) > clamped_limit
        page = page[:clamped_limit]
        next_cursor: str | None = None
        if has_more and page:
            tail = page[-1]
            next_cursor = _Cursor(
                timestamp=tail.received_at,
                source_table=tail.source_table,
                source_id=str(tail.id),
            ).encode()

        self.log_completed(
            "list_events",
            triage=triage_token,
            count=len(page),
            has_more=has_more,
        )
        return InboxListResponse(
            items=page,
            next_cursor=next_cursor,
            has_more=has_more,
            counts=counts,
        )

    @staticmethod
    def _compute_counts(items: list[InboxItem]) -> InboxFilterCounts:
        counts = {
            _FILTER_ALL: 0,
            _FILTER_NEEDS_TRIAGE: 0,
            _FILTER_ORPHANS: 0,
            _FILTER_UNRECOGNIZED: 0,
            _FILTER_OPT_OUTS: 0,
            _FILTER_OPT_INS: 0,
            _FILTER_ARCHIVED: 0,
        }
        for item in items:
            counts[_FILTER_ALL] += 1
            if item.triage_status == "pending":
                counts[_FILTER_NEEDS_TRIAGE] += 1
            if item.triage_status == "dismissed":
                counts[_FILTER_ARCHIVED] += 1
            status = (item.status or "").lower()
            if item.customer_id is None or status == "orphan":
                counts[_FILTER_ORPHANS] += 1
            if status == "needs_review":
                counts[_FILTER_UNRECOGNIZED] += 1
            if status == "opted_out":
                counts[_FILTER_OPT_OUTS] += 1
            if item.source_table == "consent":
                if status == _CONSENT_STATUS_OPT_OUT:
                    counts[_FILTER_OPT_OUTS] += 1
                elif status == _CONSENT_STATUS_OPT_IN:
                    counts[_FILTER_OPT_INS] += 1
        return InboxFilterCounts(
            all=counts[_FILTER_ALL],
            needs_triage=counts[_FILTER_NEEDS_TRIAGE],
            orphans=counts[_FILTER_ORPHANS],
            unrecognized=counts[_FILTER_UNRECOGNIZED],
            opt_outs=counts[_FILTER_OPT_OUTS],
            opt_ins=counts[_FILTER_OPT_INS],
            archived=counts[_FILTER_ARCHIVED],
        )

    async def _fetch_confirmation_responses(
        self,
        limit: int,
    ) -> list[InboxItem]:
        stmt = (
            select(JobConfirmationResponse, Customer)
            .join(
                Customer,
                Customer.id == JobConfirmationResponse.customer_id,
                isouter=True,
            )
            .order_by(JobConfirmationResponse.received_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items: list[InboxItem] = []
        for row, customer in result.all():
            triage_status = _classify_triage(
                source_table="job_confirmation_responses",
                status=row.status,
                customer_id=row.customer_id,
            )
            items.append(
                InboxItem(
                    id=row.id,
                    source_table="job_confirmation_responses",
                    triage_status=triage_status,
                    received_at=row.received_at,
                    body=row.raw_reply_body,
                    from_phone=row.from_phone,
                    customer_id=row.customer_id,
                    customer_name=(
                        customer.full_name if customer is not None else None
                    ),
                    appointment_id=row.appointment_id,
                    parsed_keyword=row.reply_keyword,
                    status=row.status,
                )
            )
        return items

    async def _fetch_reschedule_requests(
        self,
        limit: int,
    ) -> list[InboxItem]:
        stmt = (
            select(RescheduleRequest, Customer)
            .join(
                Customer,
                Customer.id == RescheduleRequest.customer_id,
                isouter=True,
            )
            .order_by(RescheduleRequest.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items: list[InboxItem] = []
        for row, customer in result.all():
            triage_status = _classify_triage(
                source_table="reschedule_requests",
                status=row.status,
                customer_id=row.customer_id,
            )
            body = row.raw_alternatives_text or "Reschedule requested"
            items.append(
                InboxItem(
                    id=row.id,
                    source_table="reschedule_requests",
                    triage_status=triage_status,
                    received_at=row.created_at,
                    body=body,
                    from_phone=None,
                    customer_id=row.customer_id,
                    customer_name=(
                        customer.full_name if customer is not None else None
                    ),
                    appointment_id=row.appointment_id,
                    parsed_keyword=None,
                    status=row.status,
                )
            )
        return items

    async def _fetch_campaign_responses(
        self,
        limit: int,
    ) -> list[InboxItem]:
        stmt = (
            select(CampaignResponse, Customer)
            .join(
                Customer,
                Customer.id == CampaignResponse.customer_id,
                isouter=True,
            )
            .order_by(CampaignResponse.received_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items: list[InboxItem] = []
        for row, customer in result.all():
            triage_status = _classify_triage(
                source_table="campaign_responses",
                status=row.status,
                customer_id=row.customer_id,
            )
            customer_name: str | None = None
            if customer is not None:
                customer_name = customer.full_name
            elif row.recipient_name:
                customer_name = row.recipient_name
            items.append(
                InboxItem(
                    id=row.id,
                    source_table="campaign_responses",
                    triage_status=triage_status,
                    received_at=row.received_at,
                    body=row.raw_reply_body,
                    from_phone=row.phone,
                    customer_id=row.customer_id,
                    customer_name=customer_name,
                    appointment_id=None,
                    parsed_keyword=row.selected_option_key,
                    status=row.status,
                )
            )
        return items

    async def _fetch_communications(
        self,
        limit: int,
    ) -> list[InboxItem]:
        stmt = (
            select(Communication, Customer)
            .join(
                Customer,
                Customer.id == Communication.customer_id,
                isouter=True,
            )
            .where(Communication.direction == "inbound")
            .order_by(Communication.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items: list[InboxItem] = []
        for row, customer in result.all():
            status_label = "addressed" if row.addressed else "unaddressed"
            triage_status = _classify_triage(
                source_table="communications",
                status=status_label,
                customer_id=row.customer_id,
            )
            items.append(
                InboxItem(
                    id=row.id,
                    source_table="communications",
                    triage_status=triage_status,
                    received_at=row.created_at,
                    body=row.content,
                    from_phone=None,
                    customer_id=row.customer_id,
                    customer_name=(
                        customer.full_name if customer is not None else None
                    ),
                    appointment_id=None,
                    parsed_keyword=None,
                    status=status_label,
                )
            )
        return items

    async def _fetch_consent_records(
        self,
        limit: int,
    ) -> list[InboxItem]:
        """F8: surface standalone STOP/START SMS replies in the inbox.

        Selects rows whose ``consent_method`` is ``text_stop`` or
        ``text_start`` — these are the auto-acknowledged consent flips
        that arrive outside any active campaign or confirmation context
        and are therefore invisible in the other four UNIONed source
        tables. STOP rows render as ``status=opt_out``; START rows as
        ``status=opt_in`` so the triage classifier and filter matcher can
        reason symbolically.
        """
        stmt = (
            select(SmsConsentRecord, Customer)
            .join(
                Customer,
                Customer.id == SmsConsentRecord.customer_id,
                isouter=True,
            )
            .where(SmsConsentRecord.consent_method.in_(("text_stop", "text_start")))
            .order_by(SmsConsentRecord.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items: list[InboxItem] = []
        for row, customer in result.all():
            method = (row.consent_method or "").lower()
            if method == "text_stop":
                status_label = _CONSENT_STATUS_OPT_OUT
                body = "Customer replied STOP — SMS consent withdrawn."
            else:
                status_label = _CONSENT_STATUS_OPT_IN
                body = "Customer replied START — SMS consent re-established."
            triage_status = _classify_triage(
                source_table="consent",
                status=status_label,
                customer_id=row.customer_id,
            )
            items.append(
                InboxItem(
                    id=row.id,
                    source_table="consent",
                    triage_status=triage_status,
                    received_at=row.created_at,
                    body=body,
                    from_phone=row.phone_number,
                    customer_id=row.customer_id,
                    customer_name=(
                        customer.full_name if customer is not None else None
                    ),
                    appointment_id=None,
                    parsed_keyword=None,
                    status=status_label,
                )
            )
        return items
