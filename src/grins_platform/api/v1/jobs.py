"""
Job API endpoints.

This module provides REST API endpoints for job management including
CRUD operations, status transitions, price calculation, and filtering.

Validates: Requirement 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7, 6.1-6.9, 7.1-7.4, 12.1-12.7
"""

from __future__ import annotations

import math
from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import (
    func as sa_func,
    select as sa_select,
)
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.dependencies import get_db_session, get_job_service
from grins_platform.exceptions import (
    CustomerNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    PropertyCustomerMismatchError,
    PropertyNotFoundError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    JobCategory,
    JobStatus,
    PricingModel,
)
from grins_platform.models.estimate import Estimate
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.schemas.dashboard import JobStatusByCategoryResponse
from grins_platform.schemas.job import (
    JobCreate,
    JobResponse,
    JobStatusHistoryResponse,
    JobStatusUpdate,
    JobUpdate,
    PaginatedJobResponse,
    PriceCalculationResponse,
)
from grins_platform.services.job_service import (
    JobService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class JobEndpoints(LoggerMixin):
    """Job API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = JobEndpoints()


# =============================================================================
# GET /api/v1/jobs/metrics/by-status - Job Status Counts by Category
# NOTE: Static routes must come BEFORE dynamic routes like /{job_id}
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/metrics/by-status",
    response_model=JobStatusByCategoryResponse,
    summary="Get job status counts by category",
    description="Get job counts for the 6 dashboard categories: "
    "New Requests, Estimates, Pending Approval, To Be Scheduled, "
    "In Progress, and Complete.",
)
async def get_job_metrics_by_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobStatusByCategoryResponse:
    """Get job counts for the 6 dashboard status categories.

    Categories:
    - new_requests: status=requested
    - estimates: category=requires_estimate
    - pending_approval: jobs with estimates awaiting customer approval
    - to_be_scheduled: status=approved
    - in_progress: status=in_progress
    - complete: status=completed

    Validates: CRM Gap Closure Req 6.2
    """
    _endpoints.log_started("get_job_metrics_by_status")

    job_repo = JobRepository(session=session)

    # Get job counts by status
    status_counts = await job_repo.count_by_status()

    # Get jobs with category=requires_estimate count
    estimates_jobs = await job_repo.find_by_category(JobCategory.REQUIRES_ESTIMATE)

    # Get pending approval count: estimates with status SENT or VIEWED
    pending_approval_stmt = sa_select(sa_func.count(Estimate.id)).where(
        Estimate.status.in_(["sent", "viewed"]),
    )
    pending_result = await session.execute(pending_approval_stmt)
    pending_approval_count = pending_result.scalar() or 0

    result = JobStatusByCategoryResponse(
        new_requests=status_counts.get(JobStatus.REQUESTED.value, 0),
        estimates=len(estimates_jobs),
        pending_approval=int(pending_approval_count),
        to_be_scheduled=status_counts.get(JobStatus.APPROVED.value, 0),
        in_progress=status_counts.get(JobStatus.IN_PROGRESS.value, 0),
        complete=status_counts.get(JobStatus.COMPLETED.value, 0),
    )

    _endpoints.log_completed(
        "get_job_metrics_by_status",
        new_requests=result.new_requests,
        estimates=result.estimates,
        pending_approval=result.pending_approval,
        to_be_scheduled=result.to_be_scheduled,
        in_progress=result.in_progress,
        complete=result.complete,
    )
    return result


# =============================================================================
# Task 12.6: GET /api/v1/jobs - List Jobs
# NOTE: Static routes must come BEFORE dynamic routes like /{job_id}
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=PaginatedJobResponse,
    summary="List jobs",
    description="List jobs with filtering, sorting, and pagination.",
)
async def list_jobs(
    service: Annotated[JobService, Depends(get_job_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
    status_filter: JobStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by job status",
    ),
    category: JobCategory | None = Query(
        default=None,
        description="Filter by job category",
    ),
    customer_id: UUID | None = Query(
        default=None,
        description="Filter by customer ID",
    ),
    property_id: UUID | None = Query(
        default=None,
        description="Filter by property ID",
    ),
    service_offering_id: UUID | None = Query(
        default=None,
        description="Filter by service offering ID",
    ),
    priority_level: int | None = Query(
        default=None,
        ge=0,
        le=2,
        description="Filter by priority level",
    ),
    date_from: datetime | None = Query(
        default=None,
        description="Filter jobs created after this date",
    ),
    date_to: datetime | None = Query(
        default=None,
        description="Filter jobs created before this date",
    ),
    search: str | None = Query(
        default=None,
        description="Search by job type or description",
    ),
    has_service_agreement: bool | None = Query(
        default=None,
        description="Filter by subscription source",
    ),
    target_date_from: date | None = Query(
        default=None,
        description="Filter by target_start_date >= this date",
    ),
    target_date_to: date | None = Query(
        default=None,
        description="Filter by target_start_date <= this date",
    ),
    sort_by: str = Query(
        default="created_at",
        description="Field to sort by",
    ),
    sort_order: str = Query(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
    limit: int | None = Query(
        default=None,
        ge=1,
        le=100,
        description="Max items to return (alias for page_size). Takes precedence over page_size when provided.",
    ),
    offset: int | None = Query(
        default=None,
        ge=0,
        description="Number of items to skip. Converted to equivalent page number.",
    ),
) -> PaginatedJobResponse:
    """List jobs with filtering and pagination.

    Validates: Requirement 6.1-6.6, 6.9, 12.1
    """
    # Support limit/offset as alternative to page/page_size
    if limit is not None:
        page_size = limit
    if offset is not None:
        page = (offset // page_size) + 1

    _endpoints.log_started(
        "list_jobs",
        page=page,
        page_size=page_size,
        filters={
            "status": status_filter.value if status_filter else None,
            "category": category.value if category else None,
            "customer_id": str(customer_id) if customer_id else None,
            "search": search,
        },
    )

    jobs, total = await service.list_jobs(
        page=page,
        page_size=page_size,
        status=status_filter,
        category=category,
        customer_id=customer_id,
        property_id=property_id,
        service_offering_id=service_offering_id,
        priority_level=priority_level,
        date_from=date_from,
        date_to=date_to,
        search=search,
        has_service_agreement=has_service_agreement,
        target_date_from=target_date_from,
        target_date_to=target_date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    _endpoints.log_completed("list_jobs", count=len(jobs), total=total)

    items: list[JobResponse] = []
    for j in jobs:
        resp = JobResponse.model_validate(j)
        if hasattr(j, "customer") and j.customer is not None:
            resp.customer_name = f"{j.customer.first_name} {j.customer.last_name}"
            resp.customer_phone = j.customer.phone
        items.append(resp)

    return PaginatedJobResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# Task 12.9: GET /api/v1/jobs/ready-to-schedule - Get Ready to Schedule Jobs
# NOTE: Must come BEFORE /{job_id} route
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/ready-to-schedule",
    response_model=PaginatedJobResponse,
    summary="Get jobs ready to schedule",
    description="Retrieve jobs with category=ready_to_schedule.",
)
async def get_ready_to_schedule(
    service: Annotated[JobService, Depends(get_job_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
) -> PaginatedJobResponse:
    """Get jobs ready to schedule.

    Validates: Requirement 6.7, 12.1
    """
    _endpoints.log_started("get_ready_to_schedule", page=page, page_size=page_size)

    jobs, total = await service.get_ready_to_schedule(page=page, page_size=page_size)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    _endpoints.log_completed("get_ready_to_schedule", count=len(jobs), total=total)

    return PaginatedJobResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# Task 12.10: GET /api/v1/jobs/needs-estimate - Get Jobs Needing Estimate
# NOTE: Must come BEFORE /{job_id} route
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/needs-estimate",
    response_model=PaginatedJobResponse,
    summary="Get jobs needing estimate",
    description="Retrieve jobs with category=requires_estimate.",
)
async def get_needs_estimate(
    service: Annotated[JobService, Depends(get_job_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
) -> PaginatedJobResponse:
    """Get jobs needing estimates.

    Validates: Requirement 6.8, 12.1
    """
    _endpoints.log_started("get_needs_estimate", page=page, page_size=page_size)

    jobs, total = await service.get_needs_estimate(page=page, page_size=page_size)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    _endpoints.log_completed("get_needs_estimate", count=len(jobs), total=total)

    return PaginatedJobResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# Task 12.11: GET /api/v1/jobs/by-status/{status} - Get Jobs by Status
# NOTE: Must come BEFORE /{job_id} route
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/by-status/{job_status}",
    response_model=PaginatedJobResponse,
    summary="Get jobs by status",
    description="Retrieve jobs with a specific status.",
)
async def get_jobs_by_status(
    job_status: JobStatus,
    service: Annotated[JobService, Depends(get_job_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
) -> PaginatedJobResponse:
    """Get jobs by status.

    Validates: Requirement 6.2, 12.1
    """
    _endpoints.log_started(
        "get_jobs_by_status",
        status=job_status.value,
        page=page,
        page_size=page_size,
    )

    jobs, total = await service.get_by_status(
        status=job_status,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    _endpoints.log_completed("get_jobs_by_status", count=len(jobs), total=total)

    return PaginatedJobResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# Task 12.2: POST /api/v1/jobs - Create Job
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job",
    description="Create a new job request with auto-categorization.",
)
async def create_job(
    data: JobCreate,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    """Create a new job request.

    Validates: Requirement 2.1-2.12, 3.1-3.5, 12.1
    """
    _endpoints.log_started(
        "create_job",
        customer_id=str(data.customer_id),
        job_type=data.job_type,
    )

    try:
        result = await service.create_job(data)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("create_job", reason="customer_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    except PropertyNotFoundError as e:
        _endpoints.log_rejected("create_job", reason="property_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property not found: {e.property_id}",
        ) from e
    except PropertyCustomerMismatchError as e:
        _endpoints.log_rejected("create_job", reason="property_customer_mismatch")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Property {e.property_id} does not belong to "
            f"customer {e.customer_id}",
        ) from e
    except ServiceOfferingNotFoundError as e:
        _endpoints.log_rejected("create_job", reason="service_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service offering not found: {e.service_id}",
        ) from e
    except ServiceOfferingInactiveError as e:
        _endpoints.log_rejected("create_job", reason="service_inactive")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service offering is inactive: {e.service_id}",
        ) from e
    else:
        _endpoints.log_completed("create_job", job_id=str(result.id))
        return JobResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 12.3: GET /api/v1/jobs/{id} - Get Job by ID
# NOTE: Dynamic routes must come AFTER static routes
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job by ID",
    description="Retrieve a job by its unique identifier.",
)
async def get_job(
    job_id: UUID,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    """Get job by ID.

    Validates: Requirement 6.1, 12.1, 12.3
    """
    _endpoints.log_started("get_job", job_id=str(job_id))

    try:
        result = await service.get_job(job_id)
    except JobNotFoundError as e:
        _endpoints.log_rejected("get_job", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    else:
        _endpoints.log_completed("get_job", job_id=str(job_id))
        return JobResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 12.4: PUT /api/v1/jobs/{id} - Update Job
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{job_id}",
    response_model=JobResponse,
    summary="Update job",
    description="Update job details. Only provided fields will be updated.",
)
async def update_job(
    job_id: UUID,
    data: JobUpdate,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    """Update job information.

    Validates: Requirement 3.6, 3.7, 12.1, 12.3
    """
    _endpoints.log_started("update_job", job_id=str(job_id))

    try:
        result = await service.update_job(job_id, data)
    except JobNotFoundError as e:
        _endpoints.log_rejected("update_job", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    else:
        _endpoints.log_completed("update_job", job_id=str(job_id))
        return JobResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 12.5: DELETE /api/v1/jobs/{id} - Soft Delete Job
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job",
    description="Soft delete a job. The record is preserved but marked as deleted.",
)
async def delete_job(
    job_id: UUID,
    service: Annotated[JobService, Depends(get_job_service)],
) -> None:
    """Soft delete a job.

    Validates: Requirement 10.11, 12.1, 12.3
    """
    _endpoints.log_started("delete_job", job_id=str(job_id))

    try:
        await service.delete_job(job_id)
    except JobNotFoundError as e:
        _endpoints.log_rejected("delete_job", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    else:
        _endpoints.log_completed("delete_job", job_id=str(job_id))


# =============================================================================
# Task 12.7: PUT /api/v1/jobs/{id}/status - Update Job Status
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{job_id}/status",
    response_model=JobResponse,
    summary="Update job status",
    description="Update job status with validation. Records status history.",
)
async def update_job_status(
    job_id: UUID,
    data: JobStatusUpdate,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    """Update job status with validation.

    Validates: Requirement 4.1-4.10, 7.1, 12.1, 12.2
    """
    _endpoints.log_started(
        "update_job_status",
        job_id=str(job_id),
        new_status=data.status.value,
    )

    try:
        result = await service.update_status(job_id, data)
    except JobNotFoundError as e:
        _endpoints.log_rejected("update_job_status", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    except InvalidStatusTransitionError as e:
        _endpoints.log_rejected(
            "update_job_status",
            reason="invalid_transition",
            current=e.current_status.value,
            requested=e.requested_status.value,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {e.current_status.value} "
            f"to {e.requested_status.value}",
        ) from e
    else:
        _endpoints.log_completed("update_job_status", job_id=str(job_id))
        return JobResponse.model_validate(result)  # type: ignore[no-any-return]


# =============================================================================
# Task 12.8: GET /api/v1/jobs/{id}/history - Get Job Status History
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{job_id}/history",
    response_model=list[JobStatusHistoryResponse],
    summary="Get job status history",
    description="Retrieve the status change history for a job.",
)
async def get_job_history(
    job_id: UUID,
    service: Annotated[JobService, Depends(get_job_service)],
) -> list[JobStatusHistoryResponse]:
    """Get job status history.

    Validates: Requirement 7.2, 12.1
    """
    _endpoints.log_started("get_job_history", job_id=str(job_id))

    try:
        history = await service.get_status_history(job_id)
    except JobNotFoundError as e:
        _endpoints.log_rejected("get_job_history", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    else:
        _endpoints.log_completed("get_job_history", count=len(history))
        return [JobStatusHistoryResponse.model_validate(h) for h in history]


# =============================================================================
# Task 12.13: POST /api/v1/jobs/{id}/calculate-price - Calculate Price
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{job_id}/calculate-price",
    response_model=PriceCalculationResponse,
    summary="Calculate job price",
    description="Calculate price based on service offering and property.",
)
async def calculate_job_price(
    job_id: UUID,
    service: Annotated[JobService, Depends(get_job_service)],
) -> PriceCalculationResponse:
    """Calculate price for a job.

    Validates: Requirement 5.1-5.7, 12.1
    """
    _endpoints.log_started("calculate_job_price", job_id=str(job_id))

    try:
        result = await service.calculate_price(job_id)
    except JobNotFoundError as e:
        _endpoints.log_rejected("calculate_job_price", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    else:
        _endpoints.log_completed(
            "calculate_job_price",
            calculated_price=str(result.get("calculated_price")),
        )
        # Convert result dict to PriceCalculationResponse
        zone_count_val = result.get("zone_count")
        pricing_model_val = result.get("pricing_model")
        calculated_price_val = result.get("calculated_price")
        return PriceCalculationResponse(
            job_id=UUID(str(result["job_id"])),
            service_offering_id=UUID(str(result["service_offering_id"]))
            if result.get("service_offering_id")
            else None,
            pricing_model=PricingModel(pricing_model_val)
            if pricing_model_val
            else None,
            base_price=Decimal(str(result["base_price"]))
            if result.get("base_price")
            else None,
            zone_count=int(zone_count_val) if zone_count_val is not None else None,
            calculated_price=Decimal(str(calculated_price_val))
            if calculated_price_val
            else None,
            requires_manual_quote=bool(result.get("requires_manual_quote", True)),
            calculation_details={},
        )


# =============================================================================
# Job Financials — Req 57, 53
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{job_id}/financials",
    summary="Get job financials",
    description="Get financial breakdown for a specific job.",
)
async def get_job_financials(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, object]:
    """Get per-job financial breakdown.

    Validates: CRM Gap Closure Req 57.2
    """
    from grins_platform.services.accounting_service import (  # noqa: PLC0415
        AccountingService,
    )

    _endpoints.log_started("get_job_financials", job_id=str(job_id))

    from grins_platform.repositories.expense_repository import (  # noqa: PLC0415
        ExpenseRepository,
    )

    repo = ExpenseRepository(session)
    svc = AccountingService(expense_repository=repo)
    try:
        result = await svc.get_job_financials(session, job_id)
        _endpoints.log_completed("get_job_financials", job_id=str(job_id))
        return result.model_dump()
    except Exception as e:
        _endpoints.log_failed("get_job_financials", error=e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job financials not found: {job_id}",
        ) from e


@router.get(  # type: ignore[untyped-decorator]
    "/{job_id}/costs",
    summary="Get job costs",
    description="Get expenses associated with a specific job.",
)
async def get_job_costs(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> dict[str, object]:
    """Get expenses for a specific job.

    Validates: CRM Gap Closure Req 53.5
    """
    from grins_platform.repositories.expense_repository import (  # noqa: PLC0415
        ExpenseRepository,
    )
    from grins_platform.schemas.expense import ExpenseResponse  # noqa: PLC0415

    _endpoints.log_started("get_job_costs", job_id=str(job_id))
    repo = ExpenseRepository(session)
    expenses, total = await repo.list_with_filters(
        page=page,
        page_size=page_size,
        job_id=job_id,
    )
    items = [ExpenseResponse.model_validate(e) for e in expenses]
    _endpoints.log_completed("get_job_costs", job_id=str(job_id), count=len(items))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
