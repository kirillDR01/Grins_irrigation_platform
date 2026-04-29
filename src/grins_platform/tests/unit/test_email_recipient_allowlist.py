"""Unit tests for the EMAIL_TEST_ADDRESS_ALLOWLIST hard guard.

Validates: Feature — estimate approval email portal (allowlist guard).
"""

from __future__ import annotations

import pytest

from grins_platform.services.email_service import (
    EmailRecipientNotAllowedError,
    _load_email_allowlist,
    _normalize_email_for_comparison,
    enforce_email_recipient_allowlist,
)


@pytest.mark.unit
class TestNormalizeEmail:
    def test_lowercases_and_strips(self) -> None:
        assert _normalize_email_for_comparison("  Foo@Bar.COM  ") == "foo@bar.com"

    def test_handles_empty(self) -> None:
        assert _normalize_email_for_comparison("") == ""


@pytest.mark.unit
class TestLoadEmailAllowlist:
    def test_unset_env_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        assert _load_email_allowlist() is None

    def test_empty_env_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMAIL_TEST_ADDRESS_ALLOWLIST", "")
        assert _load_email_allowlist() is None

    def test_comma_only_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMAIL_TEST_ADDRESS_ALLOWLIST", ",")
        assert _load_email_allowlist() is None

    def test_single_email_returns_singleton_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EMAIL_TEST_ADDRESS_ALLOWLIST", "a@b.com")
        assert _load_email_allowlist() == ["a@b.com"]

    def test_comma_separated_returns_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "EMAIL_TEST_ADDRESS_ALLOWLIST",
            "  Foo@Bar.com , bar@baz.com ",
        )
        assert _load_email_allowlist() == ["foo@bar.com", "bar@baz.com"]


@pytest.mark.unit
class TestEnforceEmailRecipientAllowlist:
    def test_no_op_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        # No exception even for arbitrary recipient.
        enforce_email_recipient_allowlist("anyone@example.com", provider="resend")

    def test_allowed_recipient_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMAIL_TEST_ADDRESS_ALLOWLIST", "ok@x.com")
        enforce_email_recipient_allowlist("ok@x.com", provider="resend")

    def test_disallowed_recipient_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMAIL_TEST_ADDRESS_ALLOWLIST", "ok@x.com")
        with pytest.raises(EmailRecipientNotAllowedError) as exc:
            enforce_email_recipient_allowlist("nope@x.com", provider="resend")
        assert "provider=resend" in str(exc.value)

    def test_case_insensitive_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMAIL_TEST_ADDRESS_ALLOWLIST", "ok@x.com")
        # Should not raise — caller used uppercase.
        enforce_email_recipient_allowlist("OK@X.COM", provider="resend")
