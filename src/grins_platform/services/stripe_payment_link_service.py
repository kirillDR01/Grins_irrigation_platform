"""Stripe Payment Link service (Architecture C — Phase 2.4).

Wraps ``stripe.PaymentLink.create`` and ``stripe.PaymentLink.update`` for
the Architecture-C flow: every Grin's invoice gets a server-side
Payment Link with ``metadata.invoice_id`` set so webhook reconciliation
is deterministic (no fuzzy matching).

Companion service to ``stripe_terminal.py`` (deprecated). The ``DOMAIN``
shared with the rest of the payment subsystem keeps log events
consistent (e.g. ``payment.stripepaymentlinkservice.create_for_invoice_started``).

Validates: Stripe Payment Links plan §Phase 2.4.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import stripe

from grins_platform.log_config import LoggerMixin, get_logger

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.invoice import Invoice
    from grins_platform.services.stripe_config import StripeSettings

logger = get_logger(__name__)

# Stripe ``product_data.name`` is capped at ~250 chars; we truncate
# defensively. Source: Stripe API reference, ``product_data`` schema.
_PRODUCT_NAME_MAX = 250


class StripePaymentLinkError(Exception):
    """Raised when a Payment Link operation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class StripePaymentLinkService(LoggerMixin):
    """Server-side Payment Link orchestration for invoices."""

    DOMAIN = "payment"

    def __init__(self, stripe_settings: StripeSettings) -> None:
        super().__init__()
        self.stripe_settings = stripe_settings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_for_invoice(
        self,
        invoice: Invoice,
        customer: Customer,
    ) -> tuple[str | None, str | None]:
        """Create a Stripe Payment Link for ``invoice``.

        Returns ``(link_id, link_url)`` on success. For $0 invoices (per
        plan F11) returns ``(None, None)`` without contacting Stripe —
        the hook in ``InvoiceService`` treats that as a no-op.

        Raises:
            StripePaymentLinkError: For configuration failures or any
                non-zero-amount Stripe error.
        """
        self.log_started(
            "create_for_invoice",
            invoice_id=str(invoice.id),
            customer_id=str(customer.id),
        )

        if invoice.total_amount == Decimal(0):
            # F11: Stripe rejects unit_amount <= 0; we silently skip.
            self.log_rejected(
                "create_for_invoice",
                reason="zero_amount",
                invoice_id=str(invoice.id),
            )
            return None, None

        if not self.stripe_settings.is_configured:
            self.log_rejected(
                "create_for_invoice",
                reason="stripe_not_configured",
            )
            msg = "Stripe is not configured"
            raise StripePaymentLinkError(msg)

        stripe.api_key = self.stripe_settings.stripe_secret_key
        stripe.api_version = self.stripe_settings.stripe_api_version

        line_items = self._build_line_items(invoice)

        params: dict[str, Any] = {
            "line_items": line_items,
            "metadata": {
                "invoice_id": str(invoice.id),
                "customer_id": str(invoice.customer_id),
            },
            "restrictions": {"completed_sessions": {"limit": 1}},
            "after_completion": {"type": "hosted_confirmation"},
            "allow_promotion_codes": False,
            "billing_address_collection": "auto",
        }

        try:
            link = stripe.PaymentLink.create(**params)
        except stripe.StripeError as exc:
            self.log_failed(
                "create_for_invoice",
                error=exc,
                invoice_id=str(invoice.id),
            )
            raise StripePaymentLinkError(str(exc)) from exc

        link_id = str(link.id)
        link_url = str(link.url)
        self.log_completed(
            "create_for_invoice",
            invoice_id=str(invoice.id),
            link_id_suffix=link_id[-6:],
        )
        return link_id, link_url

    def deactivate(self, link_id: str) -> None:
        """Mark a Payment Link inactive in Stripe.

        Idempotent: Stripe accepts ``active=false`` on an already-inactive
        link without error. Any other Stripe error is wrapped in
        ``StripePaymentLinkError``.
        """
        self.log_started(
            "deactivate",
            link_id_suffix=link_id[-6:],
        )

        if not self.stripe_settings.is_configured:
            self.log_rejected(
                "deactivate",
                reason="stripe_not_configured",
            )
            msg = "Stripe is not configured"
            raise StripePaymentLinkError(msg)

        stripe.api_key = self.stripe_settings.stripe_secret_key
        stripe.api_version = self.stripe_settings.stripe_api_version

        try:
            stripe.PaymentLink.modify(link_id, active=False)
        except stripe.StripeError as exc:
            self.log_failed("deactivate", error=exc, link_id_suffix=link_id[-6:])
            raise StripePaymentLinkError(str(exc)) from exc

        self.log_completed("deactivate", link_id_suffix=link_id[-6:])

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_line_items(
        self,
        invoice: Invoice,
    ) -> list[dict[str, Any]]:
        """Translate ``Invoice.line_items`` JSONB to Stripe inline price_data.

        Handles both JSONB shapes per plan F2:

        * Pydantic ``InvoiceLineItem`` shape:
          ``{description, quantity, unit_price, total}`` — uses
          ``total / quantity`` for the unit amount.
        * Legacy shape from ``create_invoice_from_appointment``:
          ``{description, amount}`` — quantity assumed 1.

        For invoices with no explicit line items (per F3), falls back
        to a single line item derived from ``Invoice.total_amount``.
        Raises ``StripePaymentLinkError`` if a line item has neither
        ``total`` nor ``amount``.
        """
        items = invoice.line_items or []
        if not items:
            unit_amount = int((invoice.total_amount * 100).to_integral_value())
            return [
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": unit_amount,
                        "product_data": {
                            "name": f"Invoice {invoice.invoice_number}"[
                                :_PRODUCT_NAME_MAX
                            ],
                        },
                    },
                    "quantity": 1,
                },
            ]

        out: list[dict[str, Any]] = []
        for raw in items:
            description = str(raw.get("description", "Service"))
            if "total" in raw or "unit_price" in raw:
                # Pydantic InvoiceLineItem shape (F2 path A)
                qty_raw = raw.get("quantity", "1")
                qty = Decimal(str(qty_raw))
                if qty <= 0:
                    msg = (
                        f"Line item quantity must be > 0, got {qty} "
                        f"for {raw}"
                    )
                    raise StripePaymentLinkError(msg)
                total = Decimal(str(raw["total"]))
                unit_amount = int((total / qty * 100).to_integral_value())
                quantity = int(qty)
            elif "amount" in raw:
                # Legacy shape from create_invoice_from_appointment (F2 path B)
                unit_amount = int(
                    (Decimal(str(raw["amount"])) * 100).to_integral_value(),
                )
                quantity = 1
            else:
                msg = f"Line item has neither 'total' nor 'amount': {raw}"
                raise StripePaymentLinkError(msg)
            if unit_amount <= 0:
                msg = (
                    f"Line item unit_amount must be > 0 cents, got "
                    f"{unit_amount} for {raw}"
                )
                raise StripePaymentLinkError(msg)
            out.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": unit_amount,
                        "product_data": {
                            "name": description[:_PRODUCT_NAME_MAX],
                        },
                    },
                    "quantity": quantity,
                },
            )
        return out
