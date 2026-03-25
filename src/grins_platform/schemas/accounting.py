"""Pydantic schemas for accounting.

Validates: CRM Gap Closure Req 52.5, 57.2, 59.2, 61.2, 61.4
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from grins_platform.schemas.expense import ExpenseByCategoryResponse


class AccountingSummaryResponse(BaseModel):
    """YTD accounting summary.

    Validates: CRM Gap Closure Req 52.5
    """

    revenue: Decimal = Field(default=Decimal(0), description="Total revenue")
    expenses: Decimal = Field(default=Decimal(0), description="Total expenses")
    profit: Decimal = Field(default=Decimal(0), description="Net profit")
    profit_margin: float = Field(default=0.0, description="Profit margin percentage")
    pending_total: Decimal = Field(
        default=Decimal(0),
        description="Total pending invoices",
    )
    past_due_total: Decimal = Field(
        default=Decimal(0),
        description="Total past-due invoices",
    )


class JobFinancialsResponse(BaseModel):
    """Per-job financial breakdown.

    Validates: CRM Gap Closure Req 57.2
    """

    job_id: UUID = Field(..., description="Job UUID")
    quoted_amount: Decimal = Field(default=Decimal(0), description="Quoted amount")
    final_amount: Decimal = Field(default=Decimal(0), description="Final amount")
    total_paid: Decimal = Field(default=Decimal(0), description="Total paid")
    material_costs: Decimal = Field(
        default=Decimal(0),
        description="Material costs",
    )
    labor_costs: Decimal = Field(default=Decimal(0), description="Labor costs")
    total_costs: Decimal = Field(default=Decimal(0), description="Total costs")
    profit: Decimal = Field(default=Decimal(0), description="Profit")
    profit_margin: float = Field(default=0.0, description="Profit margin percentage")


class TaxSummaryResponse(BaseModel):
    """Tax preparation summary.

    Validates: CRM Gap Closure Req 59.2
    """

    expense_categories: list[ExpenseByCategoryResponse] = Field(
        default_factory=list,
        description="Expenses by tax category",
    )
    total_revenue: Decimal = Field(
        default=Decimal(0),
        description="Total revenue",
    )
    total_deductions: Decimal = Field(
        default=Decimal(0),
        description="Total deductions",
    )


class TaxEstimateResponse(BaseModel):
    """Estimated tax due.

    Validates: CRM Gap Closure Req 61.2
    """

    revenue: Decimal = Field(default=Decimal(0), description="Total revenue")
    deductions: Decimal = Field(default=Decimal(0), description="Total deductions")
    taxable_income: Decimal = Field(
        default=Decimal(0),
        description="Taxable income",
    )
    effective_tax_rate: float = Field(
        default=0.0,
        description="Effective tax rate",
    )
    estimated_tax_due: Decimal = Field(
        default=Decimal(0),
        description="Estimated tax due",
    )


class TaxProjectionRequest(BaseModel):
    """What-if tax projection input.

    Validates: CRM Gap Closure Req 61.4
    """

    additional_revenue: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Hypothetical additional revenue",
    )
    additional_expenses: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Hypothetical additional expenses",
    )


class TaxProjectionResponse(BaseModel):
    """What-if tax projection result.

    Validates: CRM Gap Closure Req 61.4
    """

    current_estimated_tax: Decimal = Field(
        default=Decimal(0),
        description="Current estimated tax",
    )
    projected_estimated_tax: Decimal = Field(
        default=Decimal(0),
        description="Projected estimated tax",
    )
    difference: Decimal = Field(
        default=Decimal(0),
        description="Difference from current",
    )
