"""Resend webhook signature verification.

Wraps the official ``resend.Webhooks.verify`` helper (Svix-format HMAC
signature) so the rest of the codebase has a typed exception, a single
import path, and a return value that includes the parsed JSON payload.

Validates: Estimate approval email portal — bounce handling.
"""

from __future__ import annotations

import json
from typing import Any

import resend


class ResendWebhookVerificationError(Exception):
    """Raised when Resend webhook signature does not verify."""


def verify_resend_webhook_signature(
    *,
    secret: str,
    headers: dict[str, str],
    raw_body: bytes,
) -> dict[str, Any]:
    """Verify a Resend (Svix-format) webhook and return the parsed payload.

    Resend's Python SDK exposes ``resend.Webhooks.verify(options)`` which
    handles the Svix algorithm internally (HMAC-SHA256 of
    ``{svix-id}.{svix-timestamp}.{body}`` with the base64-decoded secret
    minus the ``whsec_`` prefix, base64-encoded digest, constant-time
    compare). We delegate to it rather than hand-rolling HMAC and
    expose the parsed JSON payload to callers.

    Args:
        secret: Webhook signing secret (``whsec_…`` form).
        headers: Lowercased request headers dict containing
            ``svix-id``, ``svix-timestamp``, ``svix-signature``.
        raw_body: Raw request body bytes (UNMODIFIED — JSON
            re-serialization breaks signature).

    Returns:
        The parsed JSON payload dict.

    Raises:
        ResendWebhookVerificationError: If secret is missing, headers
            are missing, signature verification fails, or the body is
            not valid JSON.
    """
    if not secret:
        msg = "secret_not_configured"
        raise ResendWebhookVerificationError(msg)

    svix_id = headers.get("svix-id", "")
    svix_timestamp = headers.get("svix-timestamp", "")
    svix_signature = headers.get("svix-signature", "")
    if not (svix_id and svix_timestamp and svix_signature):
        msg = "missing_svix_headers"
        raise ResendWebhookVerificationError(msg)

    try:
        body_str = raw_body.decode("utf-8")
    except UnicodeDecodeError as e:
        msg = f"body_not_utf8: {e}"
        raise ResendWebhookVerificationError(msg) from e

    try:
        resend.Webhooks.verify(
            {
                "payload": body_str,
                "headers": {
                    "id": svix_id,
                    "timestamp": svix_timestamp,
                    "signature": svix_signature,
                },
                "webhook_secret": secret,
            }
        )
    except Exception as e:
        msg = f"signature_invalid: {e}"
        raise ResendWebhookVerificationError(msg) from e

    try:
        payload = json.loads(body_str)
    except ValueError as e:
        msg = f"body_not_json: {e}"
        raise ResendWebhookVerificationError(msg) from e
    if not isinstance(payload, dict):
        msg = "payload_not_dict"
        raise ResendWebhookVerificationError(msg)
    return payload
