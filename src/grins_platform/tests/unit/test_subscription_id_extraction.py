"""Unit tests for _extract_subscription_id() and customer_id fallback.

Validates BUG #16 fix: invoice.paid no longer skips when subscription field
is missing or uses newer Stripe API formats.
"""

from __future__ import annotations

import pytest

from grins_platform.api.v1.webhooks import StripeWebhookHandler


class TestExtractSubscriptionId:
    """Tests for StripeWebhookHandler._extract_subscription_id()."""

    @pytest.mark.unit
    def test_legacy_string(self) -> None:
        """Legacy format: subscription is a plain string ID."""
        obj = {"subscription": "sub_abc123"}
        assert StripeWebhookHandler._extract_subscription_id(obj) == "sub_abc123"

    @pytest.mark.unit
    def test_expanded_object(self) -> None:
        """Expanded format: subscription is an object with id field."""
        obj = {"subscription": {"id": "sub_expanded", "status": "active"}}
        assert StripeWebhookHandler._extract_subscription_id(obj) == "sub_expanded"

    @pytest.mark.unit
    def test_new_parent_format_string(self) -> None:
        """New Stripe API (2025-03-31+): parent.subscription_details.subscription."""
        obj = {
            "subscription": "",
            "parent": {
                "subscription_details": {
                    "subscription": "sub_new_api",
                },
            },
        }
        assert StripeWebhookHandler._extract_subscription_id(obj) == "sub_new_api"

    @pytest.mark.unit
    def test_new_parent_format_object(self) -> None:
        """New Stripe API with expanded subscription in parent path."""
        obj = {
            "parent": {
                "subscription_details": {
                    "subscription": {"id": "sub_nested_obj"},
                },
            },
        }
        assert StripeWebhookHandler._extract_subscription_id(obj) == "sub_nested_obj"

    @pytest.mark.unit
    def test_empty_returns_empty(self) -> None:
        """No subscription info at all returns empty string."""
        assert StripeWebhookHandler._extract_subscription_id({}) == ""

    @pytest.mark.unit
    def test_null_subscription_returns_empty(self) -> None:
        """subscription=None returns empty string."""
        obj = {"subscription": None}
        assert StripeWebhookHandler._extract_subscription_id(obj) == ""

    @pytest.mark.unit
    def test_empty_string_tries_parent(self) -> None:
        """Empty subscription string falls through to parent path."""
        obj = {
            "subscription": "",
            "parent": {
                "subscription_details": {
                    "subscription": "sub_fallback",
                },
            },
        }
        assert StripeWebhookHandler._extract_subscription_id(obj) == "sub_fallback"

    @pytest.mark.unit
    def test_legacy_takes_precedence_over_parent(self) -> None:
        """When both legacy and parent paths exist, legacy wins."""
        obj = {
            "subscription": "sub_legacy",
            "parent": {
                "subscription_details": {
                    "subscription": "sub_parent",
                },
            },
        }
        assert StripeWebhookHandler._extract_subscription_id(obj) == "sub_legacy"

    @pytest.mark.unit
    def test_empty_parent_details(self) -> None:
        """Parent exists but subscription_details is empty."""
        obj = {"parent": {"subscription_details": {}}}
        assert StripeWebhookHandler._extract_subscription_id(obj) == ""

    @pytest.mark.unit
    def test_parent_without_subscription_details(self) -> None:
        """Parent exists but has no subscription_details key."""
        obj = {"parent": {"type": "quote"}}
        assert StripeWebhookHandler._extract_subscription_id(obj) == ""
