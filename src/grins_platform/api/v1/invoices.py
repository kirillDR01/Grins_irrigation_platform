"""
Invoice API endpoints.

This module provides FastAPI endpoints for invoice management,
including CRUD operations, status transitions, payments, and lien tracking.

Validates: Requirements 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7,
           11.1-11.8, 12.1-12.5, 13.1-13.7, 17.7-17.8, 22.1-22.7
"""

from datetime import date as date_type
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.auth_dependencies import (
    AdminUser,
    ManagerOrAdminUser,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.exceptions import (
    InvalidInvoiceOperationError,
    InvoiceNotFoundError,
)
from grins_platform.models.enums import InvoiceStatus
from grins_platform.repositories.invoice_repository import InvoiceRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoiceListParams,
    InvoiceResponse,
    InvoiceUpdate,
    LienDeadlineResponse,
    LienFiledRequest,
    PaginatedInvoiceResponse,
    PaymentRecord,
)
from grins_platform.services.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["invoices"])


async def get_invoice_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvoiceService:
    """Get InvoiceService dependency.

    Args:
        session: Database session from dependency injection

    Returns:
        InvoiceService instance
    """
    invoice_repository = InvoiceRepository(session=session)
    job_repository = JobRepository(session=session)
    return InvoiceService(
        invoice_repository=invoice_repository,
        job_repository=job_repository,
    )


