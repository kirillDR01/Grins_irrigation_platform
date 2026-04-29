"""Unit test for Bug 2 — ``send_payment_link`` catches ``EmailRecipientNotAllowedError``.

When the dev/staging email allowlist refuses the recipient and SMS also
fails, the service must surface ``NoContactMethodError`` (HTTP 422 via
the typed handler) — not propagate the email exception (HTTP 500).

Validates: bughunt 2026-04-28 §Bug 2.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import NoContactMethodError
from grins_platform.services.email_service import EmailRecipientNotAllowedError
from grins_platform.services.invoice_service import InvoiceService


def _make_invoice() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        customer_id=uuid4(),
        invoice_number="INV-2026-0099",
        total_amount=Decimal("100.00"),
        line_items=[],
        stripe_payment_link_id="plink_x",
        stripe_payment_link_url="https://buy.stripe.com/test",
        stripe_payment_link_active=True,
        payment_link_sent_at=None,
        payment_link_sent_count=0,
    )


def _make_customer() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        first_name="Blocked",
        last_name="Customer",
        phone="+15555550001",  # NOT in SMS allowlist; SMS will soft-fail
        email="not-on-allowlist@example.com",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_email_allowlist_refusal_surfaces_as_no_contact_method(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Email-allowlist exception must be caught and converted to 422 path."""
    invoice = _make_invoice()
    customer = _make_customer()

    invoice_repo = AsyncMock()
    invoice_repo.get_by_id.return_value = invoice
    invoice_repo.update.return_value = invoice

    customer_repo = AsyncMock()
    customer_repo.get_by_id.return_value = customer

    sms_service = AsyncMock()
    # SMS soft-fails so we proceed to the email branch.
    sms_service.send_message.return_value = {"success": False, "status": "failed"}

    email_service = MagicMock()
    email_service._send_email = MagicMock(
        side_effect=EmailRecipientNotAllowedError(
            "recipient_not_in_email_allowlist: provider=resend"
        ),
    )

    service = InvoiceService(
        invoice_repository=invoice_repo,
        job_repository=MagicMock(),
        customer_repository=customer_repo,
        payment_link_service=MagicMock(),
        sms_service=sms_service,
        email_service=email_service,
    )

    with pytest.raises(NoContactMethodError):
        await service.send_payment_link(invoice.id)

    # _send_email was attempted exactly once (and raised).
    assert email_service._send_email.call_count == 1
