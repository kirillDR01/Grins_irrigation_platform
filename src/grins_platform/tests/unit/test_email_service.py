"""Unit tests for EmailService.

Tests email sending for each compliance event, template rendering,
delivery status handling, skip behavior when EMAIL_API_KEY unavailable,
commercial email suppression list check, COMPANY_PHYSICAL_ADDRESS missing
behavior, and unsubscribe token generation/validation.

Validates: Requirements 39B.1-39B.10, 39C.1-39C.4, 67.1-67.10, 70.1-70.4, 40.1
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from jose import jwt as jose_jwt

from grins_platform.models.enums import DisclosureType, EmailType
from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import EmailService

# =============================================================================
# Helpers
# =============================================================================


def _configured_settings(**overrides: str) -> EmailSettings:
    """Return EmailSettings with email API configured."""
    defaults: dict[str, str] = {
        "email_api_key": "test-key",
        "company_physical_address": "123 Main St, Minneapolis, MN 55401",
        "stripe_customer_portal_url": "https://billing.stripe.com/test",
    }
    defaults.update(overrides)
    return EmailSettings(**defaults)  # type: ignore[arg-type]


def _unconfigured_settings() -> EmailSettings:
    """Return EmailSettings with no API key (pending mode)."""
    return EmailSettings(
        email_api_key="",
        company_physical_address="123 Main St",
        stripe_customer_portal_url="https://billing.stripe.com/test",
    )


def _mock_customer(*, email: str | None = "test@example.com") -> MagicMock:
    c = MagicMock()
    c.id = uuid4()
    c.email = email
    c.full_name = "Jane Doe"
    return c


def _mock_agreement() -> MagicMock:
    a = MagicMock()
    a.id = uuid4()
    a.annual_price = "599.00"
    a.start_date = datetime(2026, 4, 1, tzinfo=UTC).date()
    a.renewal_date = datetime(2027, 4, 1, tzinfo=UTC).date()
    a.cancelled_at = datetime(2026, 6, 15, tzinfo=UTC)
    a.cancellation_reason = "Moving"
    a.cancellation_refund_amount = "299.50"
    a.stripe_subscription_id = "sub_test123"
    tier = MagicMock()
    tier.name = "Professional"
    tier.package_type = "residential"
    tier.billing_frequency = "annually"
    tier.included_services = ["Spring Startup", "Mid-Season", "Winterization"]
    a.tier = tier
    return a


def _mock_tier() -> MagicMock:
    t = MagicMock()
    t.name = "Professional"
    t.package_type = "residential"
    t.billing_frequency = "annually"
    t.included_services = ["Spring Startup", "Mid-Season", "Winterization"]
    return t


def _mock_lead(*, email: str | None = "lead@example.com") -> MagicMock:
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = email
    lead.first_name = "Bob"
    return lead


# =============================================================================
# Email classification
# =============================================================================


class TestEmailClassification:
    """Validates: Requirement 67.1"""

    def test_transactional_types(self) -> None:
        svc = EmailService(settings=_configured_settings())
        for t in (
            "welcome",
            "confirmation",
            "renewal_notice",
            "annual_notice",
            "cancellation_conf",
            "lead_confirmation",
        ):
            assert svc._classify_email(t) == EmailType.TRANSACTIONAL

    def test_commercial_types(self) -> None:
        svc = EmailService(settings=_configured_settings())
        assert svc._classify_email("promo") == EmailType.COMMERCIAL
        assert svc._classify_email("newsletter") == EmailType.COMMERCIAL


# =============================================================================
# Sender selection
# =============================================================================


class TestSenderSelection:
    """Validates: Requirement 67.2, 70.2"""

    def test_transactional_sender(self) -> None:
        svc = EmailService(settings=_configured_settings())
        assert "noreply" in svc._get_sender(EmailType.TRANSACTIONAL)

    def test_commercial_sender(self) -> None:
        svc = EmailService(settings=_configured_settings())
        sender = svc._get_sender(EmailType.COMMERCIAL)
        assert "noreply" not in sender


# =============================================================================
# Template rendering
# =============================================================================


class TestTemplateRendering:
    """Validates: Requirement 39B.9"""

    def test_welcome_template_renders(self) -> None:
        svc = EmailService(settings=_configured_settings())
        html = svc._render_template(
            "welcome.html",
            {
                "customer_name": "Jane",
                "tier_name": "Professional",
                "package_type": "residential",
                "annual_price": "599.00",
                "start_date": "2026-04-01",
                "included_services": ["Spring Startup"],
                "session_id": "sess_123",
            },
        )
        assert "Jane" in html
        assert "Professional" in html
        assert "599.00" in html

    def test_confirmation_template_renders(self) -> None:
        svc = EmailService(settings=_configured_settings())
        html = svc._render_template(
            "confirmation.html",
            {
                "customer_name": "Jane",
                "tier_name": "Professional",
                "annual_price": "599.00",
                "billing_frequency": "annually",
                "renewal_date": "2027-04-01",
                "included_services": [],
            },
        )
        assert "Jane" in html
        assert "Minnesota" in html or "325G" in html

    def test_renewal_notice_template_renders(self) -> None:
        svc = EmailService(settings=_configured_settings())
        html = svc._render_template(
            "renewal_notice.html",
            {
                "customer_name": "Jane",
                "renewal_date": "2027-04-01",
                "annual_price": "599.00",
                "completed_jobs": [],
            },
        )
        assert "Jane" in html

    def test_annual_notice_template_renders(self) -> None:
        svc = EmailService(settings=_configured_settings())
        html = svc._render_template(
            "annual_notice.html",
            {
                "customer_name": "Jane",
                "tier_name": "Professional",
                "annual_price": "599.00",
                "included_services": [],
            },
        )
        assert "Jane" in html

    def test_cancellation_conf_template_renders(self) -> None:
        svc = EmailService(settings=_configured_settings())
        html = svc._render_template(
            "cancellation_conf.html",
            {
                "customer_name": "Jane",
                "cancellation_date": "2026-06-15",
                "cancellation_reason": "Moving",
                "refund_amount": "299.50",
            },
        )
        assert "Jane" in html

    def test_lead_confirmation_template_renders(self) -> None:
        svc = EmailService(settings=_configured_settings())
        html = svc._render_template(
            "lead_confirmation.html",
            {
                "customer_name": "Bob",
            },
        )
        assert "Bob" in html

    def test_template_includes_business_defaults(self) -> None:
        svc = EmailService(settings=_configured_settings())
        html = svc._render_template(
            "welcome.html",
            {
                "customer_name": "Jane",
                "tier_name": "Pro",
                "package_type": "res",
                "annual_price": "100",
                "start_date": "",
                "included_services": [],
                "session_id": "",
            },
        )
        assert "Grin" in html


# =============================================================================
# Send methods — configured (API key present)
# =============================================================================


class TestSendWelcomeEmail:
    """Validates: Requirements 39C.1, 39C.2"""

    def test_sends_when_configured(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_welcome_email(
            _mock_customer(),
            _mock_agreement(),
            _mock_tier(),
        )
        assert result["sent"] is True
        assert result["sent_via"] == "email"
        assert result["recipient_email"] == "test@example.com"
        assert result["content"]  # non-empty HTML

    def test_skips_when_no_email(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_welcome_email(
            _mock_customer(email=None),
            _mock_agreement(),
            _mock_tier(),
        )
        assert result["sent"] is False
        assert result["reason"] == "no_email"


class TestSendConfirmationEmail:
    """Validates: Requirements 39B.3, 70.1, 70.2, 70.3"""

    def test_sends_and_returns_disclosure_type(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_confirmation_email(
            _mock_customer(),
            _mock_agreement(),
            _mock_tier(),
        )
        assert result["sent"] is True
        assert result["disclosure_type"] == DisclosureType.CONFIRMATION

    def test_skips_when_no_email(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_confirmation_email(
            _mock_customer(email=None),
            _mock_agreement(),
            _mock_tier(),
        )
        assert result["sent"] is False


class TestSendRenewalNotice:
    """Validates: Requirements 39B.4"""

    def test_sends_renewal_notice(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_renewal_notice(_mock_customer(), _mock_agreement())
        assert result["sent"] is True
        assert result["disclosure_type"] == DisclosureType.RENEWAL_NOTICE

    def test_skips_when_no_email(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_renewal_notice(
            _mock_customer(email=None),
            _mock_agreement(),
        )
        assert result["sent"] is False


class TestSendAnnualNotice:
    """Validates: Requirements 39B.5"""

    def test_sends_annual_notice(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_annual_notice(_mock_customer(), _mock_agreement())
        assert result["sent"] is True
        assert result["disclosure_type"] == DisclosureType.ANNUAL_NOTICE

    def test_skips_when_no_email(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_annual_notice(
            _mock_customer(email=None),
            _mock_agreement(),
        )
        assert result["sent"] is False


class TestSendCancellationConfirmation:
    """Validates: Requirements 39B.6"""

    def test_sends_cancellation_confirmation(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_cancellation_confirmation(
            _mock_customer(),
            _mock_agreement(),
        )
        assert result["sent"] is True
        assert result["disclosure_type"] == DisclosureType.CANCELLATION_CONF

    def test_skips_when_no_email(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_cancellation_confirmation(
            _mock_customer(email=None),
            _mock_agreement(),
        )
        assert result["sent"] is False


class TestSendLeadConfirmation:
    """Validates: Requirements 55.1, 55.2, 55.3"""

    def test_sends_lead_confirmation(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_lead_confirmation(_mock_lead())
        assert result["sent"] is True
        assert result["recipient_email"] == "lead@example.com"

    def test_skips_when_no_email(self) -> None:
        svc = EmailService(settings=_configured_settings())
        result = svc.send_lead_confirmation(_mock_lead(email=None))
        assert result["sent"] is False
        assert result["reason"] == "no_email"


# =============================================================================
# Pending mode — EMAIL_API_KEY not configured
# =============================================================================


class TestPendingMode:
    """Validates: Requirements 39B.8, 39B.10"""

    def test_welcome_pending_when_unconfigured(self) -> None:
        svc = EmailService(settings=_unconfigured_settings())
        result = svc.send_welcome_email(
            _mock_customer(),
            _mock_agreement(),
            _mock_tier(),
        )
        assert result["sent"] is False
        assert result["sent_via"] == "pending"

    def test_confirmation_pending_when_unconfigured(self) -> None:
        svc = EmailService(settings=_unconfigured_settings())
        result = svc.send_confirmation_email(
            _mock_customer(),
            _mock_agreement(),
            _mock_tier(),
        )
        assert result["sent"] is False
        assert result["sent_via"] == "pending"

    def test_lead_confirmation_pending_when_unconfigured(self) -> None:
        svc = EmailService(settings=_unconfigured_settings())
        result = svc.send_lead_confirmation(_mock_lead())
        assert result["sent"] is False
        assert result["sent_via"] == "pending"


# =============================================================================
# Commercial email suppression / opt-in checks
# =============================================================================


class TestSuppressionAndOptIn:
    """Validates: Requirements 67.5, 67.7"""

    def test_suppressed_email_blocked(self) -> None:
        svc = EmailService(settings=_configured_settings())
        suppressed = {"blocked@example.com"}
        assert (
            svc.check_suppression_and_opt_in(
                "blocked@example.com",
                email_opt_in=True,
                suppressed_emails=suppressed,
            )
            is False
        )

    def test_suppression_case_insensitive(self) -> None:
        svc = EmailService(settings=_configured_settings())
        suppressed = {"Blocked@Example.com"}
        assert (
            svc.check_suppression_and_opt_in(
                "blocked@example.com",
                email_opt_in=True,
                suppressed_emails=suppressed,
            )
            is False
        )

    def test_opted_out_blocked(self) -> None:
        svc = EmailService(settings=_configured_settings())
        assert (
            svc.check_suppression_and_opt_in(
                "user@example.com",
                email_opt_in=False,
            )
            is False
        )

    def test_allowed_when_opted_in_and_not_suppressed(self) -> None:
        svc = EmailService(settings=_configured_settings())
        assert (
            svc.check_suppression_and_opt_in(
                "user@example.com",
                email_opt_in=True,
            )
            is True
        )


# =============================================================================
# COMPANY_PHYSICAL_ADDRESS missing — refuse commercial
# =============================================================================


class TestCommercialAddressRequired:
    """Validates: Requirement 67.10"""

    def test_commercial_refused_without_address(self) -> None:
        svc = EmailService(
            settings=EmailSettings(
                email_api_key="key",
                company_physical_address="",
                stripe_customer_portal_url="",
            ),
        )
        assert svc._can_send_commercial() is False

    def test_commercial_allowed_with_address(self) -> None:
        svc = EmailService(settings=_configured_settings())
        assert svc._can_send_commercial() is True


# =============================================================================
# Unsubscribe token generation and validation
# =============================================================================


class TestUnsubscribeToken:
    """Validates: Requirements 67.4, 67.6, 67.8"""

    def test_generate_and_verify_roundtrip(self) -> None:
        cid = uuid4()
        email = "user@example.com"
        token = EmailService.generate_unsubscribe_token(cid, email)
        payload = EmailService.verify_unsubscribe_token(token)
        assert payload is not None
        assert payload["sub"] == str(cid)
        assert payload["email"] == email
        assert payload["purpose"] == "unsubscribe"

    def test_invalid_token_returns_none(self) -> None:
        assert EmailService.verify_unsubscribe_token("garbage") is None

    def test_expired_token_returns_none(self) -> None:
        payload = {
            "sub": str(uuid4()),
            "email": "x@x.com",
            "exp": datetime.now(UTC) - timedelta(days=1),
            "purpose": "unsubscribe",
        }
        token = jose_jwt.encode(
            payload,
            "dev-secret-key-change-in-production",
            algorithm="HS256",
        )
        assert EmailService.verify_unsubscribe_token(token) is None

    def test_wrong_purpose_returns_none(self) -> None:
        payload = {
            "sub": str(uuid4()),
            "email": "x@x.com",
            "exp": datetime.now(UTC) + timedelta(days=30),
            "purpose": "other",
        }
        token = jose_jwt.encode(
            payload,
            "dev-secret-key-change-in-production",
            algorithm="HS256",
        )
        assert EmailService.verify_unsubscribe_token(token) is None

    def test_token_validity_at_least_30_days(self) -> None:
        token = EmailService.generate_unsubscribe_token(uuid4(), "a@b.com")
        payload = jose_jwt.decode(
            token,
            "dev-secret-key-change-in-production",
            algorithms=["HS256"],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert exp >= datetime.now(UTC) + timedelta(days=29)


# =============================================================================
# Content hashing
# =============================================================================


class TestContentHash:
    def test_hash_deterministic(self) -> None:
        h1 = EmailService.hash_content("hello")
        h2 = EmailService.hash_content("hello")
        assert h1 == h2

    def test_hash_is_sha256(self) -> None:
        expected = hashlib.sha256(b"test").hexdigest()
        assert EmailService.hash_content("test") == expected
