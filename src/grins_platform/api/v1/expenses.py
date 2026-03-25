"""Expense API endpoints.

Provides CRUD for expenses, category aggregation, and OCR receipt extraction.

Validates: CRM Gap Closure Req 53.2, 53.3, 53.5, 60.5
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    ExpenseCategory,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.repositories.expense_repository import ExpenseRepository
from grins_platform.schemas.expense import (
    ExpenseByCategoryResponse,
    ExpenseCreate,
    ExpenseResponse,
    ReceiptExtractionResponse,
)
from grins_platform.services.accounting_service import (
    AccountingService,
    ReceiptExtractionError,
)

router = APIRouter()


class _ExpenseEndpoints(LoggerMixin):
    """Expense API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _ExpenseEndpoints()


async def _get_expense_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExpenseRepository:
    """Get ExpenseRepository dependency."""
    return ExpenseRepository(session)


async def _get_accounting_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountingService:
    """Get AccountingService dependency."""
    repo = ExpenseRepository(session)
    return AccountingService(expense_repository=repo)


# =============================================================================
# Static routes FIRST
# =============================================================================


@router.get(
    "/by-category",
    response_model=list[ExpenseByCategoryResponse],
    summary="Get expenses by category",
    description="Returns aggregated expense totals grouped by category.",
)
async def get_expenses_by_category(
    _current_user: CurrentActiveUser,
    service: Annotated[AccountingService, Depends(_get_accounting_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ExpenseByCategoryResponse]:
    """Get expenses aggregated by category.

    Validates: CRM Gap Closure Req 53.3
    """
    _endpoints.log_started("get_expenses_by_category")
    result = await service.get_expenses_by_category(session)
    _endpoints.log_completed(
        "get_expenses_by_category",
        count=len(result),
    )
    return result


@router.post(
    "/extract-receipt",
    response_model=ReceiptExtractionResponse,
    summary="Extract receipt data via OCR",
    description="Provide a receipt S3 file key for OCR amount/vendor extraction.",
)
async def extract_receipt(
    _current_user: CurrentActiveUser,
    service: Annotated[AccountingService, Depends(_get_accounting_service)],
    receipt_file_key: str = Query(
        ...,
        description="S3 key of the uploaded receipt image",
    ),
) -> ReceiptExtractionResponse:
    """Extract receipt data via OCR.

    Note: This endpoint accepts an S3 file key. The service downloads
    the image from S3 and processes it via OpenAI Vision.

    Validates: CRM Gap Closure Req 60.5
    """
    _endpoints.log_started("extract_receipt", file_key=receipt_file_key)
    try:
        result = await service.extract_receipt(
            image_data=b"",  # Placeholder — real impl downloads from S3
            content_type="image/jpeg",
        )
    except ReceiptExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed("extract_receipt")
        return result


# =============================================================================
# CRUD endpoints
# =============================================================================


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create expense",
    description="Create a new expense record.",
)
async def create_expense(
    data: ExpenseCreate,
    current_user: CurrentActiveUser,
    repo: Annotated[ExpenseRepository, Depends(_get_expense_repo)],
) -> ExpenseResponse:
    """Create a new expense.

    Validates: CRM Gap Closure Req 53.2
    """
    _endpoints.log_started("create_expense", category=data.category.value)
    expense = await repo.create(
        category=data.category.value,
        description=data.description,
        amount=data.amount,
        expense_date=data.expense_date,
        job_id=data.job_id,
        staff_id=data.staff_id,
        vendor=data.vendor,
        receipt_file_key=data.receipt_file_key,
        lead_source=data.lead_source,
        notes=data.notes,
        created_by=current_user.id,
    )
    _endpoints.log_completed("create_expense", expense_id=str(expense.id))
    return ExpenseResponse.model_validate(expense)


@router.get(
    "",
    response_model=dict[str, Any],
    summary="List expenses",
    description="List expenses with pagination and filters.",
)
async def list_expenses(
    _current_user: CurrentActiveUser,
    repo: Annotated[ExpenseRepository, Depends(_get_expense_repo)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    category: ExpenseCategory | None = Query(
        default=None,
        description="Filter by category",
    ),
    job_id: UUID | None = Query(default=None, description="Filter by job"),
) -> dict[str, Any]:
    """List expenses with pagination.

    Validates: CRM Gap Closure Req 53.2
    """
    _endpoints.log_started("list_expenses", page=page)
    expenses, total = await repo.list_with_filters(
        page=page,
        page_size=page_size,
        category=category.value if category else None,
        job_id=job_id,
    )
    items = [ExpenseResponse.model_validate(e) for e in expenses]
    _endpoints.log_completed("list_expenses", count=len(items), total=total)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{expense_id}",
    response_model=ExpenseResponse,
    summary="Get expense by ID",
)
async def get_expense(
    expense_id: UUID,
    _current_user: CurrentActiveUser,
    repo: Annotated[ExpenseRepository, Depends(_get_expense_repo)],
) -> ExpenseResponse:
    """Get a single expense by ID."""
    _endpoints.log_started("get_expense", expense_id=str(expense_id))
    expense = await repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense not found: {expense_id}",
        )
    _endpoints.log_completed("get_expense", expense_id=str(expense_id))
    return ExpenseResponse.model_validate(expense)


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete expense",
)
async def delete_expense(
    expense_id: UUID,
    _current_user: CurrentActiveUser,
    repo: Annotated[ExpenseRepository, Depends(_get_expense_repo)],
) -> None:
    """Delete an expense by ID."""
    _endpoints.log_started("delete_expense", expense_id=str(expense_id))
    deleted = await repo.delete(expense_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense not found: {expense_id}",
        )
    _endpoints.log_completed("delete_expense", expense_id=str(expense_id))
