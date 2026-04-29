"""Unit tests for the Payment Link email template.

Stripe Payment Links plan §Phase 4.3 — snapshot-style assertions over the
Jinja2 template rendering, plus a wiring check for
``InvoiceService._render_payment_link_email``.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import EmailService
from grins_platform.services.invoice_service import InvoiceService


def _build_email_service() -> EmailService:
    """Real EmailService — Jinja env + template loader are real."""
    return EmailService(settings=EmailSettings(resend_api_key="re_test"))


@pytest.mark.unit
class TestPaymentLinkEmailTemplate:
    """Phase 4.3: payment_link_email.{html,txt} render correctly."""

    def test_html_template_renders_all_required_vars(self) -> None:
        es = _build_email_service()
        context = {
            "customer_first_name": "Kirill",
            "invoice_number": "INV-2026-0042",
            "total_amount": "299.50",
            "payment_link_url": "https://buy.stripe.com/test_RENDER",
        }
        html = es._render_template("payment_link_email.html", context)

        assert "Kirill" in html
        assert "INV-2026-0042" in html
        assert "$299.50" in html
        assert "https://buy.stripe.com/test_RENDER" in html
        # Defaults injected by _render_template
        assert "Grin" in html  # business_name (Grin's Irrigation; HTML-escaped)
        assert "(952) 818-1020" in html
        assert "info@grinsirrigation.com" in html
        # Has a clickable Pay invoice button
        assert 'href="https://buy.stripe.com/test_RENDER"' in html
        assert "Pay invoice" in html

    def test_text_template_renders_all_required_vars(self) -> None:
        es = _build_email_service()
        context = {
            "customer_first_name": "Kirill",
            "invoice_number": "INV-2026-0042",
            "total_amount": "299.50",
            "payment_link_url": "https://buy.stripe.com/test_RENDER",
        }
        text = es._render_template("payment_link_email.txt", context)

        assert "Kirill" in text
        assert "INV-2026-0042" in text
        assert "$299.50" in text
        assert "https://buy.stripe.com/test_RENDER" in text
        assert "Grin's Irrigation" in text
        assert "(952) 818-1020" in text
        # Plaintext should not contain HTML tags
        assert "<a " not in text
        assert "<p>" not in text

    def test_html_template_escapes_unsafe_customer_name(self) -> None:
        """HTML autoescape must protect against XSS via customer name."""
        es = _build_email_service()
        context = {
            "customer_first_name": "<script>alert(1)</script>",
            "invoice_number": "INV-1",
            "total_amount": "10.00",
            "payment_link_url": "https://buy.stripe.com/test_X",
        }
        html = es._render_template("payment_link_email.html", context)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html


@pytest.mark.unit
class TestRenderPaymentLinkEmailWiring:
    """Phase 4.3: ``InvoiceService._render_payment_link_email`` uses the
    Jinja2 templates via ``EmailService._render_template`` rather than the
    inline f-string body.
    """

    def test_uses_jinja_templates_when_email_service_present(self) -> None:
        es = _build_email_service()
        svc = InvoiceService(
            invoice_repository=MagicMock(),
            job_repository=MagicMock(),
            customer_repository=MagicMock(),
            email_service=es,
        )
        invoice = SimpleNamespace(
            id="iid",
            stripe_payment_link_url="https://buy.stripe.com/test_WIRED",
            total_amount=Decimal("125.00"),
            invoice_number="INV-WIRED",
        )
        customer = SimpleNamespace(first_name="Kirill")

        html, text = svc._render_payment_link_email(customer, invoice)

        # Both bodies came from the Jinja templates (assert markers unique
        # to the template, not the inline fallback).
        assert "background: #6366f1; color: #ffffff" in html
        assert "Pay invoice" in html
        assert "https://buy.stripe.com/test_WIRED" in html
        assert "INV-WIRED" in html
        assert "$125.00" in html
        assert "(952) 818-1020" in html  # business_phone default

        # Plaintext came from .txt template (no HTML, has dash-from-template)
        assert "<" not in text
        assert "INV-WIRED" in text
        assert "https://buy.stripe.com/test_WIRED" in text
        assert "Grin's Irrigation" in text

    def test_falls_back_to_inline_when_email_service_missing(self) -> None:
        svc = InvoiceService(
            invoice_repository=MagicMock(),
            job_repository=MagicMock(),
            customer_repository=MagicMock(),
            email_service=None,
        )
        invoice = SimpleNamespace(
            id="iid",
            stripe_payment_link_url="https://buy.stripe.com/test_FALLBACK",
            total_amount=Decimal("75.00"),
            invoice_number="INV-FB",
        )
        customer = SimpleNamespace(first_name="Kirill")

        html, text = svc._render_payment_link_email(customer, invoice)

        # Inline fallback still includes the link + invoice number so the
        # service degrades gracefully.
        assert "https://buy.stripe.com/test_FALLBACK" in html
        assert "INV-FB" in html
        assert "https://buy.stripe.com/test_FALLBACK" in text

    def test_uses_first_name_default_when_missing(self) -> None:
        es = _build_email_service()
        svc = InvoiceService(
            invoice_repository=MagicMock(),
            job_repository=MagicMock(),
            customer_repository=MagicMock(),
            email_service=es,
        )
        invoice = SimpleNamespace(
            id="iid",
            stripe_payment_link_url="https://buy.stripe.com/test_NONAME",
            total_amount=Decimal("50.00"),
            invoice_number="INV-NN",
        )
        customer = SimpleNamespace(first_name=None)

        html, text = svc._render_payment_link_email(customer, invoice)

        assert "Hi there" in html
        assert "Hi there" in text
