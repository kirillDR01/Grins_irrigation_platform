"""Unit tests for the EMAIL_TEST_REDIRECT_TO env-driven redirect.

Production leaves ``EMAIL_TEST_REDIRECT_TO`` unset and the function is
a no-op. Dev/staging sets it to a single test inbox so every outbound
email — regardless of the original recipient (customer / technician /
admin) — is rewritten before allowlist enforcement, letting one inbox
catch every test send.
"""

from __future__ import annotations

import pytest

from grins_platform.services.email_service import (
    EmailRecipientNotAllowedError,
    _load_email_test_redirect,
    apply_email_test_redirect,
    enforce_email_recipient_allowlist,
)


@pytest.mark.unit
class TestLoadEmailTestRedirect:
    def test_unset_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
        assert _load_email_test_redirect() is None

    def test_empty_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMAIL_TEST_REDIRECT_TO", "")
        assert _load_email_test_redirect() is None

    def test_whitespace_only_returns_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EMAIL_TEST_REDIRECT_TO", "   ")
        assert _load_email_test_redirect() is None

    def test_set_returns_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "EMAIL_TEST_REDIRECT_TO",
            "kirillrakitinsecond@gmail.com",
        )
        assert _load_email_test_redirect() == "kirillrakitinsecond@gmail.com"


@pytest.mark.unit
class TestApplyEmailTestRedirect:
    def test_unset_returns_original_unchanged(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
        final, original = apply_email_test_redirect("real@example.com")
        assert final == "real@example.com"
        assert original is None

    def test_set_rewrites_to_target(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "EMAIL_TEST_REDIRECT_TO",
            "kirillrakitinsecond@gmail.com",
        )
        final, original = apply_email_test_redirect("admin@grinsirrigation.com")
        assert final == "kirillrakitinsecond@gmail.com"
        assert original == "admin@grinsirrigation.com"


@pytest.mark.unit
class TestRedirectThenAllowlistDefenseInDepth:
    """Redirect must run BEFORE allowlist; redirect target must be allowed."""

    def test_misconfig_redirect_to_blocked_addr_still_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EMAIL_TEST_REDIRECT_TO", "wrong@example.com")
        monkeypatch.setenv(
            "EMAIL_TEST_ADDRESS_ALLOWLIST",
            "kirillrakitinsecond@gmail.com",
        )
        final, _ = apply_email_test_redirect("admin@grinsirrigation.com")
        assert final == "wrong@example.com"
        with pytest.raises(EmailRecipientNotAllowedError):
            enforce_email_recipient_allowlist(final, provider="resend")

    def test_correct_redirect_passes_allowlist(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "EMAIL_TEST_REDIRECT_TO",
            "kirillrakitinsecond@gmail.com",
        )
        monkeypatch.setenv(
            "EMAIL_TEST_ADDRESS_ALLOWLIST",
            "kirillrakitinsecond@gmail.com",
        )
        # Original recipient is a non-allowlisted admin/tech address.
        final, original = apply_email_test_redirect("ops@grinsirrigation.com")
        assert original == "ops@grinsirrigation.com"
        enforce_email_recipient_allowlist(final, provider="resend")

    def test_production_style_no_redirect_no_allowlist(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        final, original = apply_email_test_redirect("real-customer@example.com")
        assert final == "real-customer@example.com"
        assert original is None
        enforce_email_recipient_allowlist(final, provider="resend")
