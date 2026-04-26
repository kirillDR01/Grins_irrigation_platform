"""Functional test for estimate email sending end-to-end at the service layer.

Validates: Feature — estimate approval email portal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import EstimateStatus
from grins_platform.services.estimate_service import EstimateService


def _make_customer(*, email: str = "jane@example.com") -> MagicMock:
    c = MagicMock()
    c.id = uuid4()
    c.email = email
    c.phone = "+19527373312"
    c.full_name = "Jane Doe"
    c.first_name = "Jane"
    return c


def _make_estimate(**overrides: Any) -> MagicMock:
    est = MagicMock()
    est.id = overrides.get("id", uuid4())
    est.customer_token = overrides.get("customer_token", uuid4())
    est.customer_id = overrides.get("customer_id")
    est.lead_id = overrides.get("lead_id")
    est.customer = overrides.get("customer")
    est.lead = overrides.get("lead")
    est.total = overrides.get("total", Decimal("499.00"))
    est.valid_until = overrides.get(
        "valid_until",
        datetime.now(tz=timezone.utc),
    )
    est.status = overrides.get("status", EstimateStatus.DRAFT.value)
    return est


@pytest.mark.functional
@pytest.mark.asyncio
class TestEstimateEmailSendWorkflow:
    """``send_estimate`` triggers a real ``send_estimate_email`` call when an
    EmailService is wired and the customer has an email address."""

    async def test_send_estimate_invokes_email_service_with_portal_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        customer = _make_customer()
        sent_est = _make_estimate(
            customer=customer,
            customer_id=customer.id,
            status=EstimateStatus.SENT.value,
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=sent_est)
        repo.update = AsyncMock(return_value=sent_est)
        repo.create_follow_up = AsyncMock(return_value=MagicMock())

        sms = AsyncMock()
        sms.send_automated_message = AsyncMock(
            return_value={"success": True, "message_id": "msg"}
        )

        email_service = MagicMock()
        email_service.send_estimate_email = MagicMock(
            return_value={
                "sent": True,
                "sent_via": "email",
                "recipient_email": customer.email,
                "content": "<p/>",
                "disclosure_type": None,
            }
        )

        svc = EstimateService(
            estimate_repository=repo,
            portal_base_url="http://localhost:5173",
            sms_service=sms,
            email_service=email_service,
        )

        result = await svc.send_estimate(sent_est.id)

        email_service.send_estimate_email.assert_called_once()
        call_kwargs = email_service.send_estimate_email.call_args.kwargs
        assert call_kwargs["portal_url"].startswith(
            "http://localhost:5173/portal/estimates/"
        )
        assert str(sent_est.customer_token) in call_kwargs["portal_url"]
        assert "email" in result.sent_via
