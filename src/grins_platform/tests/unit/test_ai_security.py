"""Tests for AI security utilities.

Validates: AI Assistant Requirements 17.1-17.10
"""

import base64
import hashlib
import hmac
import os
from unittest.mock import patch

import pytest

from grins_platform.services.ai.security import validate_twilio_signature


@pytest.mark.unit
class TestTwilioSignatureValidation:
    """Test Twilio webhook signature validation."""

    def test_valid_signature(self) -> None:
        """Test that valid signature is accepted."""
        auth_token = "test_auth_token"
        url = "https://example.com/webhook"
        params = {"From": "+16125551234", "Body": "Hello"}

        # Generate valid signature
        data = url + "Body" + params["Body"] + "From" + params["From"]
        expected = hmac.new(
            auth_token.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(expected).decode("utf-8")

        with patch.dict(os.environ, {"TWILIO_AUTH_TOKEN": auth_token}):
            assert validate_twilio_signature(url, params, signature)

    def test_invalid_signature(self) -> None:
        """Test that invalid signature is rejected."""
        auth_token = "test_auth_token"
        url = "https://example.com/webhook"
        params = {"From": "+16125551234", "Body": "Hello"}
        invalid_signature = "invalid_signature"

        with patch.dict(os.environ, {"TWILIO_AUTH_TOKEN": auth_token}):
            assert not validate_twilio_signature(url, params, invalid_signature)

    def test_missing_auth_token(self) -> None:
        """Test that missing auth token rejects all signatures."""
        url = "https://example.com/webhook"
        params = {"From": "+16125551234"}
        signature = "any_signature"

        with patch.dict(os.environ, {"TWILIO_AUTH_TOKEN": ""}):
            assert not validate_twilio_signature(url, params, signature)

    def test_tampered_params(self) -> None:
        """Test that tampered params are detected."""
        auth_token = "test_auth_token"
        url = "https://example.com/webhook"
        original_params = {"From": "+16125551234", "Body": "Hello"}

        # Generate signature for original params
        data = url + "Body" + original_params["Body"] + "From" + original_params["From"]
        expected = hmac.new(
            auth_token.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(expected).decode("utf-8")

        # Tamper with params
        tampered_params = {"From": "+16125551234", "Body": "Tampered"}

        with patch.dict(os.environ, {"TWILIO_AUTH_TOKEN": auth_token}):
            assert not validate_twilio_signature(url, tampered_params, signature)

    def test_empty_params(self) -> None:
        """Test signature validation with empty params."""
        auth_token = "test_auth_token"
        url = "https://example.com/webhook"
        params: dict[str, str] = {}

        # Generate valid signature for empty params
        data = url
        expected = hmac.new(
            auth_token.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(expected).decode("utf-8")

        with patch.dict(os.environ, {"TWILIO_AUTH_TOKEN": auth_token}):
            assert validate_twilio_signature(url, params, signature)
