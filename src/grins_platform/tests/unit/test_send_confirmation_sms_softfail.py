"""Regression tests for B-3 (2026-05-04 sign-off).

``POST /api/v1/appointments/<id>/send-confirmation`` previously returned
HTTP 500 whenever the SMS provider rejected the recipient (consent denied,
rate-limited, allowlist mismatch, generic provider error). The route now
catches the SMSError hierarchy and returns 422 with a structured detail
body (``attempted_channels`` + ``sms_failure_reason``) — same vocabulary
as ``InvoiceService.send_payment_link``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.appointments import router as appointments_router
from grins_platform.api.v1.dependencies import get_full_appointment_service
from grins_platform.services.sms_service import (
    SMSConsentDeniedError,
    SMSError,
    SMSRateLimitDeniedError,
)


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(appointments_router, prefix="/api/v1/appointments")
    return test_app


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.is_active = True
    return user


async def _post_send_confirmation(
    app: FastAPI,
    sms_exc: Exception,
) -> tuple[int, dict]:
    appt_id = uuid4()
    mock_service = AsyncMock()
    mock_service.send_confirmation.side_effect = sms_exc

    app.dependency_overrides[get_full_appointment_service] = lambda: mock_service
    from grins_platform.api.v1.auth_dependencies import get_current_active_user

    app.dependency_overrides[get_current_active_user] = _mock_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/appointments/{appt_id}/send-confirmation",
        )
    return resp.status_code, resp.json()


@pytest.mark.unit
class TestSendConfirmationSMSSoftFail:
    """B-3 — SMSError → 422 with attempted_channels + sms_failure_reason."""

    @pytest.mark.asyncio
    async def test_sms_consent_denied_returns_422_with_consent_reason(
        self, app: FastAPI
    ) -> None:
        status_code, body = await _post_send_confirmation(
            app, SMSConsentDeniedError("consent denied")
        )
        assert status_code == 422
        assert body["detail"]["sms_failure_reason"] == "consent"
        assert body["detail"]["attempted_channels"] == ["sms"]

    @pytest.mark.asyncio
    async def test_sms_rate_limit_returns_422_with_rate_limit_reason(
        self, app: FastAPI
    ) -> None:
        status_code, body = await _post_send_confirmation(
            app, SMSRateLimitDeniedError("rate limit hit")
        )
        assert status_code == 422
        assert body["detail"]["sms_failure_reason"] == "rate_limit"
        assert body["detail"]["attempted_channels"] == ["sms"]

    @pytest.mark.asyncio
    async def test_generic_sms_error_returns_422_with_provider_error_reason(
        self, app: FastAPI
    ) -> None:
        status_code, body = await _post_send_confirmation(
            app, SMSError("provider blew up")
        )
        assert status_code == 422
        assert body["detail"]["sms_failure_reason"] == "provider_error"
        assert body["detail"]["attempted_channels"] == ["sms"]
