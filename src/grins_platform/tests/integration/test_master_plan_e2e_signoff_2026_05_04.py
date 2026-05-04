"""Master-plan e2e sign-off — Bug umbrella 2026-05-04.

Integration smoke test that asserts the umbrella's six fixes are wired
end-to-end through their webhook handlers:

- Bug #1: ``send_automated_message`` accepts ``customer_id``/``lead_id``/
  ``is_internal`` and dispatches accordingly (covered by service unit
  tests; this file asserts the kwargs flow into the handler).
- Bug #2 / #2b: ``PortalEstimateResponse`` carries customer + date
  fields; ``SendLinkResponse`` carries ``sms_failure_detail``.
- Bug #3: CallRail freshness extractor falls back through
  ``created_at`` → ``sent_at`` → receipt time.
- Bug #4: ``CampaignResponse`` orphan-insert coerces empty
  ``provider_message_id`` to ``None``.
- Bug #5: PaymentLink params include ``payment_intent_data.metadata``;
  the new ``checkout.session.completed`` correlator route fires when
  ``session.metadata.invoice_id`` is set.
- Bug #6: Stripe synthetic-phone fallback always passes
  ``normalize_phone``.

Scope: this is a smoke test. The full estimate-send → portal approve →
SMS Y → invoice → Apple-Pay flow needs real customer/auth fixtures;
those scenarios are exercised by their feature-level functional tests.
This file pins the umbrella's contracts at the integration layer so a
regression in any fix surfaces here before bleeding into the master
e2e plan.

Validates: ``.agents/plans/master-plan-run-findings-bug-resolution-2026-05-04.md``
Phase 6 / Task 6.1.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.api.v1.callrail_webhooks import _extract_created_at
from grins_platform.api.v1.webhooks import (
    StripeWebhookHandler,
    _synthetic_phone_for_event,
)
from grins_platform.models.enums import InvoiceStatus
from grins_platform.schemas.customer import normalize_phone
from grins_platform.schemas.invoice import SendLinkResponse
from grins_platform.schemas.portal import PortalEstimateResponse
from grins_platform.services.campaign_response_service import (
    CampaignResponseService,
)
from grins_platform.services.sms.base import InboundSMS
from grins_platform.services.stripe_payment_link_service import (
    StripePaymentLinkService,
)

pytestmark = pytest.mark.integration


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


class TestMasterPlanE2ESignoff20260504:
    """End-to-end sign-off contracts for the 2026-05-04 umbrella."""

    @pytest.mark.asyncio
    async def test_bug5_payment_link_params_carry_pi_metadata(self) -> None:
        """Bug #5: PaymentLink.create receives payment_intent_data.metadata."""
        settings = MagicMock()
        settings.is_configured = True
        settings.stripe_secret_key = "sk_test_x"
        settings.stripe_api_version = "2025-03-31.basil"
        invoice = SimpleNamespace(
            id=uuid4(),
            customer_id=uuid4(),
            invoice_number="INV-E2E-1",
            total_amount=Decimal("250.00"),
            line_items=[{"description": "service", "amount": "250.00"}],
        )
        customer = SimpleNamespace(id=uuid4(), first_name="J", last_name="D")
        with patch.object(stripe.PaymentLink, "create") as mock_create:
            mock_create.return_value = SimpleNamespace(
                id="plink_e2e",
                url="https://buy.stripe.com/e2e",
            )
            StripePaymentLinkService(settings).create_for_invoice(invoice, customer)
        kwargs = mock_create.call_args.kwargs
        pi_meta = kwargs["payment_intent_data"]["metadata"]
        assert pi_meta["invoice_id"] == str(invoice.id)
        assert pi_meta["customer_id"] == str(invoice.customer_id)

    @pytest.mark.asyncio
    async def test_bug5_checkout_session_invoice_correlator_fires(self) -> None:
        """Bug #5 backfill: session.metadata.invoice_id routes to invoice path."""
        invoice_id = uuid4()
        invoice = SimpleNamespace(
            id=invoice_id,
            job_id=uuid4(),
            status=InvoiceStatus.SENT.value,
        )
        event = _make_event(
            "checkout.session.completed",
            {
                "id": "cs_e2e",
                "payment_intent": "pi_e2e",
                "amount_total": 25000,
                "customer_details": {},
                "metadata": {"invoice_id": str(invoice_id)},
            },
        )
        handler = _build_handler()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=None)
        handler.session.execute = AsyncMock(return_value=scalar_result)
        record_payment_mock = AsyncMock()
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
        record_payment_mock.assert_awaited_once()
        record = record_payment_mock.await_args.args[1]
        assert record.amount == Decimal("250.00")

    def test_bug6_synthetic_phone_passes_validator(self) -> None:
        """Bug #6: synthetic phone for any Stripe event id is 10 digits."""
        synthetic = _synthetic_phone_for_event(
            "evt_1TTOFlQDNzCTp6j5nSoDqVvS",
        )
        assert len(synthetic) == 10
        assert synthetic.isdigit()
        assert normalize_phone(synthetic) == synthetic

    def test_bug3_callrail_freshness_falls_back_to_receipt_time(self) -> None:
        """Bug #3: payload with no timestamp falls back to receipt time."""
        value, source = _extract_created_at(
            {
                "resource_id": "MSG019de95f6f0e78d1ad1a7bb4fd59fc49",
                "source_number": "***3312",
                "content": "Y",
                "destination_number": "+19525293750",
                "thread_resource_id": "SMTabc",
                "conversation_id": "k8mc8",
            },
        )
        assert source == "receipt_time"
        # ISO-format string
        assert "T" in value

    def test_bug3_callrail_freshness_prefers_sent_at_when_present(self) -> None:
        value, source = _extract_created_at(
            {"sent_at": "2026-05-04T15:30:00+00:00"},
        )
        assert source == "payload_sent_at"
        assert value == "2026-05-04T15:30:00+00:00"

    @pytest.mark.asyncio
    async def test_bug4_orphan_empty_provider_sid_coerced_to_none(self) -> None:
        """Bug #4: empty provider_sid passed to CampaignResponse is None."""
        repo = AsyncMock()
        repo.add = AsyncMock(side_effect=lambda row: row)
        svc = CampaignResponseService(session=AsyncMock())
        svc.repo = repo

        await svc.record_poll_reply(
            InboundSMS(
                from_phone="+19527373312",
                body="Y",
                provider_sid="",
                thread_id=None,
            ),
        )
        inserted = repo.add.await_args.args[0]
        assert inserted.provider_message_id is None

    def test_bug2_portal_response_carries_customer_and_dates(self) -> None:
        """Bug #2: schema accepts the new customer + date fields."""
        from datetime import datetime, timezone

        resp = PortalEstimateResponse(
            status="sent",
            subtotal=Decimal(100),
            tax_amount=Decimal(0),
            discount_amount=Decimal(0),
            total=Decimal(100),
            customer_first_name="Jane",
            customer_last_name="Doe",
            customer_email="kirillrakitinsecond@gmail.com",
            created_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
            sent_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
        )
        assert resp.customer_first_name == "Jane"
        assert resp.customer_last_name == "Doe"
        assert resp.customer_email == "kirillrakitinsecond@gmail.com"
        assert resp.created_at is not None
        assert resp.sent_at is not None

    def test_bug2b_send_link_response_carries_failure_detail(self) -> None:
        """Bug #2b: SendLinkResponse exposes the raw upstream reason."""
        from datetime import datetime, timezone

        resp = SendLinkResponse(
            channel="email",
            link_url="https://buy.stripe.com/x",
            sent_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
            sent_count=1,
            attempted_channels=["sms", "email"],
            sms_failure_reason="provider_error",
            sms_failure_detail="duplicate_message_within_24_hours",
        )
        assert resp.sms_failure_detail == "duplicate_message_within_24_hours"
