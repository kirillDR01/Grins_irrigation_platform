"""Security utilities for AI features.

Validates: AI Assistant Requirements 17.1-17.10
"""

import base64
import hashlib
import hmac
import os
import re
from typing import Any, ClassVar


class InputSanitizer:
    """Sanitize user input for AI prompts.

    Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
    """

    # Dangerous characters to remove
    DANGEROUS_CHARS: ClassVar[list[str]] = ["<", ">", "{", "}", "[", "]", "|"]

    # Prompt injection patterns (case-insensitive)
    INJECTION_PATTERNS: ClassVar[list[str]] = [
        r"ignore\s+previous\s+instructions",
        r"disregard\s+all\s+instructions",
        r"forget\s+above\s+instructions",
        r"system:\s*you\s+are\s+now",
        r"assistant:\s*i\s+will",
        r"user:\s*tell\s+me",
        r"<\|endoftext\|>",
        r"\[inst\].*\[/inst\]",
        r"###\s*instruction:",
        r"you\s+are\s+now\s+a",
        r"act\s+as\s+a",
        r"pretend\s+to\s+be",
        r"roleplay\s+as",
    ]

    def sanitize_user_input(self, user_input: str | None) -> str:
        """Sanitize user input for inclusion in AI prompts.

        Args:
            user_input: Raw user input

        Returns:
            Sanitized input safe for AI prompts
        """
        if not user_input:
            return ""

        # Check for prompt injection
        if self._detect_prompt_injection(user_input):
            return ""

        # Remove dangerous characters
        sanitized = user_input
        for char in self.DANGEROUS_CHARS:
            sanitized = sanitized.replace(char, "")

        # Normalize whitespace
        sanitized = " ".join(sanitized.split())

        # Enforce length limit
        if len(sanitized) > 2000:
            sanitized = sanitized[:2000]

        return sanitized

    def _detect_prompt_injection(self, text: str) -> bool:
        """Detect prompt injection attempts.

        Args:
            text: Input text to check

        Returns:
            True if injection detected, False otherwise
        """
        text_lower = text.lower()
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def validate_structured_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate and sanitize structured input.

        Args:
            data: Dictionary of input data

        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_user_input(value)
            else:
                sanitized[key] = value
        return sanitized


def validate_twilio_signature(
    url: str,
    params: dict[str, Any],
    signature: str,
) -> bool:
    """Validate Twilio webhook signature.

    Args:
        url: Full webhook URL
        params: Request parameters
        signature: X-Twilio-Signature header value

    Returns:
        True if signature is valid, False otherwise

    Validates: Requirement 17.9
    """
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    if not auth_token:
        return False

    # Build data string: URL + sorted params
    data = url
    for key in sorted(params.keys()):
        data += key + str(params[key])

    # Compute HMAC-SHA1
    expected = hmac.new(
        auth_token.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    ).digest()

    # Encode as base64
    expected_signature = base64.b64encode(expected).decode("utf-8")

    # Compare signatures
    return hmac.compare_digest(expected_signature, signature)
