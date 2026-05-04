"""Unit tests for the START re-opt-in keyword (F3).

Validates: F3 sign-off (run-20260504-185844-full).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from grins_platform.services.sms_service import (
    EXACT_OPT_IN_KEYWORDS,
    OPT_IN_CONFIRMATION_MSG,
    SMSService,
)


@pytest.mark.asyncio
class TestStartKeyword:
    """Tests for the START re-opt-in keyword path."""

    def _service(self, *, send_text_result=None) -> SMSService:
        """Build SMSService with mocked session + provider + lead-touch."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        provider = MagicMock()
        provider.send_text = AsyncMock(
            return_value=send_text_result or MagicMock(message_id="msg-1"),
        )

        service = SMSService(session)
        service.provider = provider  # type: ignore[assignment]
        # Patch lead-touch + audit-twin so we don't need a full DB.
        service._touch_lead_last_contacted = AsyncMock()  # type: ignore[method-assign]
        service._record_customer_sms_opt_in_audit = AsyncMock()  # type: ignore[method-assign]
        return service

    async def test_exact_opt_in_keywords_includes_start(self) -> None:
        """The keyword set must include START at minimum."""
        assert "start" in EXACT_OPT_IN_KEYWORDS

    async def test_handle_inbound_dispatches_to_opt_in_for_start(self) -> None:
        service = self._service()
        service._process_exact_opt_in = AsyncMock(  # type: ignore[method-assign]
            return_value={"action": "opt_in"},
        )

        result = await service.handle_inbound(
            from_phone="+19527373312",
            body="START",
            provider_sid="SM-1",
        )

        service._process_exact_opt_in.assert_awaited_once()
        assert result == {"action": "opt_in"}

    async def test_process_exact_opt_in_writes_consent_record(self) -> None:
        """A START keyword writes consent_method=text_start, consent_given=True."""
        service = self._service()
        with (
            patch(
                "grins_platform.services.sms_service.log_consent_opt_in_sms",
                new=AsyncMock(),
            ) as mock_audit_event,
        ):
            result = await service._process_exact_opt_in(
                "+19527373312", "start",
            )

        # The session.add call received the new consent record
        assert service.session.add.call_count == 1
        record = service.session.add.call_args.args[0]
        assert record.consent_method == "text_start"
        assert record.consent_given is True
        assert record.consent_type == "marketing"

        # Audit event emitted
        mock_audit_event.assert_awaited_once()

        # Provider got the OPT_IN_CONFIRMATION_MSG
        service.provider.send_text.assert_awaited_once()
        sent_args = service.provider.send_text.call_args
        assert sent_args.args[1] == OPT_IN_CONFIRMATION_MSG

        # Return shape
        assert result["action"] == "opt_in"
        assert result["message"] == OPT_IN_CONFIRMATION_MSG

    async def test_process_exact_opt_in_emits_persistent_audit(self) -> None:
        """The gap-05 persistent audit row goes through the dedicated helper."""
        service = self._service()
        with patch(
            "grins_platform.services.sms_service.log_consent_opt_in_sms",
            new=AsyncMock(),
        ):
            await service._process_exact_opt_in("+19527373312", "start")

        service._record_customer_sms_opt_in_audit.assert_awaited_once()
        kwargs = service._record_customer_sms_opt_in_audit.call_args.kwargs
        assert kwargs["action"] == "consent.opt_in_sms"
        assert kwargs["phone_e164"] == "+19527373312"
        assert kwargs["raw_body"] == "start"
