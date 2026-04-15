"""Property-based tests for audit trail and raw body preservation.

Property 7: Append-only audit trail with raw body preservation —
N replies produce N rows, each with verbatim ``raw_reply_body``,
no rows deleted or updated.

Validates: Requirements 2.5, 5.6, 8.1, 8.4
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from grins_platform.models.campaign_response import CampaignResponse

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


def _make_options(count: int) -> list[dict[str, str]]:
    return [{"key": str(i), "label": f"Week {i}"} for i in range(1, count + 1)]


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
    msg.recipient_phone = None  # real phone resolved from Customer/Lead
    return msg


def _make_service() -> tuple[CampaignResponseService, list[CampaignResponse]]:
    """Return a service whose repo.add appends to a captured list."""
    session = AsyncMock()
    svc = CampaignResponseService(session)
    captured: list[CampaignResponse] = []

    async def _capture(row: CampaignResponse) -> CampaignResponse:
        captured.append(row)
        return row

    svc.repo = MagicMock()
    svc.repo.add = AsyncMock(side_effect=_capture)
    return svc, captured


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_reply_bodies = st.text(min_size=1, max_size=100)
_option_counts = st.integers(min_value=2, max_value=5)


# ---------------------------------------------------------------------------
# Property 7: Append-only audit trail with raw body preservation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditTrailProperty7:
    """Property 7 — N replies produce N rows, each with verbatim
    raw_reply_body, no rows deleted or updated."""

    @given(
        bodies=st.lists(_reply_bodies, min_size=1, max_size=10),
        count=_option_counts,
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_n_replies_produce_n_rows(
        self,
        bodies: list[str],
        count: int,
    ) -> None:
        """Req 5.6, 8.1: Each inbound reply inserts a new row."""
        svc, captured = _make_service()
        options = _make_options(count)
        campaign = _mock_campaign(poll_options=options)
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)

        with patch.object(svc, "correlate_reply", return_value=corr):
            for body in bodies:
                inbound = FakeInbound(body=body)
                await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        assert len(captured) == len(bodies)

    @given(
        bodies=st.lists(_reply_bodies, min_size=1, max_size=10),
        count=_option_counts,
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_raw_reply_body_preserved_verbatim(
        self,
        bodies: list[str],
        count: int,
    ) -> None:
        """Req 2.5: raw_reply_body stores the verbatim inbound text."""
        svc, captured = _make_service()
        options = _make_options(count)
        campaign = _mock_campaign(poll_options=options)
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)

        with patch.object(svc, "correlate_reply", return_value=corr):
            for body in bodies:
                inbound = FakeInbound(body=body)
                await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        for i, row in enumerate(captured):
            assert row.raw_reply_body == bodies[i]

    @given(count=_option_counts)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_duplicate_replies_all_stored(
        self,
        count: int,
    ) -> None:
        """Req 8.1, 8.4: Duplicate replies from same phone each produce
        a separate row — no upsert or delete."""
        svc, captured = _make_service()
        options = _make_options(count)
        campaign = _mock_campaign(poll_options=options)
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)
        body = "1"

        with patch.object(svc, "correlate_reply", return_value=corr):
            for _ in range(3):
                inbound = FakeInbound(body=body, from_phone="+16125559999")
                await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        assert len(captured) == 3
        for row in captured:
            assert row.raw_reply_body == body
            assert row.phone == "+16125559999"

    @given(
        bodies=st.lists(_reply_bodies, min_size=1, max_size=10),
        count=_option_counts,
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_repo_add_called_not_update_or_delete(
        self,
        bodies: list[str],
        count: int,
    ) -> None:
        """Req 8.1: Only repo.add is called — no update/delete methods."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = MagicMock()
        svc.repo.add = AsyncMock(side_effect=lambda row: row)

        options = _make_options(count)
        campaign = _mock_campaign(poll_options=options)
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)

        with patch.object(svc, "correlate_reply", return_value=corr):
            for body in bodies:
                inbound = FakeInbound(body=body)
                await svc.record_poll_reply(inbound)  # type: ignore[arg-type]

        assert svc.repo.add.call_count == len(bodies)
        # Verify no update/delete methods were called on the repo
        for attr in ("update", "delete", "remove", "upsert"):
            method = getattr(svc.repo, attr, None)
            if method is not None:
                method.assert_not_called()
