"""SMS segment counter — GSM-7 vs UCS-2 detection and segment calculation.

Includes the auto-appended sender prefix and STOP footer in the count.
"""

from __future__ import annotations

import math
import os
from typing import Literal

# GSM-7 basic character set (standard 7-bit encoding)
_GSM7_BASIC: frozenset[str] = frozenset(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ"
    " !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "ÄÖÑܧ¿abcdefghijklmnopqrstuvwxyz"
    "äöñüà",
)

# GSM-7 extension characters (each costs 2 chars: escape + char)
_GSM7_EXTENSION: frozenset[str] = frozenset("^{}\\[~]|€")

Encoding = Literal["GSM-7", "UCS-2"]

# Defaults
_DEFAULT_PREFIX = "Grin's Irrigation: "
_DEFAULT_FOOTER = " Reply STOP to opt out."


def _detect_encoding(text: str) -> Encoding:
    """Return 'GSM-7' if all chars are in GSM-7 alphabet, else 'UCS-2'."""
    for ch in text:
        if ch not in _GSM7_BASIC and ch not in _GSM7_EXTENSION:
            return "UCS-2"
    return "GSM-7"


def _gsm7_char_count(text: str) -> int:
    """Count GSM-7 character units (extension chars cost 2)."""
    return sum(2 if ch in _GSM7_EXTENSION else 1 for ch in text)


def count_segments(
    text: str,
    *,
    include_prefix: bool = True,
    include_footer: bool = True,
) -> tuple[Encoding, int, int]:
    """Count SMS segments for *text* including prefix and STOP footer.

    Returns ``(encoding, segments, char_count)`` where *char_count* is
    the total character units (GSM-7 extension chars count as 2).
    """
    prefix = (
        os.environ.get("SMS_SENDER_PREFIX", _DEFAULT_PREFIX) if include_prefix else ""
    )
    footer = _DEFAULT_FOOTER if include_footer else ""
    full = f"{prefix}{text}{footer}"

    encoding = _detect_encoding(full)

    if encoding == "GSM-7":
        chars = _gsm7_char_count(full)
        segments = 1 if chars <= 160 else math.ceil(chars / 153)
    else:
        chars = len(full)
        segments = 1 if chars <= 70 else math.ceil(chars / 67)

    return encoding, segments, chars
