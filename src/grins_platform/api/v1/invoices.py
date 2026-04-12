"""
Invoice API endpoints.

This module provides FastAPI endpoints for invoice management,
including CRUD operations, status transitions, payments, and lien tracking.

Validates: Requirements 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7,
           11.1-11.8, 12.1-12.5, 13.1-13.7, 17.7-17.8, 22.1-22.7
"""

from datetime import date as date_cls
from decimal import Decimal
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
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import InvoiceStatus
from grins_platform.repositories.invoice_repository import InvoiceRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.schemas.dashboard import PendingInvoiceMetricsResponse
from grins_platform.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoiceListParams,
    InvoiceResponse,
    InvoiceUpdate,
    LienDeadlineResponse,
    LienFiledRequest,
    MassNotifyRequest,
    MassNotifyResponse,
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


class _InvoiceEndpoints(LoggerMixin):
    """Invoice API endpoint handlers with logging."""

    DOMAIN = "api"


_invoice_endpoints = _InvoiceEndpoints()


# =============================================================================
# Static Path Endpoints (MUST come before dynamic /{invoice_id} routes)
# =============================================================================


@router.get(
    "/metrics/pending",
    response_model=PendingInvoiceMetricsResponse,
    summary="Get pending invoice metrics",
    description="Get count and total amount of pending invoices "
    "(status SENT or VIEWED).",
)
async def get_pending_invoice_metrics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PendingInvoiceMetricsResponse:
    """Get pending invoice metrics for the dashboard.

    Returns the count and total amount of invoices with status
    SENT or VIEWED (not yet paid).

    Validates: CRM Gap Closure Req 5.2
    """
    _invoice_endpoints.log_started("get_pending_invoice_metrics")

    repo = InvoiceRepository(session=session)
    count, total_amount = await repo.get_pending_metrics()

    _invoice_endpoints.log_completed(
        "get_pending_invoice_metrics",
        count=count,
        total_amount=float(total_amount),
    )
    return PendingInvoiceMetricsResponse(
        count=count,
        total_amount=float(total_amount),
    )


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
    description="List invoices with 9-axis composable AND filtering.",
)
async def list_invoices(
    _current_user: ManagerOrAdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: InvoiceStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by status",
    ),
    customer_id: UUID | None = Query(default=None, description="Filter by customer ID"),
    customer_search: str | None = Query(
        default=None,
        description="Search by customer name",
    ),
    job_id: UUID | None = Query(default=None, description="Filter by job"),
    date_from: str | None = Query(default=None, description="Filter from date"),
    date_to: str | None = Query(default=None, description="Filter to date"),
    date_type: str = Query(
        default="created",
        description="Date field: created, due, or paid",
    ),
    amount_min: float | None = Query(
        default=None,
        ge=0,
        description="Minimum total amount",
    ),
    amount_max: float | None = Query(
        default=None,
        ge=0,
        description="Maximum total amount",
    ),
    payment_types: str | None = Query(
        default=None,
        description="Comma-separated payment methods",
    ),
    days_until_due_min: int | None = Query(
        default=None,
        description="Minimum days until due",
    ),
    days_until_due_max: int | None = Query(
        default=None,
        description="Maximum days until due",
    ),
    days_past_due_min: int | None = Query(
        default=None,
        description="Minimum days past due",
    ),
    days_past_due_max: int | None = Query(
        default=None,
        description="Maximum days past due",
    ),
    invoice_number: str | None = Query(
        default=None,
        description="Exact invoice number match",
    ),
    lien_eligible: bool | None = Query(
        default=None,
        description="Filter by lien eligibility",
    ),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", description="Sort order (asc/desc)"),
) -> PaginatedInvoiceResponse:
    """List invoices with 9-axis composable AND filtering.

    Validates: Requirements 13.1-13.7, 28.1
    """
    params = InvoiceListParams(
        page=page,
        page_size=page_size,
        status=status_filter,
        customer_id=customer_id,
        customer_search=customer_search,
        job_id=job_id,
        date_from=date_cls.fromisoformat(date_from) if date_from else None,
        date_to=date_cls.fromisoformat(date_to) if date_to else None,
        date_type=date_type if date_type in ("created", "due", "paid") else "created",
        amount_min=Decimal(str(amount_min)) if amount_min is not None else None,
        amount_max=Decimal(str(amount_max)) if amount_max is not None else None,
        payment_types=payment_types,
        days_until_due_min=days_until_due_min,
        days_until_due_max=days_until_due_max,
        days_past_due_min=days_past_due_min,
        days_past_due_max=days_past_due_max,
        invoice_number=invoice_number,
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


# =============================================================================
# Bulk Notify — Req 38
# =============================================================================


@router.post(
    "/bulk-notify",
    summary="Bulk notify invoices",
    description="Send notifications for multiple invoices at once.",
)
async def bulk_notify_invoices(
    invoice_ids: list[UUID],
    notification_type: str = "REMINDER",
    _current_user: ManagerOrAdminUser = None,  # type: ignore[assignment]
    service: Annotated[InvoiceService, Depends(get_invoice_service)] = None,  # type: ignore[assignment]
) -> dict[str, object]:
    """Send bulk notifications for invoices.

    Validates: CRM Gap Closure Req 38.1
    """
    _invoice_endpoints.log_started(
        "bulk_notify_invoices",
        count=len(invoice_ids),
        notification_type=notification_type,
    )

    sent = 0
    failed = 0
    skipped = 0

    for inv_id in invoice_ids:
        try:
            if notification_type == "REMINDER":
                await service.send_reminder(inv_id)
            elif notification_type == "LIEN_WARNING":
                await service.send_lien_warning(inv_id)
            else:
                await service.send_reminder(inv_id)
            sent += 1
        except InvoiceNotFoundError:  # noqa: PERF203
            skipped += 1
        except Exception:
            _invoice_endpoints.logger.warning(
                "bulk_notify_single_failure",
                invoice_id=str(inv_id),
                notification_type=notification_type,
            )
            failed += 1

    _invoice_endpoints.log_completed(
        "bulk_notify_invoices",
        sent=sent,
        failed=failed,
        skipped=skipped,
    )
    return {
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "total": len(invoice_ids),
    }


# =============================================================================
# Mass Notify — Req 29.3, 29.4
# =============================================================================


@router.post(
    "/mass-notify",
    response_model=MassNotifyResponse,
    summary="Mass notify customers by invoice criteria",
    description="Send bulk SMS to past-due, due-soon, or lien-eligible customers.",
)
async def mass_notify_invoices(
    request: MassNotifyRequest,
    _current_user: AdminUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> MassNotifyResponse:
    """Send mass notifications based on invoice criteria.

    Validates: Requirements 29.3, 29.4
    """
    _invoice_endpoints.log_started(
        "mass_notify_invoices",
        notification_type=request.notification_type,
    )

    result = await service.mass_notify(
        notification_type=request.notification_type,
        due_soon_days=request.due_soon_days,
        lien_days_past_due=request.lien_days_past_due,
        lien_min_amount=request.lien_min_amount,
        template=request.template,
    )

    _invoice_endpoints.log_completed(
        "mass_notify_invoices",
        notification_type=request.notification_type,
        targeted=result.targeted,
        sent=result.sent,
    )
    return result


# =============================================================================
# Invoice PDF — Req 80
# =============================================================================


@router.post(
    "/{invoice_id}/generate-pdf",
    summary="Generate invoice PDF",
    description="Generate a PDF for an invoice and store in S3.",
)
async def generate_invoice_pdf(
    invoice_id: UUID,
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Generate PDF for an invoice.

    Validates: CRM Gap Closure Req 80.2
    """
    from grins_platform.services.invoice_pdf_service import (  # noqa: PLC0415
        InvoiceNotFoundError as PDFInvoiceNotFoundError,
        InvoicePDFService,
    )

    _invoice_endpoints.log_started(
        "generate_invoice_pdf",
        invoice_id=str(invoice_id),
    )
    try:
        svc = InvoicePDFService()
        document_url = await svc.generate_pdf(session, invoice_id)
        _invoice_endpoints.log_completed(
            "generate_invoice_pdf",
            invoice_id=str(invoice_id),
        )
        return {"invoice_id": str(invoice_id), "document_url": document_url}
    except PDFInvoiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{invoice_id}/pdf",
    summary="Get invoice PDF download URL",
    description="Get a pre-signed download URL for an invoice PDF.",
)
async def get_invoice_pdf(
    invoice_id: UUID,
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Get pre-signed download URL for invoice PDF.

    Validates: CRM Gap Closure Req 80.3
    """
    from grins_platform.services.invoice_pdf_service import (  # noqa: PLC0415
        InvoicePDFNotFoundError,
        InvoicePDFService,
    )

    _invoice_endpoints.log_started(
        "get_invoice_pdf",
        invoice_id=str(invoice_id),
    )
    try:
        svc = InvoicePDFService()
        url = await svc.get_pdf_url(session, invoice_id)
        _invoice_endpoints.log_completed(
            "get_invoice_pdf",
            invoice_id=str(invoice_id),
        )
        return {"invoice_id": str(invoice_id), "download_url": url}
    except InvoicePDFNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


__all__ = ["router"]
