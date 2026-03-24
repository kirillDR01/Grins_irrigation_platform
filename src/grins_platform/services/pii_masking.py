"""PII masking structlog processor.

Automatically masks personally identifiable information in log output:
- Phone numbers: show last 4 digits only (***1234)
- Email addresses: show first char + domain (j***@example.com)
- Street addresses: fully masked (***MASKED***)
- Card numbers: REDACTED
- JWT tokens, API keys, passwords, Stripe customer IDs: REDACTED
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging

    import structlog

# Patterns for PII detection
_PHONE_PATTERN = re.compile(
    r"\b\d{10,11}\b"
    r"|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"
    r"|\b\(\d{3}\)\s?\d{3}[-.\s]\d{4}\b",
)
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
)
_CARD_PATTERN = re.compile(
    r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
)

# Keys that contain PII and need masking
_PHONE_KEYS = frozenset(
    {
        "phone",
        "phone_number",
        "mobile",
        "cell",
        "telephone",
        "fax",
    },
)
_EMAIL_KEYS = frozenset({"email", "email_address", "e_mail"})
_ADDRESS_KEYS = frozenset(
    {
        "address",
        "street",
        "street_address",
        "full_address",
        "mailing_address",
    },
)
_CARD_KEYS = frozenset(
    {
        "card_number",
        "card_num",
        "cc_number",
        "credit_card",
    },
)
_REDACT_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "jwt",
        "api_key",
        "apikey",
        "auth_token",
        "access_token",
        "refresh_token",
        "stripe_customer_id",
        "stripe_id",
    },
)


def mask_phone(value: str) -> str:
    """Mask phone number, showing only last 4 digits."""
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 4:
        return f"***{digits[-4:]}"
    return "***MASKED***"


def mask_email(value: str) -> str:
    """Mask email, showing first char + domain."""
    if "@" in value:
        local, domain = value.rsplit("@", 1)
        if local:
            return f"{local[0]}***@{domain}"
    return "***@***"


def mask_address(_value: str) -> str:
    """Fully mask street address."""
    return "***MASKED***"


def _mask_value_by_key(key: str, value: object) -> object:
    """Mask a value based on its key name."""
    if not isinstance(value, str) or not value:
        return value

    key_lower = key.lower()

    if key_lower in _REDACT_KEYS:
        return "REDACTED"
    if key_lower in _PHONE_KEYS:
        return mask_phone(value)
    if key_lower in _EMAIL_KEYS:
        return mask_email(value)
    if key_lower in _ADDRESS_KEYS:
        return mask_address(value)
    if key_lower in _CARD_KEYS:
        return "REDACTED"

    return value


def _mask_string_inline(value: str) -> str:
    """Mask PII patterns found inline in string values."""
    result = _CARD_PATTERN.sub("REDACTED", value)
    result = _EMAIL_PATTERN.sub(
        lambda m: mask_email(m.group(0)),
        result,
    )
    return _PHONE_PATTERN.sub(
        lambda m: mask_phone(m.group(0)),
        result,
    )


def _mask_recursive(value: object) -> object:
    """Recursively mask PII in nested structures."""
    if isinstance(value, dict):
        return {k: _mask_value_by_key(k, _mask_recursive(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_recursive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask_recursive(item) for item in value)
    if isinstance(value, str):
        return _mask_string_inline(value)
    return value


def pii_masking_processor(
    _logger: logging.Logger | structlog.stdlib.BoundLogger,
    _method_name: str,
    event_dict: dict[str, object],
) -> dict[str, object]:
    """Structlog processor that masks PII fields in log output."""
    masked: dict[str, object] = {}
    for key, value in event_dict.items():
        masked_value = _mask_value_by_key(key, value)
        if masked_value is value:
            masked_value = _mask_recursive(value)
        masked[key] = masked_value
    return masked
