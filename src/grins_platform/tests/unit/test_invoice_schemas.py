"""Tests for Invoice Pydantic schemas.

This module tests the invoice-related Pydantic schemas including
validation for line items, payment amounts, and enum values.

Requirements: 7.1-7.10, 9.1-9.7
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.models.enums import InvoiceStatus, PaymentMethod
from grins_platform.schemas.invoice import (
    InvoiceCreate,
    InvoiceLineItem,
    InvoiceListParams,
    InvoiceUpdate,
    LienFiledRequest,
    PaymentRecord,
)


class TestInvoiceLineItemValidation:
    """Test suite for InvoiceLineItem schema validation."""

    def test_valid_line_item(self) -> None:
        """Test creating a valid line item."""
        item = InvoiceLineItem(
            description="Spring Startup",
            quantity=Decimal(1),
            unit_price=Decimal("100.00"),
            total=Decimal("100.00"),
        )
        assert item.description == "Spring Startup"
        assert item.quantity == Decimal(1)
        assert item.unit_price == Decimal("100.00")
        assert item.total == Decimal("100.00")

    def test_line_item_with_multiple_quantity(self) -> None:
        """Test line item with quantity > 1."""
        item = InvoiceLineItem(
            description="Sprinkler Head Replacement",
            quantity=Decimal(5),
            unit_price=Decimal("50.00"),
            total=Decimal("250.00"),
        )
        assert item.quantity == Decimal(5)
        assert item.total == Decimal("250.00")

    def test_line_item_zero_quantity_rejected(self) -> None:
        """Test that zero quantity is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceLineItem(
                description="Test Item",
                quantity=Decimal(0),
                unit_price=Decimal("100.00"),
                total=Decimal("0.00"),
            )
        errors = exc_info.value.errors()
        assert any("quantity" in str(e["loc"]) for e in errors)

    def test_line_item_negative_quantity_rejected(self) -> None:
        """Test that negative quantity is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceLineItem(
                description="Test Item",
                quantity=Decimal(-1),
                unit_price=Decimal("100.00"),
                total=Decimal("-100.00"),
            )
        errors = exc_info.value.errors()
        assert any("quantity" in str(e["loc"]) for e in errors)

    def test_line_item_negative_unit_price_rejected(self) -> None:
        """Test that negative unit price is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceLineItem(
                description="Test Item",
                quantity=Decimal(1),
                unit_price=Decimal("-50.00"),
                total=Decimal("-50.00"),
            )
        errors = exc_info.value.errors()
        assert any("unit_price" in str(e["loc"]) for e in errors)

    def test_line_item_negative_total_rejected(self) -> None:
        """Test that negative total is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceLineItem(
                description="Test Item",
                quantity=Decimal(1),
                unit_price=Decimal("50.00"),
                total=Decimal("-50.00"),
            )
        errors = exc_info.value.errors()
        assert any("total" in str(e["loc"]) for e in errors)

    def test_line_item_zero_unit_price_allowed(self) -> None:
        """Test that zero unit price is allowed (free items)."""
        item = InvoiceLineItem(
            description="Complimentary Service",
            quantity=Decimal(1),
            unit_price=Decimal("0.00"),
            total=Decimal("0.00"),
        )
        assert item.unit_price == Decimal("0.00")

    def test_line_item_empty_description_rejected(self) -> None:
        """Test that empty description is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceLineItem(
                description="",
                quantity=Decimal(1),
                unit_price=Decimal("100.00"),
                total=Decimal("100.00"),
            )
        errors = exc_info.value.errors()
        assert any("description" in str(e["loc"]) for e in errors)

    def test_line_item_description_max_length(self) -> None:
        """Test description max length validation."""
        long_desc = "A" * 501
        with pytest.raises(ValidationError) as exc_info:
            InvoiceLineItem(
                description=long_desc,
                quantity=Decimal(1),
                unit_price=Decimal("100.00"),
                total=Decimal("100.00"),
            )
        errors = exc_info.value.errors()
        assert any("description" in str(e["loc"]) for e in errors)

    def test_line_item_decimal_precision(self) -> None:
        """Test line item handles decimal precision."""
        item = InvoiceLineItem(
            description="Precision Test",
            quantity=Decimal("2.5"),
            unit_price=Decimal("33.33"),
            total=Decimal("83.33"),
        )
        assert item.quantity == Decimal("2.5")
        assert item.unit_price == Decimal("33.33")


