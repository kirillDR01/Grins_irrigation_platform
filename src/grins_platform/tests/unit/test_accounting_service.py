"""Unit tests for AccountingService.

Tests accounting summary, expense aggregation, per-job financials,
tax summary, tax estimation, what-if projections, receipt OCR parsing,
Plaid MCC auto-categorization, and edge cases (zero division, missing keys).

Properties:
  P53: Accounting summary calculation correctness
  P54: Expense category aggregation and per-job cost linkage
  P56: Per-job financial calculations
  P57: Customer acquisition cost calculation
  P58: Tax summary aggregation by category
  P59: Tax estimation calculation
  P60: Plaid transaction auto-categorization

Validates: Requirements 52.2, 52.5, 52.7, 53.3, 53.5, 53.8, 53.9,
           57.1, 57.2, 57.4, 58.1, 58.2, 58.5, 59.1, 59.2, 59.5,
           60.6, 61.1, 61.2, 61.3, 61.4, 61.5, 62.4, 62.7
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import ExpenseCategory
from grins_platform.schemas.accounting import TaxProjectionRequest
from grins_platform.services.accounting_service import (
    MCC_CATEGORY_MAP,
    AccountingService,
)

# =============================================================================
# Helpers
# =============================================================================


def _build_service(
    *,
    expense_repo: AsyncMock | None = None,
    effective_tax_rate: float = 0.30,
) -> AccountingService:
    """Build an AccountingService with mocked dependencies."""
    return AccountingService(
        expense_repository=expense_repo or AsyncMock(),
        effective_tax_rate=effective_tax_rate,
    )


def _mock_db_execute_results(
    *scalar_values: Any,
) -> AsyncMock:
    """Create a mock db session that returns scalar values in sequence.

    Each call to db.execute() returns a result whose .scalar() gives
    the next value from *scalar_values*.
    """
    db = AsyncMock()
    results = []
    for val in scalar_values:
        result_mock = MagicMock()
        result_mock.scalar.return_value = val
        result_mock.scalar_one_or_none.return_value = val
        results.append(result_mock)
    db.execute.side_effect = results
    return db


def _make_expense_mock(
    *,
    amount: Decimal,
    category: str = ExpenseCategory.MATERIALS.value,
) -> MagicMock:
    """Create a mock Expense object."""
    e = MagicMock()
    e.amount = amount
    e.category = category
    return e


# =============================================================================
# Property 53: Accounting summary calculation correctness
# Validates: Requirements 52.2, 52.5
# =============================================================================


@pytest.mark.unit
class TestProperty53AccountingSummaryCalculation:
    """Property 53: Accounting summary calculation correctness.

    For any revenue (paid invoices) and expenses, the summary SHALL
    return correct revenue, expenses, profit (revenue - expenses),
    profit_margin (profit/revenue * 100), pending_total, and
    past_due_total.

    **Validates: Requirements 52.2, 52.5**
    """

    @pytest.mark.asyncio
    async def test_get_summary_with_revenue_and_expenses_returns_correct_profit(
        self,
    ) -> None:
        """Revenue=10000, expenses=3000 → profit=7000, margin=70%."""
        repo = AsyncMock()
        repo.get_total_spend.return_value = Decimal("3000.00")
        svc = _build_service(expense_repo=repo)

        # db.execute returns: revenue, pending, past_due
        db = AsyncMock()
        revenue_result = MagicMock()
        revenue_result.scalar.return_value = Decimal("10000.00")
        pending_result = MagicMock()
        pending_result.scalar.return_value = Decimal("2000.00")
        past_due_result = MagicMock()
        past_due_result.scalar.return_value = Decimal("500.00")
        db.execute.side_effect = [revenue_result, pending_result, past_due_result]

        result = await svc.get_summary(db)

        assert result.revenue == Decimal("10000.00")
        assert result.expenses == Decimal("3000.00")
        assert result.profit == Decimal("7000.00")
        assert result.profit_margin == 70.0
        assert result.pending_total == Decimal("2000.00")
        assert result.past_due_total == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_get_summary_with_zero_revenue_returns_zero_profit_margin(
        self,
    ) -> None:
        """When revenue is 0, profit margin should be 0.0 (no division error)."""
        repo = AsyncMock()
        repo.get_total_spend.return_value = Decimal("500.00")
        svc = _build_service(expense_repo=repo)

        db = AsyncMock()
        revenue_result = MagicMock()
        revenue_result.scalar.return_value = Decimal(0)
        pending_result = MagicMock()
        pending_result.scalar.return_value = Decimal(0)
        past_due_result = MagicMock()
        past_due_result.scalar.return_value = Decimal(0)
        db.execute.side_effect = [revenue_result, pending_result, past_due_result]

        result = await svc.get_summary(db)

        assert result.revenue == Decimal(0)
        assert result.expenses == Decimal("500.00")
        assert result.profit == Decimal("-500.00")
        assert result.profit_margin == 0.0

    @pytest.mark.asyncio
    async def test_get_summary_with_no_data_returns_all_zeros(self) -> None:
        """Empty database returns all-zero summary."""
        repo = AsyncMock()
        repo.get_total_spend.return_value = Decimal(0)
        svc = _build_service(expense_repo=repo)

        db = AsyncMock()
        zero_result = MagicMock()
        zero_result.scalar.return_value = Decimal(0)
        db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=Decimal(0))),
            MagicMock(scalar=MagicMock(return_value=Decimal(0))),
            MagicMock(scalar=MagicMock(return_value=Decimal(0))),
        ]

        result = await svc.get_summary(db)

        assert result.revenue == Decimal(0)
        assert result.expenses == Decimal(0)
        assert result.profit == Decimal(0)
        assert result.profit_margin == 0.0
        assert result.pending_total == Decimal(0)
        assert result.past_due_total == Decimal(0)


# =============================================================================
# Property 54: Expense category aggregation and per-job cost linkage
# Validates: Requirements 53.3, 53.5
# =============================================================================


@pytest.mark.unit
class TestProperty54ExpenseCategoryAggregation:
    """Property 54: Expense category aggregation and per-job cost linkage.

    get_expenses_by_category SHALL return aggregated totals per category
    sorted by total descending.

    **Validates: Requirements 53.3, 53.5**
    """

    @pytest.mark.asyncio
    async def test_get_expenses_by_category_returns_aggregated_results(
        self,
    ) -> None:
        """Aggregation returns correct category, total, count tuples."""
        repo = AsyncMock()
        repo.aggregate_by_category.return_value = [
            ("materials", Decimal("5000.00"), 10),
            ("fuel", Decimal("1200.00"), 25),
            ("labor", Decimal("800.00"), 5),
        ]
        svc = _build_service(expense_repo=repo)
        db = AsyncMock()

        result = await svc.get_expenses_by_category(db)

        assert len(result) == 3
        assert result[0].category == "materials"
        assert result[0].total == Decimal("5000.00")
        assert result[0].count == 10
        assert result[1].category == "fuel"
        assert result[1].total == Decimal("1200.00")
        assert result[2].category == "labor"
        assert result[2].total == Decimal("800.00")

    @pytest.mark.asyncio
    async def test_get_expenses_by_category_with_no_expenses_returns_empty(
        self,
    ) -> None:
        """No expenses returns empty list."""
        repo = AsyncMock()
        repo.aggregate_by_category.return_value = []
        svc = _build_service(expense_repo=repo)
        db = AsyncMock()

        result = await svc.get_expenses_by_category(db)

        assert result == []


# =============================================================================
# Property 56: Per-job financial calculations
# Validates: Requirements 57.1, 57.2
# =============================================================================


@pytest.mark.unit
class TestProperty56PerJobFinancials:
    """Property 56: Per-job financial calculations.

    get_job_financials SHALL calculate profit = total_paid - total_costs,
    profit_margin = (profit / total_paid) * 100, with zero division
    handling when total_paid is 0.

    **Validates: Requirements 57.1, 57.2**
    """

    @pytest.mark.asyncio
    async def test_get_job_financials_with_paid_invoices_and_expenses(
        self,
    ) -> None:
        """Calculates profit and margin correctly from invoices and expenses."""
        job_id = uuid4()
        repo = AsyncMock()
        repo.get_by_job.return_value = [
            _make_expense_mock(
                amount=Decimal("500.00"),
                category=ExpenseCategory.MATERIALS.value,
            ),
            _make_expense_mock(
                amount=Decimal("300.00"),
                category=ExpenseCategory.LABOR.value,
            ),
            _make_expense_mock(
                amount=Decimal("100.00"),
                category=ExpenseCategory.FUEL.value,
            ),
        ]
        svc = _build_service(expense_repo=repo)

        # Mock job with quoted/final amounts
        job_mock = MagicMock()
        job_mock.quoted_amount = Decimal("2000.00")
        job_mock.final_amount = Decimal("2200.00")

        # db.execute: first call returns job, second returns paid total
        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job_mock
        paid_result = MagicMock()
        paid_result.scalar.return_value = Decimal("2200.00")

        db = AsyncMock()
        db.execute.side_effect = [job_result, paid_result]

        result = await svc.get_job_financials(db, job_id)

        assert result.job_id == job_id
        assert result.quoted_amount == Decimal("2000.00")
        assert result.final_amount == Decimal("2200.00")
        assert result.total_paid == Decimal("2200.00")
        assert result.material_costs == Decimal("500.00")
        assert result.labor_costs == Decimal("300.00")
        assert result.total_costs == Decimal("900.00")
        assert result.profit == Decimal("1300.00")
        # profit_margin = (1300 / 2200) * 100 = 59.09
        expected_margin = float(
            (Decimal("1300.00") / Decimal("2200.00") * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP,
            ),
        )
        assert result.profit_margin == expected_margin

    @pytest.mark.asyncio
    async def test_get_job_financials_with_zero_total_paid_returns_zero_margin(
        self,
    ) -> None:
        """Zero total_paid → profit_margin = 0.0 (no ZeroDivisionError)."""
        job_id = uuid4()
        repo = AsyncMock()
        repo.get_by_job.return_value = [
            _make_expense_mock(
                amount=Decimal("200.00"),
                category=ExpenseCategory.MATERIALS.value,
            ),
        ]
        svc = _build_service(expense_repo=repo)

        job_mock = MagicMock()
        job_mock.quoted_amount = Decimal("1000.00")
        job_mock.final_amount = Decimal("1000.00")

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job_mock
        paid_result = MagicMock()
        paid_result.scalar.return_value = Decimal(0)

        db = AsyncMock()
        db.execute.side_effect = [job_result, paid_result]

        result = await svc.get_job_financials(db, job_id)

        assert result.total_paid == Decimal(0)
        assert result.profit == Decimal("-200.00")
        assert result.profit_margin == 0.0

    @pytest.mark.asyncio
    async def test_get_job_financials_with_no_job_returns_zero_amounts(
        self,
    ) -> None:
        """Non-existent job → all amounts zero."""
        job_id = uuid4()
        repo = AsyncMock()
        repo.get_by_job.return_value = []
        svc = _build_service(expense_repo=repo)

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = None
        paid_result = MagicMock()
        paid_result.scalar.return_value = Decimal(0)

        db = AsyncMock()
        db.execute.side_effect = [job_result, paid_result]

        result = await svc.get_job_financials(db, job_id)

        assert result.quoted_amount == Decimal(0)
        assert result.final_amount == Decimal(0)
        assert result.total_paid == Decimal(0)
        assert result.total_costs == Decimal(0)
        assert result.profit == Decimal(0)
        assert result.profit_margin == 0.0


# =============================================================================
# Property 57: Customer acquisition cost calculation
# Validates: Requirements 58.1, 58.2
# =============================================================================


@pytest.mark.unit
class TestProperty57CustomerAcquisitionCost:
    """Property 57: Customer acquisition cost calculation.

    CAC = marketing_spend / converted_customers. When converted_customers
    is 0, CAC should be handled gracefully (no division error).

    Note: CAC is computed in MarketingService, but the accounting service
    provides the expense data that feeds into it. These tests verify the
    expense aggregation supports marketing-category filtering which is
    the accounting side of CAC.

    **Validates: Requirements 58.1, 58.2**
    """

    @pytest.mark.asyncio
    async def test_expenses_by_category_includes_marketing_spend(self) -> None:
        """Marketing expenses are correctly aggregated for CAC input."""
        repo = AsyncMock()
        repo.aggregate_by_category.return_value = [
            ("marketing", Decimal("3000.00"), 15),
            ("materials", Decimal("2000.00"), 8),
        ]
        svc = _build_service(expense_repo=repo)
        db = AsyncMock()

        result = await svc.get_expenses_by_category(db)

        marketing = [r for r in result if r.category == "marketing"]
        assert len(marketing) == 1
        assert marketing[0].total == Decimal("3000.00")
        assert marketing[0].count == 15

    @pytest.mark.asyncio
    async def test_expenses_by_category_with_zero_marketing_spend(self) -> None:
        """No marketing expenses → marketing category absent from results."""
        repo = AsyncMock()
        repo.aggregate_by_category.return_value = [
            ("materials", Decimal("1000.00"), 5),
        ]
        svc = _build_service(expense_repo=repo)
        db = AsyncMock()

        result = await svc.get_expenses_by_category(db)

        marketing = [r for r in result if r.category == "marketing"]
        assert len(marketing) == 0


# =============================================================================
# Property 58: Tax summary aggregation by category
# Validates: Requirements 59.1, 59.2
# =============================================================================


@pytest.mark.unit
class TestProperty58TaxSummaryAggregation:
    """Property 58: Tax summary aggregation by category.

    get_tax_summary SHALL return expense categories with totals and
    total_revenue for the given tax year.

    **Validates: Requirements 59.1, 59.2**
    """

    @pytest.mark.asyncio
    async def test_get_tax_summary_returns_categories_and_revenue(self) -> None:
        """Tax summary includes expense categories and revenue for year."""
        repo = AsyncMock()
        repo.aggregate_by_category.return_value = [
            ("materials", Decimal("8000.00"), 40),
            ("fuel", Decimal("3000.00"), 60),
            ("labor", Decimal("5000.00"), 20),
        ]
        svc = _build_service(expense_repo=repo)

        revenue_result = MagicMock()
        revenue_result.scalar.return_value = Decimal("50000.00")
        db = AsyncMock()
        db.execute.return_value = revenue_result

        result = await svc.get_tax_summary(db, tax_year=2024)

        assert len(result.expense_categories) == 3
        assert result.total_revenue == Decimal("50000.00")
        assert result.total_deductions == Decimal("16000.00")
        assert result.expense_categories[0].category == "materials"
        assert result.expense_categories[0].total == Decimal("8000.00")

    @pytest.mark.asyncio
    async def test_get_tax_summary_with_no_expenses_returns_zero_deductions(
        self,
    ) -> None:
        """No expenses → total_deductions = 0."""
        repo = AsyncMock()
        repo.aggregate_by_category.return_value = []
        svc = _build_service(expense_repo=repo)

        revenue_result = MagicMock()
        revenue_result.scalar.return_value = Decimal("20000.00")
        db = AsyncMock()
        db.execute.return_value = revenue_result

        result = await svc.get_tax_summary(db, tax_year=2024)

        assert result.expense_categories == []
        assert result.total_deductions == Decimal(0)
        assert result.total_revenue == Decimal("20000.00")


# =============================================================================
# Property 59: Tax estimation calculation
# Validates: Requirements 61.1, 61.2, 61.3, 61.4
# =============================================================================


@pytest.mark.unit
class TestProperty59TaxEstimation:
    """Property 59: Tax estimation calculation.

    get_tax_estimate: estimated_tax = (revenue - deductions) x rate.
    When deductions exceed revenue, taxable_income = 0.
    project_tax: adds hypothetical amounts and recalculates.

    **Validates: Requirements 61.1, 61.2, 61.3, 61.4**
    """

    @pytest.mark.asyncio
    async def test_get_tax_estimate_calculates_correctly(self) -> None:
        """(revenue - deductions) x rate = estimated_tax_due."""
        repo = AsyncMock()
        repo.get_total_spend.return_value = Decimal("15000.00")
        svc = _build_service(expense_repo=repo, effective_tax_rate=0.30)

        revenue_result = MagicMock()
        revenue_result.scalar.return_value = Decimal("50000.00")
        db = AsyncMock()
        db.execute.return_value = revenue_result

        result = await svc.get_tax_estimate(db)

        assert result.revenue == Decimal("50000.00")
        assert result.deductions == Decimal("15000.00")
        assert result.taxable_income == Decimal("35000.00")
        assert result.effective_tax_rate == 0.30
        expected_tax = (Decimal("35000.00") * Decimal("0.30")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
        assert result.estimated_tax_due == expected_tax

    @pytest.mark.asyncio
    async def test_get_tax_estimate_with_deductions_exceeding_revenue(
        self,
    ) -> None:
        """Deductions > revenue → taxable_income = 0, tax = 0."""
        repo = AsyncMock()
        repo.get_total_spend.return_value = Decimal("60000.00")
        svc = _build_service(expense_repo=repo, effective_tax_rate=0.30)

        revenue_result = MagicMock()
        revenue_result.scalar.return_value = Decimal("40000.00")
        db = AsyncMock()
        db.execute.return_value = revenue_result

        result = await svc.get_tax_estimate(db)

        assert result.taxable_income == Decimal(0)
        assert result.estimated_tax_due == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_project_tax_adds_hypothetical_and_recalculates(self) -> None:
        """project_tax adds additional_revenue/expenses to current estimate."""
        repo = AsyncMock()
        repo.get_total_spend.return_value = Decimal("10000.00")
        svc = _build_service(expense_repo=repo, effective_tax_rate=0.25)

        revenue_result = MagicMock()
        revenue_result.scalar.return_value = Decimal("40000.00")
        db = AsyncMock()
        # get_tax_estimate is called internally by project_tax
        db.execute.return_value = revenue_result

        projection = TaxProjectionRequest(
            additional_revenue=Decimal("10000.00"),
            additional_expenses=Decimal("5000.00"),
        )

        result = await svc.project_tax(db, projection)

        # Current: (40000 - 10000) * 0.25 = 7500
        current_tax = (Decimal("30000.00") * Decimal("0.25")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
        # Projected: (50000 - 15000) * 0.25 = 8750
        projected_tax = (Decimal("35000.00") * Decimal("0.25")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

        assert result.current_estimated_tax == current_tax
        assert result.projected_estimated_tax == projected_tax
        assert result.difference == projected_tax - current_tax

    @pytest.mark.asyncio
    async def test_project_tax_difference_is_correct(self) -> None:
        """difference = projected_tax - current_tax."""
        repo = AsyncMock()
        repo.get_total_spend.return_value = Decimal("5000.00")
        svc = _build_service(expense_repo=repo, effective_tax_rate=0.30)

        revenue_result = MagicMock()
        revenue_result.scalar.return_value = Decimal("20000.00")
        db = AsyncMock()
        db.execute.return_value = revenue_result

        projection = TaxProjectionRequest(
            additional_revenue=Decimal(0),
            additional_expenses=Decimal("3000.00"),
        )

        result = await svc.project_tax(db, projection)

        # Current: (20000 - 5000) * 0.30 = 4500
        # Projected: (20000 - 8000) * 0.30 = 3600
        # Difference: 3600 - 4500 = -900
        assert result.difference == Decimal("-900.00")


# =============================================================================
# Property 60: Plaid transaction auto-categorization
# Validates: Requirements 62.4
# =============================================================================


@pytest.mark.unit
class TestProperty60PlaidAutoCategorization:
    """Property 60: Plaid transaction auto-categorization.

    _categorize_by_mcc SHALL map known MCC codes to the correct
    ExpenseCategory and return OTHER for unknown codes.

    **Validates: Requirements 62.4**
    """

    def test_categorize_by_mcc_maps_known_codes_correctly(self) -> None:
        """All known MCC codes in MCC_CATEGORY_MAP resolve correctly."""
        for mcc_code, expected_category in MCC_CATEGORY_MAP.items():
            result = AccountingService._categorize_by_mcc(mcc_code)
            assert result == expected_category, (
                f"MCC {mcc_code}: expected {expected_category}, got {result}"
            )

    def test_categorize_by_mcc_materials_codes(self) -> None:
        """Building materials MCC codes → MATERIALS."""
        for code in ["5211", "5231", "5251", "5261"]:
            result = AccountingService._categorize_by_mcc(code)
            assert result == ExpenseCategory.MATERIALS

    def test_categorize_by_mcc_fuel_codes(self) -> None:
        """Gas station MCC codes → FUEL."""
        for code in ["5541", "5542"]:
            assert AccountingService._categorize_by_mcc(code) == ExpenseCategory.FUEL

    def test_categorize_by_mcc_vehicle_codes(self) -> None:
        """Vehicle repair MCC codes → VEHICLE."""
        for code in ["5511", "5521", "7531", "7534", "7538"]:
            assert AccountingService._categorize_by_mcc(code) == ExpenseCategory.VEHICLE

    def test_categorize_by_mcc_returns_other_for_unknown_codes(self) -> None:
        """Unknown MCC codes → OTHER."""
        assert AccountingService._categorize_by_mcc("9999") == ExpenseCategory.OTHER
        assert AccountingService._categorize_by_mcc("") == ExpenseCategory.OTHER
        assert AccountingService._categorize_by_mcc("0000") == ExpenseCategory.OTHER


# =============================================================================
# Receipt OCR response parsing
# Validates: Requirements 60.6
# =============================================================================


@pytest.mark.unit
class TestReceiptOCRParsing:
    """Tests for _parse_receipt_response static method.

    Validates correct JSON parsing, markdown code fence handling,
    and graceful invalid JSON handling.
    """

    def test_parse_receipt_response_with_valid_json(self) -> None:
        """Valid JSON -> correctly parsed ReceiptExtractionResponse."""
        raw = (
            '{"amount": 42.50, "vendor": "Home Depot",'
            ' "category": "materials", "confidence": 0.95}'
        )
        result = AccountingService._parse_receipt_response(raw)

        assert result.amount == Decimal("42.50")
        assert result.vendor == "Home Depot"
        assert result.category == "materials"
        assert result.confidence == 0.95

    def test_parse_receipt_response_with_markdown_code_fences(self) -> None:
        """Markdown-wrapped JSON -> strips fences and parses."""
        raw = (
            '```json\n{"amount": 15.99, "vendor": "Shell",'
            ' "category": "fuel", "confidence": 0.88}\n```'
        )
        result = AccountingService._parse_receipt_response(raw)

        assert result.amount == Decimal("15.99")
        assert result.vendor == "Shell"
        assert result.category == "fuel"
        assert result.confidence == 0.88

    def test_parse_receipt_response_with_invalid_json(self) -> None:
        """Invalid JSON → confidence=0.0, all fields None."""
        result = AccountingService._parse_receipt_response("not valid json at all")

        assert result.amount is None
        assert result.vendor is None
        assert result.category is None
        assert result.confidence == 0.0

    def test_parse_receipt_response_with_null_fields(self) -> None:
        """JSON with null fields → None values preserved."""
        raw = '{"amount": null, "vendor": null, "category": null, "confidence": 0.1}'
        result = AccountingService._parse_receipt_response(raw)

        assert result.amount is None
        assert result.vendor is None
        assert result.category is None
        assert result.confidence == 0.1

    def test_parse_receipt_response_clamps_confidence(self) -> None:
        """Confidence > 1.0 → clamped to 1.0; < 0.0 → clamped to 0.0."""
        high = '{"amount": 10, "confidence": 5.0}'
        result_high = AccountingService._parse_receipt_response(high)
        assert result_high.confidence == 1.0

        low = '{"amount": 10, "confidence": -0.5}'
        result_low = AccountingService._parse_receipt_response(low)
        assert result_low.confidence == 0.0


# =============================================================================
# extract_receipt and sync_transactions edge cases
# Validates: Requirements 60.6, 62.7
# =============================================================================


@pytest.mark.unit
class TestExtractReceiptAndSyncEdgeCases:
    """Edge case tests for extract_receipt and sync_transactions."""

    @pytest.mark.asyncio
    async def test_extract_receipt_with_no_api_key_returns_zero_confidence(
        self,
    ) -> None:
        """No OPENAI_API_KEY → returns response with confidence=0.0."""
        svc = _build_service()

        with patch.dict("os.environ", {}, clear=True):
            result = await svc.extract_receipt(
                image_data=b"fake-image-bytes",
                content_type="image/jpeg",
            )

        assert result.confidence == 0.0
        assert result.amount is None

    @pytest.mark.asyncio
    async def test_sync_transactions_with_no_access_token_returns_zero(
        self,
    ) -> None:
        """No Plaid access token → returns 0 (no transactions synced)."""
        svc = _build_service()
        db = AsyncMock()

        with patch.dict("os.environ", {}, clear=True):
            count = await svc.sync_transactions(db, access_token=None)

        assert count == 0
