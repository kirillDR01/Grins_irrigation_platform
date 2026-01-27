"""Property tests for SMS opt-in enforcement.

Property 13: SMS Opt-in Enforcement

Validates: Requirements 12.8, 12.9
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.schemas.ai import MessageType
from grins_platform.services.sms_service import SMSOptInError, SMSService


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
        """Property: Customers without opt-in cannot receive SMS."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)

        with pytest.raises(SMSOptInError):
            await service.send_message(
                customer_id=uuid4(),
                phone="6125551234",
                message=message,
                message_type=message_type,
                sms_opt_in=False,  # Not opted in
            )

    @given(
        message_type=st.sampled_from(list(MessageType)),
    )
    @settings(max_examples=10)
    async def test_opted_in_customers_can_receive_sms(
        self,
        message_type: MessageType,
    ) -> None:
        """Property: Customers with opt-in can receive SMS."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)

        # Mock repository methods
        mock_message = AsyncMock()
        mock_message.id = uuid4()
        service.message_repo.create = AsyncMock(return_value=mock_message)
        service.message_repo.update = AsyncMock(return_value=mock_message)
        # No recent messages
        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[],
        )

        result = await service.send_message(
            customer_id=uuid4(),
            phone="6125551234",
            message="Test message",
            message_type=message_type,
            sms_opt_in=True,  # Opted in
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
                twilio_sid="SM123",
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
                twilio_sid="SM123",
            )
            assert result["action"] == "confirm"
