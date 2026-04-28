"""Unit tests for ``InvoiceService.send_payment_link``.

Validates: Stripe Payment Links plan §Phase 2.7.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from grins_platform.exceptions import (
    LeadOnlyInvoiceError,
    NoContactMethodError,
)
from grins_platform.services.invoice_service import (
    InvalidInvoiceOperationError,
    InvoiceNotFoundError,
    InvoiceService,
)
from grins_platform.services.sms_service import (
    SMSConsentDeniedError,
    SMSError,
)


def _make_invoice(
    *,
    invoice_id: UUID | None = None,
    customer_id: UUID | None = None,
    total: Decimal = Decimal("100.00"),
    link_url: str | None = "https://buy.stripe.com/test",
    link_active: bool = True,
    sent_count: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=invoice_id or uuid4(),
        customer_id=customer_id or uuid4(),
        invoice_number="INV-2026-0001",
        total_amount=total,
        line_items=[],
        stripe_payment_link_id="plink_x" if link_url else None,
        stripe_payment_link_url=link_url,
        stripe_payment_link_active=link_active,
        payment_link_sent_at=None,
        payment_link_sent_count=sent_count,
    )


def _make_customer(
    *,
    phone: str | None = "+19527373312",
    email: str | None = "kirillrakitinsecond@gmail.com",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        first_name="Jane",
        last_name="Doe",
        phone=phone,
        email=email,
    )


def _build_service(
    *,
    invoice: SimpleNamespace,
    customer: SimpleNamespace | None,
    sms_result: dict | None = None,
    sms_exc: type[Exception] | None = None,
    email_sent: bool = True,
) -> InvoiceService:
    invoice_repo = AsyncMock()
    invoice_repo.get_by_id.return_value = invoice
    invoice_repo.update.return_value = invoice

    customer_repo = AsyncMock()
    customer_repo.get_by_id.return_value = customer

    sms_service = AsyncMock()
    if sms_exc is not None:
        sms_service.send_message.side_effect = sms_exc("boom")
    else:
        sms_service.send_message.return_value = sms_result or {"success": True}

    email_service = MagicMock()
    email_service._send_email = MagicMock(return_value=email_sent)

    payment_link_service = MagicMock()
    payment_link_service.create_for_invoice.return_value = (
        "plink_lazy",
        "https://buy.stripe.com/lazy",
    )

    return InvoiceService(
        invoice_repository=invoice_repo,
        job_repository=MagicMock(),
        customer_repository=customer_repo,
        payment_link_service=payment_link_service,
        sms_service=sms_service,
        email_service=email_service,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_sms_happy_path() -> None:
    """SMS happy path returns ``channel='sms'`` and increments count."""
    invoice = _make_invoice()
    customer = _make_customer()
    service = _build_service(invoice=invoice, customer=customer)
    response = await service.send_payment_link(invoice.id)
    assert response.channel == "sms"
    assert response.sent_count == 1
    assert response.link_url == invoice.stripe_payment_link_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_falls_back_to_email_on_sms_consent_denied() -> None:
    """Hard-STOP customers fall through cleanly to email."""
    invoice = _make_invoice()
    customer = _make_customer()
    service = _build_service(
        invoice=invoice,
        customer=customer,
        sms_exc=SMSConsentDeniedError,
    )
    response = await service.send_payment_link(invoice.id)
    assert response.channel == "email"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_falls_back_to_email_on_sms_error() -> None:
    """Provider errors fall through to email path."""
    invoice = _make_invoice()
    customer = _make_customer()
    service = _build_service(
        invoice=invoice,
        customer=customer,
        sms_exc=SMSError,
    )
    response = await service.send_payment_link(invoice.id)
    assert response.channel == "email"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_email_only_when_no_phone() -> None:
    """Customers without a phone go straight to email."""
    invoice = _make_invoice()
    customer = _make_customer(phone=None)
    service = _build_service(invoice=invoice, customer=customer)
    response = await service.send_payment_link(invoice.id)
    assert response.channel == "email"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_no_phone_no_email_raises() -> None:
    """Customer with neither contact method raises ``NoContactMethodError``."""
    invoice = _make_invoice()
    customer = _make_customer(phone=None, email=None)
    service = _build_service(invoice=invoice, customer=customer)
    with pytest.raises(NoContactMethodError):
        await service.send_payment_link(invoice.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_zero_amount_invoice_rejected() -> None:
    """$0 invoices cannot send a Payment Link (F11)."""
    invoice = _make_invoice(total=Decimal(0))
    customer = _make_customer()
    service = _build_service(invoice=invoice, customer=customer)
    with pytest.raises(InvalidInvoiceOperationError):
        await service.send_payment_link(invoice.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_lead_only_invoice_rejected() -> None:
    """Null customer (lead-only) raises ``LeadOnlyInvoiceError``."""
    invoice = _make_invoice()
    service = _build_service(invoice=invoice, customer=None)
    with pytest.raises(LeadOnlyInvoiceError):
        await service.send_payment_link(invoice.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_invoice_not_found_raises() -> None:
    """Missing invoice raises ``InvoiceNotFoundError``."""
    invoice_repo = AsyncMock()
    invoice_repo.get_by_id.return_value = None
    service = InvoiceService(
        invoice_repository=invoice_repo,
        job_repository=MagicMock(),
        customer_repository=AsyncMock(),
    )
    with pytest.raises(InvoiceNotFoundError):
        await service.send_payment_link(uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_lazy_creates_when_missing() -> None:
    """If invoice has no link, ``_attach_payment_link`` is called."""
    invoice = _make_invoice(link_url=None, link_active=False)
    customer = _make_customer()
    invoice_repo = AsyncMock()
    # First get returns invoice with no link, second returns with link.
    invoice_with_link = _make_invoice(
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
    )
    invoice_repo.get_by_id.side_effect = [invoice, invoice_with_link, invoice_with_link]
    customer_repo = AsyncMock()
    customer_repo.get_by_id.return_value = customer

    payment_link_service = MagicMock()
    payment_link_service.create_for_invoice.return_value = (
        "plink_lazy",
        "https://buy.stripe.com/lazy",
    )
    sms_service = AsyncMock()
    sms_service.send_message.return_value = {"success": True}

    service = InvoiceService(
        invoice_repository=invoice_repo,
        job_repository=MagicMock(),
        customer_repository=customer_repo,
        payment_link_service=payment_link_service,
        sms_service=sms_service,
    )
    response = await service.send_payment_link(invoice.id)
    assert response.channel == "sms"
    payment_link_service.create_for_invoice.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_payment_link_sms_uses_transactional_consent_type() -> None:
    """Per F12, SMS path passes ``consent_type='transactional'``."""
    invoice = _make_invoice()
    customer = _make_customer()
    service = _build_service(invoice=invoice, customer=customer)
    await service.send_payment_link(invoice.id)
    call = service.sms_service.send_message.await_args
    assert call.kwargs["consent_type"] == "transactional"
