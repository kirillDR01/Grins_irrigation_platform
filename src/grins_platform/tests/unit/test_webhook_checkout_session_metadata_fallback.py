"""Bug #5 — checkout.session.completed invoice-payment correlator.

When a Stripe Payment Link checkout completes, ``session.metadata.invoice_id``
is populated by Stripe from the link's metadata (always — Stripe controls
this propagation, not us). For in-flight Payment Links created before
``payment_intent_data.metadata`` shipped, the PI handler reads empty
metadata and returns ``unmatched_metadata``. This defensive correlator
fires from the checkout-session path and reconciles those payments.

Validates: ``.agents/plans/master-plan-run-findings-bug-resolution-2026-05-04.md``
Phase 1 / Task 1.4.
"""

from __future__ import annotations

import contextlib
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.api.v1.webhooks import StripeWebhookHandler
from grins_platform.models.enums import InvoiceStatus

pytestmark = pytest.mark.unit


def _make_event(event_type: str, payload: dict[str, Any]) -> stripe.Event:
    raw: dict[str, Any] = {
        "id": f"evt_{uuid4().hex[:24]}",
        "type": event_type,
        "object": "event",
        "data": {"object": payload},
    }
    return stripe.Event.construct_from(raw, key="sk_test")  # type: ignore[no-untyped-call]


def _build_handler() -> StripeWebhookHandler:
    session = AsyncMock()
    session.execute = AsyncMock()
    handler = StripeWebhookHandler(session=session)
    handler.repo = AsyncMock()
    return handler


class TestCheckoutSessionInvoicePaymentFallback:
    """When session.metadata.invoice_id is set, route to invoice path."""

    @pytest.mark.asyncio
    async def test_session_with_invoice_metadata_records_payment(self) -> None:
        invoice_id = uuid4()
        job_id = uuid4()
        invoice = SimpleNamespace(
            id=invoice_id,
            job_id=job_id,
            status=InvoiceStatus.SENT.value,
        )
        event = _make_event(
            "checkout.session.completed",
            {
                "id": "cs_test_invoice_1",
                "payment_intent": "pi_session_1",
                "amount_total": 12345,
                "customer_details": {"email": "kirillrakitinsecond@gmail.com"},
                "metadata": {"invoice_id": str(invoice_id)},
            },
        )
        handler = _build_handler()
        record_payment_mock = AsyncMock()
        update_mock = AsyncMock()
        job_obj = SimpleNamespace(payment_collected_on_site=False)
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=job_obj)
        handler.session.execute = AsyncMock(return_value=scalar_result)
        with (
            patch(
                "grins_platform.repositories.invoice_repository.InvoiceRepository",
            ) as mock_repo_cls,
            patch(
                "grins_platform.services.invoice_service.InvoiceService",
            ) as mock_svc_cls,
        ):
            mock_repo_cls.return_value.get_by_id = AsyncMock(return_value=invoice)
            mock_repo_cls.return_value.update = update_mock
            mock_svc_cls.return_value.record_payment = record_payment_mock

            await handler._handle_checkout_completed(event)

        record_payment_mock.assert_awaited_once()
        record = record_payment_mock.await_args.args[1]
        assert record.amount == Decimal("123.45")
        assert record.payment_reference == "stripe:pi_session_1"
        update_mock.assert_awaited_with(
            invoice_id,
            stripe_payment_link_active=False,
        )
        assert job_obj.payment_collected_on_site is True

    @pytest.mark.asyncio
    async def test_session_without_payment_intent_falls_back_to_session_id(
        self,
    ) -> None:
        """Async PaymentIntents may leave ``session.payment_intent`` null."""
        invoice_id = uuid4()
        invoice = SimpleNamespace(
            id=invoice_id,
            job_id=uuid4(),
            status=InvoiceStatus.SENT.value,
        )
        event = _make_event(
            "checkout.session.completed",
            {
                "id": "cs_async_no_pi",
                "payment_intent": None,
                "amount_total": 5000,
                "customer_details": {},
                "metadata": {"invoice_id": str(invoice_id)},
            },
        )
        handler = _build_handler()
        record_payment_mock = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=None)
        handler.session.execute = AsyncMock(return_value=scalar_result)
        with (
            patch(
                "grins_platform.repositories.invoice_repository.InvoiceRepository",
            ) as mock_repo_cls,
            patch(
                "grins_platform.services.invoice_service.InvoiceService",
            ) as mock_svc_cls,
        ):
            mock_repo_cls.return_value.get_by_id = AsyncMock(return_value=invoice)
            mock_repo_cls.return_value.update = AsyncMock()
            mock_svc_cls.return_value.record_payment = record_payment_mock
            await handler._handle_checkout_completed(event)
        record = record_payment_mock.await_args.args[1]
        assert record.payment_reference == "stripe:cs_async_no_pi"

    @pytest.mark.asyncio
    async def test_already_paid_invoice_is_no_op(self) -> None:
        """Idempotency — second arrival of session is short-circuited."""
        invoice_id = uuid4()
        invoice = SimpleNamespace(
            id=invoice_id,
            job_id=uuid4(),
            status=InvoiceStatus.PAID.value,
        )
        event = _make_event(
            "checkout.session.completed",
            {
                "id": "cs_replay",
                "payment_intent": "pi_replay",
                "amount_total": 100,
                "customer_details": {},
                "metadata": {"invoice_id": str(invoice_id)},
            },
        )
        handler = _build_handler()
        with (
            patch(
                "grins_platform.repositories.invoice_repository.InvoiceRepository",
            ) as mock_repo_cls,
            patch(
                "grins_platform.services.invoice_service.InvoiceService",
            ) as mock_svc_cls,
        ):
            mock_repo_cls.return_value.get_by_id = AsyncMock(return_value=invoice)
            await handler._handle_checkout_completed(event)
        mock_svc_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_without_invoice_metadata_runs_agreement_path(
        self,
    ) -> None:
        """Agreement-signup checkouts must NOT be routed to invoice path."""
        event = _make_event(
            "checkout.session.completed",
            {
                "id": "cs_agreement",
                "payment_intent": "pi_agreement",
                "customer_details": {"email": "kirillrakitinsecond@gmail.com"},
                "customer": "cus_x",
                "metadata": {
                    "package_type": "residential",
                    "package_tier": "starter",
                },
            },
        )
        handler = _build_handler()
        invoice_handler = AsyncMock()
        # Patch the invoice-payment helper to verify it is NOT called.
        # Agreement path requires more wiring than we provide here, so
        # we suppress whatever it raises — we only care that the
        # invoice helper was NOT invoked.
        with (
            patch.object(
                handler,
                "_handle_checkout_completed_invoice_payment",
                new=invoice_handler,
            ),
            patch(
                "grins_platform.repositories.customer_repository.CustomerRepository",
            ),
            contextlib.suppress(Exception),
        ):
            await handler._handle_checkout_completed(event)
        invoice_handler.assert_not_awaited()
