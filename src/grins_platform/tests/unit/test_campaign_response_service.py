"""Unit tests for CampaignResponseService.

Parametrized parser tests, correlator tests, and recorder tests.

Validates: Requirements 17.1, 17.2, 17.3
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.services.campaign_response_service import (
    CampaignResponseService,
    CorrelationResult,
)
from grins_platform.services.sms.base import InboundSMS

# =============================================================================
# Helpers
# =============================================================================

_POLL_OPTIONS: list[dict[str, str]] = [
    {"key": "1", "label": "Week of Apr 6"},
    {"key": "2", "label": "Week of Apr 13"},
    {"key": "3", "label": "Week of Apr 20"},
]


def _make_inbound(
    body: str = "1",
    thread_id: str | None = "thread-abc",
    from_phone: str = "+16125551234",
    provider_sid: str = "msg-xyz",
) -> InboundSMS:
    return InboundSMS(
        from_phone=from_phone,
        body=body,
        provider_sid=provider_sid,
        thread_id=thread_id,
    )


def _make_sent_message(
    *,
    campaign_id: Any | None = None,
    delivery_status: str = "sent",
    customer_id: Any | None = None,
    lead_id: Any | None = None,
    recipient_phone: str | None = None,
) -> MagicMock:
    msg = MagicMock()
    msg.id = uuid4()
    msg.campaign_id = campaign_id or uuid4()
    msg.delivery_status = delivery_status
    msg.customer_id = customer_id
    msg.lead_id = lead_id
    msg.customer = None
    msg.lead = None
    msg.recipient_phone = recipient_phone
    msg.created_at = datetime.now(timezone.utc)
    return msg


def _make_campaign(
    *,
    poll_options: list[dict[str, Any]] | None = None,
) -> MagicMock:
    c = MagicMock()
    c.id = uuid4()
    c.poll_options = poll_options
    return c


# =============================================================================
# parse_poll_reply — parametrized
# =============================================================================


@pytest.mark.unit
class TestParsePollReply:
    """Parametrized unit tests for the reply parser."""

    @pytest.mark.parametrize(
        ("body", "expected_key"),
        [
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
        ],
    )
    def test_valid_digits(self, body: str, expected_key: str) -> None:
        result = CampaignResponseService.parse_poll_reply(body, _POLL_OPTIONS)
        assert result.ok is True
        assert result.option_key == expected_key

    @pytest.mark.parametrize(
        "body",
        [
            " 1 ",
            "  2  ",
            "\t3\t",
            "\n1\n",
            "1.",
            "2!",
            "3?",
            " 1! ",
            "  2.  ",
        ],
    )
    def test_whitespace_and_punctuation_stripped(self, body: str) -> None:
        result = CampaignResponseService.parse_poll_reply(body, _POLL_OPTIONS)
        assert result.ok is True
        assert result.option_key is not None

    @pytest.mark.parametrize(
        ("body", "expected_key"),
        [
            ("Option 1", "1"),
            ("option 2", "2"),
            ("OPTION 3", "3"),
            ("Option  1", "1"),  # double space — \s+ matches
            (" Option 2 ", "2"),
        ],
    )
    def test_option_n_format(self, body: str, expected_key: str | None) -> None:
        result = CampaignResponseService.parse_poll_reply(body, _POLL_OPTIONS)
        if expected_key is not None:
            assert result.ok is True
            assert result.option_key == expected_key
        else:
            assert result.ok is False

    @pytest.mark.parametrize(
        "body",
        [
            "4",  # out of range (only 3 options)
            "5",
            "0",
            "9",
        ],
    )
    def test_out_of_range_digit(self, body: str) -> None:
        result = CampaignResponseService.parse_poll_reply(body, _POLL_OPTIONS)
        assert result.ok is False

    @pytest.mark.parametrize(
        "body",
        [
            "",
            "hello",
            "yes",
            "no",
            "abc",
            "12",
            "one",
            "two",
            "first",
        ],
    )
    def test_unrecognized_input(self, body: str) -> None:
        result = CampaignResponseService.parse_poll_reply(body, _POLL_OPTIONS)
        assert result.ok is False

    @pytest.mark.parametrize(
        "body",
        [
            "\u0661",  # Arabic-Indic digit 1
            "\u0662",  # Arabic-Indic digit 2
            "\uff11",  # Fullwidth digit 1
        ],
    )
    def test_unicode_digits_rejected(self, body: str) -> None:
        """Non-ASCII digits are not recognized."""
        result = CampaignResponseService.parse_poll_reply(body, _POLL_OPTIONS)
        assert result.ok is False

    def test_spelled_out_numbers_rejected(self) -> None:
        for word in ("one", "two", "three"):
            result = CampaignResponseService.parse_poll_reply(word, _POLL_OPTIONS)
            assert result.ok is False

    def test_ambiguous_multi_digit_rejected(self) -> None:
        result = CampaignResponseService.parse_poll_reply("12", _POLL_OPTIONS)
        assert result.ok is False

    def test_parsed_result_includes_label(self) -> None:
        result = CampaignResponseService.parse_poll_reply("2", _POLL_OPTIONS)
        assert result.ok is True
        assert result.option_label == "Week of Apr 13"


# =============================================================================
# correlate_reply
# =============================================================================


@pytest.mark.unit
class TestCorrelateReply:
    """Unit tests for thread-based correlation."""

    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        """Matching sent_message with campaign returns both."""
        campaign = _make_campaign(poll_options=_POLL_OPTIONS)
        sent_msg = _make_sent_message(campaign_id=campaign.id)
        sent_msg.campaign = campaign

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sent_msg
        session.execute.return_value = mock_result

        svc = CampaignResponseService(session)
        corr = await svc.correlate_reply("thread-abc")

        assert corr.campaign is campaign
        assert corr.sent_message is sent_msg

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self) -> None:
        """No matching sent_message returns empty CorrelationResult."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        svc = CampaignResponseService(session)
        corr = await svc.correlate_reply("thread-missing")

        assert corr.campaign is None
        assert corr.sent_message is None

    @pytest.mark.asyncio
    async def test_sent_message_without_campaign_id_returns_empty(self) -> None:
        """sent_message with campaign_id=None returns empty."""
        sent_msg = _make_sent_message()
        sent_msg.campaign_id = None

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sent_msg
        session.execute.return_value = mock_result

        svc = CampaignResponseService(session)
        corr = await svc.correlate_reply("thread-no-campaign")

        assert corr.campaign is None
        assert corr.sent_message is None


