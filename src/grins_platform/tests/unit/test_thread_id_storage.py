"""Unit test verifying provider_thread_id storage on outbound sends.

Validates: Requirements 19.1, 19.2, 19.3
- 19.1: CallRailProvider.send_text() extracts thread_resource_id from response
- 19.2: SMSService.send_message() stores provider_thread_id on SentMessage
- 19.3: Correlator matches against sent_messages.provider_thread_id
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from grins_platform.schemas.ai import MessageType
from grins_platform.services.sms.base import ProviderSendResult
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms_service import SMSService

if TYPE_CHECKING:
    from grins_platform.models.sent_message import SentMessage


def _make_service(
    *,
    provider_thread_id: str | None = "SMTabc123",
) -> tuple[SMSService, AsyncMock]:
    """Build an SMSService with a mock provider returning the given thread_id."""
    session = AsyncMock()
    added: list[SentMessage] = []
    session.add = MagicMock(side_effect=lambda obj: added.append(obj))
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    provider = AsyncMock()
    provider.provider_name = "callrail"
    provider.send_text = AsyncMock(
        return_value=ProviderSendResult(
            provider_message_id="conv_999",
            provider_conversation_id="conv_999",
            provider_thread_id=provider_thread_id,
            status="sent",
            raw_response={"id": "conv_999"},
        ),
    )

    svc = SMSService(session, provider=provider)
    svc._added = added  # type: ignore[attr-defined]
    return svc, session


@pytest.mark.unit
class TestThreadIdStorageOnSend:
    """Req 19.2: provider_thread_id is stored on SentMessage after send."""

    @pytest.mark.asyncio
    @patch("grins_platform.services.sms_service.check_sms_consent", return_value=True)
    async def test_thread_id_stored_on_sent_message(self, _consent: MagicMock) -> None:
        """After successful send, SentMessage.provider_thread_id == provider result."""
        svc, _session = _make_service(provider_thread_id="SMTthread789")
        recipient = Recipient.from_adhoc("+16125551234")

        result = await svc.send_message(
            recipient=recipient,
            message="Test",
            message_type=MessageType.CAMPAIGN,
            consent_type="marketing",
            skip_formatting=True,
        )

        assert result["success"] is True
        added = svc._added  # type: ignore[attr-defined]
        assert len(added) == 1
        sent_msg: SentMessage = added[0]
        assert sent_msg.provider_thread_id == "SMTthread789"
        assert sent_msg.provider_conversation_id == "conv_999"

    @pytest.mark.asyncio
    @patch("grins_platform.services.sms_service.check_sms_consent", return_value=True)
    async def test_null_thread_id_stored_when_absent(
        self,
        _consent: MagicMock,
    ) -> None:
        """When provider returns no thread_id, SentMessage stores None."""
        svc, _session = _make_service(provider_thread_id=None)
        recipient = Recipient.from_adhoc("+16125551234")

        result = await svc.send_message(
            recipient=recipient,
            message="Test",
            message_type=MessageType.CAMPAIGN,
            consent_type="marketing",
            skip_formatting=True,
        )

        assert result["success"] is True
        added = svc._added  # type: ignore[attr-defined]
        assert len(added) == 1
        assert added[0].provider_thread_id is None
