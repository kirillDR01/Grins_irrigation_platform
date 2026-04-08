"""Unit tests for the SMS_TEST_PHONE_ALLOWLIST hard guard.

The guard is a safety gate that lives on every SMS provider's
``send_text`` entry point. When ``SMS_TEST_PHONE_ALLOWLIST`` is set in
the environment it refuses to send to any number not on the list,
raising :class:`RecipientNotAllowedError`. When unset (production
default) the guard is a no-op.
"""

from __future__ import annotations

import pytest

from grins_platform.services.sms.base import (
    RecipientNotAllowedError,
    _load_allowlist,
    _normalize_phone_for_comparison,
    enforce_recipient_allowlist,
)


class TestNormalizePhoneForComparison:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("+19527373312", "+19527373312"),
            ("9527373312", "+19527373312"),
            ("(952) 737-3312", "+19527373312"),
            ("952-737-3312", "+19527373312"),
            (" 952.737.3312 ", "+19527373312"),
            ("1-952-737-3312", "+19527373312"),
            ("", ""),
            ("abc", ""),
        ],
    )
    def test_normalizes_common_us_phone_formats(
        self, raw: str, expected: str
    ) -> None:
        assert _normalize_phone_for_comparison(raw) == expected


class TestLoadAllowlist:
    def test_unset_env_var_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SMS_TEST_PHONE_ALLOWLIST", raising=False)
        assert _load_allowlist() is None

    def test_empty_env_var_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "")
        assert _load_allowlist() is None

    def test_whitespace_only_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "   ")
        assert _load_allowlist() is None

    def test_single_phone_normalized(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "9527373312")
        assert _load_allowlist() == ["+19527373312"]

    def test_multiple_phones_mixed_formats(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "SMS_TEST_PHONE_ALLOWLIST",
            "+19527373312, (612) 555-1212,  9995551234",
        )
        result = _load_allowlist()
        assert result == ["+19527373312", "+16125551212", "+19995551234"]

    def test_stray_commas_are_dropped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", ",,+19527373312,,,")
        assert _load_allowlist() == ["+19527373312"]


class TestEnforceRecipientAllowlist:
    def test_no_env_var_is_a_noop(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SMS_TEST_PHONE_ALLOWLIST", raising=False)
        # Should not raise for any phone, including obvious non-test numbers.
        enforce_recipient_allowlist("+14155551212", provider="callrail")
        enforce_recipient_allowlist("", provider="callrail")

    def test_allowed_phone_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "+19527373312")
        enforce_recipient_allowlist("+19527373312", provider="callrail")

    def test_allowed_phone_different_format_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "+19527373312")
        # Same number, different input format
        enforce_recipient_allowlist("9527373312", provider="callrail")
        enforce_recipient_allowlist("(952) 737-3312", provider="callrail")
        enforce_recipient_allowlist("952-737-3312", provider="twilio")

    def test_blocked_phone_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "+19527373312")
        with pytest.raises(RecipientNotAllowedError) as exc_info:
            enforce_recipient_allowlist("+14155551212", provider="callrail")
        assert "recipient_not_in_allowlist" in str(exc_info.value)
        assert "callrail" in str(exc_info.value)

    def test_blocked_phone_raises_with_provider_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SMS_TEST_PHONE_ALLOWLIST", "+19527373312")
        with pytest.raises(RecipientNotAllowedError) as exc_info:
            enforce_recipient_allowlist("+16125551212", provider="twilio")
        assert "twilio" in str(exc_info.value)

    def test_multiple_allowed_any_matches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "SMS_TEST_PHONE_ALLOWLIST",
            "+19527373312,+16125551212",
        )
        enforce_recipient_allowlist("+19527373312", provider="callrail")
        enforce_recipient_allowlist("+16125551212", provider="callrail")
        with pytest.raises(RecipientNotAllowedError):
            enforce_recipient_allowlist("+19995551234", provider="callrail")
