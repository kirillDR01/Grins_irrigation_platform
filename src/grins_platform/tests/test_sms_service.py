"""Property tests for SMS opt-in enforcement.

Property 13: SMS Opt-in Enforcement

Validates: Requirements 12.8, 12.9
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.schemas.ai import MessageType
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms_service import SMSConsentDeniedError, SMSService


@pytest.mark.asyncio
class TestSMSOptInProperty:
    """Property-based tests for SMS opt-in enforcement."""

    @given(
        message_type=st.sampled_from(list(MessageType)),
        message=st.text(min_size=1, max_size=160),
    )
    @settings(max_examples=20)
    async def test_opted_out_customers_cannot_receive_sms(
        self,
        message_type: MessageType,
        message: str,
    ) -> None:
        """Property: Customers without consent cannot receive SMS."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)
        recipient = Recipient(
            phone="+16125551234",
            source_type="customer",
            customer_id=uuid4(),
        )

        with (
            patch(
                "grins_platform.services.sms_service.check_sms_consent",
                return_value=False,
            ),
            pytest.raises(SMSConsentDeniedError),
        ):
            await service.send_message(
                recipient=recipient,
                message=message,
                message_type=message_type,
                consent_type="marketing",
            )

    @given(
        message_type=st.sampled_from(list(MessageType)),
    )
    @settings(max_examples=10)
    async def test_opted_in_customers_can_receive_sms(
        self,
        message_type: MessageType,
    ) -> None:
        """Property: Customers with consent can receive SMS."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)
        recipient = Recipient(
            phone="+16125551234",
            source_type="customer",
            customer_id=uuid4(),
        )

        # No recent messages
        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[],
        )

        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=True,
        ):
            result = await service.send_message(
                recipient=recipient,
                message="Test message",
                message_type=message_type,
            )

        assert result["success"] is True
        assert "message_id" in result

    async def test_phone_formatting_e164(self) -> None:
        """Test phone number formatting to E.164."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)

        # Test 10-digit number
        assert service._format_phone("6125551234") == "+16125551234"

        # Test with dashes
        assert service._format_phone("612-555-1234") == "+16125551234"

        # Test with parentheses
        assert service._format_phone("(612) 555-1234") == "+16125551234"

        # Test with country code
        assert service._format_phone("16125551234") == "+16125551234"

    async def test_webhook_opt_out_keywords(self) -> None:
        """Test webhook handles opt-out keywords."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)

        for keyword in ["STOP", "stop", "UNSUBSCRIBE", "cancel"]:
            result = await service.handle_webhook(
                from_phone="+16125551234",
                body=keyword,
                provider_sid="SM123",
            )
            assert result["action"] == "opt_out"

    async def test_webhook_confirmation_keywords(self) -> None:
        """Test webhook handles confirmation keywords."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)

        for keyword in ["YES", "yes", "confirm", "Y"]:
            result = await service.handle_webhook(
                from_phone="+16125551234",
                body=keyword,
                provider_sid="SM123",
            )
            assert result["action"] == "confirm"
