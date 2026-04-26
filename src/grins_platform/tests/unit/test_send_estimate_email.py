"""Unit tests for EmailService.send_estimate_email.

Validates: Feature — estimate approval email portal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import EmailService


def _configured() -> EmailSettings:
    return EmailSettings(resend_api_key="re_test", email_api_key="")


def _mock_estimate(
    *,
    total: str = "599.00",
    valid_until: datetime | None = None,
) -> MagicMock:
    est = MagicMock()
    est.id = uuid4()
    est.total = Decimal(total)
    est.valid_until = valid_until or datetime(2026, 6, 25, tzinfo=timezone.utc)
    return est


def _mock_customer(*, email: str | None = "jane@example.com") -> MagicMock:
    c = MagicMock()
    c.email = email
    c.full_name = "Jane Doe"
    c.first_name = "Jane"
    return c


@pytest.mark.unit
class TestSendEstimateEmail:
    def test_with_valid_customer_returns_sent_true(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_1"}
            result = service.send_estimate_email(
                customer=_mock_customer(),
                estimate=_mock_estimate(),
                portal_url="http://localhost:5173/portal/estimates/abc",
            )
        assert result["sent"] is True
        assert result["sent_via"] == "email"
        assert result["recipient_email"] == "jane@example.com"
        assert "Review your estimate" in result["content"]

    def test_without_email_returns_no_email_reason(self) -> None:
        service = EmailService(settings=_configured())
        result = service.send_estimate_email(
            customer=_mock_customer(email=None),
            estimate=_mock_estimate(),
            portal_url="http://x/y",
        )
        assert result["sent"] is False
        assert result["reason"] == "no_email"

    def test_uses_estimate_total_in_template(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            result = service.send_estimate_email(
                customer=_mock_customer(),
                estimate=_mock_estimate(total="1234.56"),
                portal_url="http://x/y",
            )
        assert "1234.56" in result["content"]

    def test_supports_lead_when_no_customer(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        lead = MagicMock(spec=["email", "first_name"])
        lead.email = "lead@example.com"
        lead.first_name = "John"
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_l"}
            result = service.send_estimate_email(
                customer=lead,
                estimate=_mock_estimate(),
                portal_url="http://x/y",
            )
        assert result["sent"] is True
        assert result["recipient_email"] == "lead@example.com"
        assert "John" in result["content"]

    def test_threads_estimate_id_tag(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        est = _mock_estimate()
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            _ = service.send_estimate_email(
                customer=_mock_customer(),
                estimate=est,
                portal_url="http://x/y",
            )
        payload = mock_send.call_args.args[0]
        tag_names = {t["name"] for t in payload["tags"]}
        assert "estimate_id" in tag_names
        ids = [t["value"] for t in payload["tags"] if t["name"] == "estimate_id"]
        assert ids == [str(est.id)]
