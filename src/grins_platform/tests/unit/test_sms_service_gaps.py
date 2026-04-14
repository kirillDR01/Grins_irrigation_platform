"""Unit tests for SMS_Service STOP keywords, consent check, and time window.

Validates: Requirements 8.1-8.6, 9.1-9.5
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from grins_platform.services.campaign_response_service import CorrelationResult
from grins_platform.services.sms_service import (
    CT_TZ,
    SMSService,
)


def _make_service() -> SMSService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    return SMSService(session)


# --- 10.1: Exact opt-out keywords ---


@pytest.mark.unit
class TestExactOptOutKeywords:
    """Test each exact keyword individually with various casing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "keyword",
        [
            "STOP",
            "stop",
            "Stop",
            "QUIT",
            "quit",
            "CANCEL",
            "cancel",
            "UNSUBSCRIBE",
            "unsubscribe",
            "END",
            "end",
            "REVOKE",
            "revoke",
        ],
    )
    async def test_exact_keyword_triggers_opt_out(self, keyword: str) -> None:
        """Each exact keyword creates opt-out SmsConsentRecord."""
        service = _make_service()
        result = await service.handle_inbound("+16125551234", keyword, "SM123")

        assert result["action"] == "opt_out"
        # session.add called for SmsConsentRecord + AuditLog
        assert service.session.add.call_count >= 1
        added = service.session.add.call_args_list[0][0][0]
        assert added.consent_given is False
        assert added.opt_out_method == "text_stop"
        assert added.opt_out_confirmation_sent is True

    @pytest.mark.asyncio
    async def test_keyword_with_whitespace(self) -> None:
        """Keywords with leading/trailing whitespace still match."""
        service = _make_service()
        result = await service.handle_inbound("+16125551234", "  STOP  ", "SM123")
        assert result["action"] == "opt_out"

    @pytest.mark.asyncio
    async def test_non_keyword_not_opt_out(self) -> None:
        """Non-keyword messages don't trigger opt-out."""
        service = _make_service()
        result = await service.handle_inbound(
            "+16125551234",
            "Hello there",
            "SM123",
        )
        assert result["action"] != "opt_out"
        service.session.add.assert_not_called()


# --- 10.2: Informal opt-out phrases ---


