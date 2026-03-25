"""Accounting service for financial aggregation, tax reporting, and integrations.

Provides: YTD summary, expense aggregation, per-job financials, tax summary,
tax estimation, what-if projections, receipt OCR (OpenAI Vision), and
Plaid transaction sync.

Validates: CRM Gap Closure Req 52, 53, 57, 59, 60, 61, 62
"""

from __future__ import annotations

import base64
import os
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import ExpenseCategory
from grins_platform.models.invoice import Invoice
from grins_platform.models.job import Job
from grins_platform.schemas.accounting import (
    AccountingSummaryResponse,
    JobFinancialsResponse,
    TaxEstimateResponse,
    TaxProjectionRequest,
    TaxProjectionResponse,
    TaxSummaryResponse,
)
from grins_platform.schemas.expense import (
    ExpenseByCategoryResponse,
    ReceiptExtractionResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.repositories.expense_repository import (
        ExpenseRepository,
    )

# Default effective tax rate for small business
# (~15.3% self-employment + income tax)
DEFAULT_EFFECTIVE_TAX_RATE = 0.30

# MCC code to ExpenseCategory mapping for Plaid auto-categorization
MCC_CATEGORY_MAP: dict[str, ExpenseCategory] = {
    # Building materials, hardware stores
    "5211": ExpenseCategory.MATERIALS,
    "5231": ExpenseCategory.MATERIALS,
    "5251": ExpenseCategory.MATERIALS,
    "5261": ExpenseCategory.MATERIALS,
    # Fuel / gas stations
    "5541": ExpenseCategory.FUEL,
    "5542": ExpenseCategory.FUEL,
    # Vehicle repair / service
    "5511": ExpenseCategory.VEHICLE,
    "5521": ExpenseCategory.VEHICLE,
    "7531": ExpenseCategory.VEHICLE,
    "7534": ExpenseCategory.VEHICLE,
    "7538": ExpenseCategory.VEHICLE,
    # Equipment rental / purchase
    "5072": ExpenseCategory.EQUIPMENT,
    "5085": ExpenseCategory.EQUIPMENT,
    "7394": ExpenseCategory.EQUIPMENT,
    # Insurance
    "6300": ExpenseCategory.INSURANCE,
    "6399": ExpenseCategory.INSURANCE,
    # Office supplies
    "5111": ExpenseCategory.OFFICE,
    "5943": ExpenseCategory.OFFICE,
    "5944": ExpenseCategory.OFFICE,
    # Marketing / advertising
    "7311": ExpenseCategory.MARKETING,
    "7312": ExpenseCategory.MARKETING,
    # Subcontractors / professional services
    "7392": ExpenseCategory.SUBCONTRACTOR,
    "8999": ExpenseCategory.SUBCONTRACTOR,
}


class PlaidConnectionError(Exception):
    """Raised when Plaid API communication fails."""

    def __init__(
        self,
        message: str = "Plaid API connection failed",
    ) -> None:
        self.message = message
        super().__init__(self.message)


class ReceiptExtractionError(Exception):
    """Raised when receipt OCR extraction fails."""

    def __init__(
        self,
        message: str = "Receipt extraction failed",
    ) -> None:
        self.message = message
        super().__init__(self.message)


class AccountingService(LoggerMixin):
    """Service for financial aggregation, tax reporting, and integrations.

    Validates: CRM Gap Closure Req 52, 53, 57, 59, 60, 61, 62
    """

    DOMAIN = "accounting"

    def __init__(
        self,
        expense_repository: ExpenseRepository,
        effective_tax_rate: float = DEFAULT_EFFECTIVE_TAX_RATE,
    ) -> None:
        """Initialize AccountingService.

        Args:
            expense_repository: Repository for expense DB operations.
            effective_tax_rate: Configurable effective tax rate.
        """
        super().__init__()
        self.expense_repo = expense_repository
        self.effective_tax_rate = effective_tax_rate

    # ------------------------------------------------------------------ #
    # get_summary -- Req 52
    # ------------------------------------------------------------------ #

    async def get_summary(
        self,
        db: AsyncSession,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> AccountingSummaryResponse:
        """Get YTD accounting summary.

        Revenue = sum of paid invoice total_amount.
        Expenses = sum of all tracked expenses.
        Profit = revenue - expenses.

        Args:
            db: Async database session.
            date_from: Start of date range (inclusive).
                Defaults to Jan 1 of current year.
            date_to: End of date range (inclusive).
                Defaults to today.

        Returns:
            AccountingSummaryResponse with financials.

        Validates: CRM Gap Closure Req 52.2, 52.5
        """
        self.log_started("get_summary")

        if date_from is None:
            date_from = date(date.today().year, 1, 1)
        if date_to is None:
            date_to = date.today()

        try:
            # Revenue: sum of paid invoices in date range
            revenue_stmt = select(
                func.coalesce(
                    func.sum(Invoice.total_amount),
                    0,
                ),
            ).where(
                Invoice.status == "paid",
                Invoice.invoice_date >= date_from,
                Invoice.invoice_date <= date_to,
            )
            revenue_result = await db.execute(revenue_stmt)
            revenue = Decimal(str(revenue_result.scalar() or 0))

            # Expenses: total spend in date range
            expenses = await self.expense_repo.get_total_spend(
                date_from=date_from,
                date_to=date_to,
            )

            # Profit
            profit = revenue - expenses

            # Profit margin
            profit_margin = float(profit / revenue * 100) if revenue > 0 else 0.0

            # Pending invoices (SENT or VIEWED)
            pending_stmt = select(
                func.coalesce(
                    func.sum(Invoice.total_amount),
                    0,
                ),
            ).where(
                Invoice.status.in_(["sent", "viewed"]),
            )
            pending_result = await db.execute(pending_stmt)
            pending_total = Decimal(
                str(pending_result.scalar() or 0),
            )

            # Past-due invoices (past due_date, not paid)
            today = date.today()
            past_due_stmt = select(
                func.coalesce(
                    func.sum(Invoice.total_amount),
                    0,
                ),
            ).where(
                Invoice.status.in_(["sent", "viewed", "overdue"]),
                Invoice.due_date < today,
            )
            past_due_result = await db.execute(past_due_stmt)
            past_due_total = Decimal(
                str(past_due_result.scalar() or 0),
            )

            summary = AccountingSummaryResponse(
                revenue=revenue,
                expenses=expenses,
                profit=profit,
                profit_margin=round(profit_margin, 2),
                pending_total=pending_total,
                past_due_total=past_due_total,
            )

        except Exception as e:
            self.log_failed("get_summary", error=e)
            raise

        self.log_completed(
            "get_summary",
            revenue=str(revenue),
            expenses=str(expenses),
            profit=str(profit),
        )
        return summary

    # ------------------------------------------------------------------ #
    # get_expenses_by_category -- Req 53
    # ------------------------------------------------------------------ #

    async def get_expenses_by_category(
        self,
        db: AsyncSession,  # noqa: ARG002
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ExpenseByCategoryResponse]:
        """Aggregate expenses by category for a date range.

        Args:
            db: Async database session (reserved for future use).
            date_from: Start of date range (inclusive).
            date_to: End of date range (inclusive).

        Returns:
            List of ExpenseByCategoryResponse sorted by total desc.

        Validates: CRM Gap Closure Req 53.3, 53.5
        """
        self.log_started("get_expenses_by_category")

        try:
            rows = await self.expense_repo.aggregate_by_category(
                date_from=date_from,
                date_to=date_to,
            )

            result = [
                ExpenseByCategoryResponse(
                    category=category,
                    total=total,
                    count=count,
                )
                for category, total, count in rows
            ]

        except Exception as e:
            self.log_failed("get_expenses_by_category", error=e)
            raise

        self.log_completed(
            "get_expenses_by_category",
            categories=len(result),
        )
        return result

    # ------------------------------------------------------------------ #
    # get_job_financials -- Req 57
    # ------------------------------------------------------------------ #

    async def get_job_financials(
        self,
        db: AsyncSession,
        job_id: UUID,
    ) -> JobFinancialsResponse:
        """Get per-job financial breakdown.

        Calculates quoted_amount, final_amount, total_paid (from invoices),
        material_costs, labor_costs, total_costs, profit, profit_margin.

        Args:
            db: Async database session.
            job_id: Job UUID.

        Returns:
            JobFinancialsResponse with all financial fields.

        Validates: CRM Gap Closure Req 57.1, 57.2
        """
        self.log_started("get_job_financials", job_id=str(job_id))

        try:
            # Get job for quoted/final amounts
            job_stmt = select(Job).where(Job.id == job_id)
            job_result = await db.execute(job_stmt)
            job = job_result.scalar_one_or_none()

            quoted_amount = Decimal(str(job.quoted_amount or 0)) if job else Decimal(0)
            final_amount = Decimal(str(job.final_amount or 0)) if job else Decimal(0)

            # Total paid from invoices linked to this job
            paid_stmt = select(
                func.coalesce(
                    func.sum(Invoice.total_amount),
                    0,
                ),
            ).where(
                Invoice.job_id == job_id,
                Invoice.status == "paid",
            )
            paid_result = await db.execute(paid_stmt)
            total_paid = Decimal(str(paid_result.scalar() or 0))

            # Get expenses by category for this job
            job_expenses = await self.expense_repo.get_by_job(job_id)

            material_costs = Decimal(0)
            labor_costs = Decimal(0)
            total_costs = Decimal(0)

            for expense in job_expenses:
                total_costs += expense.amount
                if expense.category == ExpenseCategory.MATERIALS.value:
                    material_costs += expense.amount
                elif expense.category == ExpenseCategory.LABOR.value:
                    labor_costs += expense.amount

            profit = total_paid - total_costs

            # Handle zero division for profit margin
            if total_paid > 0:
                profit_margin = float(
                    (profit / total_paid * 100).quantize(
                        Decimal("0.01"),
                        rounding=ROUND_HALF_UP,
                    ),
                )
            else:
                profit_margin = 0.0

            financials = JobFinancialsResponse(
                job_id=job_id,
                quoted_amount=quoted_amount,
                final_amount=final_amount,
                total_paid=total_paid,
                material_costs=material_costs,
                labor_costs=labor_costs,
                total_costs=total_costs,
                profit=profit,
                profit_margin=profit_margin,
            )

        except Exception as e:
            self.log_failed(
                "get_job_financials",
                error=e,
                job_id=str(job_id),
            )
            raise

        self.log_completed(
            "get_job_financials",
            job_id=str(job_id),
            profit=str(profit),
            profit_margin=profit_margin,
        )
        return financials

    # ------------------------------------------------------------------ #
    # get_tax_summary -- Req 59
    # ------------------------------------------------------------------ #

    async def get_tax_summary(
        self,
        db: AsyncSession,
        tax_year: int,
    ) -> TaxSummaryResponse:
        """Get tax preparation summary for a given year.

        Returns expense totals by tax category and total revenue.
        Data is structured for CSV export.

        Args:
            db: Async database session.
            tax_year: Tax year to summarize.

        Returns:
            TaxSummaryResponse with expense categories and revenue.

        Validates: CRM Gap Closure Req 59.1, 59.2, 59.3, 59.4
        """
        self.log_started("get_tax_summary", tax_year=tax_year)

        try:
            year_start = date(tax_year, 1, 1)
            year_end = date(tax_year, 12, 31)

            # Expense totals by category
            rows = await self.expense_repo.aggregate_by_category(
                date_from=year_start,
                date_to=year_end,
            )

            expense_categories = [
                ExpenseByCategoryResponse(
                    category=category,
                    total=total,
                    count=count,
                )
                for category, total, count in rows
            ]

            total_deductions = sum(
                (cat.total for cat in expense_categories),
                Decimal(0),
            )

            # Total revenue for the tax year (paid invoices)
            revenue_stmt = select(
                func.coalesce(
                    func.sum(Invoice.total_amount),
                    0,
                ),
            ).where(
                Invoice.status == "paid",
                Invoice.invoice_date >= year_start,
                Invoice.invoice_date <= year_end,
            )
            revenue_result = await db.execute(revenue_stmt)
            total_revenue = Decimal(
                str(revenue_result.scalar() or 0),
            )

            summary = TaxSummaryResponse(
                expense_categories=expense_categories,
                total_revenue=total_revenue,
                total_deductions=total_deductions,
            )

        except Exception as e:
            self.log_failed(
                "get_tax_summary",
                error=e,
                tax_year=tax_year,
            )
            raise

        self.log_completed(
            "get_tax_summary",
            tax_year=tax_year,
            total_revenue=str(total_revenue),
            total_deductions=str(total_deductions),
        )
        return summary

    # ------------------------------------------------------------------ #
    # get_tax_estimate -- Req 61
    # ------------------------------------------------------------------ #

    async def get_tax_estimate(
        self,
        db: AsyncSession,
    ) -> TaxEstimateResponse:
        """Get estimated tax due based on YTD revenue and deductions.

        Formula: estimated_tax_due = (revenue - deductions) x rate

        Args:
            db: Async database session.

        Returns:
            TaxEstimateResponse with revenue, deductions, taxable
            income, effective rate, and estimated tax due.

        Validates: CRM Gap Closure Req 61.1, 61.2
        """
        self.log_started("get_tax_estimate")

        try:
            year_start = date(date.today().year, 1, 1)
            today = date.today()

            # YTD revenue
            revenue_stmt = select(
                func.coalesce(
                    func.sum(Invoice.total_amount),
                    0,
                ),
            ).where(
                Invoice.status == "paid",
                Invoice.invoice_date >= year_start,
                Invoice.invoice_date <= today,
            )
            revenue_result = await db.execute(revenue_stmt)
            revenue = Decimal(str(revenue_result.scalar() or 0))

            # YTD deductions (all expenses)
            deductions = await self.expense_repo.get_total_spend(
                date_from=year_start,
                date_to=today,
            )

            taxable_income = max(revenue - deductions, Decimal(0))
            rate = Decimal(str(self.effective_tax_rate))
            estimated_tax_due = (taxable_income * rate).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            estimate = TaxEstimateResponse(
                revenue=revenue,
                deductions=deductions,
                taxable_income=taxable_income,
                effective_tax_rate=self.effective_tax_rate,
                estimated_tax_due=estimated_tax_due,
            )

        except Exception as e:
            self.log_failed("get_tax_estimate", error=e)
            raise

        self.log_completed(
            "get_tax_estimate",
            estimated_tax_due=str(estimated_tax_due),
        )
        return estimate

    # ------------------------------------------------------------------ #
    # project_tax -- Req 61
    # ------------------------------------------------------------------ #

    async def project_tax(
        self,
        db: AsyncSession,
        projection: TaxProjectionRequest,
    ) -> TaxProjectionResponse:
        """What-if tax projection with hypothetical revenue/expenses.

        Adds hypothetical amounts to current YTD figures and recalculates.

        Args:
            db: Async database session.
            projection: Hypothetical additional revenue and expenses.

        Returns:
            TaxProjectionResponse with current vs projected tax.

        Validates: CRM Gap Closure Req 61.3, 61.4
        """
        self.log_started(
            "project_tax",
            additional_revenue=str(projection.additional_revenue),
            additional_expenses=str(projection.additional_expenses),
        )

        try:
            # Get current estimate
            current = await self.get_tax_estimate(db)

            # Projected figures
            projected_revenue = current.revenue + projection.additional_revenue
            projected_deductions = current.deductions + projection.additional_expenses
            projected_taxable = max(
                projected_revenue - projected_deductions,
                Decimal(0),
            )
            rate = Decimal(str(self.effective_tax_rate))
            projected_tax = (projected_taxable * rate).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            difference = projected_tax - current.estimated_tax_due

            result = TaxProjectionResponse(
                current_estimated_tax=current.estimated_tax_due,
                projected_estimated_tax=projected_tax,
                difference=difference,
            )

        except Exception as e:
            self.log_failed("project_tax", error=e)
            raise

        self.log_completed(
            "project_tax",
            current_tax=str(current.estimated_tax_due),
            projected_tax=str(projected_tax),
            difference=str(difference),
        )
        return result

    # ------------------------------------------------------------------ #
    # extract_receipt -- Req 60
    # ------------------------------------------------------------------ #

    async def extract_receipt(
        self,
        image_data: bytes,
        content_type: str = "image/jpeg",
    ) -> ReceiptExtractionResponse:
        """Extract amount, vendor, category from receipt via OpenAI Vision.

        Args:
            image_data: Raw image bytes.
            content_type: MIME type of the image.

        Returns:
            ReceiptExtractionResponse with extracted fields.

        Raises:
            ReceiptExtractionError: If the OpenAI API call fails.

        Validates: CRM Gap Closure Req 60.1, 60.2
        """
        self.log_started("extract_receipt", content_type=content_type)

        try:
            from openai import AsyncOpenAI  # noqa: PLC0415

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.log_rejected(
                    "extract_receipt",
                    reason="OPENAI_API_KEY not configured",
                )
                return ReceiptExtractionResponse(
                    amount=None,
                    vendor=None,
                    category=None,
                    confidence=0.0,
                )

            client = AsyncOpenAI(api_key=api_key)

            # Encode image to base64 for the Vision API
            b64_image = base64.b64encode(image_data).decode("utf-8")
            data_url = f"data:{content_type};base64,{b64_image}"

            prompt_text = (
                "Extract the following from this receipt image. "
                "Return ONLY valid JSON with these fields:\n"
                '- "amount": numeric total amount (float)\n'
                '- "vendor": store/vendor name (string)\n'
                '- "category": one of: materials, labor, fuel, '
                "equipment, vehicle, insurance, marketing, "
                "office, subcontractor, other (string)\n"
                '- "confidence": your confidence 0.0-1.0 (float)\n'
                "If you cannot extract a field, set it to null."
            )

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    },
                ],
                max_tokens=300,
            )

            # Parse the response
            raw = response.choices[0].message.content or "{}"
            extracted = self._parse_receipt_response(raw)

        except ImportError:
            self.log_rejected(
                "extract_receipt",
                reason="openai package not installed",
            )
            return ReceiptExtractionResponse(confidence=0.0)

        except Exception as e:
            self.log_failed("extract_receipt", error=e)
            raise ReceiptExtractionError(str(e)) from e

        self.log_completed(
            "extract_receipt",
            amount=str(extracted.amount),
            vendor=extracted.vendor,
            category=extracted.category,
            confidence=extracted.confidence,
        )
        return extracted

    @staticmethod
    def _parse_receipt_response(
        raw_text: str,
    ) -> ReceiptExtractionResponse:
        """Parse OpenAI Vision response into ReceiptExtractionResponse.

        Args:
            raw_text: Raw text response from the API.

        Returns:
            Parsed ReceiptExtractionResponse.
        """
        import json  # noqa: PLC0415

        # Strip markdown code fences if present
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError:
            return ReceiptExtractionResponse(confidence=0.0)

        amount_raw = data.get("amount")
        amount = Decimal(str(amount_raw)) if amount_raw is not None else None

        vendor = data.get("vendor")
        category = data.get("category")
        confidence = float(data.get("confidence", 0.0))

        return ReceiptExtractionResponse(
            amount=amount,
            vendor=vendor,
            category=category,
            confidence=min(max(confidence, 0.0), 1.0),
        )

    # ------------------------------------------------------------------ #
    # sync_transactions -- Req 62
    # ------------------------------------------------------------------ #

    async def sync_transactions(
        self,
        db: AsyncSession,
        access_token: str | None = None,
    ) -> int:
        """Sync transactions from Plaid and create expense records.

        Fetches recent transactions from connected bank accounts,
        auto-categorizes by MCC code, and creates expense records.

        Args:
            db: Async database session.
            access_token: Plaid access token. Falls back to env var
                PLAID_ACCESS_TOKEN if not provided.

        Returns:
            Number of new expense records created.

        Raises:
            PlaidConnectionError: If Plaid API communication fails.

        Validates: CRM Gap Closure Req 62.2, 62.3, 62.4, 62.5
        """
        self.log_started("sync_transactions")

        token = access_token or os.getenv("PLAID_ACCESS_TOKEN")
        if not token:
            self.log_rejected(
                "sync_transactions",
                reason="No Plaid access token configured",
            )
            return 0

        try:
            import plaid  # noqa: PLC0415
            from plaid.api import plaid_api  # noqa: PLC0415
            from plaid.model.transactions_get_request import (  # noqa: PLC0415
                TransactionsGetRequest,
            )
            from plaid.model.transactions_get_request_options import (  # noqa: PLC0415
                TransactionsGetRequestOptions,
            )

            client_id = os.getenv("PLAID_CLIENT_ID", "")
            secret = os.getenv("PLAID_SECRET", "")
            plaid_env = os.getenv("PLAID_ENV", "sandbox")

            host = (
                plaid.Environment.Sandbox
                if plaid_env == "sandbox"
                else plaid.Environment.Production
            )
            configuration = plaid.Configuration(
                host=host,
                api_key={
                    "clientId": client_id,
                    "secret": secret,
                },
            )

            api_client = plaid.ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)

            # Fetch last 30 days of transactions
            end_date = date.today()
            start_date = date(end_date.year, end_date.month, 1)

            request = TransactionsGetRequest(
                access_token=token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(count=500),
            )

            response = client.transactions_get(request)
            transactions = response.transactions

            created_count = 0
            for txn in transactions:
                # Skip positive amounts (credits/refunds)
                if txn.amount <= 0:
                    continue

                # Auto-categorize by MCC code
                mcc = str(
                    getattr(txn, "merchant_category_code", "") or "",
                )
                category = self._categorize_by_mcc(mcc)

                # Create expense record
                await self.expense_repo.create(
                    category=category.value,
                    description=txn.name or "Plaid transaction",
                    amount=Decimal(str(abs(txn.amount))),
                    expense_date=txn.date,
                    vendor=(getattr(txn, "merchant_name", None) or txn.name),
                    notes=f"Auto-imported from Plaid (MCC: {mcc})",
                )
                created_count += 1

            await db.commit()

        except ImportError:
            self.log_rejected(
                "sync_transactions",
                reason="plaid-python package not installed",
            )
            return 0

        except Exception as e:
            self.log_failed("sync_transactions", error=e)
            raise PlaidConnectionError(str(e)) from e

        self.log_completed(
            "sync_transactions",
            transactions_fetched=len(transactions),
            expenses_created=created_count,
        )
        return created_count

    @staticmethod
    def _categorize_by_mcc(mcc_code: str) -> ExpenseCategory:
        """Map a Plaid MCC code to an ExpenseCategory.

        Args:
            mcc_code: Merchant Category Code string.

        Returns:
            Matching ExpenseCategory, defaults to OTHER.

        Validates: CRM Gap Closure Req 62.4
        """
        return MCC_CATEGORY_MAP.get(mcc_code, ExpenseCategory.OTHER)
