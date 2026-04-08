"""Null SMS provider for testing — records sends in memory.

Validates: Requirement 1.9
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from grins_platform.services.sms.base import InboundSMS, ProviderSendResult


@dataclass
class NullProvider:
    """SMS provider that records all sends in memory without side effects."""

    sent: list[dict[str, str]] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]

    @property
    def provider_name(self) -> str:
        return "null"

    async def send_text(self, to: str, body: str) -> ProviderSendResult:
        msg_id = str(uuid.uuid4())
        self.sent.append({"to": to, "body": body, "id": msg_id})
        return ProviderSendResult(provider_message_id=msg_id, status="sent")

    async def verify_webhook_signature(
        self,
        headers: dict[str, str],  # noqa: ARG002
        raw_body: bytes,  # noqa: ARG002
    ) -> bool:
        return True

    def parse_inbound_webhook(self, payload: dict[str, Any]) -> InboundSMS:  # noqa: ARG002
        return InboundSMS(
            from_phone="+10000000000",
            body="test inbound",
            provider_sid="null-test",
            to_phone="+10000000001",
        )
