"""Unit tests for Stripe webhook endpoint and idempotency.

Tests signature verification, duplicate event skipping, event routing,
and HTTP 200 response guarantee.

Validates: Requirements 6.1-6.7, 7.1-7.3, 40.1
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.api.v1.webhooks import StripeWebhookHandler, stripe_webhook

# =============================================================================
# Helpers
# =============================================================================


def _make_stripe_event(
    event_type: str = "checkout.session.completed",
    event_id: str | None = None,
) -> stripe.Event:
    """Build a minimal Stripe Event dict-like object."""
    eid = event_id or f"evt_{uuid4().hex[:24]}"
    data: dict[str, Any] = {
        "id": eid,
        "type": event_type,
        "object": "event",
        "data": {"object": {}},
    }
    return stripe.Event.construct_from(data, key="sk_test")  # type: ignore[no-untyped-call]


# =============================================================================
# StripeWebhookHandler - idempotency / deduplication
# =============================================================================


class TestWebhookIdempotency:
    """Tests for webhook event deduplication."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_duplicate_event_returns_already_processed(self) -> None:
        """Second processing of same event_id is skipped."""
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_stripe_event()

        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = MagicMock()

        result = await handler.handle_event(event)

        assert result == {"status": "already_processed"}
        handler.repo.create_event_record.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_new_event_is_processed(self) -> None:
        """First-time event is processed and recorded."""
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_stripe_event(event_type="invoice.paid")

        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = None
        event_record = MagicMock()
        handler.repo.create_event_record.return_value = event_record

        result = await handler.handle_event(event)

        assert result == {"status": "processed"}
        handler.repo.create_event_record.assert_called_once()
        handler.repo.mark_processed.assert_called_once_with(event_record)
        session.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_duplicate_does_not_mutate_state(self) -> None:
        """Duplicate event causes no writes."""
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_stripe_event()

        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = MagicMock()

        await handler.handle_event(event)

        handler.repo.mark_processed.assert_not_called()
        handler.repo.mark_failed.assert_not_called()
        session.commit.assert_not_called()


# =============================================================================
# Event routing
# =============================================================================


class TestWebhookEventRouting:
    """Tests that events are routed to the correct handler methods."""

    HANDLED_TYPES: ClassVar[list[str]] = [
        "checkout.session.completed",
        "invoice.paid",
        "invoice.payment_failed",
        "invoice.upcoming",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ]

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("event_type", HANDLED_TYPES)
    async def test_known_event_types_are_routed(self, event_type: str) -> None:
        """Each known event type invokes its handler without error."""
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_stripe_event(event_type=event_type)

        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = None
        handler.repo.create_event_record.return_value = MagicMock()

        # Mock checkout handler since it has real logic requiring DB
        handler._handle_checkout_completed = AsyncMock()  # type: ignore[method-assign]

        result = await handler.handle_event(event)

        assert result["status"] == "processed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_event_type_still_processed(self) -> None:
        """Unhandled event types are recorded but not routed."""
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_stripe_event(event_type="unknown.event.type")

        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = None
        handler.repo.create_event_record.return_value = MagicMock()

        result = await handler.handle_event(event)

        assert result["status"] == "processed"


# =============================================================================
# Handler failure path
# =============================================================================