@pytest.mark.unit
class TestInformalOptOut:
    """Test informal opt-out phrase detection."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "phrase",
        [
            "stop texting me",
            "take me off the list",
            "no more texts",
            "opt out",
            "don't text me",
        ],
    )
    async def test_informal_phrase_flags_for_review(self, phrase: str) -> None:
        """Informal phrases flag for admin review, no auto opt-out."""
        service = _make_service()
        result = await service.handle_inbound("+16125551234", phrase, "SM123")

        assert result["action"] == "informal_opt_out_flagged"
        service.session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_informal_phrase_in_longer_message(self) -> None:
        """Informal phrase embedded in longer message still detected."""
        service = _make_service()
        result = await service.handle_inbound(
            "+16125551234",
            "Please stop texting me, I don't want these",
            "SM123",
        )
        assert result["action"] == "informal_opt_out_flagged"


# --- 10.3: Consent check ---


@pytest.mark.unit
class TestConsentCheck:
    """Test check_sms_consent_legacy method."""

    @pytest.mark.asyncio
    async def test_opted_out_phone_returns_false(self) -> None:
        """Opted-out phone → False."""
        service = _make_service()
        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=False,
        ):
            assert await service.check_sms_consent_legacy("6125551234") is False

    @pytest.mark.asyncio
    async def test_opted_in_phone_returns_true(self) -> None:
        """Opted-in phone → True."""
        service = _make_service()
        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=True,
        ):
            assert await service.check_sms_consent_legacy("6125551234") is True

    @pytest.mark.asyncio
    async def test_no_records_returns_true(self) -> None:
        """No consent records → default True."""
        service = _make_service()
        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=True,
        ):
            assert await service.check_sms_consent_legacy("6125551234") is True


# --- 10.4: Time window enforcement ---


@pytest.mark.unit
class TestTimeWindow:
    """Test enforce_time_window method."""

    def test_759am_ct_defers(self) -> None:
        """7:59 AM CT → defer to 8:00 AM."""
        service = _make_service()
        fake_now = datetime(2026, 3, 10, 7, 59, 0, tzinfo=CT_TZ)
        with patch("grins_platform.services.sms_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = service.enforce_time_window("+16125551234", "test", "automated")

        assert result is not None
        assert result.hour == 8
        assert result.minute == 0
        assert result.date() == fake_now.date()  # same day, before window

    def test_800am_ct_sends(self) -> None:
        """8:00 AM CT → send immediately."""
        service = _make_service()
        fake_now = datetime(2026, 3, 10, 8, 0, 0, tzinfo=CT_TZ)
        with patch("grins_platform.services.sms_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = service.enforce_time_window("+16125551234", "test", "automated")

        assert result is None

    def test_859pm_ct_sends(self) -> None:
        """8:59 PM CT → send immediately."""
        service = _make_service()
        fake_now = datetime(2026, 3, 10, 20, 59, 0, tzinfo=CT_TZ)
        with patch("grins_platform.services.sms_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = service.enforce_time_window("+16125551234", "test", "automated")

        assert result is None

    def test_900pm_ct_defers(self) -> None:
        """9:00 PM CT → defer to next day 8:00 AM."""
        service = _make_service()
        fake_now = datetime(2026, 3, 10, 21, 0, 0, tzinfo=CT_TZ)
        with patch("grins_platform.services.sms_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = service.enforce_time_window("+16125551234", "test", "automated")

        assert result is not None
        assert result.hour == 8
        assert result.minute == 0
        # Should be next day
        assert result.date() == datetime(2026, 3, 11).date()

    def test_manual_message_bypasses_time_window(self) -> None:
        """Manual messages bypass time window at any hour."""
        service = _make_service()
        # 3 AM CT - outside window
        fake_now = datetime(2026, 3, 10, 3, 0, 0, tzinfo=CT_TZ)
        with patch("grins_platform.services.sms_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = service.enforce_time_window("+16125551234", "test", "manual")

        assert result is None


# --- 10.5: Wiring consent check + time window into automated sends ---


@pytest.mark.unit
class TestAutomatedMessageWiring:
    """Test send_automated_message wires consent check and time window."""

    @pytest.mark.asyncio
    async def test_opted_out_skips_send(self) -> None:
        """Opted-out phone → message not sent."""
        service = _make_service()
        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=False,
        ):
            result = await service.send_automated_message(
                "6125551234",
                "Hello",
                "automated",
            )
        assert result["success"] is False
        assert result["reason"] == "opted_out"

    @pytest.mark.asyncio
    async def test_in_window_sends_immediately(self) -> None:
        """Opted-in phone within time window → sends immediately."""
        service = _make_service()

        fake_now = datetime(2026, 3, 10, 10, 0, 0, tzinfo=CT_TZ)
        with (
            patch(
                "grins_platform.services.sms_service.check_sms_consent",
                return_value=True,
            ),
            patch(
                "grins_platform.services.sms_service.datetime",
            ) as mock_dt,
        ):
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            mock_dt.strftime = datetime.strftime

            result = await service.send_automated_message(
                "6125551234",
                "Hello",
                "automated",
            )

        assert result["success"] is True
        assert "provider_message_id" in result

    @pytest.mark.asyncio
    async def test_outside_window_defers(self) -> None:
        """Opted-in phone outside time window → deferred."""
        service = _make_service()

        fake_now = datetime(2026, 3, 10, 22, 0, 0, tzinfo=CT_TZ)
        with (
            patch(
                "grins_platform.services.sms_service.check_sms_consent",
                return_value=True,
            ),
            patch(
                "grins_platform.services.sms_service.datetime",
            ) as mock_dt,
        ):
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = await service.send_automated_message(
                "6125551234",
                "Hello",
                "automated",
            )

        assert result["success"] is True
        assert result["deferred"] is True


# --- Phase 2: masked-phone resolution on inbound routes ---


@pytest.mark.unit
class TestConfirmationReplyUsesRealPhone:
    """CR-3: Y/R/C auto-replies must target the E.164 recipient_phone
    stored on the original SentMessage, not the CallRail-masked inbound
    ``from_phone`` (e.g. ``***3312``)."""

    @pytest.mark.asyncio
    async def test_auto_reply_sent_to_real_phone_not_mask(self) -> None:
        service = _make_service()
        service.provider = AsyncMock()
        service.provider.send_text = AsyncMock(
            return_value={"success": True, "message_id": "SM-auto"},
        )

        original = SimpleNamespace(recipient_phone="+19527373312")
        handle_result = {
            "action": "confirmed",
            "appointment_id": "apt-1",
            "auto_reply": "Your appointment has been confirmed.",
            "recipient_phone": "+19527373312",
        }

        with (
            patch(
                "grins_platform.services.job_confirmation_service.JobConfirmationService._find_confirmation_message",
                new=AsyncMock(return_value=original),
            ),
            patch(
                "grins_platform.services.job_confirmation_service.JobConfirmationService.handle_confirmation",
                new=AsyncMock(return_value=handle_result),
            ),
        ):
            out = await service._try_confirmation_reply(
                from_phone="***3312",
                body="Y",
                provider_sid="SM-in",
                thread_id="THR-1",
            )

        assert out is not None
        service.provider.send_text.assert_awaited_once()
        target_phone = service.provider.send_text.await_args.args[0]
        assert target_phone == "+19527373312"
        assert "3312" not in target_phone or target_phone.startswith("+1")

    @pytest.mark.asyncio
    async def test_follow_up_sms_also_sent_to_real_phone(self) -> None:
        """Reschedule follow-up SMS must also bypass the masked sender."""
        service = _make_service()
        service.provider = AsyncMock()
        service.provider.send_text = AsyncMock(
            return_value={"success": True, "message_id": "SM-fu"},
        )

        original = SimpleNamespace(recipient_phone="+19527373312")
        handle_result = {
            "action": "reschedule_requested",
            "appointment_id": "apt-1",
            "reschedule_request_id": "rr-1",
            "auto_reply": "We received your reschedule request.",
            "follow_up_sms": "Please reply with 2-3 dates and times.",
            "recipient_phone": "+19527373312",
        }

        with (
            patch(
                "grins_platform.services.job_confirmation_service.JobConfirmationService._find_confirmation_message",
                new=AsyncMock(return_value=original),
            ),
            patch(
                "grins_platform.services.job_confirmation_service.JobConfirmationService.handle_confirmation",
                new=AsyncMock(return_value=handle_result),
            ),
        ):
            await service._try_confirmation_reply(
                from_phone="***3312",
                body="R",
                provider_sid="SM-in",
                thread_id="THR-1",
            )

        assert service.provider.send_text.await_count == 2
        for call in service.provider.send_text.await_args_list:
            assert call.args[0] == "+19527373312"


@pytest.mark.unit
class TestStopOnAppointmentThreadRecordsE164:
    """CR-4: STOP on a thread whose SentMessage has no ``campaign_id``
    (appointment-confirmation thread) must still resolve to the real
    E.164 ``recipient_phone`` — not the masked ``***3312``."""

    @pytest.mark.asyncio
    async def test_stop_on_appointment_thread_stores_full_e164(self) -> None:
        service = _make_service()
        service.provider = AsyncMock()
        service.provider.send_text = AsyncMock(
            return_value={"success": True, "message_id": "SM-stop-ack"},
        )

        sent_msg = MagicMock()
        sent_msg.recipient_phone = "+19527373312"
        sent_msg.campaign_id = None
        corr = CorrelationResult(campaign=None, sent_message=sent_msg)

        with patch(
            "grins_platform.services.campaign_response_service.CampaignResponseService.correlate_reply",
            new=AsyncMock(return_value=corr),
        ):
            await service._process_exact_opt_out(
                "***3312",
                "stop",
                thread_id="THR-9",
            )

        record = service.session.add.call_args_list[0][0][0]
        assert record.phone_number == "+19527373312"
        assert record.consent_given is False
        assert record.opt_out_method == "text_stop"


# --- Sprint 1: CR-8 send_automated_message delegation ---


@pytest.mark.unit
class TestSendAutomatedMessageDelegatesToSendMessage:
    """CR-8: ``send_automated_message`` must route through
    ``send_message`` so automated sends get SentMessage audit, per-type
    dedup, consent check, and lead-touch — instead of bypassing them."""

    @pytest.mark.asyncio
    async def test_maps_lead_confirmation_string_to_enum(self) -> None:
        """Legacy ``"lead_confirmation"`` maps to ``LEAD_CONFIRMATION``."""
        from grins_platform.schemas.ai import MessageType

        service = _make_service()
        send_mock = AsyncMock(return_value={"success": True, "message_id": "SM-1"})
        touch_mock = AsyncMock()
        service.send_message = send_mock  # type: ignore[method-assign]
        service._touch_lead_last_contacted = touch_mock  # type: ignore[method-assign]

        fake_now = datetime(2026, 3, 10, 10, 0, 0, tzinfo=CT_TZ)
        with patch(
            "grins_platform.services.sms_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            await service.send_automated_message(
                "+16125551234",
                "Hello",
                "lead_confirmation",
            )

        sent_type = send_mock.await_args.kwargs["message_type"]
        assert sent_type == MessageType.LEAD_CONFIRMATION

    @pytest.mark.asyncio
    async def test_unknown_string_falls_back_to_automated_notification(self) -> None:
        """Unknown legacy strings default to ``AUTOMATED_NOTIFICATION`` so
        dedup still groups per-type rather than collapsing to CUSTOM."""
        from grins_platform.schemas.ai import MessageType

        service = _make_service()
        send_mock = AsyncMock(return_value={"success": True, "message_id": "SM-2"})
        touch_mock = AsyncMock()
        service.send_message = send_mock  # type: ignore[method-assign]
        service._touch_lead_last_contacted = touch_mock  # type: ignore[method-assign]

        fake_now = datetime(2026, 3, 10, 10, 0, 0, tzinfo=CT_TZ)
        with patch(
            "grins_platform.services.sms_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            await service.send_automated_message(
                "+16125551234",
                "Hello",
                "totally_new_type",
            )

        assert (
            send_mock.await_args.kwargs["message_type"]
            == MessageType.AUTOMATED_NOTIFICATION
        )

    @pytest.mark.asyncio
    async def test_deferred_short_circuits_before_send_message(self) -> None:
        """Outside the 8AM-9PM CT window, the shim returns deferred
        without calling ``send_message`` (which has no time-window policy)."""
        service = _make_service()
        send_mock = AsyncMock()
        service.send_message = send_mock  # type: ignore[method-assign]

        fake_now = datetime(2026, 3, 10, 22, 0, 0, tzinfo=CT_TZ)
        with patch(
            "grins_platform.services.sms_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = await service.send_automated_message(
                "+16125551234",
                "Hello",
                "automated",
            )

        assert result["success"] is True
        assert result["deferred"] is True
        send_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_consent_denied_from_send_message_translates_to_opted_out(
        self,
    ) -> None:
        """When ``send_message`` raises ``SMSConsentDeniedError`` the shim
        returns the legacy ``{"success": False, "reason": "opted_out"}``
        payload callers depend on."""
        from grins_platform.services.sms_service import SMSConsentDeniedError

        service = _make_service()
        send_mock = AsyncMock(side_effect=SMSConsentDeniedError("denied"))
        service.send_message = send_mock  # type: ignore[method-assign]

        fake_now = datetime(2026, 3, 10, 10, 0, 0, tzinfo=CT_TZ)
        with patch(
            "grins_platform.services.sms_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = await service.send_automated_message(
                "+16125551234",
                "Hi",
                "automated",
            )

        assert result == {"success": False, "reason": "opted_out"}

    @pytest.mark.asyncio
    async def test_phone_based_lead_touch_runs_after_send(self) -> None:
        """Because ad-hoc Recipient has no ``lead_id``, ``send_message``'s
        built-in lead-touch no-ops; the shim must do a phone-based touch
        so legacy callers still bump ``last_contacted_at``."""
        service = _make_service()
        send_mock = AsyncMock(return_value={"success": True, "message_id": "SM-3"})
        touch_mock = AsyncMock()
        service.send_message = send_mock  # type: ignore[method-assign]
        service._touch_lead_last_contacted = touch_mock  # type: ignore[method-assign]

        fake_now = datetime(2026, 3, 10, 10, 0, 0, tzinfo=CT_TZ)
        with patch(
            "grins_platform.services.sms_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            await service.send_automated_message(
                "+16125551234",
                "Hi",
                "automated",
            )

        touch_mock.assert_awaited_once_with(phone="+16125551234")


# --- Sprint 1: L-7/L-11 inbound correlation-branch lead-touch ---


@pytest.mark.unit
class TestInboundLeadTouchUsesRealPhone:
    """L-7/L-11: inbound Y/R/C and opt-out branches must update
    ``Lead.last_contacted_at`` with the correlation-resolved real E.164,
    not the masked CallRail ``from_phone``."""

    @pytest.mark.asyncio
    async def test_opt_out_touches_lead_with_real_phone(self) -> None:
        service = _make_service()
        service.provider = AsyncMock()
        service.provider.send_text = AsyncMock()
        touch_mock = AsyncMock()
        service._touch_lead_last_contacted = touch_mock  # type: ignore[method-assign]

        sent_msg = MagicMock()
        sent_msg.recipient_phone = "+19527373312"
        sent_msg.campaign_id = None
        corr = CorrelationResult(campaign=None, sent_message=sent_msg)

        with patch(
            "grins_platform.services.campaign_response_service.CampaignResponseService.correlate_reply",
            new=AsyncMock(return_value=corr),
        ):
            await service._process_exact_opt_out(
                "***3312",
                "stop",
                thread_id="THR-1",
            )

        calls_with_real = [
            c
            for c in touch_mock.await_args_list
            if c.kwargs.get("phone") == "+19527373312"
        ]
        assert len(calls_with_real) >= 1, (
            "Expected at least one _touch_lead_last_contacted call with "
            "the real E.164 phone resolved from the correlated SentMessage."
        )

    @pytest.mark.asyncio
    async def test_confirmation_reply_touches_lead_with_real_phone(self) -> None:
        service = _make_service()
        service.provider = AsyncMock()
        service.provider.send_text = AsyncMock()
        touch_mock = AsyncMock()
        service._touch_lead_last_contacted = touch_mock  # type: ignore[method-assign]

        original = SimpleNamespace(recipient_phone="+19527373312")
        handle_result = {
            "action": "confirmed",
            "appointment_id": "apt-1",
            "auto_reply": "Confirmed.",
            "recipient_phone": "+19527373312",
        }

        with (
            patch(
                "grins_platform.services.job_confirmation_service.JobConfirmationService._find_confirmation_message",
                new=AsyncMock(return_value=original),
            ),
            patch(
                "grins_platform.services.job_confirmation_service.JobConfirmationService.handle_confirmation",
                new=AsyncMock(return_value=handle_result),
            ),
        ):
            await service._try_confirmation_reply(
                from_phone="***3312",
                body="Y",
                provider_sid="SM-in",
                thread_id="THR-1",
            )

        calls_with_real = [
            c
            for c in touch_mock.await_args_list
            if c.kwargs.get("phone") == "+19527373312"
        ]
        assert len(calls_with_real) >= 1


# --- Sprint 1: H-10 handle_webhook fallback STOP writes consent ---


@pytest.mark.unit
class TestHandleWebhookFallbackStopWritesConsent:
    """H-10: the fallback STOP branch in ``handle_webhook`` (reachable
    when a caller invokes ``handle_webhook`` directly, bypassing
    ``handle_inbound``) must route through ``_process_exact_opt_out`` so
    an ``SmsConsentRecord`` is actually persisted rather than silently
    returning an ``opt_out`` action with no DB row."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "keyword",
        ["stop", "STOP", "unsubscribe", "cancel", "quit", "end", "revoke"],
    )
    async def test_direct_webhook_stop_persists_consent_record(
        self,
        keyword: str,
    ) -> None:
        service = _make_service()
        service.provider = AsyncMock()
        service.provider.send_text = AsyncMock()

        result = await service.handle_webhook(
            "+16125551234",
            keyword,
            "SM-direct",
        )

        assert result["action"] == "opt_out"
        assert service.session.add.call_count >= 1
        record = service.session.add.call_args_list[0][0][0]
        assert record.consent_given is False
        assert record.opt_out_method == "text_stop"
