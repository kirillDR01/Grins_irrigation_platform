"""Unit tests for ``StripePaymentLinkService``.

Validates: Stripe Payment Links plan §Phase 2.4.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.services.stripe_payment_link_service import (
    StripePaymentLinkError,
    StripePaymentLinkService,
)


def _make_settings(*, configured: bool = True) -> MagicMock:
    settings = MagicMock()
    settings.is_configured = configured
    settings.stripe_secret_key = "sk_test_xxx"
    settings.stripe_api_version = "2025-03-31.basil"
    return settings


def _make_invoice(
    *,
    total_amount: Decimal = Decimal("100.00"),
    line_items: list[dict[str, object]] | None = None,
    invoice_number: str = "INV-2026-0001",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        customer_id=uuid4(),
        invoice_number=invoice_number,
        total_amount=total_amount,
        line_items=line_items,
    )


def _make_customer() -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), first_name="Jane", last_name="Doe")


# =============================================================================
# create_for_invoice
# =============================================================================


class TestCreateForInvoice:
    """Tests for ``StripePaymentLinkService.create_for_invoice``."""

    @pytest.mark.unit
    def test_create_for_invoice_with_legacy_line_items_returns_id_and_url(
        self,
    ) -> None:
        """Legacy ``{description, amount}`` line items convert to cents."""
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice(
            line_items=[
                {"description": "irrigation_repair service", "amount": "100.00"},
            ],
        )
        customer = _make_customer()
        with patch.object(stripe.PaymentLink, "create") as mock_create:
            mock_create.return_value = SimpleNamespace(
                id="plink_test_123",
                url="https://buy.stripe.com/test_xxx",
            )
            link_id, link_url = service.create_for_invoice(invoice, customer)
        assert link_id == "plink_test_123"
        assert link_url == "https://buy.stripe.com/test_xxx"
        kwargs = mock_create.call_args.kwargs
        assert kwargs["line_items"][0]["price_data"]["unit_amount"] == 10000
        assert kwargs["metadata"]["invoice_id"] == str(invoice.id)
        assert kwargs["restrictions"] == {"completed_sessions": {"limit": 1}}

    @pytest.mark.unit
    def test_create_for_invoice_with_pydantic_line_items_uses_total_over_quantity(
        self,
    ) -> None:
        """Pydantic ``{quantity, unit_price, total}`` items split per-unit."""
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice(
            line_items=[
                {
                    "description": "Sprinkler heads",
                    "quantity": "4",
                    "unit_price": "25.00",
                    "total": "100.00",
                },
            ],
        )
        customer = _make_customer()
        with patch.object(stripe.PaymentLink, "create") as mock_create:
            mock_create.return_value = SimpleNamespace(
                id="plink_x",
                url="https://buy.stripe.com/x",
            )
            service.create_for_invoice(invoice, customer)
        kwargs = mock_create.call_args.kwargs
        item = kwargs["line_items"][0]
        assert item["quantity"] == 4
        assert item["price_data"]["unit_amount"] == 2500

    @pytest.mark.unit
    def test_create_for_invoice_falls_back_when_line_items_empty(self) -> None:
        """Invoices with no explicit line items use ``total_amount`` directly."""
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice(line_items=None, total_amount=Decimal("75.50"))
        customer = _make_customer()
        with patch.object(stripe.PaymentLink, "create") as mock_create:
            mock_create.return_value = SimpleNamespace(
                id="plink_y",
                url="https://buy.stripe.com/y",
            )
            service.create_for_invoice(invoice, customer)
        kwargs = mock_create.call_args.kwargs
        assert kwargs["line_items"][0]["price_data"]["unit_amount"] == 7550
        assert (
            kwargs["line_items"][0]["price_data"]["product_data"]["name"]
            == "Invoice INV-2026-0001"
        )

    @pytest.mark.unit
    def test_create_for_invoice_with_zero_amount_returns_none_tuple(self) -> None:
        """$0 invoices skip the Stripe call (F11)."""
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice(total_amount=Decimal(0))
        customer = _make_customer()
        with patch.object(stripe.PaymentLink, "create") as mock_create:
            link_id, link_url = service.create_for_invoice(invoice, customer)
        assert link_id is None
        assert link_url is None
        mock_create.assert_not_called()

    @pytest.mark.unit
    def test_create_for_invoice_raises_when_stripe_not_configured(self) -> None:
        """Missing Stripe config raises ``StripePaymentLinkError``."""
        service = StripePaymentLinkService(_make_settings(configured=False))
        invoice = _make_invoice()
        customer = _make_customer()
        with pytest.raises(StripePaymentLinkError):
            service.create_for_invoice(invoice, customer)

    @pytest.mark.unit
    def test_create_for_invoice_wraps_stripe_error(self) -> None:
        """Stripe API failures bubble as ``StripePaymentLinkError``."""
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice()
        customer = _make_customer()
        with patch.object(
            stripe.PaymentLink,
            "create",
            side_effect=stripe.StripeError("rate limit"),
        ):
            with pytest.raises(StripePaymentLinkError):
                service.create_for_invoice(invoice, customer)

    @pytest.mark.unit
    def test_create_for_invoice_truncates_long_descriptions(self) -> None:
        """Stripe ``product_data.name`` capped at 250 chars defensively."""
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice(
            line_items=[
                {"description": "x" * 500, "amount": "10.00"},
            ],
        )
        customer = _make_customer()
        with patch.object(stripe.PaymentLink, "create") as mock_create:
            mock_create.return_value = SimpleNamespace(
                id="plink_t",
                url="https://buy.stripe.com/t",
            )
            service.create_for_invoice(invoice, customer)
        name = mock_create.call_args.kwargs["line_items"][0]["price_data"][
            "product_data"
        ]["name"]
        assert len(name) <= 250

    @pytest.mark.unit
    def test_create_for_invoice_rejects_line_item_missing_amount(self) -> None:
        """Line items with neither ``total`` nor ``amount`` raise."""
        service = StripePaymentLinkService(_make_settings())
        invoice = _make_invoice(line_items=[{"description": "broken"}])
        customer = _make_customer()
        with pytest.raises(StripePaymentLinkError):
            service.create_for_invoice(invoice, customer)


# =============================================================================
# deactivate
# =============================================================================


class TestDeactivate:
    """Tests for ``StripePaymentLinkService.deactivate``."""

    @pytest.mark.unit
    def test_deactivate_calls_stripe_modify_with_active_false(self) -> None:
        """Deactivation flips the Stripe-side ``active`` flag to False."""
        service = StripePaymentLinkService(_make_settings())
        with patch.object(stripe.PaymentLink, "modify") as mock_modify:
            service.deactivate("plink_abc123")
        mock_modify.assert_called_once_with("plink_abc123", active=False)

    @pytest.mark.unit
    def test_deactivate_wraps_stripe_error(self) -> None:
        """Stripe failures bubble as ``StripePaymentLinkError``."""
        service = StripePaymentLinkService(_make_settings())
        with patch.object(
            stripe.PaymentLink,
            "modify",
            side_effect=stripe.StripeError("network"),
        ):
            with pytest.raises(StripePaymentLinkError):
                service.deactivate("plink_xyz")
