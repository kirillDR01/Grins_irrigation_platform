"""Unit tests for webhook error handling and timezone fix.

Tests that the StripeWebhookHandler properly handles errors during
event processing: rolls back the failed transaction, creates a new
failed event record, and commits successfully.

Validates: Requirements 7.1, 7.2 (BUG #10 fix)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.api.v1.webhooks import StripeWebhookHandler
from grins_platform.repositories.stripe_webhook_event_repository import (
    StripeWebhookEventRepository,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_event(
    event_type: str,
    data_object: dict[str, Any] | None = None,
    event_id: str | None = None,
) -> stripe.Event:
    """Build a Stripe Event with custom data.object."""
    eid = event_id or f"evt_{uuid4().hex[:24]}"
    raw: dict[str, Any] = {
        "id": eid,
        "type": event_type,
        "object": "event",
        "data": {"object": data_object or {}},
    }
    return stripe.Event.construct_from(raw, key="sk_test")  # type: ignore[no-untyped-call]


def _make_handler() -> tuple[StripeWebhookHandler, AsyncMock]:
    """Create handler with mocked session and repo (event already new)."""
    session = AsyncMock()
    handler = StripeWebhookHandler(session)
    handler.repo = AsyncMock()
    handler.repo.get_by_stripe_event_id.return_value = None
    handler.repo.create_event_record.return_value = MagicMock()
    return handler, session


# =============================================================================
# Error handling tests (BUG #10 fix)
# =============================================================================


@pytest.mark.unit
class TestWebhookErrorHandling:
    """Tests for webhook handler error recovery after BUG #10 fix."""

    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerService")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_handler_rollback_on_processing_error(
        self,
        _mock_cust_repo_cls: MagicMock,
        _mock_cust_svc_cls: MagicMock,
        _mock_agr_repo_cls: MagicMock,
        _mock_tier_repo_cls: MagicMock,
        _mock_agr_svc_cls: MagicMock,
        _mock_compliance_cls: MagicMock,
        _mock_job_gen_cls: MagicMock,
        _mock_email_cls: MagicMock,
    ) -> None:
        """When _route_event raises, handler calls session.rollback(),
        creates a new failed event record, and commits successfully."""
        handler, session = _make_handler()
        event = _make_event(
            "checkout.session.completed",
            data_object={"customer_details": {"email": "test@test.com"}},
        )

        # Make _route_event raise to simulate processing failure
        error_msg = "timezone mismatch simulation"
        handler._route_event = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError(error_msg),
        )

        # Create a fresh failed record mock
        failed_record = MagicMock()
        # First call returns the initial pending record,
        # second call (after rollback) returns the failed record
        handler.repo.create_event_record.side_effect = [
            MagicMock(),  # initial pending record
            failed_record,  # re-created after rollback
        ]

        result = await handler.handle_event(event)

        # Verify rollback was called
        session.rollback.assert_awaited_once()

        # Verify a new failed event record was created after rollback
        assert handler.repo.create_event_record.await_count == 2
        second_call = handler.repo.create_event_record.call_args_list[1]
        assert second_call.kwargs["processing_status"] == "failed"
        assert second_call.kwargs["stripe_event_id"] == event["id"]
        assert second_call.kwargs["event_type"] == "checkout.session.completed"

        # Verify error_message was set on the failed record
        assert failed_record.error_message == error_msg

        # Verify processed_at was set with timezone-aware datetime
        assert failed_record.processed_at is not None
        assert failed_record.processed_at.tzinfo is not None

        # Verify commit was called (for the new failed record)
        session.commit.assert_awaited_once()

        # Verify result indicates failure
        assert result["status"] == "failed"
        assert error_msg in result["error"]

    @pytest.mark.asyncio
    async def test_successful_processing_marks_processed(self) -> None:
        """Successful processing calls mark_processed and commits."""
        handler, session = _make_handler()
        event = _make_event("customer.subscription.updated")

        # Make _route_event succeed (no-op)
        handler._route_event = AsyncMock()  # type: ignore[method-assign]

        event_record = MagicMock()
        handler.repo.create_event_record.return_value = event_record

        result = await handler.handle_event(event)

        # Verify mark_processed was called on the event record
        handler.repo.mark_processed.assert_awaited_once_with(event_record)

        # Verify commit was called
        session.commit.assert_awaited_once()

        # Verify no rollback
        session.rollback.assert_not_awaited()

        # Verify result
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_successful_processing_sets_timezone_aware_processed_at(
        self,
    ) -> None:
        """mark_processed sets a timezone-aware datetime on processed_at."""
        handler, session = _make_handler()
        event = _make_event("invoice.paid")

        handler._route_event = AsyncMock()  # type: ignore[method-assign]

        event_record = MagicMock()
        handler.repo.create_event_record.return_value = event_record

        # Use the real mark_processed from the repo class
        real_repo = StripeWebhookEventRepository(session)
        handler.repo.mark_processed = real_repo.mark_processed

        await handler.handle_event(event)

        # Verify processed_at was set with timezone info
        assert event_record.processing_status == "processed"
        assert event_record.processed_at is not None
        assert event_record.processed_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_deduplicate_returns_already_processed(self) -> None:
        """Already-processed events return 'already_processed' status."""
        handler, session = _make_handler()
        event = _make_event("checkout.session.completed")

        # Simulate existing event
        handler.repo.get_by_stripe_event_id.return_value = MagicMock()

        result = await handler.handle_event(event)

        assert result["status"] == "already_processed"
        session.commit.assert_not_awaited()
        session.rollback.assert_not_awaited()
