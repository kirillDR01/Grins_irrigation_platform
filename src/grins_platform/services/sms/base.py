"""SMS provider abstraction: Protocol, result, and inbound dataclasses.

Defines the pluggable provider interface (Strategy pattern) and the
value objects returned by all providers.

Validates: Requirements 1.1, 1.7, 22.1, 38
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ProviderSendResult:
    """Result from a provider send_text call.

    Includes CallRail-specific fields (provider_conversation_id,
    provider_thread_id) that are None for providers that don't use them.
    """

    provider_message_id: str
    status: str  # "sent", "queued", "failed"
    provider_conversation_id: str | None = None
    provider_thread_id: str | None = None
    raw_response: dict[str, Any] | None = None
    request_id: str | None = None


@dataclass(frozen=True)
class InboundSMS:
    """Parsed inbound SMS from any provider."""

    from_phone: str  # E.164
    body: str
    provider_sid: str
    to_phone: str | None = None


@runtime_checkable
class BaseSMSProvider(Protocol):
    """Protocol that all SMS providers must satisfy."""

    @property
    def provider_name(self) -> str: ...

    async def send_text(self, to: str, body: str) -> ProviderSendResult: ...

    async def verify_webhook_signature(
        self,
        headers: dict[str, str],
        raw_body: bytes,
    ) -> bool: ...

    def parse_inbound_webhook(self, payload: dict[str, Any]) -> InboundSMS: ...
