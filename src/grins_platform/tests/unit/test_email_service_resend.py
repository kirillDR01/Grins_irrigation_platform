"""Unit tests for EmailService Resend integration.

Validates: Feature — estimate approval email portal (Resend wiring).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from grins_platform.models.enums import EmailType
from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import (
    COMMERCIAL_SENDER,
    EmailRecipientNotAllowedError,
    EmailService,
)


def _configured() -> EmailSettings:
    return EmailSettings(resend_api_key="re_test", email_api_key="")


def _unconfigured() -> EmailSettings:
    return EmailSettings(resend_api_key="", email_api_key="")


@pytest.mark.unit
class TestSendEmailWithResend:
    def test_calls_resend_with_expected_payload(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_123"}
            sent = service._send_email(
                to_email="recipient@example.com",
                subject="Hello",
                html_body="<p>Hi</p>",
                email_type="estimate_sent",
                classification=EmailType.TRANSACTIONAL,
            )
        assert sent is True
        mock_send.assert_called_once()
        payload = mock_send.call_args.args[0]
        assert payload["to"] == ["recipient@example.com"]
        assert payload["subject"] == "Hello"
        assert payload["html"] == "<p>Hi</p>"
        assert payload["reply_to"] == COMMERCIAL_SENDER
        assert {"name": "email_type", "value": "estimate_sent"} in payload["tags"]

    def test_returns_false_when_resend_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send",
            side_effect=RuntimeError("vendor down"),
        ):
            sent = service._send_email(
                to_email="recipient@example.com",
                subject="X",
                html_body="<p/>",
                email_type="estimate_sent",
                classification=EmailType.TRANSACTIONAL,
            )
        assert sent is False

    def test_raises_when_recipient_blocked_by_allowlist(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EMAIL_TEST_ADDRESS_ALLOWLIST", "allowed@example.com")
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            with pytest.raises(EmailRecipientNotAllowedError):
                service._send_email(
                    to_email="other@example.com",
                    subject="X",
                    html_body="<p/>",
                    email_type="estimate_sent",
                    classification=EmailType.TRANSACTIONAL,
                )
            mock_send.assert_not_called()

    def test_returns_false_when_settings_not_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        monkeypatch.delenv("EMAIL_API_KEY", raising=False)
        service = EmailService(settings=EmailSettings(_env_file=None))
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            sent = service._send_email(
                to_email="recipient@example.com",
                subject="X",
                html_body="<p/>",
                email_type="estimate_sent",
                classification=EmailType.TRANSACTIONAL,
            )
        assert sent is False
        mock_send.assert_not_called()

    def test_passes_extra_tags(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            _ = service._send_email(
                to_email="r@x.com",
                subject="X",
                html_body="<p/>",
                email_type="estimate_sent",
                classification=EmailType.TRANSACTIONAL,
                extra_tags=[{"name": "estimate_id", "value": "est-1"}],
            )
        payload = mock_send.call_args.args[0]
        assert {"name": "estimate_id", "value": "est-1"} in payload["tags"]

    def test_includes_text_body_when_provided(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            _ = service._send_email(
                to_email="r@x.com",
                subject="X",
                html_body="<p/>",
                email_type="estimate_sent",
                classification=EmailType.TRANSACTIONAL,
                text_body="plain",
            )
        payload = mock_send.call_args.args[0]
        assert payload["text"] == "plain"


@pytest.mark.unit
class TestSendInternalEstimateDecisionEmail:
    def test_calls_send_email_with_decision_subject(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            sent = service.send_internal_estimate_decision_email(
                to_email="staff@x.com",
                decision="approved",
                customer_name="Jane Doe",
                total="599.00",
                estimate_id="est-abc",
                rejection_reason=None,
            )
        assert sent is True
        payload = mock_send.call_args.args[0]
        assert "APPROVED for Jane Doe" in payload["subject"]
