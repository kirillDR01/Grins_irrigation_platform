"""Property test for email classification correctness.

Property 9: Email Classification Correctness
For any compliance email template (CONFIRMATION, RENEWAL_NOTICE,
ANNUAL_NOTICE, CANCELLATION_CONF): zero promotional elements,
transactional sender, no unsubscribe link.

Validates: Requirements 67.1, 70.1, 70.2, 70.3
"""

from __future__ import annotations

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import EmailType
from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import (
    TRANSACTIONAL_SENDER,
    EmailService,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMPLIANCE_EMAIL_TYPES = [
    "confirmation",
    "renewal_notice",
    "annual_notice",
    "cancellation_conf",
]

# Promotional patterns that must NOT appear in compliance emails (Req 70.1)
PROMOTIONAL_PATTERNS = [
    "upgrade your plan",
    "discount code",
    "limited time offer",
    "special offer",
    "promo code",
    "upgrade now",
    "exclusive deal",
    "act now",
    "buy now",
    "free trial",
]

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

compliance_types = st.sampled_from(COMPLIANCE_EMAIL_TYPES)
customer_names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "Zs")),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip())
prices = st.decimals(min_value=1, max_value=9999, places=2).map(str)
dates = st.dates().map(str)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings() -> EmailSettings:
    return EmailSettings(
        email_api_key="test-key",
        company_physical_address="123 Main St, Minneapolis, MN 55401",
        stripe_customer_portal_url="https://billing.stripe.com/test",
    )


def _render_compliance_template(
    svc: EmailService,
    email_type: str,
    customer_name: str,
    price: str,
    date_str: str,
) -> str:
    """Render a compliance template with given params."""
    if email_type == "confirmation":
        return svc._render_template(
            "confirmation.html",
            {
                "customer_name": customer_name,
                "tier_name": "Test Plan",
                "annual_price": price,
                "billing_frequency": "annually",
                "renewal_date": date_str,
                "included_services": [],
            },
        )
    if email_type == "renewal_notice":
        return svc._render_template(
            "renewal_notice.html",
            {
                "customer_name": customer_name,
                "renewal_date": date_str,
                "annual_price": price,
                "completed_jobs": [],
            },
        )
    if email_type == "annual_notice":
        return svc._render_template(
            "annual_notice.html",
            {
                "customer_name": customer_name,
                "tier_name": "Test Plan",
                "annual_price": price,
                "included_services": [],
            },
        )
    # cancellation_conf
    return svc._render_template(
        "cancellation_conf.html",
        {
            "customer_name": customer_name,
            "cancellation_date": date_str,
            "cancellation_reason": "Customer request",
            "refund_amount": price,
        },
    )


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmailClassificationCorrectness:
    """Property 9 — compliance emails have zero promotional content,
    use transactional sender, and contain no unsubscribe link."""

    @given(email_type=compliance_types)
    @settings(max_examples=20)
    def test_compliance_emails_classified_as_transactional(
        self,
        email_type: str,
    ) -> None:
        """All compliance email types are classified TRANSACTIONAL (Req 67.1)."""
        svc = EmailService(settings=_settings())
        assert svc._classify_email(email_type) == EmailType.TRANSACTIONAL

    @given(email_type=compliance_types)
    @settings(max_examples=20)
    def test_compliance_emails_use_transactional_sender(
        self,
        email_type: str,
    ) -> None:
        """Compliance emails use noreply@ sender (Req 70.2)."""
        svc = EmailService(settings=_settings())
        classification = svc._classify_email(email_type)
        sender = svc._get_sender(classification)
        assert sender == TRANSACTIONAL_SENDER

    @given(
        email_type=compliance_types,
        customer_name=customer_names,
        price=prices,
        date_str=dates,
    )
    @settings(max_examples=30)
    def test_compliance_templates_contain_no_promotional_content(
        self,
        email_type: str,
        customer_name: str,
        price: str,
        date_str: str,
    ) -> None:
        """Compliance templates have zero promotional elements (Req 70.1)."""
        svc = EmailService(settings=_settings())
        html = _render_compliance_template(
            svc,
            email_type,
            customer_name,
            price,
            date_str,
        )
        html_lower = html.lower()
        for pattern in PROMOTIONAL_PATTERNS:
            assert pattern not in html_lower, (
                f"Compliance template '{email_type}' contains "
                f"promotional pattern: '{pattern}'"
            )

    @given(
        email_type=compliance_types,
        customer_name=customer_names,
        price=prices,
        date_str=dates,
    )
    @settings(max_examples=30)
    def test_compliance_templates_contain_no_unsubscribe_link(
        self,
        email_type: str,
        customer_name: str,
        price: str,
        date_str: str,
    ) -> None:
        """Compliance templates have no unsubscribe link (Req 70.3).

        A 'Manage your subscription' link to Stripe Portal is permitted.
        """
        svc = EmailService(settings=_settings())
        html = _render_compliance_template(
            svc,
            email_type,
            customer_name,
            price,
            date_str,
        )
        html_lower = html.lower()
        assert "unsubscribe" not in html_lower, (
            f"Compliance template '{email_type}' contains "
            f"an unsubscribe link — not allowed for transactional emails"
        )
