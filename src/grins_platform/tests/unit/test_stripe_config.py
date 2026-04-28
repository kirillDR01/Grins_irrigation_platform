"""Unit tests for StripeSettings.

Pinning the Stripe API version is load-bearing: if the SDK version drifts
ahead of the version Stripe declares on incoming webhook events, payload
shapes diverge silently. These tests fail loudly if the default ever
becomes empty.
"""

from __future__ import annotations

import pytest

from grins_platform.services.stripe_config import StripeSettings


@pytest.mark.unit
def test_stripe_api_version_default_is_pinned() -> None:
    settings = StripeSettings()
    assert settings.stripe_api_version != ""
    # The pin is meant to track what existing webhook endpoints declare.
    # Bumping this default is a deliberate PR with regression tests.
    assert settings.stripe_api_version == "2025-03-31.basil"


@pytest.mark.unit
def test_stripe_api_version_overridable_via_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_API_VERSION", "2099-01-01.future")
    settings = StripeSettings()
    assert settings.stripe_api_version == "2099-01-01.future"


@pytest.mark.unit
def test_is_configured_unaffected_by_api_version() -> None:
    """Pinning the version must not change is_configured semantics."""
    settings = StripeSettings(
        stripe_secret_key="sk_test_x",
        stripe_webhook_secret="whsec_x",
    )
    assert settings.is_configured is True
