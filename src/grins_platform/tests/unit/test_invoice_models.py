"""Tests for Invoice model and related enums.

This module tests the Invoice SQLAlchemy model, InvoiceStatus enum,
and PaymentMethod enum.

Requirements: 7.1-7.10, 8.1-8.10, 9.2
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from grins_platform.models.enums import InvoiceStatus, PaymentMethod
from grins_platform.models.invoice import Invoice


class TestInvoiceStatusEnum:
    """Test suite for InvoiceStatus enum."""

    def test_draft_value(self) -> None:
        """Test draft status value."""
        assert InvoiceStatus.DRAFT.value == "draft"

    def test_sent_value(self) -> None:
        """Test sent status value."""
        assert InvoiceStatus.SENT.value == "sent"

    def test_viewed_value(self) -> None:
        """Test viewed status value."""
        assert InvoiceStatus.VIEWED.value == "viewed"

    def test_paid_value(self) -> None:
        """Test paid status value."""
        assert InvoiceStatus.PAID.value == "paid"

    def test_partial_value(self) -> None:
        """Test partial status value."""
        assert InvoiceStatus.PARTIAL.value == "partial"

    def test_overdue_value(self) -> None:
        """Test overdue status value."""
        assert InvoiceStatus.OVERDUE.value == "overdue"

    def test_lien_warning_value(self) -> None:
        """Test lien_warning status value."""
        assert InvoiceStatus.LIEN_WARNING.value == "lien_warning"

    def test_lien_filed_value(self) -> None:
        """Test lien_filed status value."""
        assert InvoiceStatus.LIEN_FILED.value == "lien_filed"

    def test_cancelled_value(self) -> None:
        """Test cancelled status value."""
        assert InvoiceStatus.CANCELLED.value == "cancelled"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert InvoiceStatus("draft") == InvoiceStatus.DRAFT
        assert InvoiceStatus("sent") == InvoiceStatus.SENT
        assert InvoiceStatus("paid") == InvoiceStatus.PAID
        assert InvoiceStatus("overdue") == InvoiceStatus.OVERDUE

    def test_all_statuses_count(self) -> None:
        """Test that all expected statuses exist."""
        expected_statuses = {
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
        actual_statuses = {status.value for status in InvoiceStatus}
        assert actual_statuses == expected_statuses


class TestPaymentMethodEnum:
    """Test suite for PaymentMethod enum."""

    def test_cash_value(self) -> None:
        """Test cash payment method value."""
        assert PaymentMethod.CASH.value == "cash"

    def test_check_value(self) -> None:
        """Test check payment method value."""
        assert PaymentMethod.CHECK.value == "check"

    def test_venmo_value(self) -> None:
        """Test venmo payment method value."""
        assert PaymentMethod.VENMO.value == "venmo"

    def test_zelle_value(self) -> None:
        """Test zelle payment method value."""
        assert PaymentMethod.ZELLE.value == "zelle"

    def test_stripe_value(self) -> None:
        """Test stripe payment method value."""
        assert PaymentMethod.STRIPE.value == "stripe"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert PaymentMethod("cash") == PaymentMethod.CASH
        assert PaymentMethod("venmo") == PaymentMethod.VENMO
        assert PaymentMethod("stripe") == PaymentMethod.STRIPE

    def test_all_payment_methods_count(self) -> None:
        """Test that all expected payment methods exist."""
        expected_methods = {"cash", "check", "venmo", "zelle", "stripe"}
        actual_methods = {method.value for method in PaymentMethod}
        assert actual_methods == expected_methods


class TestInvoiceModel:
    """Test suite for Invoice model."""

    def test_invoice_tablename(self) -> None:
        """Test invoice table name."""
        assert Invoice.__tablename__ == "invoices"

    def test_invoice_instantiation(self) -> None:
        """Test Invoice model can be instantiated."""
        invoice = Invoice()
        assert invoice is not None

    def test_invoice_with_basic_fields(self) -> None:
        """Test Invoice model with basic fields set."""
        invoice = Invoice()
        invoice.invoice_number = "INV-2025-0001"
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.due_date = date(2025, 2, 15)
        invoice.status = "draft"

        assert invoice.invoice_number == "INV-2025-0001"
        assert invoice.amount == Decimal("150.00")
        assert invoice.late_fee_amount == Decimal("0.00")
        assert invoice.total_amount == Decimal("150.00")
        assert invoice.due_date == date(2025, 2, 15)
        assert invoice.status == "draft"

    def test_invoice_with_payment_info(self) -> None:
        """Test Invoice model with payment information."""
        invoice = Invoice()
        invoice.payment_method = "venmo"
        invoice.payment_reference = "txn_123456"
        invoice.paid_at = datetime(2025, 1, 29, 10, 30, 0)
        invoice.paid_amount = Decimal("150.00")

        assert invoice.payment_method == "venmo"
        assert invoice.payment_reference == "txn_123456"
        assert invoice.paid_at == datetime(2025, 1, 29, 10, 30, 0)
        assert invoice.paid_amount == Decimal("150.00")

    def test_invoice_with_reminder_info(self) -> None:
        """Test Invoice model with reminder information."""
        invoice = Invoice()
        invoice.reminder_count = 2
        invoice.last_reminder_sent = datetime(2025, 1, 28, 9, 0, 0)

        assert invoice.reminder_count == 2
        assert invoice.last_reminder_sent == datetime(2025, 1, 28, 9, 0, 0)

    def test_invoice_with_lien_info(self) -> None:
        """Test Invoice model with lien tracking information."""
        invoice = Invoice()
        invoice.lien_eligible = True
        invoice.lien_warning_sent = datetime(2025, 1, 15, 10, 0, 0)
        invoice.lien_filed_date = date(2025, 3, 1)

        assert invoice.lien_eligible is True
        assert invoice.lien_warning_sent == datetime(2025, 1, 15, 10, 0, 0)
        assert invoice.lien_filed_date == date(2025, 3, 1)

    def test_invoice_with_line_items(self) -> None:
        """Test Invoice model with line items JSONB field."""
        invoice = Invoice()
        invoice.line_items = [
            {
                "description": "Spring Startup",
                "quantity": 1,
                "unit_price": 100.00,
                "total": 100.00,
            },
            {
                "description": "Zone Adjustment",
                "quantity": 2,
                "unit_price": 25.00,
                "total": 50.00,
            },
        ]

        assert invoice.line_items is not None
        assert len(invoice.line_items) == 2
        assert invoice.line_items[0]["description"] == "Spring Startup"
        assert invoice.line_items[1]["quantity"] == 2

    def test_invoice_with_notes(self) -> None:
        """Test Invoice model with notes field."""
        invoice = Invoice()
        invoice.notes = "Customer requested itemized breakdown"

        assert invoice.notes == "Customer requested itemized breakdown"

    def test_invoice_nullable_fields(self) -> None:
        """Test Invoice model nullable fields can be None."""
        invoice = Invoice()
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.paid_amount = None
        invoice.last_reminder_sent = None
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None

        assert invoice.payment_method is None
        assert invoice.payment_reference is None
        assert invoice.paid_at is None
        assert invoice.paid_amount is None
        assert invoice.last_reminder_sent is None
        assert invoice.lien_warning_sent is None
        assert invoice.lien_filed_date is None
        assert invoice.line_items is None
        assert invoice.notes is None

    def test_invoice_repr(self) -> None:
        """Test invoice string representation."""
        invoice = Invoice()
        invoice.id = UUID("12345678-1234-5678-1234-567812345678")
        invoice.invoice_number = "INV-2025-0001"
        invoice.status = "draft"
        invoice.total_amount = Decimal("150.00")

        repr_str = repr(invoice)
        assert "Invoice" in repr_str
        assert "INV-2025-0001" in repr_str
        assert "draft" in repr_str
        assert "150.00" in repr_str

    def test_invoice_decimal_precision(self) -> None:
        """Test Invoice model handles decimal precision correctly."""
        invoice = Invoice()
        invoice.amount = Decimal("99.99")
        invoice.late_fee_amount = Decimal("15.50")
        invoice.total_amount = Decimal("115.49")
        invoice.paid_amount = Decimal("50.25")

        assert invoice.amount == Decimal("99.99")
        assert invoice.late_fee_amount == Decimal("15.50")
        assert invoice.total_amount == Decimal("115.49")
        assert invoice.paid_amount == Decimal("50.25")

    def test_invoice_status_values(self) -> None:
        """Test Invoice model accepts all valid status values."""
        invoice = Invoice()

        for status in InvoiceStatus:
            invoice.status = status.value
            assert invoice.status == status.value

    def test_invoice_payment_method_values(self) -> None:
        """Test Invoice model accepts all valid payment method values."""
        invoice = Invoice()

        for method in PaymentMethod:
            invoice.payment_method = method.value
            assert invoice.payment_method == method.value


class TestInvoiceRelationships:
    """Test suite for Invoice model relationships."""

    def test_invoice_has_job_relationship(self) -> None:
        """Test Invoice model has job relationship defined."""
        assert hasattr(Invoice, "job")

    def test_invoice_has_customer_relationship(self) -> None:
        """Test Invoice model has customer relationship defined."""
        assert hasattr(Invoice, "customer")

    def test_invoice_job_relationship_type(self) -> None:
        """Test Invoice job relationship is properly configured."""
        # Check the relationship is defined in the mapper
        mapper = Invoice.__mapper__
        assert "job" in mapper.relationships

    def test_invoice_customer_relationship_type(self) -> None:
        """Test Invoice customer relationship is properly configured."""
        # Check the relationship is defined in the mapper
        mapper = Invoice.__mapper__
        assert "customer" in mapper.relationships
