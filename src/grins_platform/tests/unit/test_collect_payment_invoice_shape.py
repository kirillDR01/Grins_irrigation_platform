"""Regression tests for B-1 (2026-05-04 sign-off).

``AppointmentService.collect_payment`` previously wrote line_items in the
legacy ``{description, amount}`` shape, but the strict ``InvoiceLineItem``
schema requires ``{description, quantity, unit_price, total}``. The shape
drift caused ``InvoiceResponse.model_validate`` to raise on serialization
and any GET to the affected invoice returned HTTP 500.

The fix: emit the strict shape from ``collect_payment`` (and an alembic
backfill for already-written rows). This test asserts the strict shape
is in fact what the writer emits.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus, PaymentMethod
from grins_platform.schemas.appointment_ops import PaymentCollectionRequest
from grins_platform.schemas.invoice import InvoiceLineItem
from grins_platform.services.appointment_service import AppointmentService


def _make_appointment() -> MagicMock:
    appt = MagicMock()
    appt.id = uuid4()
    appt.job_id = uuid4()
    appt.staff_id = uuid4()
    appt.status = AppointmentStatus.IN_PROGRESS.value
    appt.scheduled_date = date(2026, 5, 4)
    appt.time_window_start = time(9, 0)
    appt.time_window_end = time(11, 0)
    appt.arrived_at = datetime.now(tz=timezone.utc)
    return appt


def _make_job() -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.customer_id = uuid4()
    job.job_type = "repair"
    return job


def _make_invoice_with_line_items(line_items: list[dict]) -> MagicMock:
    inv = MagicMock()
    inv.id = uuid4()
    inv.invoice_number = "INV-2026-0001"
    inv.line_items = line_items
    inv.total_amount = Decimal("250.00")
    inv.status = "paid"
    inv.paid_amount = Decimal("250.00")
    inv.customer_id = uuid4()
    return inv


@pytest.mark.unit
class TestCollectPaymentInvoiceShape:
    """B-1 — collect_payment must write strict InvoiceLineItem shape."""

    @pytest.mark.asyncio
    async def test_writer_emits_strict_line_item_shape(self) -> None:
        """The line_items kwarg passed to repo.create has strict shape."""
        appointment = _make_appointment()
        job = _make_job()

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        invoice_repo = AsyncMock()
        invoice_repo.get_next_sequence = AsyncMock(return_value=1)

        captured_line_items: list[dict] = []

        async def fake_create(**kwargs):
            captured_line_items.extend(kwargs["line_items"])
            return _make_invoice_with_line_items(kwargs["line_items"])

        invoice_repo.create = AsyncMock(side_effect=fake_create)
        invoice_repo.update = AsyncMock(return_value=_make_invoice_with_line_items([]))
        invoice_repo.find_by_job_id = AsyncMock(return_value=None)

        service = AppointmentService(
            appointment_repository=appt_repo,
            job_repository=job_repo,
            staff_repository=AsyncMock(),
            invoice_repository=invoice_repo,
        )

        # Bypass the existing-invoice lookup helper so we hit the create branch.
        async def _no_existing(_job_id):
            return None

        service._find_invoice_for_job = _no_existing  # type: ignore[assignment,method-assign]

        # Prevent real SMS/email receipt dispatch — we only care about the
        # writer's line_items shape, not the receipt path.
        async def _noop_receipts(*_args, **_kwargs):
            return None

        service._send_payment_receipts = _noop_receipts  # type: ignore[assignment,method-assign]

        request = PaymentCollectionRequest(
            payment_method=PaymentMethod.CASH,
            amount=Decimal("250.00"),
            reference_number=None,
        )
        await service.collect_payment(appointment.id, request)

        assert len(captured_line_items) == 1
        item = captured_line_items[0]
        # Strict shape keys.
        assert set(item.keys()) == {"description", "quantity", "unit_price", "total"}
        # Pydantic v2 must accept this dict directly.
        validated = InvoiceLineItem.model_validate(item)
        assert validated.quantity == Decimal(1)
        assert validated.unit_price == Decimal("250.00")
        assert validated.total == Decimal("250.00")
