"""Stripe Terminal service for tap-to-pay integration.

Validates: Requirements 16.6, 16.7
"""

import stripe

from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.services.stripe_config import StripeSettings

logger = get_logger(__name__)


class StripeTerminalError(Exception):
    """Raised when a Stripe Terminal operation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class StripeTerminalService(LoggerMixin):
    """Service for Stripe Terminal tap-to-pay operations.

    Validates: Requirements 16.6, 16.7
    """

    DOMAIN = "payment"

    def __init__(self, stripe_settings: StripeSettings) -> None:
        super().__init__()
        self.stripe_settings = stripe_settings

    def create_connection_token(self) -> str:
        """Create a Stripe Terminal connection token for the frontend SDK.

        Returns:
            The connection token secret string.

        Raises:
            StripeTerminalError: If token creation fails.

        Validates: Requirement 16.6
        """
        self.log_started("create_connection_token")

        if not self.stripe_settings.is_configured:
            self.log_rejected(
                "create_connection_token",
                reason="stripe_not_configured",
            )
            msg = "Stripe is not configured"
            raise StripeTerminalError(msg)

        stripe.api_key = self.stripe_settings.stripe_secret_key
        stripe.api_version = self.stripe_settings.stripe_api_version

        try:
            location_id = self.stripe_settings.stripe_terminal_location_id
            params: dict[str, object] = {}
            if location_id:
                params["location"] = location_id

            token = stripe.terminal.ConnectionToken.create(**params)
            self.log_completed("create_connection_token")
            return token.secret  # type: ignore[return-value]
        except stripe.StripeError as e:
            self.log_failed("create_connection_token", error=e)
            raise StripeTerminalError(str(e)) from e

    def create_payment_intent(
        self,
        amount_cents: int,
        currency: str = "usd",
        description: str = "",
    ) -> stripe.PaymentIntent:
        """Create a PaymentIntent for in-person tap-to-pay collection.

        Args:
            amount_cents: Amount in cents (e.g. 5000 for $50.00).
            currency: Three-letter ISO currency code (default: usd).
            description: Optional description for the payment.

        Returns:
            The created Stripe PaymentIntent object.

        Raises:
            StripeTerminalError: If PaymentIntent creation fails.

        Validates: Requirement 16.7
        """
        self.log_started(
            "create_payment_intent",
            amount_cents=amount_cents,
            currency=currency,
        )

        if not self.stripe_settings.is_configured:
            self.log_rejected(
                "create_payment_intent",
                reason="stripe_not_configured",
            )
            msg = "Stripe is not configured"
            raise StripeTerminalError(msg)

        if amount_cents <= 0:
            self.log_rejected(
                "create_payment_intent",
                reason="invalid_amount",
            )
            msg = "Amount must be greater than zero"
            raise StripeTerminalError(msg)

        stripe.api_key = self.stripe_settings.stripe_secret_key
        stripe.api_version = self.stripe_settings.stripe_api_version

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                description=description or "In-person tap-to-pay payment",
                payment_method_types=["card_present"],
                capture_method="automatic",
            )
            self.log_completed(
                "create_payment_intent",
                payment_intent_id=intent.id,
            )
            return intent
        except stripe.StripeError as e:
            self.log_failed("create_payment_intent", error=e)
            raise StripeTerminalError(str(e)) from e
