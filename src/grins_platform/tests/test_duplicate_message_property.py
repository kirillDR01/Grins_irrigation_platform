"""Property test for duplicate message prevention.

Property 11: Duplicate Message Prevention

Validates: Requirement 7.7
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.schemas.ai import MessageType
from grins_platform.services.sms_service import SMSService


@pytest.mark.asyncio
class TestDuplicateMessageProperty:
    """Property-based tests for duplicate message prevention."""

    @given(
        message_type=st.sampled_from(list(MessageType)),
        message=st.text(min_size=1, max_size=160),
    )
    @settings(max_examples=20)
    async def test_duplicate_message_within_24_hours_prevented(
        self,
        message_type: MessageType,
        message: str,
    ) -> None:
        """Property: Duplicate messages within 24 hours are prevented.

        Given a customer and message type, if a message was sent within
        the last 24 hours, attempting to send the same type again should
        be prevented.
        """
        mock_session = AsyncMock()
        service = SMSService(mock_session)

        customer_id = uuid4()
        phone = "6125551234"

        # Mock a recent message of the same type
        mock_recent_message = AsyncMock()
        mock_recent_message.id = uuid4()
        mock_recent_message.customer_id = customer_id
        mock_recent_message.message_type = message_type.value
        mock_recent_message.created_at = datetime.now() - timedelta(hours=12)

        # Mock repository to return the recent message
        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[mock_recent_message],
        )

        # Attempt to send duplicate should be prevented
        result = await service.send_message(
            customer_id=customer_id,
            phone=phone,
            message=message,
            message_type=message_type,
            sms_opt_in=True,
        )

        # Should indicate duplicate was prevented
        assert result["success"] is False
        assert "duplicate" in result.get("reason", "").lower()

    @given(
        message_type=st.sampled_from(list(MessageType)),
        message=st.text(min_size=1, max_size=160),
    )
    @settings(max_examples=20)
    async def test_message_after_24_hours_allowed(
        self,
        message_type: MessageType,
        message: str,
    ) -> None:
        """Property: Messages after 24 hours are allowed.

        Given a customer and message type, if the last message was sent
        more than 24 hours ago, a new message should be allowed.
        """
        mock_session = AsyncMock()
        service = SMSService(mock_session)

        customer_id = uuid4()
        phone = "6125551234"

        # Mock an old message (>24 hours ago)
        mock_old_message = AsyncMock()
        mock_old_message.id = uuid4()
        mock_old_message.customer_id = customer_id
        mock_old_message.message_type = message_type.value
        mock_old_message.created_at = datetime.now() - timedelta(hours=25)

        # Mock repository to return empty (old message filtered out)
        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[],  # No recent messages
        )

        # Mock successful send
        mock_new_message = AsyncMock()
        mock_new_message.id = uuid4()
        service.message_repo.create = AsyncMock(return_value=mock_new_message)
        service.message_repo.update = AsyncMock(return_value=mock_new_message)

        # Should allow sending
        result = await service.send_message(
            customer_id=customer_id,
            phone=phone,
            message=message,
            message_type=message_type,
            sms_opt_in=True,
        )

        assert result["success"] is True
        assert "message_id" in result

    @given(
        message_type1=st.sampled_from(list(MessageType)),
        message_type2=st.sampled_from(list(MessageType)),
    )
    @settings(max_examples=20)
    async def test_different_message_types_allowed(
        self,
        message_type1: MessageType,
        message_type2: MessageType,
    ) -> None:
        """Property: Different message types are allowed even if recent.

        Given a customer, if a message of type A was sent recently,
        a message of type B should still be allowed.
        """
        # Skip if same type
        if message_type1 == message_type2:
            return

        mock_session = AsyncMock()
        service = SMSService(mock_session)

        customer_id = uuid4()
        phone = "6125551234"

        # Mock a recent message of type1
        mock_recent_message = AsyncMock()
        mock_recent_message.id = uuid4()
        mock_recent_message.customer_id = customer_id
        mock_recent_message.message_type = message_type1.value
        mock_recent_message.created_at = datetime.now() - timedelta(hours=1)

        # Mock repository to return empty for type2 (different type)
        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[],  # No recent messages of type2
        )

        # Mock successful send
        mock_new_message = AsyncMock()
        mock_new_message.id = uuid4()
        service.message_repo.create = AsyncMock(return_value=mock_new_message)
        service.message_repo.update = AsyncMock(return_value=mock_new_message)

        # Should allow sending type2
        result = await service.send_message(
            customer_id=customer_id,
            phone=phone,
            message="Test message",
            message_type=message_type2,
            sms_opt_in=True,
        )

        assert result["success"] is True
        assert "message_id" in result

    async def test_duplicate_check_uses_correct_timeframe(self) -> None:
        """Test that duplicate check uses 24-hour timeframe."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)

        customer_id = uuid4()
        message_type = MessageType.APPOINTMENT_CONFIRMATION

        # Mock repository calls
        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[],
        )

        # Mock successful message creation and update
        mock_message = AsyncMock()
        mock_message.id = uuid4()
        service.message_repo.create = AsyncMock(return_value=mock_message)
        service.message_repo.update = AsyncMock(return_value=mock_message)

        # Attempt to send
        await service.send_message(
            customer_id=customer_id,
            phone="6125551234",
            message="Test",
            message_type=message_type,
            sms_opt_in=True,
        )

        # Verify repository was called with 24-hour timeframe
        service.message_repo.get_by_customer_and_type.assert_called_once_with(
            customer_id=customer_id,
            message_type=message_type,
            hours_back=24,
        )
