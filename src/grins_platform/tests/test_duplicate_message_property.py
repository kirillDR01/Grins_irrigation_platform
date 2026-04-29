"""Property test for duplicate message prevention.

Property 11: Duplicate Message Prevention

Validates: Requirement 7.7
"""

from datetime import datetime, timedelta
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
from grins_platform.services.sms_service import SMSService


def _make_recipient() -> tuple[Recipient, str]:
    cid = uuid4()
    phone = "+16125551234"
    return (
        Recipient(phone=phone, source_type="customer", customer_id=cid),
        phone,
    )


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
        """Property: Duplicate messages within 24 hours are prevented."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)
        recipient, _ = _make_recipient()

        mock_recent = AsyncMock()
        mock_recent.id = uuid4()
        mock_recent.created_at = datetime.now() - timedelta(hours=12)

        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[mock_recent],
        )

        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=True,
        ):
            result = await service.send_message(
                recipient=recipient,
                message=message,
                message_type=message_type,
            )

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
        """Property: Messages after 24 hours are allowed."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)
        recipient, _ = _make_recipient()

        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[],
        )

        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=True,
        ):
            result = await service.send_message(
                recipient=recipient,
                message=message,
                message_type=message_type,
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
        """Property: Different message types are allowed even if recent."""
        if message_type1 == message_type2:
            return

        mock_session = AsyncMock()
        service = SMSService(mock_session)
        recipient, _ = _make_recipient()

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
                message_type=message_type2,
            )

        assert result["success"] is True
        assert "message_id" in result

    async def test_duplicate_check_uses_correct_timeframe(self) -> None:
        """Test that duplicate check uses 24-hour timeframe."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)
        recipient, _ = _make_recipient()

        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[],
        )

        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=True,
        ):
            await service.send_message(
                recipient=recipient,
                message="Test",
                message_type=MessageType.APPOINTMENT_CONFIRMATION,
            )

        service.message_repo.get_by_customer_and_type.assert_called_once_with(
            customer_id=recipient.customer_id,
            message_type=MessageType.APPOINTMENT_CONFIRMATION,
            hours_back=24,
            appointment_id=None,
        )

    async def test_appointment_confirmation_dedupe_scoped_per_appointment(
        self,
    ) -> None:
        """Bug #4 fix: different appointment_ids for same customer both succeed."""
        mock_session = AsyncMock()
        service = SMSService(mock_session)
        recipient, _ = _make_recipient()
        appt_1 = uuid4()
        appt_2 = uuid4()

        # No prior messages for either appointment
        service.message_repo.get_by_customer_and_type = AsyncMock(
            return_value=[],
        )

        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=True,
        ):
            result1 = await service.send_message(
                recipient=recipient,
                message="Appt 1 confirmed",
                message_type=MessageType.APPOINTMENT_CONFIRMATION,
                appointment_id=appt_1,
            )
            result2 = await service.send_message(
                recipient=recipient,
                message="Appt 2 confirmed",
                message_type=MessageType.APPOINTMENT_CONFIRMATION,
                appointment_id=appt_2,
            )

        assert result1["success"] is True
        assert result2["success"] is True

        # Verify dedupe was scoped per appointment_id
        calls = service.message_repo.get_by_customer_and_type.call_args_list
        assert (
            calls[0].kwargs.get("appointment_id") == appt_1
            or calls[0][1].get("appointment_id") == appt_1
        )
        assert (
            calls[1].kwargs.get("appointment_id") == appt_2
            or calls[1][1].get("appointment_id") == appt_2
        )
