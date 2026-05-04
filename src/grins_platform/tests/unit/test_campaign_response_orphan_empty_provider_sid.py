"""Bug #4 — empty provider_sid must be coerced to None on orphan insert.

The partial unique index ``ix_campaign_responses_provider_message_id``
excludes ``NULL`` (per Postgres semantics) but treats ``''`` as a
non-null value. Two orphan rows with ``provider_sid=""`` collided on
insert, raised IntegrityError, and poisoned the session — preventing
any subsequent appointment-confirmation logic from running for that
inbound webhook.

Validates: ``.agents/plans/master-plan-run-findings-bug-resolution-2026-05-04.md``
Phase 4 / Task 4.3.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.services.campaign_response_service import (
    CampaignResponseService,
    CorrelationResult,
)
from grins_platform.services.sms.base import InboundSMS

pytestmark = pytest.mark.unit


def _make_inbound(
    provider_sid: str,
    *,
    thread_id: str | None = None,
) -> InboundSMS:
    return InboundSMS(
        from_phone="+19527373312",
        body="Y",
        provider_sid=provider_sid,
        thread_id=thread_id,
    )


def _build_service() -> tuple[CampaignResponseService, AsyncMock]:
    repo = AsyncMock()
    # add() echoes back the row passed in so the test can inspect kwargs.
    repo.add = AsyncMock(side_effect=lambda row: row)
    svc = CampaignResponseService(session=AsyncMock())
    svc.repo = repo
    return svc, repo


class TestOrphanEmptyProviderSidCoercion:
    @pytest.mark.asyncio
    async def test_empty_provider_sid_is_coerced_to_none(self) -> None:
        svc, repo = _build_service()
        # Force the orphan path: no thread_id → no correlation.
        svc.correlate_reply = AsyncMock(return_value=CorrelationResult())  # type: ignore[method-assign]

        await svc.record_poll_reply(_make_inbound(provider_sid=""))

        repo.add.assert_awaited_once()
        inserted = repo.add.await_args.args[0]
        assert inserted.provider_message_id is None
        assert inserted.campaign_id is None

    @pytest.mark.asyncio
    async def test_real_provider_sid_passes_through_unchanged(self) -> None:
        svc, repo = _build_service()
        svc.correlate_reply = AsyncMock(return_value=CorrelationResult())  # type: ignore[method-assign]

        await svc.record_poll_reply(
            _make_inbound(provider_sid="MSG019de95f6f0e78d1ad1a7bb4fd59fc49"),
        )

        inserted = repo.add.await_args.args[0]
        assert inserted.provider_message_id == (
            "MSG019de95f6f0e78d1ad1a7bb4fd59fc49"
        )

    @pytest.mark.asyncio
    async def test_orphan_with_correlated_sent_message_keeps_link(
        self,
    ) -> None:
        """If a sent_message correlated, its id is still threaded through.

        ``record_poll_reply`` only consults ``correlate_reply`` when the
        inbound carries a ``thread_id``; pass one through so the mock
        fires.
        """
        svc, repo = _build_service()
        sent_msg = MagicMock()
        sent_msg.id = "sent-msg-id"
        svc.correlate_reply = AsyncMock(  # type: ignore[method-assign]
            return_value=CorrelationResult(sent_message=sent_msg, campaign=None),
        )

        await svc.record_poll_reply(
            _make_inbound(provider_sid="", thread_id="thread-abc"),
        )

        inserted = repo.add.await_args.args[0]
        assert inserted.provider_message_id is None
        assert inserted.sent_message_id == "sent-msg-id"
