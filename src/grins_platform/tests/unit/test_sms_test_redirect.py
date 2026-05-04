"""Unit tests for the SMS_TEST_REDIRECT_TO env-driven redirect.

Production leaves ``SMS_TEST_REDIRECT_TO`` unset and the function is a
no-op. Dev/staging sets it to a single test phone so every outbound
SMS — regardless of the original recipient (customer / technician /
admin) — is rewritten before allowlist enforcement, letting one inbox
catch every test send.
"""

from __future__ import annotations

import pytest

from grins_platform.services.sms.base import (
    RecipientNotAllowedError,
    _load_test_redirect,
    apply_test_redirect,
    enforce_recipient_allowlist,
)


class TestLoadTestRedirect:
    def test_unset_env_var_returns_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("SMS_TEST_REDIRECT_TO", raising=False)
        assert _load_test_redirect() is None

    def test_empty_returns_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SMS_TEST_REDIRECT_TO", "")
        assert _load_test_redirect() is None

    def test_whitespace_only_returns_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SMS_TEST_REDIRECT_TO", "   ")
        assert _load_test_redirect() is None

    def test_set_returns_value(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SMS_TEST_REDIRECT_TO", "+19527373312")
        assert _load_test_redirect() == "+19527373312"


class TestApplyTestRedirect:
    def test_unset_returns_original_unchanged(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("SMS_TEST_REDIRECT_TO", raising=False)
        final, original = apply_test_redirect("+14155551212")
        assert final == "+14155551212"
        assert original is None

    def test_set_rewrites_to_target(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SMS_TEST_REDIRECT_TO", "+19527373312")
        final, original = apply_test_redirect("+14155551212")
        assert final == "+19527373312"
        assert original == "+14155551212"

    def test_set_rewrites_even_when_original_is_already_target(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # When the caller already passed the target phone, redirect still
        # fires and reports the original. (No-op in effect; just keeps the
        # log/audit signal honest.)
        monkeypatch.setenv("SMS_TEST_REDIRECT_TO", "+19527373312")
        final, original = apply_test_redirect("+19527373312")
        assert final == "+19527373312"
        assert original == "+19527373312"


class TestRedirectThenAllowlistDefenseInDepth:
    """Redirect must run BEFORE allowlist; redirect target must be allowed."""

    def test_misconfig_redirect_to_blocked_phone_still_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Operator typo: redirected to a phone that is NOT on the allowlist.
        # The defense-in-depth allowlist must still refuse the send.
        monkeypatch.setenv("SMS_TEST_REDIRECT_TO", "+14155551212")
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "+19527373312")
        final, _ = apply_test_redirect("+18005551111")
        assert final == "+14155551212"
        with pytest.raises(RecipientNotAllowedError):
            enforce_recipient_allowlist(final, provider="callrail")

    def test_correct_redirect_passes_allowlist(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SMS_TEST_REDIRECT_TO", "+19527373312")
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "+19527373312")
        # Original recipient is some random non-allowlisted phone (a tech,
        # an admin, etc) — redirect rewrites it, allowlist accepts the
        # rewritten value.
        final, original = apply_test_redirect("+18005551111")
        assert original == "+18005551111"
        enforce_recipient_allowlist(final, provider="callrail")

    def test_redirect_unset_uses_original_for_allowlist(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Production-style: no redirect, no allowlist. Original passes through.
        monkeypatch.delenv("SMS_TEST_REDIRECT_TO", raising=False)
        monkeypatch.delenv("SMS_TEST_PHONE_ALLOWLIST", raising=False)
        final, original = apply_test_redirect("+14155551212")
        assert final == "+14155551212"
        assert original is None
        enforce_recipient_allowlist(final, provider="callrail")
