"""CallRail SMS provider - sends texts via CallRail v3 API.

Implements BaseSMSProvider Protocol against the verified contract
from Phase 0.5 (design.md "Phase 0.5 Verified CallRail API Contract").

Validates: Requirements 2.1-2.8, 2.10, 38, 44
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
from typing import Any

import httpx

from grins_platform.log_config import LoggerMixin
from grins_platform.services.sms.base import (
    InboundSMS,
    ProviderSendResult,
    enforce_recipient_allowlist,
)

# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------


class CallRailError(Exception):
    """Base CallRail error."""


class CallRailAuthError(CallRailError):
    """401 Unauthorized."""


class CallRailRateLimitError(CallRailError):
    """429 Too Many Requests."""

    def __init__(
        self,
        message: str = "Rate limited",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CallRailValidationError(CallRailError):
    """400 / 422 validation error."""


# ---------------------------------------------------------------------------
# Phone masking helper
# ---------------------------------------------------------------------------


def _mask_phone(phone: str) -> str:
    """Mask phone for logging: +1952***3312."""
    if len(phone) >= 8:
        return phone[:4] + "***" + phone[-4:]
    return "***"


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

_BASE_URL = "https://api.callrail.com"


class CallRailProvider(LoggerMixin):
    """SMS provider that sends via CallRail v3 text-messages API."""

    DOMAIN = "sms"

    def __init__(
        self,
        api_key: str,
        account_id: str,
        company_id: str,
        tracking_number: str,
        webhook_secret: str = "",
    ) -> None:
        super().__init__()
        self._api_key = api_key
        self._account_id = account_id
        self._company_id = company_id
        self._tracking_number = tracking_number
        self._webhook_secret = webhook_secret
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={
                "Authorization": f'Token token="{api_key}"',
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    # -- Protocol fields -----------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "callrail"

    # -- Core send -----------------------------------------------------------

    async def send_text(self, to: str, body: str) -> ProviderSendResult:
        """Send SMS via POST /v3/a/{account_id}/text-messages.json."""
        # Hard allow-list guard — no-op in production (env var unset),
        # enforced in dev/staging. Runs BEFORE any logging or network
        # I/O so a blocked send leaves no trail beyond the refusal log.
        enforce_recipient_allowlist(to, provider=self.provider_name)

        url = f"/v3/a/{self._account_id}/text-messages.json"
        payload = {
            "company_id": self._company_id,
            "tracking_number": self._tracking_number,
            "customer_phone_number": to,
            "content": body,
        }

        self.log_started("send_text", phone=_mask_phone(to))

        try:
            resp = await self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            self.log_failed("send_text", error=exc, phone=_mask_phone(to))
            msg = f"HTTP transport error: {exc}"
            raise CallRailError(msg) from exc

        # Capture useful headers
        x_request_id = resp.headers.get("x-request-id", "")
        rate_headers = self._extract_rate_headers(resp.headers)

        self._check_error_status(resp, to)

        data: dict[str, Any] = resp.json()

        # Parse conversation-oriented response
        conversation_id = str(data.get("id", ""))
        thread_id = ""
        recent = data.get("recent_messages")
        if isinstance(recent, list) and recent:
            first_msg: dict[str, Any] = recent[0]  # pyright: ignore[reportUnknownVariableType]
            sms_thread: Any = first_msg.get("sms_thread")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            if isinstance(sms_thread, dict):
                thread_id = str(sms_thread.get("id", ""))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]

        self.log_completed(
            "send_text",
            phone=_mask_phone(to),
            conversation_id=conversation_id,
            x_request_id=x_request_id,
            **rate_headers,
        )

        return ProviderSendResult(
            provider_message_id=conversation_id,
            provider_conversation_id=conversation_id,
            provider_thread_id=thread_id or None,
            status="sent",
            raw_response=data,
            request_id=x_request_id,
        )

    def _check_error_status(self, resp: httpx.Response, to: str) -> None:
        """Raise typed exceptions for non-200 responses."""
        if resp.status_code == 200:
            return
        if resp.status_code == 401:
            self.log_failed("send_text", phone=_mask_phone(to), status_code=401)
            raise CallRailAuthError
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("retry-after", "60"))
            self.log_failed("send_text", phone=_mask_phone(to), status_code=429)
            raise CallRailRateLimitError(retry_after=retry_after)
        if resp.status_code in (400, 422):
            self.log_failed(
                "send_text",
                phone=_mask_phone(to),
                status_code=resp.status_code,
            )
            msg = f"CallRail validation error ({resp.status_code}): {resp.text}"
            raise CallRailValidationError(msg)
        self.log_failed(
            "send_text",
            phone=_mask_phone(to),
            status_code=resp.status_code,
        )
        msg = f"Unexpected status {resp.status_code}: {resp.text}"
        raise CallRailError(msg)

    # -- Tracker listing -----------------------------------------------------

    async def list_tracking_numbers(self) -> list[dict[str, Any]]:
        """GET /v3/a/{account_id}/trackers.json."""
        url = f"/v3/a/{self._account_id}/trackers.json"
        resp = await self._client.get(url)
        if resp.status_code == 401:
            raise CallRailAuthError
        resp.raise_for_status()  # pyright: ignore[reportUnusedCallResult]
        data: dict[str, Any] = resp.json()
        trackers: list[dict[str, Any]] = data.get("trackers", [])
        return trackers

    # -- Webhook verification ------------------------------------------------

    async def verify_webhook_signature(
        self,
        headers: dict[str, str],
        raw_body: bytes,
    ) -> bool:
        """Verify CallRail webhook HMAC signature."""
        if not self._webhook_secret:
            return False
        signature = headers.get("x-callrail-signature", "")
        if not signature:
            return False
        expected = hmac.new(
            self._webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    # -- Inbound parsing -----------------------------------------------------

    def parse_inbound_webhook(self, payload: dict[str, Any]) -> InboundSMS:
        """Parse CallRail inbound SMS webhook payload."""
        return InboundSMS(
            from_phone=str(payload.get("customer_phone_number", "")),
            body=str(payload.get("content", "")),
            provider_sid=str(payload.get("id", "")),
            to_phone=str(payload.get("tracking_phone_number", "")),
        )

    # -- Rate-limit header extraction ----------------------------------------

    @staticmethod
    def _extract_rate_headers(headers: httpx.Headers) -> dict[str, int]:
        """Extract x-rate-limit-* headers as ints for logging/tracking."""
        result: dict[str, int] = {}
        for key in (
            "x-rate-limit-hourly-allowed",
            "x-rate-limit-hourly-used",
            "x-rate-limit-daily-allowed",
            "x-rate-limit-daily-used",
        ):
            val = headers.get(key)
            if val is not None:
                with contextlib.suppress(ValueError):
                    result[key.replace("-", "_").replace("x_", "")] = int(val)
        return result

    # -- Cleanup -------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
