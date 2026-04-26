"""Email service configuration settings.

Validates: Requirements 39B.1, 39B.2, 67.3, 67.10
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from grins_platform.log_config import get_logger

logger = get_logger(__name__)


class EmailSettings(BaseSettings):
    """Configuration for email service integration.

    ``resend_api_key`` is the primary key (env: ``RESEND_API_KEY``).
    ``email_api_key`` is the legacy fallback (env: ``EMAIL_API_KEY``).
    ``is_configured`` is True when *either* is non-empty so that flipping
    the env var is enough to migrate.
    """

    resend_api_key: str = ""
    email_api_key: str = ""
    portal_base_url: str = "http://localhost:5173"
    internal_notification_email: str = ""
    resend_webhook_secret: str = ""
    company_physical_address: str = ""
    stripe_customer_portal_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_configured(self) -> bool:
        """Check if email sending is available."""
        return bool(self.resend_api_key or self.email_api_key)

    def log_configuration_status(self) -> None:
        """Log warnings if critical email settings are missing."""
        if not self.resend_api_key and not self.email_api_key:
            logger.warning(
                "email.config.missing_key",
                key="RESEND_API_KEY",
                message=(
                    "Email API key not configured "
                    "(neither RESEND_API_KEY nor EMAIL_API_KEY) "
                    "— emails recorded as pending"
                ),
            )
        if not self.company_physical_address:
            logger.warning(
                "email.config.missing_address",
                key="COMPANY_PHYSICAL_ADDRESS",
                message=(
                    "Physical address not configured — commercial emails disabled"
                ),
            )