# =============================================================================
# record_poll_reply
# =============================================================================


@pytest.mark.unit
class TestRecordPollReply:
    """Unit tests for the full record_poll_reply orchestration."""

    @pytest.mark.asyncio
    async def test_orphan_when_no_thread_id(self) -> None:
        """Inbound with no thread_id produces orphan."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda row: row)

        inbound = _make_inbound(body="1", thread_id=None)
        row = await svc.record_poll_reply(inbound)

        assert row.status == "orphan"
        assert row.campaign_id is None

    @pytest.mark.asyncio
    async def test_orphan_when_no_campaign_found(self) -> None:
        """Inbound with thread_id but no matching campaign → orphan."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda row: row)

        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(),
        ):
            inbound = _make_inbound(body="1")
            row = await svc.record_poll_reply(inbound)

        assert row.status == "orphan"

    @pytest.mark.asyncio
    async def test_needs_review_when_no_poll_options(self) -> None:
        """Campaign without poll_options → needs_review."""
        campaign = _make_campaign(poll_options=None)
        sent_msg = _make_sent_message(campaign_id=campaign.id)

        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda row: row)

        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(campaign=campaign, sent_message=sent_msg),
        ):
            inbound = _make_inbound(body="1")
            row = await svc.record_poll_reply(inbound)

        assert row.status == "needs_review"
        assert row.campaign_id == campaign.id

    @pytest.mark.asyncio
    async def test_parsed_reply(self) -> None:
        """Valid digit reply to poll campaign → parsed with option info."""
        campaign = _make_campaign(poll_options=_POLL_OPTIONS)
        sent_msg = _make_sent_message(campaign_id=campaign.id)

        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda row: row)

        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(campaign=campaign, sent_message=sent_msg),
        ):
            inbound = _make_inbound(body="2")
            row = await svc.record_poll_reply(inbound)

        assert row.status == "parsed"
        assert row.selected_option_key == "2"
        assert row.selected_option_label == "Week of Apr 13"

    @pytest.mark.asyncio
    async def test_needs_review_for_unparseable_reply(self) -> None:
        """Unrecognized reply to poll campaign → needs_review."""
        campaign = _make_campaign(poll_options=_POLL_OPTIONS)
        sent_msg = _make_sent_message(campaign_id=campaign.id)

        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda row: row)

        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(campaign=campaign, sent_message=sent_msg),
        ):
            inbound = _make_inbound(body="hello world")
            row = await svc.record_poll_reply(inbound)

        assert row.status == "needs_review"
        assert row.selected_option_key is None

    @pytest.mark.asyncio
    async def test_raw_reply_body_preserved(self) -> None:
        """raw_reply_body is stored verbatim."""
        campaign = _make_campaign(poll_options=_POLL_OPTIONS)
        sent_msg = _make_sent_message(campaign_id=campaign.id)

        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda row: row)

        raw = "  2!  "
        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(campaign=campaign, sent_message=sent_msg),
        ):
            inbound = _make_inbound(body=raw)
            row = await svc.record_poll_reply(inbound)

        assert row.raw_reply_body == raw

    @pytest.mark.asyncio
    async def test_stop_bookkeeping_independent(self) -> None:
        """record_opt_out_as_response failure doesn't raise."""
        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=RuntimeError("db error"))

        # Should not raise even though repo.add fails
        inbound = _make_inbound(body="STOP", thread_id="thread-abc")

        # Mock correlate to return a campaign
        campaign = _make_campaign()
        sent_msg = _make_sent_message(campaign_id=campaign.id)
        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(campaign=campaign, sent_message=sent_msg),
        ):
            await svc.record_opt_out_as_response(inbound)
            # No exception raised — bookkeeping failure is swallowed

    @pytest.mark.asyncio
    async def test_customer_snapshot_populated(self) -> None:
        """When sent_message has a customer, recipient_name is populated."""
        campaign = _make_campaign(poll_options=_POLL_OPTIONS)
        sent_msg = _make_sent_message(campaign_id=campaign.id)
        customer = MagicMock()
        customer.first_name = "Jane"
        customer.last_name = "Doe"
        sent_msg.customer = customer
        sent_msg.customer_id = uuid4()
        sent_msg.lead = None
        sent_msg.lead_id = None

        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda row: row)

        with patch.object(
            svc,
            "correlate_reply",
            return_value=CorrelationResult(campaign=campaign, sent_message=sent_msg),
        ):
            inbound = _make_inbound(body="1")
            row = await svc.record_poll_reply(inbound)

        assert row.recipient_name == "Jane Doe"


