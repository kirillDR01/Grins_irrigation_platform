"""Unit tests for SMS_Service STOP keywords, consent check, and time window.

Validates: Requirements 8.1-8.6, 9.1-9.5
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        service.session.add.assert_called_once()
        added = service.session.add.call_args[0][0]
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
    """Test check_sms_consent method."""

    @pytest.mark.asyncio
    async def test_opted_out_phone_returns_false(self) -> None:
        """Opted-out phone → False."""
        service = _make_service()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = False
        service.session.execute = AsyncMock(return_value=mock_result)

        assert await service.check_sms_consent("6125551234") is False

    @pytest.mark.asyncio
    async def test_opted_in_phone_returns_true(self) -> None:
        """Opted-in phone → True."""
        service = _make_service()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True
        service.session.execute = AsyncMock(return_value=mock_result)

        assert await service.check_sms_consent("6125551234") is True

    @pytest.mark.asyncio
    async def test_no_records_returns_true(self) -> None:
        """No consent records → default True."""
        service = _make_service()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.session.execute = AsyncMock(return_value=mock_result)

        assert await service.check_sms_consent("6125551234") is True


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
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = False
        service.session.execute = AsyncMock(return_value=mock_result)

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
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True
        service.session.execute = AsyncMock(return_value=mock_result)

        fake_now = datetime(2026, 3, 10, 10, 0, 0, tzinfo=CT_TZ)
        with patch("grins_platform.services.sms_service.datetime") as mock_dt:
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
        assert "twilio_sid" in result

    @pytest.mark.asyncio
    async def test_outside_window_defers(self) -> None:
        """Opted-in phone outside time window → deferred."""
        service = _make_service()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True
        service.session.execute = AsyncMock(return_value=mock_result)

        fake_now = datetime(2026, 3, 10, 22, 0, 0, tzinfo=CT_TZ)
        with patch("grins_platform.services.sms_service.datetime") as mock_dt:
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
