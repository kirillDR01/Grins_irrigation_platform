"""Bug #5 — Stripe Payment Link must mirror metadata onto PaymentIntent.

Stripe does NOT auto-propagate ``PaymentLink.metadata`` to the PaymentIntent
that Checkout creates from the link. Without ``payment_intent_data.metadata``,
the ``payment_intent.succeeded`` handler reads an empty ``metadata`` dict and
returns ``unmatched_metadata`` — every Apple-Pay / card payment fails to
reconcile and the invoice never moves from ``draft``.

These tests guard against regression of that fix.

Validates: ``.agents/plans/master-plan-run-findings-bug-resolution-2026-05-04.md``
Phase 1 / Task 1.2.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.services.stripe_payment_link_service import (
    StripePaymentLinkService,
)

pytestmark = pytest.mark.unit


def _make_settings() -> MagicMock:
    settings = MagicMock()
    settings.is_configured = True
    settings.stripe_secret_key = "sk_test_xxx"
    settings.stripe_api_version = "2025-03-31.basil"
    return settings


def _make_invoice() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        customer_id=uuid4(),
        invoice_number="INV-2026-0099",
        total_amount=Decimal("100.00"),
        line_items=[{"description": "Repair", "amount": "100.00"}],
    )


def _make_customer() -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), first_name="Jane", last_name="Doe")


class TestPaymentIntentMetadataMirroring:
    """``payment_intent_data.metadata`` must mirror top-level ``metadata``."""

    def test_payment_intent_data_metadata_includes_invoice_id(self) -> None:
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice()
        customer = _make_customer()
        with patch.object(stripe.PaymentLink, "create") as mock_create:
            mock_create.return_value = SimpleNamespace(
                id="plink_meta_1",
                url="https://buy.stripe.com/meta_1",
            )
            service.create_for_invoice(invoice, customer)
        kwargs = mock_create.call_args.kwargs
        assert "payment_intent_data" in kwargs
        pi_meta = kwargs["payment_intent_data"]["metadata"]
        assert pi_meta["invoice_id"] == str(invoice.id)
        assert pi_meta["customer_id"] == str(invoice.customer_id)

    def test_top_level_and_pi_metadata_match(self) -> None:
        """The two metadata dicts must carry identical keys/values.

        If they drift, downstream reconciliation will silently
        prefer one over the other depending on which event arrived
        first.
        """
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice()
        customer = _make_customer()
        with patch.object(stripe.PaymentLink, "create") as mock_create:
            mock_create.return_value = SimpleNamespace(
                id="plink_meta_2",
                url="https://buy.stripe.com/meta_2",
            )
            service.create_for_invoice(invoice, customer)
        kwargs = mock_create.call_args.kwargs
        assert kwargs["metadata"] == kwargs["payment_intent_data"]["metadata"]