class TestPaymentRecordValidation:
    """Test suite for PaymentRecord schema validation."""

    def test_valid_payment_record(self) -> None:
        """Test creating a valid payment record."""
        payment = PaymentRecord(
            amount=Decimal("150.00"),
            payment_method=PaymentMethod.VENMO,
            payment_reference="txn_123456",
        )
        assert payment.amount == Decimal("150.00")
        assert payment.payment_method == PaymentMethod.VENMO
        assert payment.payment_reference == "txn_123456"

    def test_payment_without_reference(self) -> None:
        """Test payment record without reference (cash)."""
        payment = PaymentRecord(
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.CASH,
        )
        assert payment.payment_reference is None

    def test_payment_zero_amount_rejected(self) -> None:
        """Test that zero payment amount is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentRecord(
                amount=Decimal("0.00"),
                payment_method=PaymentMethod.CASH,
            )
        errors = exc_info.value.errors()
        assert any("amount" in str(e["loc"]) for e in errors)

    def test_payment_negative_amount_rejected(self) -> None:
        """Test that negative payment amount is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentRecord(
                amount=Decimal("-50.00"),
                payment_method=PaymentMethod.CHECK,
            )
        errors = exc_info.value.errors()
        assert any("amount" in str(e["loc"]) for e in errors)

    def test_payment_all_methods(self) -> None:
        """Test payment record accepts all payment methods."""
        for method in PaymentMethod:
            payment = PaymentRecord(
                amount=Decimal("100.00"),
                payment_method=method,
            )
            assert payment.payment_method == method

    def test_payment_invalid_method_rejected(self) -> None:
        """Test that invalid payment method is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentRecord(
                amount=Decimal("100.00"),
                payment_method="invalid_method",  # type: ignore[arg-type]
            )
        errors = exc_info.value.errors()
        assert any("payment_method" in str(e["loc"]) for e in errors)

    def test_payment_reference_max_length(self) -> None:
        """Test payment reference max length validation."""
        long_ref = "A" * 256
        with pytest.raises(ValidationError) as exc_info:
            PaymentRecord(
                amount=Decimal("100.00"),
                payment_method=PaymentMethod.STRIPE,
                payment_reference=long_ref,
            )
        errors = exc_info.value.errors()
        assert any("payment_reference" in str(e["loc"]) for e in errors)

    def test_payment_small_amount(self) -> None:
        """Test payment with small amount (cents)."""
        payment = PaymentRecord(
            amount=Decimal("0.01"),
            payment_method=PaymentMethod.CASH,
        )
        assert payment.amount == Decimal("0.01")


class TestInvoiceCreateValidation:
    """Test suite for InvoiceCreate schema validation."""

    def test_valid_invoice_create(self) -> None:
        """Test creating a valid invoice."""
        invoice = InvoiceCreate(
            job_id=uuid4(),
            amount=Decimal("150.00"),
            due_date=date(2025, 2, 15),
        )
        assert invoice.amount == Decimal("150.00")
        assert invoice.late_fee_amount == Decimal(0)

    def test_invoice_create_with_late_fee(self) -> None:
        """Test invoice creation with late fee."""
        invoice = InvoiceCreate(
            job_id=uuid4(),
            amount=Decimal("150.00"),
            late_fee_amount=Decimal("25.00"),
            due_date=date(2025, 2, 15),
        )
        assert invoice.late_fee_amount == Decimal("25.00")

    def test_invoice_create_with_line_items(self) -> None:
        """Test invoice creation with line items."""
        line_items = [
            InvoiceLineItem(
                description="Spring Startup",
                quantity=Decimal(1),
                unit_price=Decimal("100.00"),
                total=Decimal("100.00"),
            ),
            InvoiceLineItem(
                description="Zone Adjustment",
                quantity=Decimal(2),
                unit_price=Decimal("25.00"),
                total=Decimal("50.00"),
            ),
        ]
        invoice = InvoiceCreate(
            job_id=uuid4(),
            amount=Decimal("150.00"),
            due_date=date(2025, 2, 15),
            line_items=line_items,
        )
        assert len(invoice.line_items) == 2  # type: ignore[arg-type]

    def test_invoice_create_negative_amount_rejected(self) -> None:
        """Test that negative amount is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceCreate(
                job_id=uuid4(),
                amount=Decimal("-100.00"),
                due_date=date(2025, 2, 15),
            )
        errors = exc_info.value.errors()
        assert any("amount" in str(e["loc"]) for e in errors)

    def test_invoice_create_negative_late_fee_rejected(self) -> None:
        """Test that negative late fee is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceCreate(
                job_id=uuid4(),
                amount=Decimal("100.00"),
                late_fee_amount=Decimal("-10.00"),
                due_date=date(2025, 2, 15),
            )
        errors = exc_info.value.errors()
        assert any("late_fee_amount" in str(e["loc"]) for e in errors)

    def test_invoice_create_with_notes(self) -> None:
        """Test invoice creation with notes."""
        invoice = InvoiceCreate(
            job_id=uuid4(),
            amount=Decimal("150.00"),
            due_date=date(2025, 2, 15),
            notes="Customer requested itemized breakdown",
        )
        assert invoice.notes == "Customer requested itemized breakdown"

    def test_invoice_create_notes_max_length(self) -> None:
        """Test notes max length validation."""
        long_notes = "A" * 2001
        with pytest.raises(ValidationError) as exc_info:
            InvoiceCreate(
                job_id=uuid4(),
                amount=Decimal("100.00"),
                due_date=date(2025, 2, 15),
                notes=long_notes,
            )
        errors = exc_info.value.errors()
        assert any("notes" in str(e["loc"]) for e in errors)


class TestInvoiceUpdateValidation:
    """Test suite for InvoiceUpdate schema validation."""

    def test_valid_invoice_update(self) -> None:
        """Test valid invoice update."""
        update = InvoiceUpdate(
            amount=Decimal("175.00"),
        )
        assert update.amount == Decimal("175.00")

    def test_invoice_update_all_fields(self) -> None:
        """Test invoice update with all fields."""
        update = InvoiceUpdate(
            amount=Decimal("200.00"),
            late_fee_amount=Decimal("25.00"),
            due_date=date(2025, 3, 1),
            notes="Updated notes",
        )
        assert update.amount == Decimal("200.00")
        assert update.late_fee_amount == Decimal("25.00")
        assert update.due_date == date(2025, 3, 1)
        assert update.notes == "Updated notes"

    def test_invoice_update_partial(self) -> None:
        """Test partial invoice update."""
        update = InvoiceUpdate(
            notes="Only updating notes",
        )
        assert update.amount is None
        assert update.notes == "Only updating notes"

    def test_invoice_update_negative_amount_rejected(self) -> None:
        """Test that negative amount is rejected in update."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceUpdate(
                amount=Decimal("-50.00"),
            )
        errors = exc_info.value.errors()
        assert any("amount" in str(e["loc"]) for e in errors)


