"""Unit tests for Architecture-C Stripe webhook handlers.

Covers ``_handle_payment_intent_succeeded``, ``_handle_payment_intent_payment_failed``,
``_handle_payment_intent_canceled``, ``_handle_charge_refunded``, and
``_handle_charge_dispute_created``.

Validates: Stripe Payment Links plan §Phase 2.10–2.13.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.api.v1.webhooks import StripeWebhookHandler
from grins_platform.models.enums import InvoiceStatus


def _make_event(event_type: str, payload: dict[str, Any]) -> stripe.Event:
    """Build a minimal Stripe Event with a payload attached."""
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


# =============================================================================
# payment_intent.succeeded
# =============================================================================


class TestPaymentIntentSucceeded:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscription_intent_is_short_circuited(self) -> None:
        """CG-7: PaymentIntents tied to a Stripe Invoice are skipped."""
        invoice_id = uuid4()
        event = _make_event(
            "payment_intent.succeeded",
            {
                "id": "pi_test",
                "currency": "usd",
                "amount_received": 5000,
                "invoice": "in_subscription_renewal",
                "metadata": {"invoice_id": str(invoice_id)},
            },
        )
        handler = _build_handler()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            await handler._handle_payment_intent_succeeded(event)
        mock_repo_cls.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_usd_currency_is_refused(self) -> None:
        """Non-USD intents are logged and ignored (out of scope)."""
        event = _make_event(
            "payment_intent.succeeded",
            {
                "id": "pi_test",
                "currency": "eur",
                "amount_received": 5000,
                "invoice": None,
                "metadata": {"invoice_id": str(uuid4())},
            },
        )
        handler = _build_handler()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            await handler._handle_payment_intent_succeeded(event)
        mock_repo_cls.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_invoice_id_metadata_is_logged(self) -> None:
        """Intents without ``metadata.invoice_id`` are unmatched, no-op."""
        event = _make_event(
            "payment_intent.succeeded",
            {
                "id": "pi_test",
                "currency": "usd",
                "amount_received": 5000,
                "invoice": None,
                "metadata": {},
            },
        )
        handler = _build_handler()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            await handler._handle_payment_intent_succeeded(event)
        mock_repo_cls.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_already_paid_invoice_is_no_op(self) -> None:
        """Replay protection: PAID invoices are not double-paid."""
        invoice_id = uuid4()
        invoice = SimpleNamespace(
            id=invoice_id,
            job_id=uuid4(),
            status=InvoiceStatus.PAID.value,
        )
        event = _make_event(
            "payment_intent.succeeded",
            {
                "id": "pi_test",
                "currency": "usd",
                "amount_received": 5000,
                "invoice": None,
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
            instance = AsyncMock()
            instance.get_by_id.return_value = invoice
            mock_repo_cls.return_value = instance
            await handler._handle_payment_intent_succeeded(event)
        mock_svc_cls.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancelled_invoice_is_refused(self) -> None:
        """CG-8: cancelled invoices logged but not paid."""
        invoice_id = uuid4()
        invoice = SimpleNamespace(
            id=invoice_id,
            job_id=uuid4(),
            status=InvoiceStatus.CANCELLED.value,
        )
        event = _make_event(
            "payment_intent.succeeded",
            {
                "id": "pi_test",
                "currency": "usd",
                "amount_received": 5000,
                "invoice": None,
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
            await handler._handle_payment_intent_succeeded(event)
        mock_svc_cls.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_happy_path_records_payment_and_updates_link_active(self) -> None:
        """Matched intent → record_payment + link_active=False."""
        invoice_id = uuid4()
        job_id = uuid4()
        invoice = SimpleNamespace(
            id=invoice_id,
            job_id=job_id,
            status=InvoiceStatus.SENT.value,
        )
        event = _make_event(
            "payment_intent.succeeded",
            {
                "id": "pi_test_happy",
                "currency": "usd",
                "amount_received": 12345,
                "invoice": None,
                "metadata": {"invoice_id": str(invoice_id)},
            },
        )
        handler = _build_handler()
        record_payment_mock = AsyncMock()
        update_mock = AsyncMock()
        # Job scalar_one_or_none returns a SimpleNamespace job
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
            patch(
                "grins_platform.services.appointment_service.AppointmentService",
            ) as mock_appt_svc_cls,
        ):
            mock_repo_cls.return_value.get_by_id = AsyncMock(return_value=invoice)
            mock_repo_cls.return_value.update = update_mock
            mock_svc_cls.return_value.record_payment = record_payment_mock
            mock_appt_svc_cls.return_value._send_payment_receipts = AsyncMock()

            await handler._handle_payment_intent_succeeded(event)

        record_payment_mock.assert_awaited_once()
        # Verify second positional/kwarg passed an "amount" of 123.45
        args = record_payment_mock.await_args
        record = args.args[1]
        assert record.amount == Decimal("123.45")
        update_mock.assert_awaited_with(
            invoice_id,
            stripe_payment_link_active=False,
        )
        assert job_obj.payment_collected_on_site is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_payment_intent_succeeded_fires_customer_receipt(self) -> None:
        """Webhook fires _send_payment_receipts after recording payment.

        **Validates: Architecture C parity — Stripe payments must trigger
        the same receipt SMS+email that cash/check do.**
        """
        invoice_id = uuid4()
        job_id = uuid4()
        invoice = SimpleNamespace(
            id=invoice_id,
            job_id=job_id,
            status=InvoiceStatus.SENT.value,
        )
        event = _make_event(
            "payment_intent.succeeded",
            {
                "id": "pi_test_receipt",
                "currency": "usd",
                "amount_received": 25000,
                "invoice": None,
                "metadata": {"invoice_id": str(invoice_id)},
            },
        )
        handler = _build_handler()
        send_receipts_mock = AsyncMock()
        job_obj = SimpleNamespace(
            id=job_id,
            payment_collected_on_site=False,
        )
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
            patch(
                "grins_platform.services.appointment_service.AppointmentService",
                autospec=True,
            ) as mock_appt_svc_cls,
        ):
            mock_repo_cls.return_value.get_by_id = AsyncMock(return_value=invoice)
            mock_repo_cls.return_value.update = AsyncMock()
            mock_svc_cls.return_value.record_payment = AsyncMock()
            mock_appt_svc_cls.return_value._send_payment_receipts = send_receipts_mock

            await handler._handle_payment_intent_succeeded(event)

        # Regression assertion: the receipt-dispatch try/except used to
        # silently swallow `AppointmentService.__init__()` TypeError when
        # ``staff_repository`` was missing. ``autospec=True`` enforces the
        # real signature, so a missing kwarg now surfaces as a failed
        # ``assert_awaited_once()`` rather than a green test that masks
        # the bug.
        send_receipts_mock.assert_awaited_once()
        args = send_receipts_mock.await_args
        # Positional: (job, invoice, amount)
        assert args.args[0] is job_obj
        assert args.args[1] is invoice
        assert args.args[2] == Decimal("250.00")
        # Confirm staff_repository was included in the construction.
        ctor_kwargs = mock_appt_svc_cls.call_args.kwargs
        assert "staff_repository" in ctor_kwargs


# =============================================================================
# checkout.session.completed (Architecture C — Payment Link reconciliation)
# =============================================================================


class TestCheckoutSessionCompletedReceipt:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_session_completed_fires_customer_receipt(
        self,
    ) -> None:
        """F8: checkout handler dispatches the customer receipt after pay.

        Stripe Payment Links arrive as ``checkout.session.completed`` with
        ``metadata.invoice_id``. The PI handler short-circuits on already
        PAID invoices, so the receipt SMS+email must fire from this
        handler to keep parity with cash/check/Venmo/Zelle.
        """
        invoice_id = uuid4()
        job_id = uuid4()
        invoice_unpaid = SimpleNamespace(
            id=invoice_id,
            job_id=job_id,
            status=InvoiceStatus.SENT.value,
        )
        invoice_paid = SimpleNamespace(
            id=invoice_id,
            job_id=job_id,
            status=InvoiceStatus.PAID.value,
        )
        session_obj: dict[str, Any] = {
            "id": "cs_test_checkout_receipt",
            "payment_intent": "pi_test_checkout_receipt",
            "amount_total": 25000,
            "metadata": {"invoice_id": str(invoice_id)},
        }
        event = _make_event("checkout.session.completed", session_obj)
        handler = _build_handler()
        send_receipts_mock = AsyncMock()
        job_obj = SimpleNamespace(
            id=job_id,
            payment_collected_on_site=False,
        )
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
            patch(
                "grins_platform.services.appointment_service.AppointmentService",
                autospec=True,
            ) as mock_appt_svc_cls,
        ):
            # First get_by_id: pre-payment unpaid row.
            # Second get_by_id (after the receipt re-fetch): paid row.
            mock_repo_cls.return_value.get_by_id = AsyncMock(
                side_effect=[invoice_unpaid, invoice_paid],
            )
            mock_repo_cls.return_value.update = AsyncMock()
            mock_svc_cls.return_value.record_payment = AsyncMock()
            mock_appt_svc_cls.return_value._send_payment_receipts = send_receipts_mock

            await handler._handle_checkout_completed_invoice_payment(
                event,
                session_obj,
                str(invoice_id),
            )

        # ``autospec=True`` enforces the real constructor signature, so a
        # missing ``staff_repository=`` kwarg surfaces as the dispatch
        # never running rather than a green test.
        send_receipts_mock.assert_awaited_once()
        args = send_receipts_mock.await_args
        assert args.args[0] is job_obj
        assert args.args[1] is invoice_paid  # the post-payment re-fetch result
        assert args.args[2] == Decimal("250.00")
        # Job flag was set by the existing in-handler logic.
        assert job_obj.payment_collected_on_site is True
        # Regression: receipt-dispatch path must construct AppointmentService
        # with all four required dependencies.
        ctor_kwargs = mock_appt_svc_cls.call_args.kwargs
        assert "staff_repository" in ctor_kwargs

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_session_completed_does_not_fire_receipt_when_already_paid(
        self,
    ) -> None:
        """F8 idempotency: replay on a PAID invoice short-circuits early.

        The PAID short-circuit at the top of the handler returns BEFORE
        the receipt-dispatch block, so a replay does not double-fire.
        """
        invoice_id = uuid4()
        invoice_paid = SimpleNamespace(
            id=invoice_id,
            job_id=uuid4(),
            status=InvoiceStatus.PAID.value,
        )
        session_obj: dict[str, Any] = {
            "id": "cs_test_replay",
            "payment_intent": "pi_test_replay",
            "amount_total": 25000,
            "metadata": {"invoice_id": str(invoice_id)},
        }
        event = _make_event("checkout.session.completed", session_obj)
        handler = _build_handler()
        send_receipts_mock = AsyncMock()
        with (
            patch(
                "grins_platform.repositories.invoice_repository.InvoiceRepository",
            ) as mock_repo_cls,
            patch(
                "grins_platform.services.appointment_service.AppointmentService",
            ) as mock_appt_svc_cls,
        ):
            mock_repo_cls.return_value.get_by_id = AsyncMock(
                return_value=invoice_paid,
            )
            mock_appt_svc_cls.return_value._send_payment_receipts = send_receipts_mock

            await handler._handle_checkout_completed_invoice_payment(
                event,
                session_obj,
                str(invoice_id),
            )

        send_receipts_mock.assert_not_awaited()


# =============================================================================
# payment_intent.payment_failed / canceled — log only
# =============================================================================


class TestPaymentIntentNonSuccess:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_payment_failed_is_log_only(self) -> None:
        """Payment failures don't mutate any invoice."""
        event = _make_event(
            "payment_intent.payment_failed",
            {"id": "pi_test", "last_payment_error": {"code": "card_declined"}},
        )
        handler = _build_handler()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            await handler._handle_payment_intent_payment_failed(event)
        mock_repo_cls.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_canceled_is_log_only(self) -> None:
        """Cancellations are noise for our flow."""
        event = _make_event(
            "payment_intent.canceled",
            {"id": "pi_test"},
        )
        handler = _build_handler()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            await handler._handle_payment_intent_canceled(event)
        mock_repo_cls.assert_not_called()