# =============================================================================
# Bug 1 — SentMessage.campaign relationship exists
# =============================================================================


@pytest.mark.unit
def test_sent_message_model_has_campaign_relationship() -> None:
    from sqlalchemy import inspect

    from grins_platform.models.sent_message import SentMessage

    mapper = inspect(SentMessage)
    rel_names = [r.key for r in mapper.relationships]
    assert "campaign" in rel_names


# =============================================================================
# Bug 4 — Broader punctuation stripping
# =============================================================================


@pytest.mark.unit
class TestCommonSmsPunctuationStripped:
    """Ensure common SMS punctuation wrappers are stripped before parsing."""

    @pytest.mark.parametrize(
        ("body", "expected_key"),
        [
            ("(1)", "1"),
            ('"1"', "1"),
            ("'2'", "2"),
            ("#3", "3"),
            ("1:", "1"),
            ("-2-", "2"),
            ("#3;", "3"),
            ("(Option 1)", "1"),
        ],
    )
    def test_common_sms_punctuation_stripped(
        self, body: str, expected_key: str
    ) -> None:
        result = CampaignResponseService.parse_poll_reply(body, _POLL_OPTIONS)
        assert result.ok is True
        assert result.option_key == expected_key


# =============================================================================
# Bug 6 — total_replied excludes opted_out/orphan
# =============================================================================


@pytest.mark.unit
class TestTotalRepliedExcludesOptedOutOrphan:
    """total_replied should only sum parsed + needs_review buckets."""

    @pytest.mark.asyncio
    async def test_total_replied_excludes_opted_out_and_orphan(self) -> None:
        campaign_id = uuid4()

        # Mock count_by_status_and_option to return all 4 statuses
        mock_counts = [
            {"status": "parsed", "option_key": "1", "count": 5},
            {"status": "needs_review", "option_key": None, "count": 2},
            {"status": "opted_out", "option_key": None, "count": 3},
            {"status": "orphan", "option_key": None, "count": 1},
        ]

        session = AsyncMock()
        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.count_by_status_and_option = AsyncMock(return_value=mock_counts)

        # Mock the campaign poll_options lookup
        mock_camp_result = MagicMock()
        mock_camp_result.scalar_one_or_none.return_value = [
            {"key": "1", "label": "Week of Apr 6"},
        ]
        # Mock the total_sent count
        mock_sent_result = MagicMock()
        mock_sent_result.scalar.return_value = 10

        session.execute = AsyncMock(side_effect=[mock_camp_result, mock_sent_result])

        summary = await svc.get_response_summary(campaign_id)

        # total_replied should be 5 + 2 = 7 (parsed + needs_review only)
        assert summary.total_replied == 7
        # But all 4 buckets should still be present
        assert len(summary.buckets) == 4
