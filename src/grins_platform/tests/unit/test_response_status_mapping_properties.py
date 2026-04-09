"""Property-based tests for response status mapping.

Property 6: Response status mapping — orphan when no campaign,
needs_review when non-poll campaign, parsed/needs_review based on
parser result for poll campaigns.

Validates: Requirements 5.1, 5.2, 5.3, 5.4
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.campaign_response_service import (
    CampaignResponseService,
    CorrelationResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeInbound:
    """Minimal InboundSMS stand-in."""

    from_phone: str = "+16125551234"
    body: str = ""
    provider_sid: str = "MSG_001"
    to_phone: str | None = None
    thread_id: str | None = "SMTabc123"
    conversation_id: str | None = None


def _mock_campaign(*, poll_options: list[dict[str, str]] | None) -> MagicMock:
    camp = MagicMock()
    camp.id = uuid4()
    camp.poll_options = poll_options
    return camp


def _mock_sent_message(campaign: MagicMock) -> MagicMock:
    msg = MagicMock()
    msg.id = uuid4()
    msg.campaign_id = campaign.id
    msg.customer_id = None
    msg.lead_id = None
    msg.customer = None
    msg.lead = None
    return msg


def _make_options(count: int) -> list[dict[str, str]]:
    return [{"key": str(i), "label": f"Week {i}"} for i in range(1, count + 1)]


def _make_service() -> tuple[CampaignResponseService, AsyncMock]:
    session = AsyncMock()
    svc = CampaignResponseService(session)
    # Stub repo.add to return its argument
    svc.repo = MagicMock()
    svc.repo.add = AsyncMock(side_effect=lambda row: row)
    return svc, session


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_valid_bodies = st.sampled_from(["1", "2", "3", " 2 ", "Option 1", "OPTION 3"])
_invalid_bodies = st.sampled_from(["hello", "yes", "2 or 3", "abc", "next week", ""])
_option_counts = st.integers(min_value=2, max_value=5)


# ---------------------------------------------------------------------------
# Property 6: Response status mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResponseStatusMapping:
    """Property 6 — status is determined by correlation + parse outcome."""

    @given(body=st.text(min_size=0, max_size=30))
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_orphan_when_no_campaign(self, body: str) -> None:
        """Req 5.1: No matching campaign → status='orphan'."""
        svc, _ = _make_service()
        inbound = FakeInbound(body=body or "x")

        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(),
        ):
            row = await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        assert row.status == "orphan"
        assert row.campaign_id is None

    @given(body=st.text(min_size=1, max_size=30))
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_needs_review_when_non_poll_campaign(self, body: str) -> None:
        """Req 5.2: Campaign with null poll_options → status='needs_review'."""
        svc, _ = _make_service()
        campaign = _mock_campaign(poll_options=None)
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)
        inbound = FakeInbound(body=body)

        with patch.object(svc, "correlate_reply", return_value=corr):
            row = await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        assert row.status == "needs_review"
        assert row.campaign_id == campaign.id

    @given(count=_option_counts)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_parsed_when_valid_digit(self, count: int) -> None:
        """Req 5.3: Poll campaign + valid digit → status='parsed'."""
        svc, _ = _make_service()
        options = _make_options(count)
        campaign = _mock_campaign(poll_options=options)
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)
        # Use key "1" which is always valid for count >= 2
        inbound = FakeInbound(body="1")

        with patch.object(svc, "correlate_reply", return_value=corr):
            row = await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        assert row.status == "parsed"
        assert row.selected_option_key == "1"
        assert row.selected_option_label == "Week 1"

    @given(count=_option_counts, body=_invalid_bodies)
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_needs_review_when_parse_fails(
        self,
        count: int,
        body: str,
    ) -> None:
        """Req 5.4: Poll campaign + unparseable reply → status='needs_review'."""
        svc, _ = _make_service()
        options = _make_options(count)
        campaign = _mock_campaign(poll_options=options)
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)
        inbound = FakeInbound(body=body if body else "unknown")

        with patch.object(svc, "correlate_reply", return_value=corr):
            row = await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        assert row.status == "needs_review"
        assert row.selected_option_key is None

    @given(count=_option_counts)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_raw_reply_body_always_preserved(self, count: int) -> None:
        """Every status path preserves the verbatim raw_reply_body."""
        svc, _ = _make_service()
        options = _make_options(count)
        campaign = _mock_campaign(poll_options=options)
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)
        body = "  1!  "
        inbound = FakeInbound(body=body)

        with patch.object(svc, "correlate_reply", return_value=corr):
            row = await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        assert row.raw_reply_body == body
