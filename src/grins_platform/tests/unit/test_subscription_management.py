"""Unit tests for subscription management: create_portal_session and manage-subscription endpoint.

Validates: Requirements 2.1, 2.2, 2.3
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from grins_platform.api.v1 import checkout as checkout_module
from grins_platform.services.checkout_service import (
    CheckoutService,
    StripeUnavailableError,
    SubscriptionNotFoundError,
)


@pytest.fixture(autouse=True)
def _reset_checkout_rate_limiter() -> None:
    """Reset the in-memory rate limiter before each test.

    The /checkout/* endpoints share a module-level _rate_store. Without
    resetting, hits from this test file leak into other tests in the same
    suite (e.g. test_integration_gaps_api), causing 429 responses.
    """
    checkout_module._rate_store.clear()

# =============================================================================
# Helpers
# =============================================================================


def _make_stripe_settings() -> MagicMock:
    s = MagicMock()
    s.stripe_secret_key = "sk_test_fake"
    s.stripe_tax_enabled = True
    s.stripe_customer_portal_url = "https://billing.stripe.com/test"
    return s


def _make_checkout_service(
    stripe_settings: MagicMock | None = None,
) -> CheckoutService:
    return CheckoutService(
        session=AsyncMock(),
        tier_repo=AsyncMock(),
        stripe_settings=stripe_settings or _make_stripe_settings(),
    )


# =============================================================================
# CheckoutService.create_portal_session
# =============================================================================


@pytest.mark.unit
class TestCreatePortalSession:
    """Tests for CheckoutService.create_portal_session."""

    @patch("grins_platform.services.checkout_service.stripe")
    async def test_valid_email_returns_portal_url(self, mock_stripe: MagicMock) -> None:
        """A known customer email should return a portal session URL."""
        mock_customer = MagicMock()
        mock_customer.id = "cus_test_123"
        mock_stripe.Customer.list.return_value = SimpleNamespace(data=[mock_customer])

        mock_portal = MagicMock()
        mock_portal.url = "https://billing.stripe.com/session/test_sess"
        mock_stripe.billing_portal.Session.create.return_value = mock_portal

        service = _make_checkout_service()
        url = await service.create_portal_session("subscriber@example.com")

        assert url == "https://billing.stripe.com/session/test_sess"
        mock_stripe.Customer.list.assert_called_once_with(
            email="subscriber@example.com", limit=1,
        )
        mock_stripe.billing_portal.Session.create.assert_called_once_with(
            customer="cus_test_123",
            return_url="https://billing.stripe.com/test",
        )

    @patch("grins_platform.services.checkout_service.stripe")
    async def test_unknown_email_raises_not_found(self, mock_stripe: MagicMock) -> None:
        """An email with no Stripe customer should raise SubscriptionNotFoundError."""
        mock_stripe.Customer.list.return_value = SimpleNamespace(data=[])

        service = _make_checkout_service()
        with pytest.raises(SubscriptionNotFoundError):
            await service.create_portal_session("unknown@example.com")

    @patch("grins_platform.services.checkout_service.stripe")
    async def test_sets_stripe_api_key(self, mock_stripe: MagicMock) -> None:
        """Should set the Stripe API key before making calls."""
        mock_stripe.Customer.list.return_value = SimpleNamespace(data=[])

        service = _make_checkout_service()
        with pytest.raises(SubscriptionNotFoundError):
            await service.create_portal_session("test@example.com")

        assert mock_stripe.api_key == "sk_test_fake"

    @patch("grins_platform.services.checkout_service.stripe")
    async def test_stripe_auth_error_raises_unavailable(
        self,
        mock_stripe: MagicMock,
    ) -> None:
        """Stripe auth/connection errors should be wrapped in StripeUnavailableError.

        Validates BUG-001 fix: previously these errors propagated as raw 500.
        """

        # Simulate stripe.error.StripeError being a real exception type
        class _FakeStripeError(Exception):
            pass

        mock_stripe.error.StripeError = _FakeStripeError
        mock_stripe.Customer.list.side_effect = _FakeStripeError(
            "You did not provide an API key.",
        )

        service = _make_checkout_service()
        with pytest.raises(StripeUnavailableError) as exc_info:
            await service.create_portal_session("anyone@example.com")

        assert "did not provide an API key" in str(exc_info.value)

    @patch("grins_platform.services.checkout_service.stripe")
    async def test_stripe_portal_session_error_raises_unavailable(
        self,
        mock_stripe: MagicMock,
    ) -> None:
        """Stripe errors on billing_portal.Session.create should also be wrapped."""

        class _FakeStripeError(Exception):
            pass

        mock_stripe.error.StripeError = _FakeStripeError

        mock_customer = MagicMock()
        mock_customer.id = "cus_test_123"
        mock_stripe.Customer.list.return_value = SimpleNamespace(data=[mock_customer])
        mock_stripe.billing_portal.Session.create.side_effect = _FakeStripeError(
            "Portal not configured.",
        )

        service = _make_checkout_service()
        with pytest.raises(StripeUnavailableError):
            await service.create_portal_session("subscriber@example.com")

    @patch("grins_platform.services.checkout_service.stripe")
    async def test_empty_portal_url_passes_none(self, mock_stripe: MagicMock) -> None:
        """When stripe_customer_portal_url is empty, return_url should be None."""
        settings = _make_stripe_settings()
        settings.stripe_customer_portal_url = ""

        mock_customer = MagicMock()
        mock_customer.id = "cus_test_456"
        mock_stripe.Customer.list.return_value = SimpleNamespace(data=[mock_customer])

        mock_portal = MagicMock()
        mock_portal.url = "https://billing.stripe.com/session/test"
        mock_stripe.billing_portal.Session.create.return_value = mock_portal

        service = _make_checkout_service(stripe_settings=settings)
        await service.create_portal_session("test@example.com")

        mock_stripe.billing_portal.Session.create.assert_called_once_with(
            customer="cus_test_456",
            return_url=None,
        )


# =============================================================================
# POST /api/v1/checkout/manage-subscription endpoint
# =============================================================================


@pytest.mark.unit
class TestManageSubscriptionEndpoint:
    """Tests for the manage-subscription API endpoint."""

    @patch("grins_platform.api.v1.checkout.EmailService")
    @patch("grins_platform.api.v1.checkout.CheckoutService")
    async def test_success_sends_email_and_returns_message(
        self,
        MockCheckoutService: MagicMock,
        MockEmailService: MagicMock,
    ) -> None:
        """Valid email should create portal session, send email, return success."""
        from httpx import ASGITransport, AsyncClient

        from grins_platform.main import app

        mock_service = AsyncMock()
        mock_service.create_portal_session.return_value = (
            "https://billing.stripe.com/session/abc"
        )
        MockCheckoutService.return_value = mock_service

        mock_email = MagicMock()
        mock_email.send_subscription_management_email.return_value = {"sent": True}
        MockEmailService.return_value = mock_email

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/checkout/manage-subscription",
                json={"email": "subscriber@example.com"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data["message"].lower() or "sent" in data["message"].lower()

        mock_service.create_portal_session.assert_called_once_with(
            "subscriber@example.com",
        )
        mock_email.send_subscription_management_email.assert_called_once_with(
            to_email="subscriber@example.com",
            portal_url="https://billing.stripe.com/session/abc",
        )

    @patch("grins_platform.api.v1.checkout.CheckoutService")
    async def test_unknown_email_returns_404(
        self,
        MockCheckoutService: MagicMock,
    ) -> None:
        """Unknown email should return 404 with descriptive message."""
        from httpx import ASGITransport, AsyncClient

        from grins_platform.main import app

        mock_service = AsyncMock()
        mock_service.create_portal_session.side_effect = SubscriptionNotFoundError(
            "unknown@example.com",
        )
        MockCheckoutService.return_value = mock_service

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/checkout/manage-subscription",
                json={"email": "unknown@example.com"},
            )

        assert resp.status_code == 404
        assert "no subscription found" in resp.json()["detail"].lower()

    @patch("grins_platform.api.v1.checkout.CheckoutService")
    async def test_stripe_unavailable_returns_503(
        self,
        MockCheckoutService: MagicMock,
    ) -> None:
        """StripeUnavailableError should map to 503 with friendly message.

        Validates BUG-001 fix: previously this propagated as raw 500.
        """
        from httpx import ASGITransport, AsyncClient

        from grins_platform.main import app

        mock_service = AsyncMock()
        mock_service.create_portal_session.side_effect = StripeUnavailableError(
            "Stripe authentication failed",
        )
        MockCheckoutService.return_value = mock_service

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/checkout/manage-subscription",
                json={"email": "subscriber@example.com"},
            )

        assert resp.status_code == 503
        body = resp.json()
        assert "temporarily unavailable" in body["detail"].lower()

    async def test_invalid_email_returns_422(self) -> None:
        """Invalid email format should return 422 validation error."""
        from httpx import ASGITransport, AsyncClient

        from grins_platform.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/checkout/manage-subscription",
                json={"email": "not-an-email"},
            )

        assert resp.status_code == 422