# =============================================================================
# charge.refunded
# =============================================================================


class TestChargeRefunded:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_full_refund_marks_invoice_refunded(self) -> None:
        """Full refunds transition invoice to REFUNDED + clear job flag."""
        invoice = SimpleNamespace(
            id=uuid4(),
            job_id=uuid4(),
            status=InvoiceStatus.PAID.value,
            notes=None,
        )
        event = _make_event(
            "charge.refunded",
            {
                "payment_intent": "pi_test_refund",
                "amount": 10000,
                "amount_refunded": 10000,
            },
        )
        handler = _build_handler()
        update_mock = AsyncMock()
        job_obj = SimpleNamespace(payment_collected_on_site=True)
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=job_obj)
        handler.session.execute = AsyncMock(return_value=scalar_result)
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_payment_intent_reference = AsyncMock(
                return_value=invoice,
            )
            mock_repo_cls.return_value.update = update_mock
            await handler._handle_charge_refunded(event)
        update_mock.assert_awaited_with(
            invoice.id,
            status=InvoiceStatus.REFUNDED.value,
            stripe_payment_link_active=False,
        )
        assert job_obj.payment_collected_on_site is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_partial_refund_keeps_invoice_partial(self) -> None:
        """Partial refunds adjust paid_amount + status=PARTIAL + annotate notes."""
        invoice = SimpleNamespace(
            id=uuid4(),
            job_id=uuid4(),
            status=InvoiceStatus.PAID.value,
            notes="prior",
        )
        event = _make_event(
            "charge.refunded",
            {
                "payment_intent": "pi_test_partial",
                "amount": 10000,
                "amount_refunded": 3000,
            },
        )
        handler = _build_handler()
        update_mock = AsyncMock()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_payment_intent_reference = AsyncMock(
                return_value=invoice,
            )
            mock_repo_cls.return_value.update = update_mock
            await handler._handle_charge_refunded(event)
        kwargs = update_mock.await_args.kwargs
        assert kwargs["status"] == InvoiceStatus.PARTIAL.value
        assert kwargs["paid_amount"] == Decimal("70.00")
        assert "Stripe partial refund" in kwargs["notes"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_full_refund_is_idempotent_on_already_refunded(self) -> None:
        """Replay of a full-refund event on a REFUNDED invoice is a no-op."""
        invoice = SimpleNamespace(
            id=uuid4(),
            job_id=uuid4(),
            status=InvoiceStatus.REFUNDED.value,
        )
        event = _make_event(
            "charge.refunded",
            {
                "payment_intent": "pi_replay",
                "amount": 5000,
                "amount_refunded": 5000,
            },
        )
        handler = _build_handler()
        update_mock = AsyncMock()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_payment_intent_reference = AsyncMock(
                return_value=invoice,
            )
            mock_repo_cls.return_value.update = update_mock
            await handler._handle_charge_refunded(event)
        update_mock.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unmatched_charge_is_logged(self) -> None:
        """Unknown PaymentIntent reference logs and returns."""
        event = _make_event(
            "charge.refunded",
            {
                "payment_intent": "pi_orphan",
                "amount": 5000,
                "amount_refunded": 5000,
            },
        )
        handler = _build_handler()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_payment_intent_reference = AsyncMock(
                return_value=None,
            )
            await handler._handle_charge_refunded(event)


# =============================================================================
# charge.dispute.created
# =============================================================================


class TestChargeDisputeCreated:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispute_marks_invoice_disputed_with_notes(self) -> None:
        """Dispute → DISPUTED status + notes annotation including reason."""
        invoice = SimpleNamespace(
            id=uuid4(),
            job_id=uuid4(),
            status=InvoiceStatus.PAID.value,
            notes=None,
        )
        event = _make_event(
            "charge.dispute.created",
            {
                "payment_intent": "pi_disputed",
                "reason": "fraudulent",
                "evidence_details": {"due_by": 1735689600},
            },
        )
        handler = _build_handler()
        update_mock = AsyncMock()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_payment_intent_reference = AsyncMock(
                return_value=invoice,
            )
            mock_repo_cls.return_value.update = update_mock
            await handler._handle_charge_dispute_created(event)
        kwargs = update_mock.await_args.kwargs
        assert kwargs["status"] == InvoiceStatus.DISPUTED.value
        assert "fraudulent" in kwargs["notes"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispute_is_idempotent_on_already_disputed(self) -> None:
        """Re-firing on an already-disputed invoice is a no-op."""
        invoice = SimpleNamespace(
            id=uuid4(),
            job_id=uuid4(),
            status=InvoiceStatus.DISPUTED.value,
            notes="prior",
        )
        event = _make_event(
            "charge.dispute.created",
            {
                "payment_intent": "pi_disputed",
                "reason": "fraudulent",
            },
        )
        handler = _build_handler()
        update_mock = AsyncMock()
        with patch(
            "grins_platform.repositories.invoice_repository.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_payment_intent_reference = AsyncMock(
                return_value=invoice,
            )
            mock_repo_cls.return_value.update = update_mock
            await handler._handle_charge_dispute_created(event)
        update_mock.assert_not_awaited()
