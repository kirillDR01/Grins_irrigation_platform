"""Email service configuration settings.

Validates: Requirements 39B.1, 39B.2, 67.3, 67.10
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from grins_platform.log_config import get_logger

logger = get_logger(__name__)

# F4: Vercel preview aliases that have been retired. Keep this list small
# and surgical — a stale alias here means estimate/portal links will 404
# in customer email inboxes.
_DEPRECATED_PORTAL_HOSTS: tuple[str, ...] = (
    "frontend-git-dev-kirilldr01s-projects.vercel.app",
)

# F4-REOPENED: ``ENVIRONMENT`` values that MUST hard-fail boot when
# ``PORTAL_BASE_URL`` is a deprecated alias. The codebase historically
# stores ``development`` (the .env.example default) on the deployed dev
# Railway service rather than ``dev``; the ``dev`` and ``production``
# tokens are accepted for forward-compat with the canonical naming the
# project is moving toward. Local boots use ``local`` / unset and stay
# warn-only.
_BOOT_FAIL_ENVIRONMENTS: frozenset[str] = frozenset(
    {"dev", "development", "production", "prod"}
)


def _is_deployed_environment() -> bool:
    """True when the process is running on a Railway service.

    F4-REOPENED hard-fails when running on *any* Railway deployment —
    using ``RAILWAY_ENVIRONMENT`` is the most reliable signal because it
    is unset locally regardless of what ``ENVIRONMENT`` is configured
    to. ``ENVIRONMENT in _BOOT_FAIL_ENVIRONMENTS`` is the secondary
    trigger so manually-set env vars (CI, staging hosts) still fail.
    """
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return True
    return os.getenv("ENVIRONMENT", "local").lower() in _BOOT_FAIL_ENVIRONMENTS


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
        if any(host in self.portal_base_url for host in _DEPRECATED_PORTAL_HOSTS):
            logger.error(
                "email.config.deprecated_portal_base_url",
                portal_base_url=self.portal_base_url,
                message=(
                    "PORTAL_BASE_URL points to a deprecated Vercel preview "
                    "alias. Estimate/portal links will 404. Update the env "
                    "var to https://grins-irrigation-platform-git-dev-"
                    "kirilldr01s-projects.vercel.app (dev) or the equivalent "
                    "canonical prod alias."
                ),
            )

    def validate_portal_base_url(self) -> None:
        """Hard-fail boot when PORTAL_BASE_URL is a deprecated alias.

        F4-REOPENED: the prior fix logged ``error`` but boot continued, so
        Railway dev silently shipped customer emails containing portal
        links pointing at a stale Vercel marketing-site bundle. This
        method raises ``RuntimeError`` whenever the process is running on
        Railway (``RAILWAY_ENVIRONMENT`` is set) or ``ENVIRONMENT`` is
        explicitly one of ``{dev, development, prod, production}``.
        Locally / in tests / unset, it logs and returns so unit tests and
        developer machines aren't blocked when a stale .env lingers.
        """
        if not any(host in self.portal_base_url for host in _DEPRECATED_PORTAL_HOSTS):
            return
        environment = os.getenv("ENVIRONMENT", "local").lower()
        railway_env = os.getenv("RAILWAY_ENVIRONMENT", "")
        if _is_deployed_environment():
            logger.error(
                "email.config.deprecated_portal_base_url",
                portal_base_url=self.portal_base_url,
                environment=environment,
                railway_environment=railway_env,
                action="boot_fail",
            )
            msg = (
                f"PORTAL_BASE_URL='{self.portal_base_url}' is a deprecated "
                f"Vercel alias and the process is deployed "
                f"(ENVIRONMENT='{environment}', "
                f"RAILWAY_ENVIRONMENT='{railway_env}'). Refusing to boot — "
                "fix the Railway env var to the canonical project alias "
                "(https://grins-irrigation-platform-git-dev-"
                "kirilldr01s-projects.vercel.app for dev) before retrying."
            )
            raise RuntimeError(msg)
        logger.error(
            "email.config.deprecated_portal_base_url",
            portal_base_url=self.portal_base_url,
            environment=environment,
            action="warn_only",
        )
