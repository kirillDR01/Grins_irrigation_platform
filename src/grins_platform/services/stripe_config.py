"""Stripe configuration settings.

Validates: Requirements 27.1, 27.2, 27.3, 27.4, 27.5, 39A.6
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from grins_platform.log_config import get_logger

logger = get_logger(__name__)


class StripeSettings(BaseSettings):
    """Configuration for Stripe payment integration."""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    stripe_customer_portal_url: str = ""
    stripe_tax_enabled: bool = True
    stripe_terminal_location_id: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_configured(self) -> bool:
        """Check if required Stripe settings are present."""
        return bool(self.stripe_secret_key and self.stripe_webhook_secret)

    def log_configuration_status(self) -> None:
        """Log warnings if critical Stripe settings are missing."""
        if not self.stripe_secret_key:
            logger.warning(
                "stripe.config.missing_key",
                key="STRIPE_SECRET_KEY",
                message="Stripe secret key not configured — payment features disabled",
            )
        if not self.stripe_webhook_secret:
            msg = "Stripe webhook secret not configured — webhook verification disabled"
            logger.warning(
                "stripe.config.missing_key",
                key="STRIPE_WEBHOOK_SECRET",
                message=msg,
            )
