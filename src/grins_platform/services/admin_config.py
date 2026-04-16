"""Admin notification configuration.

Holds the admin-facing recipient address used by the cancellation-alert
email sent from :class:`NotificationService.send_admin_cancellation_alert`.

In production the ``ADMIN_NOTIFICATION_EMAIL`` env var must be set. There is
intentionally no default — a missing value is logged and the SMS
short-circuit in ``_handle_cancel`` continues as normal, which is the
desired failure mode (admin email failure must not block customer replies).

Validates: bughunt 2026-04-16 finding H-5
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from grins_platform.log_config import get_logger

logger = get_logger(__name__)


class AdminNotificationSettings(BaseSettings):
    """Configuration for admin-facing system alerts.

    Validates: bughunt 2026-04-16 finding H-5
    """

    admin_notification_email: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_configured(self) -> bool:
        """Return True if a recipient is configured."""
        return bool(self.admin_notification_email)

    def log_configuration_status(self) -> None:
        """Log a warning if the recipient address is missing."""
        if not self.admin_notification_email:
            logger.warning(
                "admin.config.missing_email",
                key="ADMIN_NOTIFICATION_EMAIL",
                message=(
                    "Admin notification email not configured — "
                    "admin cancellation alerts will skip email dispatch."
                ),
            )
