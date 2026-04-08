"""Property tests for SMS_Service STOP keywords, consent check, and time window.

Properties 12-16:
  P12: Exact opt-out keyword triggers automatic opt-out
  P13: Informal opt-out language flags for admin review
  P14: Consent check blocks sending to opted-out numbers
  P15: SMS time window enforcement
  P16: Manual messages bypass time window

Validates: Requirements 8.1-8.6, 9.2, 9.5
"""

from __future__ import annotations

from datetime import datetime, time
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.sms_service import (
    CT_TZ,
    EXACT_OPT_OUT_KEYWORDS,
    INFORMAL_OPT_OUT_PHRASES,
    SMSService,
)


def _make_service() -> SMSService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    return SMSService(session)


# --- Property 12: Exact opt-out keyword triggers automatic opt-out ---


@pytest.mark.unit
class TestProperty12ExactOptOutKeyword:
    """Property 12: Exact opt-out keyword triggers automatic opt-out.

    Validates: Requirements 8.1, 8.2, 8.3, 8.4
    """

    @given(
        keyword=st.sampled_from(sorted(EXACT_OPT_OUT_KEYWORDS)),
        upper=st.booleans(),
        leading_space=st.booleans(),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_exact_keyword_triggers_opt_out(
        self,
        keyword: str,
        upper: bool,
        leading_space: bool,
    ) -> None:
        """Any exact keyword (any casing/whitespace) creates opt-out record."""
        body = keyword.upper() if upper else keyword
        if leading_space:
            body = f"  {body}  "

        service = _make_service()
        result = await service.handle_inbound("+16125551234", body, "SM123")

        assert result["action"] == "opt_out"
        # session.add called for SmsConsentRecord + AuditLog
        assert service.session.add.call_count >= 1
        added = service.session.add.call_args_list[0][0][0]
        assert added.consent_given is False
        assert added.opt_out_method == "text_stop"
        assert added.opt_out_confirmation_sent is True


# --- Property 13: Informal opt-out language flags for admin review ---


@pytest.mark.unit
class TestProperty13InformalOptOut:
    """Property 13: Informal opt-out language flags for admin review.

    Validates: Requirements 8.5
    """

    @given(phrase=st.sampled_from(list(INFORMAL_OPT_OUT_PHRASES)))
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_informal_phrase_flags_for_review(self, phrase: str) -> None:
        """Informal phrases flag for admin review, no opt-out record created."""
        service = _make_service()
        result = await service.handle_inbound("+16125551234", phrase, "SM123")

        assert result["action"] == "informal_opt_out_flagged"
        # No SmsConsentRecord should be added
        service.session.add.assert_not_called()


# --- Property 14: Consent check blocks sending to opted-out numbers ---


@pytest.mark.unit
class TestProperty14ConsentCheckBlocks:
    """Property 14: Consent check blocks sending to opted-out numbers.

    Validates: Requirements 8.6
    """

    @given(consent_given=st.booleans())
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_consent_check_reflects_latest_record(
        self,
        consent_given: bool,
    ) -> None:
        """check_sms_consent_legacy returns consent_given from module."""
        service = _make_service()
        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=consent_given,
        ):
            result = await service.check_sms_consent_legacy("6125551234")
        assert result is consent_given

    @pytest.mark.asyncio
    async def test_no_records_defaults_to_allow(self) -> None:
        """No consent records = default allow (True)."""
        service = _make_service()
        with patch(
            "grins_platform.services.sms_service.check_sms_consent",
            return_value=True,
        ):
            result = await service.check_sms_consent_legacy("6125551234")
        assert result is True


# --- Property 15: SMS time window enforcement ---


@pytest.mark.unit
class TestProperty15TimeWindow:
    """Property 15: SMS time window enforcement.

    Validates: Requirements 9.2
    """

    @given(
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
    )
    @settings(max_examples=100)
    def test_time_window_enforcement(self, hour: int, minute: int) -> None:
        """Messages deferred outside 8AM-9PM CT, sent within."""
        fake_now = datetime(2026, 3, 10, hour, minute, 0, tzinfo=CT_TZ)

        service = _make_service()
        with patch(
            "grins_platform.services.sms_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = service.enforce_time_window(
                "+16125551234",
                "test",
                "automated",
            )

        in_window = time(8, 0) <= fake_now.time() < time(21, 0)
        if in_window:
            assert result is None
        else:
            assert result is not None
            assert result.hour == 8
            assert result.minute == 0


# --- Property 16: Manual messages bypass time window ---


@pytest.mark.unit
class TestProperty16ManualBypass:
    """Property 16: Manual messages bypass time window.

    Validates: Requirements 9.5
    """

    @given(
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
    )
    @settings(max_examples=50)
    def test_manual_messages_never_deferred(
        self,
        hour: int,
        minute: int,
    ) -> None:
        """Manual messages bypass time window regardless of time."""
        fake_now = datetime(2026, 3, 10, hour, minute, 0, tzinfo=CT_TZ)

        service = _make_service()
        with patch(
            "grins_platform.services.sms_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = service.enforce_time_window(
                "+16125551234",
                "test",
                "manual",
            )

        assert result is None
