"""Pydantic schemas for expense management.

Validates: CRM Gap Closure Req 53.3, 60.1, 75.1, 75.2
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.models.enums import ExpenseCategory


class ExpenseCreate(BaseModel):
    """Schema for creating an expense.

    Validates: CRM Gap Closure Req 53.3, 75.1, 75.2
    """

    category: ExpenseCategory = Field(..., description="Expense category")
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Expense description",
    )
    amount: Decimal = Field(..., gt=0, description="Expense amount")
    expense_date: date = Field(..., description="Date of expense")
    job_id: UUID | None = Field(default=None, description="Associated job UUID")
    staff_id: UUID | None = Field(default=None, description="Staff member UUID")
    vendor: str | None = Field(
        default=None,
        max_length=200,
        description="Vendor name",
    )
    receipt_file_key: str | None = Field(
        default=None,
        max_length=500,
        description="S3 key for receipt",
    )
    lead_source: str | None = Field(
        default=None,
        max_length=50,
        description="Marketing attribution source",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Additional notes",
    )


class ExpenseResponse(BaseModel):
    """Schema for expense response.

    Validates: CRM Gap Closure Req 53.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Expense UUID")
    category: ExpenseCategory = Field(..., description="Expense category")
    description: str = Field(..., description="Expense description")
    amount: Decimal = Field(..., description="Expense amount")
    expense_date: date = Field(..., description="Date of expense")
    job_id: UUID | None = Field(default=None, description="Associated job UUID")
    staff_id: UUID | None = Field(default=None, description="Staff member UUID")
    vendor: str | None = Field(default=None, description="Vendor name")
    receipt_file_key: str | None = Field(
        default=None,
        description="S3 key for receipt",
    )
    receipt_amount_extracted: Decimal | None = Field(
        default=None,
        description="OCR-extracted amount",
    )
    lead_source: str | None = Field(
        default=None,
        description="Marketing attribution source",
    )
    notes: str | None = Field(default=None, description="Additional notes")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")


class ExpenseByCategoryResponse(BaseModel):
    """Aggregated expenses by category.

    Validates: CRM Gap Closure Req 53.3
    """

    category: str = Field(..., description="Expense category")
    total: Decimal = Field(..., description="Total amount for category")
    count: int = Field(..., ge=0, description="Number of expenses")


class ReceiptExtractionResponse(BaseModel):
    """Response from OCR receipt extraction.

    Validates: CRM Gap Closure Req 60.1
    """

    amount: Decimal | None = Field(default=None, description="Extracted amount")
    vendor: str | None = Field(default=None, description="Extracted vendor name")
    category: str | None = Field(
        default=None,
        description="Suggested expense category",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score",
    )
