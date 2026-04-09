"""Property-based tests for STOP bookkeeping independence.

Property 12: STOP bookkeeping independence — STOP reply creates
``opted_out`` row; bookkeeping failure does not prevent consent
revocation.

Validates: Requirements 6.2, 6.4
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
    body: str = "STOP"
    provider_sid: str = "MSG_001"
    to_phone: str | None = None
    thread_id: str | None = "SMTabc123"
    conversation_id: str | None = None


def _mock_campaign() -> MagicMock:
    camp = MagicMock()
    camp.id = uuid4()
    camp.poll_options = [{"key": "1", "label": "Week 1"}]
    return camp


def _mock_sent_message(campaign: MagicMock) -> MagicMock:
    msg = MagicMock()
    msg.id = uuid4()
    msg.campaign_id = campaign.id
    msg.customer_id = None
    msg.lead_id = None
    msg.recipient_phone = None
    return msg


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_stop_bodies = st.sampled_from(["STOP", "stop", "Stop", "STOP ", " stop"])
_thread_ids = st.text(min_size=3, max_size=30, alphabet="abcdefSMT0123456789")


# ---------------------------------------------------------------------------
# Property 12: STOP bookkeeping independence
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStopBookkeepingProperty12:
    """Property 12 — STOP reply creates opted_out row; bookkeeping
    failure does not prevent consent revocation."""

    @given(body=_stop_bodies, thread_id=_thread_ids)
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_stop_creates_opted_out_row(
        self,
        body: str,
        thread_id: str,
    ) -> None:
        """Req 6.2: STOP reply correlated to campaign creates opted_out row."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        captured: list[object] = []

        async def _capture(row: object) -> object:
            captured.append(row)
            return row

        svc.repo = MagicMock()
        svc.repo.add = AsyncMock(side_effect=_capture)

        campaign = _mock_campaign()
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)
        inbound = FakeInbound(body=body, thread_id=thread_id)

        with patch.object(svc, "correlate_reply", return_value=corr):
            await svc.record_opt_out_as_response(inbound)  # type: ignore[arg-type]

        assert len(captured) == 1
        row = captured[0]
        assert row.status == "opted_out"
        assert row.campaign_id == campaign.id

    @given(body=_stop_bodies)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_no_thread_id_skips_bookkeeping(self, body: str) -> None:
        """Req 6.3: No thread_id → no bookkeeping row created."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = MagicMock()
        svc.repo.add = AsyncMock()

        inbound = FakeInbound(body=body, thread_id=None)
        await svc.record_opt_out_as_response(inbound)  # type: ignore[arg-type]

        svc.repo.add.assert_not_called()

    @given(body=_stop_bodies, thread_id=_thread_ids)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_no_campaign_match_skips_bookkeeping(
        self,
        body: str,
        thread_id: str,
    ) -> None:
        """Req 6.3: No campaign match → no bookkeeping row."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = MagicMock()
        svc.repo.add = AsyncMock()

        inbound = FakeInbound(body=body, thread_id=thread_id)

        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(),
        ):
            await svc.record_opt_out_as_response(inbound)  # type: ignore[arg-type]

        svc.repo.add.assert_not_called()

    @given(body=_stop_bodies, thread_id=_thread_ids)
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_bookkeeping_failure_does_not_raise(
        self,
        body: str,
        thread_id: str,
    ) -> None:
        """Req 6.4: Bookkeeping failure is swallowed — no exception propagates."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = MagicMock()
        svc.repo.add = AsyncMock(side_effect=RuntimeError("DB down"))

        campaign = _mock_campaign()
        sent_msg = _mock_sent_message(campaign)
        corr = CorrelationResult(campaign=campaign, sent_message=sent_msg)
        inbound = FakeInbound(body=body, thread_id=thread_id)

        with patch.object(svc, "correlate_reply", return_value=corr):
            # Must not raise — failure is swallowed
            await svc.record_opt_out_as_response(inbound)  # type: ignore[arg-type]

    @given(body=_stop_bodies, thread_id=_thread_ids)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_correlate_failure_does_not_raise(
        self,
        body: str,
        thread_id: str,
    ) -> None:
        """Req 6.4: Correlation failure is also swallowed."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = MagicMock()
        svc.repo.add = AsyncMock()

        inbound = FakeInbound(body=body, thread_id=thread_id)

        with patch.object(
            svc,
            "correlate_reply",
            side_effect=RuntimeError("DB down"),
        ):
            # Must not raise
            await svc.record_opt_out_as_response(inbound)  # type: ignore[arg-type]

        svc.repo.add.assert_not_called()
