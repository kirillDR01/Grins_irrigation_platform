"""F4: tests for ``EmailSettings.log_configuration_status``.

Validates the deprecated-PORTAL_BASE_URL warning that prevents stale
Vercel preview aliases from silently breaking customer portal links.

Validates: F4 sign-off (run-20260504-185844-full).
"""

from __future__ import annotations

from unittest.mock import patch

from grins_platform.services.email_config import EmailSettings


def test_log_configuration_status_warns_on_deprecated_portal_host() -> None:
    """A PORTAL_BASE_URL containing the deprecated alias must log an error."""
    settings = EmailSettings(
        resend_api_key="fake",
        company_physical_address="123 Test St",
        portal_base_url=(
            "https://frontend-git-dev-kirilldr01s-projects.vercel.app"
        ),
    )

    with patch("grins_platform.services.email_config.logger") as mock_logger:
        settings.log_configuration_status()

    mock_logger.error.assert_called_once()
    call_kwargs = mock_logger.error.call_args.kwargs
    assert call_kwargs["portal_base_url"] == (
        "https://frontend-git-dev-kirilldr01s-projects.vercel.app"
    )


def test_log_configuration_status_silent_on_canonical_portal_host() -> None:
    """The canonical alias must NOT trigger the deprecation error."""
    settings = EmailSettings(
        resend_api_key="fake",
        company_physical_address="123 Test St",
        portal_base_url=(
            "https://grins-irrigation-platform-git-dev-"
            "kirilldr01s-projects.vercel.app"
        ),
    )

    with patch("grins_platform.services.email_config.logger") as mock_logger:
        settings.log_configuration_status()

    # The deprecation event is logged via ``logger.error``; no other call site
    # in ``log_configuration_status`` uses ``error``.
    mock_logger.error.assert_not_called()


def test_log_configuration_status_silent_on_localhost_default() -> None:
    """The localhost default value must NOT trigger the deprecation error."""
    settings = EmailSettings(
        resend_api_key="fake",
        company_physical_address="123 Test St",
        portal_base_url="http://localhost:5173",
    )

    with patch("grins_platform.services.email_config.logger") as mock_logger:
        settings.log_configuration_status()

    mock_logger.error.assert_not_called()
