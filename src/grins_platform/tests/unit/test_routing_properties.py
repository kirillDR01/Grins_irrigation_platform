"""Property-based tests for poll reply routing.

Property 13: Routing — parsed/needs_review replies don't duplicate to
communications; orphans fall through to handle_webhook.

Validates: Requirements 7.2, 7.3, 7.4
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.sms_service import SMSService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_phones = st.from_regex(r"\+1612555\d{4}", fullmatch=True)
_thread_ids = st.text(min_size=3, max_size=30, alphabet="abcdefSMT0123456789")
# Bodies that won't match STOP/opt-out keywords
_non_stop_bodies = st.sampled_from(["1", "2", "option 3", "hello", "next week"])


# ---------------------------------------------------------------------------
# Property 13: Routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRoutingProperty13:
    """Property 13 — parsed/needs_review replies are NOT written to
    communications table; orphans ARE written to both."""

    @given(phone=_phones, body=_non_stop_bodies, thread_id=_thread_ids)
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_parsed_reply_does_not_call_handle_webhook(
        self,
        phone: str,
        body: str,
        thread_id: str,
    ) -> None:
        """Req 7.2: parsed reply → no communications table write."""
        session = AsyncMock()
        svc = SMSService(session)

        with (
            patch.object(
                svc,
                "_try_poll_reply",
                return_value={
                    "action": "poll_reply",
                    "phone": phone,
                    "status": "parsed",
                    "option_key": "1",
                },
            ) as mock_poll,
            patch.object(svc, "handle_webhook") as mock_webhook,
        ):
            result = await svc.handle_inbound(phone, body, "SID1", thread_id)

        mock_poll.assert_awaited_once()
        mock_webhook.assert_not_awaited()
        assert result["status"] == "parsed"

    @given(phone=_phones, body=_non_stop_bodies, thread_id=_thread_ids)
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_needs_review_reply_does_not_call_handle_webhook(
        self,
        phone: str,
        body: str,
        thread_id: str,
    ) -> None:
        """Req 7.3: needs_review reply → no communications table write."""
        session = AsyncMock()
        svc = SMSService(session)

        with (
            patch.object(
                svc,
                "_try_poll_reply",
                return_value={
                    "action": "poll_reply",
                    "phone": phone,
                    "status": "needs_review",
                    "option_key": None,
                },
            ) as mock_poll,
            patch.object(svc, "handle_webhook") as mock_webhook,
        ):
            result = await svc.handle_inbound(phone, body, "SID1", thread_id)

        mock_poll.assert_awaited_once()
        mock_webhook.assert_not_awaited()
        assert result["status"] == "needs_review"

    @given(phone=_phones, body=_non_stop_bodies, thread_id=_thread_ids)
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_orphan_reply_falls_through_to_handle_webhook(
        self,
        phone: str,
        body: str,
        thread_id: str,
    ) -> None:
        """Req 7.4: orphan reply → falls through to handle_webhook."""
        session = AsyncMock()
        svc = SMSService(session)

        webhook_result = {"action": "forward", "phone": phone, "body": body}

        with (
            patch.object(
                svc,
                "_try_poll_reply",
                return_value=None,
            ) as mock_poll,
            patch.object(
                svc,
                "_try_confirmation_reply",
                return_value=None,
            ),
            patch.object(
                svc,
                "handle_webhook",
                return_value=webhook_result,
            ) as mock_webhook,
        ):
            result = await svc.handle_inbound(phone, body, "SID1", thread_id)

        mock_poll.assert_awaited_once()
        mock_webhook.assert_awaited_once_with(phone, body, "SID1")
        assert result["action"] == "forward"

    @given(phone=_phones, body=_non_stop_bodies)
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_no_thread_id_skips_poll_branch(
        self,
        phone: str,
        body: str,
    ) -> None:
        """No thread_id → poll branch skipped, falls through to handle_webhook."""
        session = AsyncMock()
        svc = SMSService(session)

        webhook_result = {"action": "forward", "phone": phone, "body": body}

        with (
            patch.object(svc, "_try_poll_reply") as mock_poll,
            patch.object(
                svc,
                "handle_webhook",
                return_value=webhook_result,
            ) as mock_webhook,
        ):
            result = await svc.handle_inbound(phone, body, "SID1", thread_id=None)

        mock_poll.assert_not_awaited()
        mock_webhook.assert_awaited_once()
        assert result["action"] == "forward"
