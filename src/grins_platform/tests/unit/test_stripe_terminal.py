"""Unit tests for Stripe Terminal tap-to-pay integration.

Tests the StripeTerminalService and API endpoints for connection token
creation, PaymentIntent creation, and payment recording.

Validates: Requirements 16.2, 16.4, 16.6, 16.7
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from grins_platform.api.v1.auth_dependencies import get_current_active_user
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.api.v1.stripe_terminal import _get_stripe_terminal_service
from grins_platform.app import create_app
from grins_platform.services.stripe_terminal import (
    StripeTerminalError,
    StripeTerminalService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_stripe_settings() -> MagicMock:
    """Create mock Stripe settings that are configured."""
    settings = MagicMock()
    settings.is_configured = True
    settings.stripe_secret_key = "sk_test_fake_key"
    settings.stripe_terminal_location_id = "tml_test_location"
    return settings


@pytest.fixture()
def mock_stripe_settings_unconfigured() -> MagicMock:
    """Create mock Stripe settings that are NOT configured."""
    settings = MagicMock()
    settings.is_configured = False
    settings.stripe_secret_key = ""
    settings.stripe_terminal_location_id = ""
    return settings


@pytest.fixture()
def service(mock_stripe_settings: MagicMock) -> StripeTerminalService:
    """Create a StripeTerminalService with mocked settings."""
    return StripeTerminalService(stripe_settings=mock_stripe_settings)


@pytest.fixture()
def client() -> TestClient:
    """Create a test client with auth and DB mocked."""
    app = create_app()

    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    mock_user.is_active = True

    async def _mock_db():  # noqa: ANN202
        yield MagicMock()

    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db_session] = _mock_db

    return TestClient(app)


# ---------------------------------------------------------------------------
# Service Unit Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStripeTerminalServiceConnectionToken:
    """Tests for create_connection_token()."""

    @patch("grins_platform.services.stripe_terminal.stripe")
    def test_returns_valid_token(
        self,
        mock_stripe: MagicMock,
        service: StripeTerminalService,
    ) -> None:
        """Connection token endpoint returns a valid token string.

        Validates: Requirement 16.6
        """
        mock_token = MagicMock()
        mock_token.secret = "pst_test_secret_token_123"
        mock_stripe.terminal.ConnectionToken.create.return_value = mock_token

        result = service.create_connection_token()

        assert result == "pst_test_secret_token_123"
        mock_stripe.terminal.ConnectionToken.create.assert_called_once()

    @patch("grins_platform.services.stripe_terminal.stripe")
    def test_passes_location_id_when_configured(
        self,
        mock_stripe: MagicMock,
        service: StripeTerminalService,
    ) -> None:
        """Connection token includes location when STRIPE_TERMINAL_LOCATION_ID is set.

        Validates: Requirement 16.8
        """
        mock_token = MagicMock()
        mock_token.secret = "pst_test_secret"
        mock_stripe.terminal.ConnectionToken.create.return_value = mock_token

        service.create_connection_token()

        mock_stripe.terminal.ConnectionToken.create.assert_called_once_with(
            location="tml_test_location"
        )

    def test_raises_when_stripe_not_configured(
        self,
        mock_stripe_settings_unconfigured: MagicMock,
    ) -> None:
        """Raises StripeTerminalError when Stripe is not configured."""
        svc = StripeTerminalService(stripe_settings=mock_stripe_settings_unconfigured)

        with pytest.raises(StripeTerminalError, match="not configured"):
            svc.create_connection_token()

    @patch("grins_platform.services.stripe_terminal.stripe")
    def test_raises_on_stripe_api_error(
        self,
        mock_stripe: MagicMock,
        service: StripeTerminalService,
    ) -> None:
        """Raises StripeTerminalError on Stripe API failure."""
        mock_stripe.StripeError = Exception
        mock_stripe.terminal.ConnectionToken.create.side_effect = Exception(
            "API error"
        )

        with pytest.raises(StripeTerminalError):
            service.create_connection_token()


@pytest.mark.unit
class TestStripeTerminalServicePaymentIntent:
    """Tests for create_payment_intent()."""

    @patch("grins_platform.services.stripe_terminal.stripe")
    def test_creates_intent_with_correct_params(
        self,
        mock_stripe: MagicMock,
        service: StripeTerminalService,
    ) -> None:
        """PaymentIntent is created with correct amount and payment_method_types.

        Validates: Requirement 16.7
        """
        mock_intent = MagicMock()
        mock_intent.id = "pi_test_123"
        mock_intent.client_secret = "pi_test_123_secret"
        mock_intent.amount = 5000
        mock_intent.currency = "usd"
        mock_intent.status = "requires_payment_method"
        mock_stripe.PaymentIntent.create.return_value = mock_intent

        result = service.create_payment_intent(
            amount_cents=5000,
            currency="usd",
            description="Test payment",
        )

        assert result.id == "pi_test_123"
        mock_stripe.PaymentIntent.create.assert_called_once_with(
            amount=5000,
            currency="usd",
            description="Test payment",
            payment_method_types=["card_present"],
            capture_method="automatic",
        )

    @patch("grins_platform.services.stripe_terminal.stripe")
    def test_uses_card_present_payment_method(
        self,
        mock_stripe: MagicMock,
        service: StripeTerminalService,
    ) -> None:
        """PaymentIntent uses card_present payment method type for tap-to-pay.

        Validates: Requirement 16.7
        """
        mock_intent = MagicMock()
        mock_stripe.PaymentIntent.create.return_value = mock_intent

        service.create_payment_intent(amount_cents=1000)

        call_kwargs = mock_stripe.PaymentIntent.create.call_args[1]
        assert call_kwargs["payment_method_types"] == ["card_present"]

    def test_rejects_zero_amount(
        self,
        service: StripeTerminalService,
    ) -> None:
        """Raises StripeTerminalError for zero or negative amounts."""
        with pytest.raises(StripeTerminalError, match="greater than zero"):
            service.create_payment_intent(amount_cents=0)

    def test_rejects_negative_amount(
        self,
        service: StripeTerminalService,
    ) -> None:
        """Raises StripeTerminalError for negative amounts."""
        with pytest.raises(StripeTerminalError, match="greater than zero"):
            service.create_payment_intent(amount_cents=-100)

    def test_raises_when_stripe_not_configured(
        self,
        mock_stripe_settings_unconfigured: MagicMock,
    ) -> None:
        """Raises StripeTerminalError when Stripe is not configured."""
        svc = StripeTerminalService(stripe_settings=mock_stripe_settings_unconfigured)

        with pytest.raises(StripeTerminalError, match="not configured"):
            svc.create_payment_intent(amount_cents=5000)

    @patch("grins_platform.services.stripe_terminal.stripe")
    def test_default_description(
        self,
        mock_stripe: MagicMock,
        service: StripeTerminalService,
    ) -> None:
        """Uses default description when none provided."""
        mock_stripe.PaymentIntent.create.return_value = MagicMock()

        service.create_payment_intent(amount_cents=1000)

        call_kwargs = mock_stripe.PaymentIntent.create.call_args[1]
        assert call_kwargs["description"] == "In-person tap-to-pay payment"


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConnectionTokenEndpoint:
    """Tests for POST /api/v1/stripe/terminal/connection-token."""

    def test_returns_token_authenticated(
        self,
        client: TestClient,
    ) -> None:
        """Connection token endpoint returns valid token for authenticated user.

        Validates: Requirement 16.6
        """
        mock_service = MagicMock()
        mock_service.create_connection_token.return_value = "pst_test_token"

        app = client.app
        app.dependency_overrides[_get_stripe_terminal_service] = lambda: mock_service  # type: ignore[index]

        response = client.post("/api/v1/stripe/terminal/connection-token")

        assert response.status_code == 200
        data = response.json()
        assert data["secret"] == "pst_test_token"

        app.dependency_overrides.pop(_get_stripe_terminal_service, None)  # type: ignore[arg-type]

    def test_returns_502_on_stripe_error(
        self,
        client: TestClient,
    ) -> None:
        """Returns 502 when Stripe Terminal fails."""
        mock_service = MagicMock()
        mock_service.create_connection_token.side_effect = StripeTerminalError(
            "Stripe unavailable"
        )

        app = client.app
        app.dependency_overrides[_get_stripe_terminal_service] = lambda: mock_service  # type: ignore[index]

        response = client.post("/api/v1/stripe/terminal/connection-token")

        assert response.status_code == 502

        app.dependency_overrides.pop(_get_stripe_terminal_service, None)  # type: ignore[arg-type]


@pytest.mark.unit
class TestCreatePaymentIntentEndpoint:
    """Tests for POST /api/v1/stripe/terminal/create-payment-intent."""

    def test_creates_intent_with_correct_amount(
        self,
        client: TestClient,
    ) -> None:
        """PaymentIntent creation with correct amount and payment_method_types.

        Validates: Requirements 16.2, 16.7
        """
        mock_intent = MagicMock()
        mock_intent.id = "pi_test_456"
        mock_intent.client_secret = "pi_test_456_secret"
        mock_intent.amount = 7500
        mock_intent.currency = "usd"
        mock_intent.status = "requires_payment_method"

        mock_service = MagicMock()
        mock_service.create_payment_intent.return_value = mock_intent

        app = client.app
        app.dependency_overrides[_get_stripe_terminal_service] = lambda: mock_service  # type: ignore[index]

        response = client.post(
            "/api/v1/stripe/terminal/create-payment-intent",
            json={"amount_cents": 7500, "currency": "usd", "description": "Invoice #123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "pi_test_456"
        assert data["amount"] == 7500
        assert data["currency"] == "usd"

        mock_service.create_payment_intent.assert_called_once_with(
            amount_cents=7500,
            currency="usd",
            description="Invoice #123",
        )

        app.dependency_overrides.pop(_get_stripe_terminal_service, None)  # type: ignore[arg-type]

    def test_rejects_zero_amount(self, client: TestClient) -> None:
        """Rejects PaymentIntent with zero amount (validation error)."""
        response = client.post(
            "/api/v1/stripe/terminal/create-payment-intent",
            json={"amount_cents": 0},
        )

        assert response.status_code == 422

    def test_rejects_missing_amount(self, client: TestClient) -> None:
        """Rejects PaymentIntent with missing amount."""
        response = client.post(
            "/api/v1/stripe/terminal/create-payment-intent",
            json={},
        )

        assert response.status_code == 422

    def test_returns_502_on_stripe_error(
        self,
        client: TestClient,
    ) -> None:
        """Returns 502 when Stripe PaymentIntent creation fails."""
        mock_service = MagicMock()
        mock_service.create_payment_intent.side_effect = StripeTerminalError(
            "Payment failed"
        )

        app = client.app
        app.dependency_overrides[_get_stripe_terminal_service] = lambda: mock_service  # type: ignore[index]

        response = client.post(
            "/api/v1/stripe/terminal/create-payment-intent",
            json={"amount_cents": 5000},
        )

        assert response.status_code == 502

        app.dependency_overrides.pop(_get_stripe_terminal_service, None)  # type: ignore[arg-type]
