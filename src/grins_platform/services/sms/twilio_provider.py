"""Twilio SMS provider — stub ported from SMSService._send_via_twilio().

Conforms to BaseSMSProvider Protocol with no behavior change from the
original stub. In production this would use the Twilio client SDK.

Validates: Requirements 1.2, 1.8
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from grins_platform.services.sms.base import InboundSMS, ProviderSendResult


class TwilioProvider:
    """SMS provider stub that mimics the original Twilio placeholder."""

    @property
    def provider_name(self) -> str:
        return "twilio"

    async def send_text(self, to: str, body: str) -> ProviderSendResult:  # noqa: ARG002
        """Send SMS via Twilio API (stub).

        Mirrors the original ``SMSService._send_via_twilio()`` behaviour:
        returns a synthetic SID without making a real API call.
        """
        sid = f"SM{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return ProviderSendResult(provider_message_id=sid, status="sent")

    async def verify_webhook_signature(
        self,
        headers: dict[str, str],  # noqa: ARG002
        raw_body: bytes,  # noqa: ARG002
    ) -> bool:
        """Verify Twilio webhook signature (stub — always returns False)."""
        return False

    def parse_inbound_webhook(self, payload: dict[str, Any]) -> InboundSMS:
        """Parse Twilio inbound SMS webhook payload (stub)."""
        return InboundSMS(
            from_phone=str(payload.get("From", "")),
            body=str(payload.get("Body", "")),
            provider_sid=str(payload.get("MessageSid", "")),
            to_phone=str(payload.get("To", "")),
        )
