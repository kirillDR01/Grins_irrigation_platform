"""Verify Twilio swap procedure works end-to-end.

Requirements: 17.1, 17.2, 17.4
- SMS_PROVIDER=twilio → factory returns TwilioProvider
- Rate limiter keys namespace by provider_name
- Swap requires zero code changes to SMSService/CampaignService/UI
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import grins_platform.services.sms.factory as _fmod
from grins_platform.services.sms.callrail_provider import CallRailProvider
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms.null_provider import NullProvider
from grins_platform.services.sms.rate_limit_tracker import (
    SMSRateLimitTracker,
)
from grins_platform.services.sms.twilio_provider import TwilioProvider


@pytest.mark.unit
class TestTwilioSwapProcedure:
    """Requirement 17.1: SMS_PROVIDER=twilio returns TwilioProvider."""

    def setup_method(self) -> None:
        _fmod._last_provider_name = None

    def test_twilio_provider_returned_when_env_set(self) -> None:
        with patch.dict(os.environ, {"SMS_PROVIDER": "twilio"}):
            provider = get_sms_provider()
        assert isinstance(provider, TwilioProvider)
        assert provider.provider_name == "twilio"

    def test_callrail_provider_returned_by_default(self) -> None:
        env = {
            "SMS_PROVIDER": "",
            "CALLRAIL_API_KEY": "test",
            "CALLRAIL_ACCOUNT_ID": "ACC_TEST",
            "CALLRAIL_COMPANY_ID": "COM_TEST",
            "CALLRAIL_TRACKING_NUMBER": "+19525293750",
            "CALLRAIL_WEBHOOK_SECRET": "secret",
        }
        with patch.dict(os.environ, env, clear=False):
            provider = get_sms_provider()
        assert isinstance(provider, CallRailProvider)
        assert provider.provider_name == "callrail"

    def test_null_provider_returned(self) -> None:
        with patch.dict(os.environ, {"SMS_PROVIDER": "null"}):
            provider = get_sms_provider()
        assert isinstance(provider, NullProvider)
        assert provider.provider_name == "null"

    def test_unknown_provider_raises(self) -> None:
        with (
            patch.dict(os.environ, {"SMS_PROVIDER": "unknown"}),
            pytest.raises(ValueError, match="Unknown SMS provider"),
        ):
            get_sms_provider()

    def test_swap_is_config_only(self) -> None:
        """Requirement 17.4: swap requires zero code changes."""
        env_callrail = {
            "SMS_PROVIDER": "callrail",
            "CALLRAIL_API_KEY": "k",
            "CALLRAIL_ACCOUNT_ID": "a",
            "CALLRAIL_COMPANY_ID": "c",
            "CALLRAIL_TRACKING_NUMBER": "+10000000000",
            "CALLRAIL_WEBHOOK_SECRET": "s",
        }
        with patch.dict(os.environ, env_callrail, clear=False):
            p1 = get_sms_provider()
        assert isinstance(p1, CallRailProvider)

        with patch.dict(os.environ, {"SMS_PROVIDER": "twilio"}):
            p2 = get_sms_provider()
        assert isinstance(p2, TwilioProvider)

        # Both conform to the same protocol — same public API
        for p in (p1, p2):
            assert hasattr(p, "send_text")
            assert hasattr(p, "verify_webhook_signature")
            assert hasattr(p, "parse_inbound_webhook")
            assert hasattr(p, "provider_name")


@pytest.mark.unit
class TestRateLimitKeyNamespacing:
    """Requirement 17.2: rate limiter keys namespace by provider_name."""

    def test_twilio_and_callrail_keys_differ(self) -> None:
        twilio_tracker = SMSRateLimitTracker(
            provider="twilio",
            account_id="ACC123",
        )
        callrail_tracker = SMSRateLimitTracker(
            provider="callrail",
            account_id="ACC123",
        )
        assert twilio_tracker._redis_key != callrail_tracker._redis_key
        assert "twilio" in twilio_tracker._redis_key
        assert "callrail" in callrail_tracker._redis_key

    def test_redis_key_format(self) -> None:
        tracker = SMSRateLimitTracker(
            provider="twilio",
            account_id="ACC_X",
        )
        assert tracker._redis_key == "sms:rl:twilio:ACC_X"

    def test_same_provider_same_account_same_key(self) -> None:
        t1 = SMSRateLimitTracker(provider="twilio", account_id="A")
        t2 = SMSRateLimitTracker(provider="twilio", account_id="A")
        assert t1._redis_key == t2._redis_key

    def test_different_accounts_different_keys(self) -> None:
        t1 = SMSRateLimitTracker(provider="callrail", account_id="A")
        t2 = SMSRateLimitTracker(provider="callrail", account_id="B")
        assert t1._redis_key != t2._redis_key


@pytest.mark.unit
class TestTwilioProviderProtocolConformance:
    """Verify TwilioProvider has the same interface as other providers."""

    @pytest.mark.asyncio
    async def test_send_text_returns_provider_send_result(self) -> None:
        provider = TwilioProvider()
        result = await provider.send_text("+19525293750", "Hello")
        assert result.status == "sent"
        assert result.provider_message_id.startswith("SM")

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_returns_bool(self) -> None:
        provider = TwilioProvider()
        result = await provider.verify_webhook_signature({}, b"")
        assert isinstance(result, bool)

    def test_parse_inbound_webhook_returns_inbound_sms(self) -> None:
        provider = TwilioProvider()
        result = provider.parse_inbound_webhook(
            {
                "From": "+11234567890",
                "Body": "STOP",
                "MessageSid": "SM123",
                "To": "+19525293750",
            },
        )
        assert result.from_phone == "+11234567890"
        assert result.body == "STOP"

    def test_provider_name_is_twilio(self) -> None:
        assert TwilioProvider().provider_name == "twilio"
