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
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
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
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
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
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
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
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
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
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
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
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
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
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
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
        # Cluster H §12: internal staff emails MUST NOT BCC the audit
        # inbox even when OUTBOUND_BCC_EMAIL is configured.
        assert "bcc" not in payload

    def test_internal_decision_email_does_not_bcc_even_when_env_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Internal helpers must pass allow_bcc=False — no audit BCC."""
        monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)
        monkeypatch.setenv("OUTBOUND_BCC_EMAIL", "info@grinsirrigation.com")
        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            service.send_internal_estimate_decision_email(
                to_email="staff@x.com",
                decision="rejected",
                customer_name="Jane",
                total="100",
                estimate_id="e-1",
            )
        payload = mock_send.call_args.args[0]
        assert "bcc" not in payload


@pytest.mark.unit
class TestSendEmailBccTruthTable:
    """Cluster H §12 — BCC is applied iff (env set) AND (allowlist unset) AND (allow_bcc=True)."""

    def _run(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        bcc_env: str | None,
        allowlist: str | None,
        allow_bcc: bool,
    ) -> dict:
        if bcc_env is None:
            monkeypatch.delenv("OUTBOUND_BCC_EMAIL", raising=False)
        else:
            monkeypatch.setenv("OUTBOUND_BCC_EMAIL", bcc_env)
        if allowlist is None:
            monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST", raising=False)
        else:
            monkeypatch.setenv("EMAIL_TEST_ADDRESS_ALLOWLIST", allowlist)
        monkeypatch.delenv("EMAIL_TEST_REDIRECT_TO", raising=False)

        # Allowlist must include the recipient when set, so the send is
        # not refused before payload construction.
        to_addr = "recipient@example.com"
        if allowlist:
            monkeypatch.setenv(
                "EMAIL_TEST_ADDRESS_ALLOWLIST", f"{allowlist},{to_addr}",
            )

        service = EmailService(settings=_configured())
        with patch(
            "grins_platform.services.email_service.resend.Emails.send"
        ) as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            service._send_email(
                to_email=to_addr,
                subject="S",
                html_body="<p/>",
                email_type="estimate_sent",
                classification=EmailType.TRANSACTIONAL,
                allow_bcc=allow_bcc,
            )
        return mock_send.call_args.args[0]

    def test_prod_shape_applies_bcc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """env set + allowlist unset + allow_bcc=True → bcc present."""
        payload = self._run(
            monkeypatch,
            bcc_env="info@grinsirrigation.com",
            allowlist=None,
            allow_bcc=True,
        )
        assert payload["bcc"] == ["info@grinsirrigation.com"]

    def test_env_unset_no_bcc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._run(
            monkeypatch,
            bcc_env=None,
            allowlist=None,
            allow_bcc=True,
        )
        assert "bcc" not in payload

    def test_env_empty_string_no_bcc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._run(
            monkeypatch,
            bcc_env="   ",
            allowlist=None,
            allow_bcc=True,
        )
        assert "bcc" not in payload

    def test_allowlist_active_suppresses_bcc(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Dev/staging guard active → BCC suppressed even with env set."""
        payload = self._run(
            monkeypatch,
            bcc_env="info@grinsirrigation.com",
            allowlist="kirillrakitinsecond@gmail.com",
            allow_bcc=True,
        )
        assert "bcc" not in payload

    def test_allow_bcc_false_suppresses_bcc(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Caller opts out via allow_bcc=False (internal helpers)."""
        payload = self._run(
            monkeypatch,
            bcc_env="info@grinsirrigation.com",
            allowlist=None,
            allow_bcc=False,
        )
        assert "bcc" not in payload
