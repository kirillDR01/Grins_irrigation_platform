"""Unit tests for EstimateService._notify_internal_decision.

Validates: Feature — estimate approval email portal (internal alerts).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.services.estimate_service import EstimateService


def _make_service(
    *,
    email_service: MagicMock | None = None,
    sms_service: AsyncMock | None = None,
) -> EstimateService:
    repo = AsyncMock()
    repo.session = AsyncMock()
    return EstimateService(
        estimate_repository=repo,
        portal_base_url="http://localhost:5173",
        email_service=email_service,
        sms_service=sms_service,
    )


def _make_estimate() -> MagicMock:
    est = MagicMock()
    est.id = uuid4()
    est.total = Decimal("499.00")
    est.rejected_reason = None
    est.customer = MagicMock()
    est.customer.full_name = "Jane Doe"
    est.lead = None
    return est


@pytest.mark.unit
class TestNotifyInternalDecision:
    @pytest.mark.asyncio
    async def test_calls_email_when_recipient_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("INTERNAL_NOTIFICATION_EMAIL", "staff@x.com")
        monkeypatch.delenv("INTERNAL_NOTIFICATION_PHONE", raising=False)
        email = MagicMock()
        email.send_internal_estimate_decision_email = MagicMock(return_value=True)
        svc = _make_service(email_service=email)
        await svc._notify_internal_decision(_make_estimate(), "approved")
        email.send_internal_estimate_decision_email.assert_called_once()
        kwargs = email.send_internal_estimate_decision_email.call_args.kwargs
        assert kwargs["to_email"] == "staff@x.com"
        assert kwargs["decision"] == "approved"

    @pytest.mark.asyncio
    async def test_calls_sms_when_phone_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("INTERNAL_NOTIFICATION_EMAIL", raising=False)
        monkeypatch.setenv("INTERNAL_NOTIFICATION_PHONE", "+19527373312")
        sms = AsyncMock()
        svc = _make_service(sms_service=sms)
        await svc._notify_internal_decision(_make_estimate(), "rejected")
        sms.send_automated_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_swallows_email_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("INTERNAL_NOTIFICATION_EMAIL", "staff@x.com")
        email = MagicMock()
        email.send_internal_estimate_decision_email = MagicMock(
            side_effect=RuntimeError("vendor down")
        )
        svc = _make_service(email_service=email)
        # Must not raise
        await svc._notify_internal_decision(_make_estimate(), "approved")

    @pytest.mark.asyncio
    async def test_swallows_sms_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("INTERNAL_NOTIFICATION_PHONE", "+19527373312")
        sms = AsyncMock()
        sms.send_automated_message = AsyncMock(side_effect=RuntimeError("twilio"))
        svc = _make_service(sms_service=sms)
        # Must not raise
        await svc._notify_internal_decision(_make_estimate(), "approved")

    @pytest.mark.asyncio
    async def test_skips_when_env_unset(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("INTERNAL_NOTIFICATION_EMAIL", raising=False)
        monkeypatch.delenv("INTERNAL_NOTIFICATION_PHONE", raising=False)
        email = MagicMock()
        sms = AsyncMock()
        svc = _make_service(email_service=email, sms_service=sms)
        await svc._notify_internal_decision(_make_estimate(), "approved")
        email.send_internal_estimate_decision_email.assert_not_called()
        sms.send_automated_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_includes_rejection_reason_for_rejected_decision(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("INTERNAL_NOTIFICATION_EMAIL", "staff@x.com")
        monkeypatch.delenv("INTERNAL_NOTIFICATION_PHONE", raising=False)
        email = MagicMock()
        email.send_internal_estimate_decision_email = MagicMock(return_value=True)
        svc = _make_service(email_service=email)
        est = _make_estimate()
        est.rejected_reason = "Too expensive"
        await svc._notify_internal_decision(est, "rejected")
        kwargs = email.send_internal_estimate_decision_email.call_args.kwargs
        assert kwargs["rejection_reason"] == "Too expensive"
