"""SignWell configuration settings.

Validates: CRM Changes Update 2 Req 18.5, 18.6
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from grins_platform.log_config import get_logger

logger = get_logger(__name__)


class SignWellSettings(BaseSettings):
    """Configuration for SignWell e-signature integration."""

    signwell_api_key: str = ""
    signwell_webhook_secret: str = ""
    signwell_api_base_url: str = "https://www.signwell.com/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_configured(self) -> bool:
        """Check if required SignWell settings are present."""
        return bool(self.signwell_api_key)

    def log_configuration_status(self) -> None:
        """Log warnings if critical SignWell settings are missing."""
        if not self.signwell_api_key:
            msg = "SignWell API key not configured"
            logger.warning(
                "signwell.config.missing_key",
                key="SIGNWELL_API_KEY",
                message=msg,
            )
        if not self.signwell_webhook_secret:
            msg = "SignWell webhook secret not configured"
            logger.warning(
                "signwell.config.missing_key",
                key="SIGNWELL_WEBHOOK_SECRET",
                message=msg,
            )