class TestWebhookFailureHandling:
    """Tests for handler failure scenarios."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handler_exception_marks_event_failed(self) -> None:
        """When a handler raises, event is marked failed and status returned."""
        session = AsyncMock()
        handler = StripeWebhookHandler(session)
        event = _make_stripe_event(event_type="checkout.session.completed")

        handler.repo = AsyncMock()
        handler.repo.get_by_stripe_event_id.return_value = None
        event_record = MagicMock()
        handler.repo.create_event_record.return_value = event_record

        # Make the internal handler raise
        handler._handle_checkout_completed = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("boom"),
        )

        result = await handler.handle_event(event)

        assert result["status"] == "failed"
        assert "boom" in result["error"]
        handler.repo.mark_failed.assert_called_once()
        session.commit.assert_called_once()


# =============================================================================
# Endpoint-level tests (signature verification)
# =============================================================================


class TestWebhookEndpointSignature:
    """Tests for the stripe_webhook endpoint signature verification."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_webhook_secret_returns_400(self) -> None:
        """When STRIPE_WEBHOOK_SECRET is empty, return 400."""
        request = AsyncMock()
        request.body = AsyncMock(return_value=b'{"id": "evt_test"}')
        request.headers = {"stripe-signature": "t=123,v1=abc"}

        db = AsyncMock()

        with patch(
            "grins_platform.api.v1.webhooks.StripeSettings",
        ) as mock_settings_cls:
            mock_settings_cls.return_value = MagicMock(stripe_webhook_secret="")
            response = await stripe_webhook(request, db)

        assert response.status_code == 400
        body = json.loads(response.body)
        assert "not configured" in body["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_signature_returns_400(self) -> None:
        """Invalid Stripe signature returns 400."""
        request = AsyncMock()
        request.body = AsyncMock(return_value=b'{"id": "evt_test"}')
        request.headers = {"stripe-signature": "t=123,v1=bad"}

        db = AsyncMock()

        with (
            patch(
                "grins_platform.api.v1.webhooks.StripeSettings",
            ) as mock_settings_cls,
            patch(
                "grins_platform.api.v1.webhooks.stripe.Webhook.construct_event",
                side_effect=stripe.SignatureVerificationError(
                    "bad sig",
                    "t=123,v1=bad",
                ),  # type: ignore[no-untyped-call]
            ),
        ):
            mock_settings_cls.return_value = MagicMock(
                stripe_webhook_secret="whsec_test",
            )
            response = await stripe_webhook(request, db)

        assert response.status_code == 400
        body = json.loads(response.body)
        assert "signature" in body["error"].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_payload_returns_400(self) -> None:
        """Malformed payload returns 400."""
        request = AsyncMock()
        request.body = AsyncMock(return_value=b"not json")
        request.headers = {"stripe-signature": "t=123,v1=abc"}

        db = AsyncMock()

        with (
            patch(
                "grins_platform.api.v1.webhooks.StripeSettings",
            ) as mock_settings_cls,
            patch(
                "grins_platform.api.v1.webhooks.stripe.Webhook.construct_event",
                side_effect=ValueError("bad payload"),
            ),
        ):
            mock_settings_cls.return_value = MagicMock(
                stripe_webhook_secret="whsec_test",
            )
            response = await stripe_webhook(request, db)

        assert response.status_code == 400
        body = json.loads(response.body)
        assert "payload" in body["error"].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_valid_signature_returns_200(self) -> None:
        """Valid signature + successful processing returns 200."""
        event_data = _make_stripe_event()

        request = AsyncMock()
        request.body = AsyncMock(return_value=b'{"id": "evt_ok"}')
        request.headers = {"stripe-signature": "t=123,v1=valid"}

        db = AsyncMock()

        with (
            patch(
                "grins_platform.api.v1.webhooks.StripeSettings",
            ) as mock_settings_cls,
            patch(
                "grins_platform.api.v1.webhooks.stripe.Webhook.construct_event",
                return_value=event_data,
            ),
            patch(
                "grins_platform.api.v1.webhooks.StripeWebhookHandler",
            ) as mock_handler_cls,
        ):
            mock_settings_cls.return_value = MagicMock(
                stripe_webhook_secret="whsec_test",
            )
            mock_handler = AsyncMock()
            mock_handler.handle_event.return_value = {"status": "processed"}
            mock_handler_cls.return_value = mock_handler

            response = await stripe_webhook(request, db)

        assert response.status_code == 200
        body = json.loads(response.body)
        assert body["status"] == "processed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handler_failure_still_returns_200(self) -> None:
        """Even when handler reports failure, endpoint returns 200."""
        event_data = _make_stripe_event()

        request = AsyncMock()
        request.body = AsyncMock(return_value=b'{"id": "evt_fail"}')
        request.headers = {"stripe-signature": "t=123,v1=valid"}

        db = AsyncMock()

        with (
            patch(
                "grins_platform.api.v1.webhooks.StripeSettings",
            ) as mock_settings_cls,
            patch(
                "grins_platform.api.v1.webhooks.stripe.Webhook.construct_event",
                return_value=event_data,
            ),
            patch(
                "grins_platform.api.v1.webhooks.StripeWebhookHandler",
            ) as mock_handler_cls,
        ):
            mock_settings_cls.return_value = MagicMock(
                stripe_webhook_secret="whsec_test",
            )
            mock_handler = AsyncMock()
            mock_handler.handle_event.return_value = {
                "status": "failed",
                "error": "oops",
            }
            mock_handler_cls.return_value = mock_handler

            response = await stripe_webhook(request, db)

        # Must still be 200 per Stripe requirements
        assert response.status_code == 200
