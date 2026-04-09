"""Campaign response service for poll reply processing.

Handles inbound reply correlation, parsing, recording, summarization,
and CSV export for scheduling poll campaigns.

Validates: Scheduling Poll Req 3.1-3.6, 4.1-4.7, 5.1-5.6, 6.1-6.4,
           16.1-16.5
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.campaign_response import CampaignResponse
from grins_platform.models.sent_message import SentMessage
from grins_platform.repositories.campaign_response_repository import (
    CampaignResponseRepository,
)
from grins_platform.schemas.campaign_response import (
    CampaignResponseBucket,
    CampaignResponseCsvRow,
    CampaignResponseSummary,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.campaign import Campaign
    from grins_platform.services.sms.base import InboundSMS


def _mask_phone(phone: str) -> str:
    """Mask phone for logging: +1XXX***XXXX."""
    if len(phone) >= 10:
        return phone[:4] + "***" + phone[-4:]
    return "***"


# Regex to strip trailing punctuation from reply body
_STRIP_PUNCT_RE = re.compile(r"^[\s.,!?)]+|[\s.,!?)]+$")

# Pattern for "Option N" format (case-insensitive)
_OPTION_N_RE = re.compile(r"^option\s+(\d)$", re.IGNORECASE)


@dataclass(frozen=True)
class CorrelationResult:
    """Result of correlating an inbound SMS to a campaign."""

    campaign: Campaign | None = field(default=None)
    sent_message: SentMessage | None = field(default=None)


@dataclass(frozen=True)
class ParseResult:
    """Result of parsing a poll reply body."""

    ok: bool
    option_key: str | None = None
    option_label: str | None = None


class CampaignResponseService(LoggerMixin):
    """Service for processing inbound poll replies.

    Validates: Scheduling Poll Req 3-7, 16
    """

    DOMAIN = "campaign_response"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session
        self.repo = CampaignResponseRepository(session)

    # ------------------------------------------------------------------
    # Correlation
    # ------------------------------------------------------------------

    async def correlate_reply(
        self,
        thread_resource_id: str,
    ) -> CorrelationResult:
        """Match inbound SMS to a campaign via thread_resource_id.

        Queries ``sent_messages WHERE provider_thread_id = :thread_id
        AND delivery_status = 'sent' ORDER BY created_at DESC LIMIT 1``.

        Validates: Req 3.1, 3.2, 3.3, 3.4, 3.5
        """
        self.log_started(
            "correlate_reply",
            thread_resource_id=thread_resource_id,
        )

        stmt = (
            select(SentMessage)
            .where(
                SentMessage.provider_thread_id == thread_resource_id,
                SentMessage.delivery_status == "sent",
            )
            .order_by(SentMessage.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        sent_msg: SentMessage | None = result.scalar_one_or_none()

        if sent_msg is None or sent_msg.campaign_id is None:
            self.log_completed("correlate_reply", matched=False)
            return CorrelationResult()

        # Eagerly load the campaign relationship
        campaign: Campaign | None = sent_msg.campaign  # type: ignore[assignment]
        if campaign is None:
            # Fallback: load campaign explicitly
            from grins_platform.models.campaign import (  # noqa: PLC0415
                Campaign as CampaignModel,
            )

            camp_result = await self.session.execute(
                select(CampaignModel).where(
                    CampaignModel.id == sent_msg.campaign_id,
                ),
            )
            campaign = camp_result.scalar_one_or_none()

        self.log_completed(
            "correlate_reply",
            matched=True,
            campaign_id=str(campaign.id) if campaign else None,
        )
        return CorrelationResult(campaign=campaign, sent_message=sent_msg)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_poll_reply(
        body: str,
        poll_options: list[dict[str, Any]],
    ) -> ParseResult:
        """Parse reply text into an option selection.

        Rules:
        1. Strip whitespace + punctuation (. , ! ) )
        2. Single digit 1-5 matching a valid key → parsed
        3. "option N" (case-insensitive) with valid digit → parsed
        4. Everything else → needs_review

        Validates: Req 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
        """
        cleaned = _STRIP_PUNCT_RE.sub("", body)

        # Build lookup of valid keys → labels
        valid_keys: dict[str, str] = {
            str(opt["key"]): str(opt.get("label", "")) for opt in poll_options
        }

        # Try single digit match
        if len(cleaned) == 1 and cleaned.isdigit():
            if cleaned in valid_keys:
                return ParseResult(
                    ok=True,
                    option_key=cleaned,
                    option_label=valid_keys[cleaned],
                )
            # Digit but out of range
            return ParseResult(ok=False)

        # Try "Option N" pattern
        m = _OPTION_N_RE.match(cleaned)
        if m:
            digit = m.group(1)
            if digit in valid_keys:
                return ParseResult(
                    ok=True,
                    option_key=digit,
                    option_label=valid_keys[digit],
                )
            return ParseResult(ok=False)

        # Unrecognized
        return ParseResult(ok=False)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    async def record_poll_reply(
        self,
        inbound: InboundSMS,
    ) -> CampaignResponse:
        """Orchestrate correlation → parsing → snapshot → insert.

        Validates: Req 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 7.1
        """
        self.log_started(
            "record_poll_reply",
            phone_masked=_mask_phone(inbound.from_phone),
        )

        now = datetime.now(timezone.utc)

        # Correlate
        if inbound.thread_id:
            corr = await self.correlate_reply(inbound.thread_id)
        else:
            corr = CorrelationResult()

        # No campaign found → orphan
        if corr.campaign is None:
            self.logger.info(
                "campaign.response.orphan",
                phone_masked=_mask_phone(inbound.from_phone),
                thread_id=inbound.thread_id,
            )
            row = await self.repo.add(
                CampaignResponse(
                    campaign_id=None,
                    sent_message_id=(
                        corr.sent_message.id if corr.sent_message else None
                    ),
                    phone=inbound.from_phone,
                    raw_reply_body=inbound.body,
                    provider_message_id=inbound.provider_sid,
                    status="orphan",
                    received_at=now,
                ),
            )
            self.log_completed("record_poll_reply", status="orphan")
            return row

        campaign = corr.campaign
        sent_msg = corr.sent_message

        # Emit correlated event (Req 16.2)
        self.logger.info(
            "campaign.response.correlated",
            phone_masked=_mask_phone(inbound.from_phone),
            campaign_id=str(campaign.id),
            sent_message_id=str(sent_msg.id) if sent_msg else None,
            thread_resource_id=inbound.thread_id,
        )

        # Snapshot recipient info from sent_message relationships
        customer_id = sent_msg.customer_id if sent_msg else None
        lead_id = sent_msg.lead_id if sent_msg else None
        recipient_name: str | None = None
        recipient_address: str | None = None

        if sent_msg and sent_msg.customer:
            c = sent_msg.customer
            first = getattr(c, "first_name", "") or ""
            last = getattr(c, "last_name", "") or ""
            recipient_name = f"{first} {last}".strip() or None
        elif sent_msg and sent_msg.lead:
            lead = sent_msg.lead
            recipient_name = getattr(lead, "name", None)
            recipient_address = getattr(lead, "address", None)

        # Campaign has no poll_options → needs_review
        if not campaign.poll_options:
            self.logger.info(
                "campaign.response.received",
                phone_masked=_mask_phone(inbound.from_phone),
                campaign_id=str(campaign.id),
                status="needs_review",
                reason="no_poll_options",
            )
            row = await self.repo.add(
                CampaignResponse(
                    campaign_id=campaign.id,
                    sent_message_id=sent_msg.id if sent_msg else None,
                    customer_id=customer_id,
                    lead_id=lead_id,
                    phone=inbound.from_phone,
                    recipient_name=recipient_name,
                    recipient_address=recipient_address,
                    raw_reply_body=inbound.body,
                    provider_message_id=inbound.provider_sid,
                    status="needs_review",
                    received_at=now,
                ),
            )
            self.log_completed("record_poll_reply", status="needs_review")
            return row

        # Parse the reply
        parse = self.parse_poll_reply(inbound.body, campaign.poll_options)

        if parse.ok:
            status = "parsed"
            self.logger.info(
                "campaign.response.received",
                phone_masked=_mask_phone(inbound.from_phone),
                campaign_id=str(campaign.id),
                status="parsed",
                option_key=parse.option_key,
            )
        else:
            status = "needs_review"
            self.logger.info(
                "campaign.response.parse_failed",
                phone_masked=_mask_phone(inbound.from_phone),
                campaign_id=str(campaign.id),
                reply_preview=inbound.body[:40],
            )

        row = await self.repo.add(
            CampaignResponse(
                campaign_id=campaign.id,
                sent_message_id=sent_msg.id if sent_msg else None,
                customer_id=customer_id,
                lead_id=lead_id,
                phone=inbound.from_phone,
                recipient_name=recipient_name,
                recipient_address=recipient_address,
                selected_option_key=parse.option_key if parse.ok else None,
                selected_option_label=parse.option_label if parse.ok else None,
                raw_reply_body=inbound.body,
                provider_message_id=inbound.provider_sid,
                status=status,
                received_at=now,
            ),
        )
        self.log_completed("record_poll_reply", status=status)
        return row

    async def record_opt_out_as_response(
        self,
        inbound: InboundSMS,
    ) -> None:
        """Record a STOP reply as a campaign_responses bookkeeping row.

        Independent operation — failure here does not block consent revocation.

        Validates: Req 6.1, 6.2, 6.3, 6.4
        """
        if not inbound.thread_id:
            return

        try:
            corr = await self.correlate_reply(inbound.thread_id)
            if corr.campaign is None:
                return

            sent_msg = corr.sent_message
            now = datetime.now(timezone.utc)

            await self.repo.add(
                CampaignResponse(
                    campaign_id=corr.campaign.id,
                    sent_message_id=sent_msg.id if sent_msg else None,
                    customer_id=sent_msg.customer_id if sent_msg else None,
                    lead_id=sent_msg.lead_id if sent_msg else None,
                    phone=inbound.from_phone,
                    raw_reply_body=inbound.body,
                    provider_message_id=inbound.provider_sid,
                    status="opted_out",
                    received_at=now,
                ),
            )
            self.logger.info(
                "campaign.response.received",
                phone_masked=_mask_phone(inbound.from_phone),
                campaign_id=str(corr.campaign.id),
                status="opted_out",
            )
        except Exception:
            # Bookkeeping failure must not block consent revocation
            self.logger.warning(
                "campaign.response.opt_out_bookkeeping_failed",
                phone_masked=_mask_phone(inbound.from_phone),
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    async def get_response_summary(
        self,
        campaign_id: UUID,
    ) -> CampaignResponseSummary:
        """Return per-option bucket counts using latest-wins query.

        Validates: Req 9.1, 9.2, 9.3
        """
        self.log_started("get_response_summary", campaign_id=str(campaign_id))

        counts = await self.repo.count_by_status_and_option(campaign_id)

        buckets: list[CampaignResponseBucket] = []
        total_replied = 0
        for row in counts:
            cnt = int(row["count"])  # type: ignore[call-overload]
            total_replied += cnt
            buckets.append(
                CampaignResponseBucket(
                    option_key=row["option_key"],  # type: ignore[arg-type]
                    status=str(row["status"]),
                    count=cnt,
                ),
            )

        # Get total_sent from campaign recipients (count sent_messages)
        from sqlalchemy import func as sa_func  # noqa: PLC0415

        sent_result = await self.session.execute(
            select(sa_func.count()).where(
                SentMessage.campaign_id == campaign_id,
                SentMessage.delivery_status == "sent",
            ),
        )
        total_sent: int = sent_result.scalar() or 0

        summary = CampaignResponseSummary(
            campaign_id=campaign_id,
            total_sent=total_sent,
            total_replied=total_replied,
            buckets=buckets,
        )
        self.log_completed(
            "get_response_summary",
            total_sent=total_sent,
            total_replied=total_replied,
        )
        return summary

    # ------------------------------------------------------------------
    # CSV Export
    # ------------------------------------------------------------------

    async def iter_csv_rows(
        self,
        campaign_id: UUID,
        option_key: str | None = None,
    ) -> AsyncIterator[CampaignResponseCsvRow]:
        """Stream CSV rows with name split logic.

        Splits ``recipient_name`` on first whitespace into first/last.

        Validates: Req 11.2, 11.3, 11.4, 11.7
        """
        self.log_started("iter_csv_rows", campaign_id=str(campaign_id))

        count = 0
        async for row in self.repo.iter_for_export(campaign_id, option_key):
            first_name, last_name = _split_name(row.recipient_name)
            count += 1
            yield CampaignResponseCsvRow(
                first_name=first_name,
                last_name=last_name,
                phone=row.phone,
                selected_option_label=row.selected_option_label or "",
                raw_reply=row.raw_reply_body,
                received_at=(row.received_at.isoformat() if row.received_at else ""),
            )

        self.log_completed("iter_csv_rows", count=count)


def _split_name(name: str | None) -> tuple[str, str]:
    """Split a name on first whitespace into (first, last).

    Single token → (token, ""). None/empty → ("", "").
    """
    if not name:
        return ("", "")
    parts = name.split(None, 1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])