class TestInvoiceListParamsValidation:
    """Test suite for InvoiceListParams schema validation."""

    def test_default_params(self) -> None:
        """Test default list parameters."""
        params = InvoiceListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"

    def test_custom_pagination(self) -> None:
        """Test custom pagination parameters."""
        params = InvoiceListParams(page=3, page_size=50)
        assert params.page == 3
        assert params.page_size == 50

    def test_status_filter(self) -> None:
        """Test status filter parameter."""
        params = InvoiceListParams(status=InvoiceStatus.OVERDUE)
        assert params.status == InvoiceStatus.OVERDUE

    def test_all_status_filters(self) -> None:
        """Test all status values as filters."""
        for status in InvoiceStatus:
            params = InvoiceListParams(status=status)
            assert params.status == status

    def test_customer_filter(self) -> None:
        """Test customer ID filter."""
        customer_id = uuid4()
        params = InvoiceListParams(customer_id=customer_id)
        assert params.customer_id == customer_id

    def test_date_range_filter(self) -> None:
        """Test date range filter."""
        params = InvoiceListParams(
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 31),
        )
        assert params.date_from == date(2025, 1, 1)
        assert params.date_to == date(2025, 1, 31)

    def test_lien_eligible_filter(self) -> None:
        """Test lien eligible filter."""
        params = InvoiceListParams(lien_eligible=True)
        assert params.lien_eligible is True

    def test_sort_order_asc(self) -> None:
        """Test ascending sort order."""
        params = InvoiceListParams(sort_order="asc")
        assert params.sort_order == "asc"

    def test_sort_order_desc(self) -> None:
        """Test descending sort order."""
        params = InvoiceListParams(sort_order="desc")
        assert params.sort_order == "desc"

    def test_invalid_sort_order_rejected(self) -> None:
        """Test that invalid sort order is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceListParams(sort_order="invalid")
        errors = exc_info.value.errors()
        assert any("sort_order" in str(e["loc"]) for e in errors)

    def test_page_zero_rejected(self) -> None:
        """Test that page 0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceListParams(page=0)
        errors = exc_info.value.errors()
        assert any("page" in str(e["loc"]) for e in errors)

    def test_page_size_over_max_rejected(self) -> None:
        """Test that page size over 100 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvoiceListParams(page_size=101)
        errors = exc_info.value.errors()
        assert any("page_size" in str(e["loc"]) for e in errors)


class TestLienFiledRequestValidation:
    """Test suite for LienFiledRequest schema validation."""

    def test_valid_lien_filed_request(self) -> None:
        """Test valid lien filed request."""
        request = LienFiledRequest(
            filing_date=date(2025, 3, 1),
        )
        assert request.filing_date == date(2025, 3, 1)

    def test_lien_filed_with_notes(self) -> None:
        """Test lien filed request with notes."""
        request = LienFiledRequest(
            filing_date=date(2025, 3, 1),
            notes="Filed with county recorder",
        )
        assert request.notes == "Filed with county recorder"

    def test_lien_filed_notes_max_length(self) -> None:
        """Test notes max length validation."""
        long_notes = "A" * 2001
        with pytest.raises(ValidationError) as exc_info:
            LienFiledRequest(
                filing_date=date(2025, 3, 1),
                notes=long_notes,
            )
        errors = exc_info.value.errors()
        assert any("notes" in str(e["loc"]) for e in errors)


class TestEnumValidation:
    """Test suite for enum validation in schemas."""

    def test_invoice_status_enum_values(self) -> None:
        """Test all InvoiceStatus enum values are valid."""
        expected = {
            "draft",
            "sent",
            "viewed",
            "paid",
            "partial",
            "overdue",
            "lien_warning",
            "lien_filed",
            "cancelled",
        }
        actual = {s.value for s in InvoiceStatus}
        assert actual == expected

    def test_payment_method_enum_values(self) -> None:
        """Test all PaymentMethod enum values are valid."""
        expected = {"cash", "check", "venmo", "zelle", "stripe"}
        actual = {m.value for m in PaymentMethod}
        assert actual == expected

    def test_invoice_status_string_conversion(self) -> None:
        """Test InvoiceStatus can be created from string."""
        for status in InvoiceStatus:
            assert InvoiceStatus(status.value) == status

    def test_payment_method_string_conversion(self) -> None:
        """Test PaymentMethod can be created from string."""
        for method in PaymentMethod:
            assert PaymentMethod(method.value) == method
