"""Functional tests for invoice filtering.

Tests the 9-axis invoice filtering with mocked DB:
- Each filter axis individually
- AND composition (combining multiple filters)
- URL serialization/deserialization round-trip

Validates: Requirements 28.1, 37.1
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import InvoiceStatus
from grins_platform.repositories.invoice_repository import InvoiceRepository
from grins_platform.schemas.invoice import InvoiceListParams

# =============================================================================
# Helpers
# =============================================================================


def _make_invoice(**overrides: Any) -> MagicMock:
    """Create a mock Invoice with sensible defaults."""
    inv = MagicMock()
    inv.id = overrides.get("id", uuid4())
    inv.customer_id = overrides.get("customer_id", uuid4())
    inv.job_id = overrides.get("job_id", uuid4())
    inv.invoice_number = overrides.get("invoice_number", f"INV-2026-{uuid4().hex[:4]}")
    inv.status = overrides.get("status", "sent")
    inv.total_amount = overrides.get("total_amount", Decimal("500.00"))
    inv.amount = overrides.get("amount", Decimal("500.00"))
    inv.late_fee_amount = overrides.get("late_fee_amount", Decimal("0.00"))
    inv.invoice_date = overrides.get("invoice_date", date.today())
    inv.due_date = overrides.get("due_date", date.today() + timedelta(days=30))
    inv.paid_at = overrides.get("paid_at")
    inv.payment_method = overrides.get("payment_method")
    inv.payment_reference = overrides.get("payment_reference")
    inv.paid_amount = overrides.get("paid_amount")
    inv.lien_eligible = overrides.get("lien_eligible", False)
    inv.created_at = overrides.get("created_at", date.today())
    inv.updated_at = overrides.get("updated_at", date.today())
    return inv


def _build_repo(session: AsyncMock | None = None) -> InvoiceRepository:
    """Create an InvoiceRepository with a mocked session."""
    s = session or AsyncMock()
    return InvoiceRepository(s)


# =============================================================================
# 1. Individual Filter Axis Tests
# =============================================================================


@pytest.mark.functional
class TestInvoiceFilterAxisStatus:
    """Axis 1: Status filter produces a clause matching Invoice.status.

    Validates: Requirement 28.1
    """

    def test_status_filter_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(status=InvoiceStatus.PAID)
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "invoices.status" in clause_str

    def test_no_status_filter_produces_no_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams()
        clauses = repo._build_filters(params)
        assert len(clauses) == 0


@pytest.mark.functional
class TestInvoiceFilterAxisCustomer:
    """Axis 2: Customer filter by ID and by name search.

    Validates: Requirement 28.1
    """

    def test_customer_id_filter_produces_clause(self) -> None:
        repo = _build_repo()
        cid = uuid4()
        params = InvoiceListParams(customer_id=cid)
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "invoices.customer_id" in clause_str

    def test_customer_search_filter_produces_subquery_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(customer_search="Smith")
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0].compile(compile_kwargs={"literal_binds": False}))
        assert "customer" in clause_str.lower()


@pytest.mark.functional
class TestInvoiceFilterAxisJob:
    """Axis 3: Job filter by job_id.

    Validates: Requirement 28.1
    """

    def test_job_id_filter_produces_clause(self) -> None:
        repo = _build_repo()
        jid = uuid4()
        params = InvoiceListParams(job_id=jid)
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "invoices.job_id" in clause_str


@pytest.mark.functional
class TestInvoiceFilterAxisDateRange:
    """Axis 4: Date range filter (created/due/paid).

    Validates: Requirement 28.1
    """

    def test_date_from_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(date_from=date(2026, 1, 1))
        clauses = repo._build_filters(params)
        assert len(clauses) == 1

    def test_date_to_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(date_to=date(2026, 12, 31))
        clauses = repo._build_filters(params)
        assert len(clauses) == 1

    def test_date_range_produces_two_clauses(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 6, 30),
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 2

    def test_date_type_due_uses_due_date_column(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(
            date_from=date(2026, 1, 1),
            date_type="due",
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "due_date" in clause_str

    def test_date_type_paid_uses_paid_at_column(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(
            date_from=date(2026, 1, 1),
            date_type="paid",
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "paid_at" in clause_str

    def test_date_type_created_uses_invoice_date_column(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(
            date_from=date(2026, 1, 1),
            date_type="created",
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "invoice_date" in clause_str


@pytest.mark.functional
class TestInvoiceFilterAxisAmountRange:
    """Axis 5: Amount range filter (min/max).

    Validates: Requirement 28.1
    """

    def test_amount_min_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(amount_min=Decimal("100.00"))
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "total_amount" in clause_str

    def test_amount_max_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(amount_max=Decimal("5000.00"))
        clauses = repo._build_filters(params)
        assert len(clauses) == 1

    def test_amount_range_produces_two_clauses(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(
            amount_min=Decimal("100.00"),
            amount_max=Decimal("5000.00"),
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 2


@pytest.mark.functional
class TestInvoiceFilterAxisPaymentType:
    """Axis 6: Payment type multi-select filter.

    Validates: Requirement 28.1
    """

    def test_single_payment_type_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(payment_types="cash")
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "payment_method" in clause_str

    def test_multiple_payment_types_produces_in_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(payment_types="cash,check,stripe")
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "payment_method" in clause_str

    def test_empty_payment_types_produces_no_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(payment_types="")
        clauses = repo._build_filters(params)
        assert len(clauses) == 0


@pytest.mark.functional
class TestInvoiceFilterAxisDaysUntilDue:
    """Axis 7: Days until due filter.

    Validates: Requirement 28.1
    """

    def test_days_until_due_min_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(days_until_due_min=7)
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "due_date" in clause_str

    def test_days_until_due_range_produces_two_clauses(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(
            days_until_due_min=7,
            days_until_due_max=30,
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 2


@pytest.mark.functional
class TestInvoiceFilterAxisDaysPastDue:
    """Axis 8: Days past due filter.

    Validates: Requirement 28.1
    """

    def test_days_past_due_min_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(days_past_due_min=30)
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "due_date" in clause_str

    def test_days_past_due_range_produces_two_clauses(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(
            days_past_due_min=30,
            days_past_due_max=90,
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 2


@pytest.mark.functional
class TestInvoiceFilterAxisInvoiceNumber:
    """Axis 9: Invoice number exact match filter.

    Validates: Requirement 28.1
    """

    def test_invoice_number_produces_clause(self) -> None:
        repo = _build_repo()
        params = InvoiceListParams(invoice_number="INV-2026-0042")
        clauses = repo._build_filters(params)
        assert len(clauses) == 1
        clause_str = str(clauses[0])
        assert "invoice_number" in clause_str


# =============================================================================
# 2. AND Composition Tests
# =============================================================================


@pytest.mark.functional
class TestInvoiceFilterANDComposition:
    """Combining multiple filter axes produces AND-composed clauses.

    Validates: Requirements 28.1, 37.1
    """

    def test_two_axes_produce_two_clauses(self) -> None:
        """Status + customer_id → 2 AND-composed clauses."""
        repo = _build_repo()
        params = InvoiceListParams(
            status=InvoiceStatus.OVERDUE,
            customer_id=uuid4(),
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 2

    def test_three_axes_produce_three_clauses(self) -> None:
        """Status + amount_min + invoice_number → 3 clauses."""
        repo = _build_repo()
        params = InvoiceListParams(
            status=InvoiceStatus.SENT,
            amount_min=Decimal("100.00"),
            invoice_number="INV-2026-0001",
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 3

    def test_all_nine_axes_produce_correct_clause_count(self) -> None:
        """All 9 axes active simultaneously → correct total clause count.

        Axes: status(1) + customer_id(1) + job_id(1) + date_range(2)
              + amount_range(2) + payment_types(1) + days_until_due(2)
              + days_past_due(2) + invoice_number(1) = 13 clauses
        """
        repo = _build_repo()
        params = InvoiceListParams(
            status=InvoiceStatus.PAID,
            customer_id=uuid4(),
            job_id=uuid4(),
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
            amount_min=Decimal("50.00"),
            amount_max=Decimal("10000.00"),
            payment_types="cash,check",
            days_until_due_min=0,
            days_until_due_max=60,
            days_past_due_min=0,
            days_past_due_max=90,
            invoice_number="INV-2026-0099",
        )
        clauses = repo._build_filters(params)
        assert len(clauses) == 13

    def test_composition_is_additive(self) -> None:
        """Adding a filter axis increases clause count by expected amount.

        Validates: Requirement 37.1 — result set is intersection of each
        individual filter's result set.
        """
        repo = _build_repo()

        base = InvoiceListParams(status=InvoiceStatus.OVERDUE)
        base_count = len(repo._build_filters(base))

        extended = InvoiceListParams(
            status=InvoiceStatus.OVERDUE,
            amount_min=Decimal("500.00"),
        )
        extended_count = len(repo._build_filters(extended))

        assert extended_count == base_count + 1

    def test_status_plus_date_range_plus_amount(self) -> None:
        """Common real-world combo: status + date range + amount min."""
        repo = _build_repo()
        params = InvoiceListParams(
            status=InvoiceStatus.OVERDUE,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 3, 31),
            amount_min=Decimal("500.00"),
        )
        clauses = repo._build_filters(params)
        # status(1) + date_from(1) + date_to(1) + amount_min(1) = 4
        assert len(clauses) == 4

    def test_days_past_due_plus_lien_eligible(self) -> None:
        """Lien-eligible invoices past due > 60 days."""
        repo = _build_repo()
        params = InvoiceListParams(
            days_past_due_min=60,
            lien_eligible=True,
        )
        clauses = repo._build_filters(params)
        # days_past_due_min(1) + lien_eligible(1) = 2
        assert len(clauses) == 2


# =============================================================================
# 3. URL Serialization / Deserialization Round-Trip
# =============================================================================


@pytest.mark.functional
class TestInvoiceFilterURLRoundTrip:
    """Filter state survives serialize → deserialize via Pydantic model_dump.

    Validates: Requirements 28.3, 37.2
    """

    def test_status_round_trip(self) -> None:
        original = InvoiceListParams(status=InvoiceStatus.PAID)
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        assert restored.status == original.status

    def test_customer_id_round_trip(self) -> None:
        cid = uuid4()
        original = InvoiceListParams(customer_id=cid)
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        assert restored.customer_id == original.customer_id

    def test_date_range_round_trip(self) -> None:
        original = InvoiceListParams(
            date_from=date(2026, 3, 1),
            date_to=date(2026, 6, 30),
            date_type="due",
        )
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        assert restored.date_from == original.date_from
        assert restored.date_to == original.date_to
        assert restored.date_type == original.date_type

    def test_amount_range_round_trip(self) -> None:
        original = InvoiceListParams(
            amount_min=Decimal("99.99"),
            amount_max=Decimal("5000.50"),
        )
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        assert restored.amount_min == original.amount_min
        assert restored.amount_max == original.amount_max

    def test_payment_types_round_trip(self) -> None:
        original = InvoiceListParams(payment_types="cash,check,stripe")
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        assert restored.payment_types == original.payment_types

    def test_days_until_due_round_trip(self) -> None:
        original = InvoiceListParams(
            days_until_due_min=7,
            days_until_due_max=30,
        )
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        assert restored.days_until_due_min == original.days_until_due_min
        assert restored.days_until_due_max == original.days_until_due_max

    def test_days_past_due_round_trip(self) -> None:
        original = InvoiceListParams(
            days_past_due_min=30,
            days_past_due_max=90,
        )
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        assert restored.days_past_due_min == original.days_past_due_min
        assert restored.days_past_due_max == original.days_past_due_max

    def test_invoice_number_round_trip(self) -> None:
        original = InvoiceListParams(invoice_number="INV-2026-0042")
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        assert restored.invoice_number == original.invoice_number

    def test_full_multi_axis_round_trip(self) -> None:
        """All axes set → serialize → deserialize → identical params."""
        original = InvoiceListParams(
            status=InvoiceStatus.OVERDUE,
            customer_id=uuid4(),
            job_id=uuid4(),
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
            date_type="due",
            amount_min=Decimal("100.00"),
            amount_max=Decimal("9999.99"),
            payment_types="cash,venmo",
            days_until_due_min=0,
            days_until_due_max=60,
            days_past_due_min=1,
            days_past_due_max=120,
            invoice_number="INV-2026-0001",
        )
        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)

        assert restored.status == original.status
        assert restored.customer_id == original.customer_id
        assert restored.job_id == original.job_id
        assert restored.date_from == original.date_from
        assert restored.date_to == original.date_to
        assert restored.date_type == original.date_type
        assert restored.amount_min == original.amount_min
        assert restored.amount_max == original.amount_max
        assert restored.payment_types == original.payment_types
        assert restored.days_until_due_min == original.days_until_due_min
        assert restored.days_until_due_max == original.days_until_due_max
        assert restored.days_past_due_min == original.days_past_due_min
        assert restored.days_past_due_max == original.days_past_due_max
        assert restored.invoice_number == original.invoice_number

    def test_round_trip_preserves_filter_clause_count(self) -> None:
        """Serialized → deserialized params produce same number of clauses."""
        repo = _build_repo()
        original = InvoiceListParams(
            status=InvoiceStatus.SENT,
            amount_min=Decimal("200.00"),
            days_past_due_min=30,
        )
        original_clauses = len(repo._build_filters(original))

        serialized = original.model_dump(exclude_none=True, mode="json")
        restored = InvoiceListParams(**serialized)
        restored_clauses = len(repo._build_filters(restored))

        assert original_clauses == restored_clauses

    def test_clear_all_returns_zero_clauses(self) -> None:
        """Default InvoiceListParams (no filters) → zero clauses.

        Validates: Requirement 37.3
        """
        repo = _build_repo()
        params = InvoiceListParams()
        clauses = repo._build_filters(params)
        assert len(clauses) == 0
