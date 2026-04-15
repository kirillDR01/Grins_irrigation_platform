"""Property-based tests for thread-based correlation.

Property 5: Thread-based correlation correctness — returns most recent
sent_message with matching ``provider_thread_id`` and
``delivery_status='sent'``; null if none exists.

Validates: Requirements 3.2, 3.3, 3.5, 19.3
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.campaign_response_service import (
    CampaignResponseService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sent_message(
    *,
    thread_id: str | None,
    delivery_status: str,
    campaign_id=None,
    created_at: datetime | None = None,
) -> MagicMock:
    """Build a mock SentMessage."""
    msg = MagicMock()
    msg.id = uuid4()
    msg.provider_thread_id = thread_id
    msg.delivery_status = delivery_status
    msg.campaign_id = campaign_id or uuid4()
    msg.created_at = created_at or datetime.now(timezone.utc)
    msg.customer_id = None
    msg.lead_id = None
    msg.customer = None
    msg.lead = None
    # campaign relationship
    campaign = MagicMock()
    campaign.id = msg.campaign_id
    campaign.poll_options = None
    msg.campaign = campaign
    return msg


def _mock_session_returning(sent_msg: MagicMock | None) -> AsyncMock:
    """Create an AsyncMock session whose execute returns *sent_msg*."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sent_msg
    session.execute.return_value = result_mock
    return session


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_thread_ids = st.text(
    min_size=1,
    max_size=30,
    alphabet=st.characters(categories=["L", "N"]),
)
_statuses = st.sampled_from(
    ["pending", "scheduled", "sent", "delivered", "failed", "cancelled"],
)


# ---------------------------------------------------------------------------
# Property 5: Thread-based correlation correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCorrelationProperty5:
    """Property 5 — correlate_reply returns the most recent sent_message
    with matching provider_thread_id and delivery_status='sent',
    or empty CorrelationResult if none exists.
    """

    @given(thread_id=_thread_ids)
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_matching_sent_message_returns_correlation(
        self,
        thread_id: str,
    ) -> None:
        """When a sent_message with matching thread_id and status='sent'
        exists, correlate_reply returns it."""
        sent_msg = _make_sent_message(
            thread_id=thread_id,
            delivery_status="sent",
        )
        session = _mock_session_returning(sent_msg)
        svc = CampaignResponseService(session)

        result = await svc.correlate_reply(thread_id)

        assert result.sent_message is sent_msg
        assert result.campaign is not None
        assert result.campaign.id == sent_msg.campaign_id

    @given(thread_id=_thread_ids)
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_no_match_returns_empty(
        self,
        thread_id: str,
    ) -> None:
        """When no sent_message matches, returns empty CorrelationResult."""
        session = _mock_session_returning(None)
        svc = CampaignResponseService(session)

        result = await svc.correlate_reply(thread_id)

        assert result.campaign is None
        assert result.sent_message is None

    @given(thread_id=_thread_ids)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_sent_message_without_campaign_id_returns_sent_message(
        self,
        thread_id: str,
    ) -> None:
        """When sent_message exists but has no campaign_id (e.g. an
        appointment-confirmation thread), the matched SentMessage is
        still returned so callers can resolve the real recipient phone.
        Campaign stays ``None``.
        """
        sent_msg = _make_sent_message(
            thread_id=thread_id,
            delivery_status="sent",
        )
        sent_msg.campaign_id = None
        session = _mock_session_returning(sent_msg)
        svc = CampaignResponseService(session)

        result = await svc.correlate_reply(thread_id)

        assert result.campaign is None
        assert result.sent_message is sent_msg

    @given(
        thread_id=_thread_ids,
        count=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_most_recent_wins(
        self,
        thread_id: str,
        count: int,
    ) -> None:
        """The DB query orders by created_at DESC LIMIT 1, so the mock
        simulates returning the most recent. Verify the service trusts
        the DB ordering and returns whatever the query yields."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        # The "most recent" message is what the DB returns (LIMIT 1)
        most_recent = _make_sent_message(
            thread_id=thread_id,
            delivery_status="sent",
            created_at=base + timedelta(hours=count),
        )
        session = _mock_session_returning(most_recent)
        svc = CampaignResponseService(session)

        result = await svc.correlate_reply(thread_id)

        assert result.sent_message is most_recent
        assert result.sent_message.created_at == base + timedelta(hours=count)

    @given(thread_id=_thread_ids)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_result_is_deterministic(
        self,
        thread_id: str,
    ) -> None:
        """Calling correlate_reply twice with same state gives same outcome."""
        sent_msg = _make_sent_message(
            thread_id=thread_id,
            delivery_status="sent",
        )

        # First call
        session1 = _mock_session_returning(sent_msg)
        svc1 = CampaignResponseService(session1)
        r1 = await svc1.correlate_reply(thread_id)

        # Second call (fresh session mock returning same object)
        session2 = _mock_session_returning(sent_msg)
        svc2 = CampaignResponseService(session2)
        r2 = await svc2.correlate_reply(thread_id)

        assert r1.sent_message is r2.sent_message
        assert (r1.campaign is None) == (r2.campaign is None)
