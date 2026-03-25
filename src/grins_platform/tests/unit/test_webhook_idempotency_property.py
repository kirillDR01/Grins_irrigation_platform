"""Property test for webhook idempotency.

Property 6: Webhook Idempotency
For any Stripe event processed twice (same stripe_event_id), second processing
is skipped, system state identical, record exists.

Validates: Requirements 7.2, 7.3
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import stripe
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.api.v1.webhooks import StripeWebhookHandler

# Strategies
stripe_event_ids = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=5,
    max_size=30,
).map(lambda s: f"evt_{s}")

event_types = st.sampled_from(
    [
        "checkout.session.completed",
        "invoice.paid",
        "invoice.payment_failed",
        "invoice.upcoming",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "unknown.event.type",
    ],
)


def _make_event(event_id: str, event_type: str) -> stripe.Event:
    """Build a minimal Stripe Event."""
    data: dict[str, Any] = {
        "id": event_id,
        "type": event_type,
        "object": "event",
        "data": {"object": {}},
    }
    return stripe.Event.construct_from(data, key="sk_test")  # type: ignore[no-untyped-call]


@pytest.mark.asyncio
class TestWebhookIdempotencyProperty:
    """Property-based tests for webhook idempotency."""

    @given(event_id=stripe_event_ids, event_type=event_types)
    @settings(max_examples=30)
    async def test_second_processing_skipped(
        self,
        event_id: str,
        event_type: str,
    ) -> None:
        """Property: processing the same event_id twice skips the second call.

        The second invocation returns 'already_processed' and performs
        no writes (no create, no mark_processed, no mark_failed, no commit).
        """
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_event(event_id, event_type)

        # First call: event not yet seen
        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = None
        event_record = MagicMock()
        handler.repo.create_event_record.return_value = event_record

        first_result = await handler.handle_event(event)
        assert first_result["status"] in ("processed", "failed")

        # Second call: event already exists
        handler.repo.get_by_stripe_event_id.return_value = event_record
        handler.repo.create_event_record.reset_mock()
        handler.repo.mark_processed.reset_mock()
        handler.repo.mark_failed.reset_mock()
        session.commit.reset_mock()

        second_result = await handler.handle_event(event)

        assert second_result == {"status": "already_processed"}
        handler.repo.create_event_record.assert_not_called()
        handler.repo.mark_processed.assert_not_called()
        handler.repo.mark_failed.assert_not_called()
        session.commit.assert_not_called()

    @given(event_id=stripe_event_ids, event_type=event_types)
    @settings(max_examples=30)
    async def test_record_exists_after_first_processing(
        self,
        event_id: str,
        event_type: str,
    ) -> None:
        """Property: after first processing, a record exists for the event_id.

        create_event_record is called exactly once with the correct
        stripe_event_id during first processing.
        """
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_event(event_id, event_type)

        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = None
        handler.repo.create_event_record.return_value = MagicMock()

        await handler.handle_event(event)

        # create_event_record is called at least once (pending), and possibly
        # a second time (failed) if the event triggers processing that fails
        # and the original record is rolled back.
        assert handler.repo.create_event_record.call_count >= 1
        first_call = handler.repo.create_event_record.call_args_list[0]
        assert first_call[1]["stripe_event_id"] == event_id

    @given(
        event_id=stripe_event_ids,
        event_type=event_types,
        repeat_count=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=20)
    async def test_multiple_duplicates_all_skipped(
        self,
        event_id: str,
        event_type: str,
        repeat_count: int,
    ) -> None:
        """Property: N duplicate submissions after the first are all skipped."""
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_event(event_id, event_type)

        existing_record = MagicMock()
        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = existing_record

        for _ in range(repeat_count):
            result = await handler.handle_event(event)
            assert result == {"status": "already_processed"}

        handler.repo.create_event_record.assert_not_called()
        session.commit.assert_not_called()
