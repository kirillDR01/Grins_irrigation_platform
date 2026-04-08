"""SMS provider abstraction: Protocol, result, and inbound dataclasses.

Defines the pluggable provider interface (Strategy pattern) and the
value objects returned by all providers.

Validates: Requirements 1.1, 1.7, 22.1, 38
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class RecipientNotAllowedError(Exception):
    """Raised when a send is blocked by ``SMS_TEST_PHONE_ALLOWLIST``.

    This is an *intentional* refusal, not a provider failure — the hard
    guard is configured per-environment (dev/staging) to make it
    impossible to accidentally text a number that isn't on the explicit
    test allow-list. Production leaves ``SMS_TEST_PHONE_ALLOWLIST``
    unset so the guard is a no-op there.
    """


_DIGITS_RE = re.compile(r"\D")


def _normalize_phone_for_comparison(phone: str) -> str:
    """Return an E.164-ish form for allow-list matching.

    Accepts any of ``+19527373312``, ``9527373312``, ``(952) 737-3312``
    and collapses them to the same canonical form so an operator
    pasting either format into the env var works. Non-US numbers
    should be passed as full E.164 and are compared verbatim after
    digit extraction.
    """
    if not phone:
        return ""
    digits = _DIGITS_RE.sub("", phone)
    if len(digits) == 10:
        digits = "1" + digits
    return f"+{digits}" if digits else ""


def _load_allowlist() -> list[str] | None:
    """Parse the ``SMS_TEST_PHONE_ALLOWLIST`` env var.

    Returns:
        A list of normalized E.164 phones when the var is set and
        non-empty, or ``None`` when the var is unset / empty (meaning
        "no restriction, allow all sends" — the production default).
    """
    raw = os.environ.get("SMS_TEST_PHONE_ALLOWLIST", "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    normalized = [_normalize_phone_for_comparison(p) for p in parts]
    # Drop any entries that normalized to empty (bogus input like a lone comma).
    return [p for p in normalized if p] or None


def enforce_recipient_allowlist(to: str, *, provider: str) -> None:
    """Raise :class:`RecipientNotAllowedError` if ``to`` is not allow-listed.

    This is the hard guard that SMS providers call at the top of
    ``send_text`` before any network I/O. If ``SMS_TEST_PHONE_ALLOWLIST``
    is unset or empty the call is a no-op (production path).

    Args:
        to: Destination phone in any format — will be normalized before
            comparison.
        provider: Provider name used purely for the error message and
            logging context.

    Raises:
        RecipientNotAllowedError: If the guard is active and ``to`` is
            not in the allow-list.
    """
    allowlist = _load_allowlist()
    if allowlist is None:
        return
    normalized_to = _normalize_phone_for_comparison(to)
    if normalized_to in allowlist:
        return
    msg = (
        f"recipient_not_in_allowlist: provider={provider} "
        f"(set SMS_TEST_PHONE_ALLOWLIST to override for dev/staging; "
        f"leave unset in production)"
    )
    raise RecipientNotAllowedError(msg)


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
    """Parsed inbound SMS from any provider.

    Note on ``from_phone``: CallRail masks customer phone numbers in
    inbound webhook payloads (e.g. ``***3312``), so for CallRail this
    field is the masked form, not E.164. Correlation back to a sent
    campaign must go through ``thread_id`` (the provider's conversation
    thread), not phone matching. Twilio and other providers that send
    full phone numbers can populate ``from_phone`` normally.
    """

    from_phone: str
    body: str
    provider_sid: str
    to_phone: str | None = None
    thread_id: str | None = None
    conversation_id: str | None = None


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