# =============================================================================
# Static Path Endpoints (MUST come before dynamic /{invoice_id} routes)
# =============================================================================


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create invoice",
    description="Create a new invoice.",
)
async def create_invoice(
    data: InvoiceCreate,
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponse:
    """Create a new invoice.

    Requires manager or admin role.

    Args:
        data: Invoice creation data
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Returns:
        Created invoice response

    Raises:
        HTTPException: 400 if job not found

    Validates: Requirements 7.1-7.10, 17.7, 22.1
    """
    try:
        return await service.create_invoice(data)
    except InvalidInvoiceOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "",
    response_model=PaginatedInvoiceResponse,
    summary="List invoices",
    description="List invoices with pagination and filters.",
)
async def list_invoices(
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: InvoiceStatus | None = Query(
        default=None, alias="status", description="Filter by status",
    ),
    customer_id: UUID | None = Query(default=None, description="Filter by customer"),
    date_from: str | None = Query(default=None, description="Filter from date"),
    date_to: str | None = Query(default=None, description="Filter to date"),
    lien_eligible: bool | None = Query(
        default=None, description="Filter by lien eligibility",
    ),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", description="Sort order (asc/desc)"),
) -> PaginatedInvoiceResponse:
    """List invoices with pagination and filters.

    Requires manager or admin role.

    Args:
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance
        page: Page number
        page_size: Items per page
        status_filter: Filter by invoice status
        customer_id: Filter by customer ID
        date_from: Filter from date (YYYY-MM-DD)
        date_to: Filter to date (YYYY-MM-DD)
        lien_eligible: Filter by lien eligibility
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)

    Returns:
        Paginated invoice response

    Validates: Requirements 13.1-13.7
    """
    params = InvoiceListParams(
        page=page,
        page_size=page_size,
        status=status_filter,
        customer_id=customer_id,
        date_from=date_type.fromisoformat(date_from) if date_from else None,
        date_to=date_type.fromisoformat(date_to) if date_to else None,
        lien_eligible=lien_eligible,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await service.list_invoices(params)


@router.get(
    "/overdue",
    response_model=PaginatedInvoiceResponse,
    summary="List overdue invoices",
    description="List overdue invoices.",
)
async def list_overdue_invoices(
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginatedInvoiceResponse:
    """List overdue invoices.

    Requires manager or admin role.

    Args:
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance
        page: Page number
        page_size: Items per page

    Returns:
        Paginated invoice response

    Validates: Requirement 13.5
    """
    params = InvoiceListParams(
        page=page,
        page_size=page_size,
        status=InvoiceStatus.OVERDUE,
    )
    return await service.list_invoices(params)


@router.get(
    "/lien-deadlines",
    response_model=LienDeadlineResponse,
    summary="Get lien deadlines",
    description="Get invoices approaching lien deadlines.",
)
async def get_lien_deadlines(
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> LienDeadlineResponse:
    """Get invoices approaching lien deadlines.

    Requires manager or admin role.

    Args:
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Returns:
        Lien deadline response with approaching deadlines

    Validates: Requirements 11.4-11.5, 13.6
    """
    return await service.get_lien_deadlines()


@router.post(
    "/generate-from-job/{job_id}",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate invoice from job",
    description="Generate an invoice from a completed job.",
)
async def generate_invoice_from_job(
    job_id: UUID,
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponse:
    """Generate an invoice from a completed job.

    Requires manager or admin role.

    Args:
        job_id: Job ID
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Returns:
        Created invoice response

    Raises:
        HTTPException: 400 if job not found, deleted, or payment collected on site

    Validates: Requirements 10.1-10.7
    """
    try:
        return await service.generate_from_job(job_id)
    except InvalidInvoiceOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# =============================================================================
# Dynamic Path Endpoints (/{invoice_id} routes)
# =============================================================================


@router.get(
    "/{invoice_id}",
    response_model=InvoiceDetailResponse,
    summary="Get invoice",
    description="Get invoice with job and customer details.",
)
async def get_invoice(
    invoice_id: UUID,
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetailResponse:
    """Get invoice with job and customer details.

    Requires manager or admin role.

    Args:
        invoice_id: Invoice ID
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Returns:
        Invoice detail response

    Raises:
        HTTPException: 404 if not found

    Validates: Requirements 13.1, 22.3
    """
    try:
        return await service.get_invoice_detail(invoice_id)
    except InvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Update invoice",
    description="Update invoice (draft only).",
)
async def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponse:
    """Update an invoice (draft only).

    Requires manager or admin role.

    Args:
        invoice_id: Invoice ID
        data: Update data
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Returns:
        Updated invoice response

    Raises:
        HTTPException: 404 if not found, 400 if not draft

    Validates: Requirements 7.1-7.10, 22.3
    """
    try:
        return await service.update_invoice(invoice_id, data)
    except InvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except InvalidInvoiceOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel invoice",
    description="Cancel an invoice.",
)
async def cancel_invoice(
    invoice_id: UUID,
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> None:
    """Cancel an invoice.

    Requires manager or admin role.

    Args:
        invoice_id: Invoice ID
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Raises:
        HTTPException: 404 if not found

    Validates: Requirements 8.9, 22.3
    """
    try:
        await service.cancel_invoice(invoice_id)
    except InvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{invoice_id}/send",
    response_model=InvoiceResponse,
    summary="Send invoice",
    description="Mark invoice as sent (draft → sent).",
)
async def send_invoice(
    invoice_id: UUID,
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponse:
    """Mark invoice as sent.

    Requires manager or admin role.

    Args:
        invoice_id: Invoice ID
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Returns:
        Updated invoice response

    Raises:
        HTTPException: 404 if not found, 400 if not draft

    Validates: Requirement 8.2
    """
    try:
        return await service.send_invoice(invoice_id)
    except InvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except InvalidInvoiceOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{invoice_id}/payment",
    response_model=InvoiceResponse,
    summary="Record payment",
    description="Record a payment on an invoice.",
)
async def record_payment(
    invoice_id: UUID,
    payment: PaymentRecord,
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponse:
    """Record a payment on an invoice.

    Requires manager or admin role.

    Args:
        invoice_id: Invoice ID
        payment: Payment details
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Returns:
        Updated invoice response

    Raises:
        HTTPException: 404 if not found

    Validates: Requirements 9.1-9.7
    """
    try:
        return await service.record_payment(invoice_id, payment)
    except InvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{invoice_id}/reminder",
    response_model=InvoiceResponse,
    summary="Send reminder",
    description="Send a payment reminder for an invoice.",
)
async def send_reminder(
    invoice_id: UUID,
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponse:
    """Send a payment reminder for an invoice.

    Requires manager or admin role.

    Args:
        invoice_id: Invoice ID
        _current_user: Authenticated manager or admin user (for auth)
        service: InvoiceService instance

    Returns:
        Updated invoice response

    Raises:
        HTTPException: 404 if not found

    Validates: Requirements 12.1-12.5
    """
    try:
        return await service.send_reminder(invoice_id)
    except InvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{invoice_id}/lien-warning",
    response_model=InvoiceResponse,
    summary="Send lien warning",
    description="Send 45-day lien warning (admin only).",
)
async def send_lien_warning(
    invoice_id: UUID,
    _current_user: AdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponse:
    """Send 45-day lien warning for an invoice.

    Requires admin role.

    Args:
        invoice_id: Invoice ID
        _current_user: Authenticated admin user (for auth)
        service: InvoiceService instance

    Returns:
        Updated invoice response

    Raises:
        HTTPException: 404 if not found

    Validates: Requirements 11.6, 17.8
    """
    try:
        return await service.send_lien_warning(invoice_id)
    except InvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{invoice_id}/lien-filed",
    response_model=InvoiceResponse,
    summary="Mark lien filed",
    description="Mark lien as filed (admin only).",
)
async def mark_lien_filed(
    invoice_id: UUID,
    request: LienFiledRequest,
    _current_user: AdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponse:
    """Mark lien as filed for an invoice.

    Requires admin role.

    Args:
        invoice_id: Invoice ID
        request: Lien filing details
        _current_user: Authenticated admin user (for auth)
        service: InvoiceService instance

    Returns:
        Updated invoice response

    Raises:
        HTTPException: 404 if not found

    Validates: Requirements 11.7, 17.8
    """
    try:
        return await service.mark_lien_filed(invoice_id, request.filing_date)
    except InvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


__all__ = ["router"]
