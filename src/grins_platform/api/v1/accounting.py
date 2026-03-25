"""Accounting API endpoints.

Provides financial summary, tax reporting, and Plaid integration.

Validates: CRM Gap Closure Req 52.5, 59.2, 61.2, 61.4, 62.2
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.accounting import (
    AccountingSummaryResponse,
    TaxEstimateResponse,
    TaxProjectionRequest,
    TaxProjectionResponse,
    TaxSummaryResponse,
)
from grins_platform.services.accounting_service import (
    AccountingService,
)

router = APIRouter()


class _AccountingEndpoints(LoggerMixin):
    """Accounting API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _AccountingEndpoints()


async def _get_accounting_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountingService:
    """Get AccountingService dependency."""
    from grins_platform.repositories.expense_repository import (  # noqa: PLC0415
        ExpenseRepository,
    )

    repo = ExpenseRepository(session)
    return AccountingService(expense_repository=repo)


@router.get(
    "/summary",
    response_model=AccountingSummaryResponse,
    summary="Get YTD accounting summary",
    description="Returns YTD revenue, expenses, profit, and margin.",
)
async def get_accounting_summary(
    _current_user: CurrentActiveUser,
    service: Annotated[AccountingService, Depends(_get_accounting_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountingSummaryResponse:
    """Get YTD accounting summary.

    Validates: CRM Gap Closure Req 52.5
    """
    _endpoints.log_started("get_accounting_summary")
    result = await service.get_summary(session)
    _endpoints.log_completed("get_accounting_summary")
    return result


@router.get(
    "/tax-summary",
    response_model=TaxSummaryResponse,
    summary="Get tax preparation summary",
    description="Returns expense categories with YTD totals for tax prep.",
)
async def get_tax_summary(
    _current_user: CurrentActiveUser,
    service: Annotated[AccountingService, Depends(_get_accounting_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaxSummaryResponse:
    """Get tax preparation summary.

    Validates: CRM Gap Closure Req 59.2
    """
    _endpoints.log_started("get_tax_summary")
    result = await service.get_tax_summary(session)
    _endpoints.log_completed("get_tax_summary")
    return result


@router.get(
    "/tax-estimate",
    response_model=TaxEstimateResponse,
    summary="Get estimated tax due",
    description="Returns estimated tax liability based on current data.",
)
async def get_tax_estimate(
    _current_user: CurrentActiveUser,
    service: Annotated[AccountingService, Depends(_get_accounting_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaxEstimateResponse:
    """Get estimated tax due.

    Validates: CRM Gap Closure Req 61.2
    """
    _endpoints.log_started("get_tax_estimate")
    result = await service.get_tax_estimate(session)
    _endpoints.log_completed("get_tax_estimate")
    return result


@router.post(
    "/tax-projection",
    response_model=TaxProjectionResponse,
    summary="Project tax impact",
    description="What-if tax projection with hypothetical revenue/expenses.",
)
async def project_tax(
    data: TaxProjectionRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[AccountingService, Depends(_get_accounting_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaxProjectionResponse:
    """Project tax impact with hypothetical values.

    Validates: CRM Gap Closure Req 61.4
    """
    _endpoints.log_started("project_tax")
    result = await service.project_tax(session, data)
    _endpoints.log_completed("project_tax")
    return result


@router.post(
    "/connect-account",
    summary="Initiate Plaid Link",
    description="Create a Plaid Link token for bank account connection.",
)
async def connect_account(
    _current_user: CurrentActiveUser,
) -> dict[str, str]:
    """Initiate Plaid Link for bank account connection.

    Validates: CRM Gap Closure Req 62.2
    """
    _endpoints.log_started("connect_account")
    # Plaid integration is stubbed — returns placeholder
    _endpoints.log_completed("connect_account")
    return {"link_token": "plaid-link-token-placeholder", "status": "pending"}
