"""
Job API endpoints.

This module provides REST API endpoints for job management including
CRUD operations, status transitions, price calculation, and filtering.

Validates: Requirement 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7, 6.1-6.9, 7.1-7.4, 12.1-12.7
"""

from __future__ import annotations

import math
import os
from datetime import (
    date,
    datetime,
    timezone,
)
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import (
    func as sa_func,
    select as sa_select,
)
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import (
    get_db_session,
    get_job_service,
    get_photo_service,
)
from grins_platform.exceptions import (
    CustomerNotFoundError,
    InvalidInvoiceOperationError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    JobTargetDateEditNotAllowedError,
    PropertyCustomerMismatchError,
    PropertyNotFoundError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    AppointmentStatus,
    JobCategory,
    JobStatus,
    PricingModel,
    PropertyType,
)
from grins_platform.models.estimate import Estimate
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.schemas.ai import MessageType
from grins_platform.schemas.customer import (
    CustomerPhotoResponse,
)
from grins_platform.schemas.dashboard import JobStatusByCategoryResponse
from grins_platform.schemas.invoice import (
    InvoiceResponse,
)
from grins_platform.schemas.job import (
    JobCompleteRequest,
    JobCompleteResponse,
    JobCreate,
    JobNoteCreate,
    JobNoteResponse,
    JobResponse,
    JobReviewPushResponse,
    JobStatusHistoryResponse,
    JobStatusUpdate,
    JobUpdate,
    PaginatedJobResponse,
    PriceCalculationResponse,
)
from grins_platform.services.job_service import (
    JobService,
)
from grins_platform.services.photo_service import (
    PhotoService,
    UploadContext,
)

router = APIRouter()


# =============================================================================
# Helper: Get active (non-terminal) appointment for a job (Req 3.1, 3.3, 3.4)
# =============================================================================


async def get_active_appointment_for_job(
    session: AsyncSession,
    job_id: UUID,
) -> Appointment | None:
    """Get the most recent non-terminal appointment for a job.

    Queries for the latest appointment that is not COMPLETED, CANCELLED, or NO_SHOW.
    Returns None if no active appointment exists.

    Validates: Requirements 3.1, 3.3, 3.4
    """
    from grins_platform.models.appointment import Appointment  # noqa: PLC0415

    terminal_statuses = {
        AppointmentStatus.COMPLETED.value,
        AppointmentStatus.CANCELLED.value,
        AppointmentStatus.NO_SHOW.value,
    }
    stmt = (
        sa_select(Appointment)
        .where(Appointment.job_id == job_id)
        .where(Appointment.status.not_in(terminal_statuses))
        .order_by(Appointment.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


class JobEndpoints(LoggerMixin):
    """Job API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = JobEndpoints()


def _populate_property_fields(job: object, resp: JobResponse) -> None:
    """Populate property address and tag fields on a JobResponse.

    Validates: Requirement 19.1-19.4, Smoothing Req 11.3, 11.4
    """
    prop = getattr(job, "job_property", None)
    if prop is None:
        return
    parts = [prop.address, prop.city, prop.state]
    if prop.zip_code:
        parts.append(prop.zip_code)
    resp.property_address = ", ".join(parts)
    resp.customer_address = resp.property_address  # convenience alias (Req 11.3)
    resp.property_city = prop.city
    resp.property_type = prop.property_type
    resp.property_is_hoa = prop.is_hoa
    # Subscription = job has a service agreement
    sa_id = getattr(job, "service_agreement_id", None)
    resp.property_is_subscription = sa_id is not None
    # Computed property tags for badge display (Req 11.4)
    tags: list[str] = []
    if prop.property_type:
        tags.append(prop.property_type.capitalize())
    if prop.is_hoa:
        tags.append("HOA")
    if sa_id is not None:
        tags.append("Subscription")
    resp.property_tags = tags if tags else None


def _populate_preference_notes(job: object, resp: JobResponse) -> None:
    """Populate service preference notes hint on a JobResponse.

    Validates: CRM2 Req 7.3 — display preference notes as read-only hint.
    """
    customer = getattr(job, "customer", None)
    if customer is None:
        return
    prefs = getattr(customer, "preferred_service_times", None)
    if not prefs:
        return
    resp.service_preference_notes = JobService._notes_from_preference(
        prefs,
        resp.job_type,
    )


def _populate_agreement_fields(job: object, resp: JobResponse) -> None:
    """Populate service agreement name and active status on a JobResponse.

    Validates: Smoothing Req 7.3, 7.5
    """
    agreement = getattr(job, "service_agreement", None)
    if agreement is None:
        return
    tier = getattr(agreement, "tier", None)
    tier_name = getattr(tier, "name", None) if tier else None
    resp.service_agreement_name = tier_name or agreement.agreement_number
    is_active = (
        agreement.status == "active"
        and (agreement.end_date is None or agreement.end_date >= date.today())
        and agreement.cancelled_at is None
    )
    resp.service_agreement_active = is_active


def _populate_customer_tags(job: object, resp: JobResponse) -> None:
    """Denormalize ``customer.tags`` onto the JobResponse (Cluster A).

    ``Customer.tags`` is declared ``lazy="selectin"`` so it auto-loads
    whenever ``Customer`` is fetched. Empty tag set yields ``[]`` (not
    ``None``) so the frontend can distinguish "no tags" from "not loaded".
    """
    from grins_platform.schemas.customer_tag import (  # noqa: PLC0415
        CustomerTagResponse,
    )

    customer = getattr(job, "customer", None)
    if customer is None:
        return
    tags = getattr(customer, "tags", None)
    if tags is None:
        resp.customer_tags = []
        return
    resp.customer_tags = [CustomerTagResponse.model_validate(t) for t in tags]


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
        new_requests=0,  # No longer a distinct status; driven by action tags
        estimates=len(estimates_jobs),
        pending_approval=int(pending_approval_count),
        to_be_scheduled=status_counts.get(JobStatus.TO_BE_SCHEDULED.value, 0),
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
    property_type: PropertyType | None = Query(
        default=None,
        description="Filter by property type (residential/commercial)",
    ),
    is_hoa: bool | None = Query(
        default=None,
        description="Filter by HOA property flag",
    ),
    is_subscription_property: bool | None = Query(
        default=None,
        description="Filter by subscription property (has active service agreement)",
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
        description="Max items to return (alias for page_size). "
        "Takes precedence over page_size when provided.",
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
        property_type=property_type,
        is_hoa=is_hoa,
        is_subscription_property=is_subscription_property,
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
        _populate_property_fields(j, resp)
        _populate_preference_notes(j, resp)
        _populate_agreement_fields(j, resp)
        _populate_customer_tags(j, resp)
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

    items: list[JobResponse] = []
    for j in jobs:
        resp = JobResponse.model_validate(j)
        if hasattr(j, "customer") and j.customer is not None:
            resp.customer_name = f"{j.customer.first_name} {j.customer.last_name}"
            resp.customer_phone = j.customer.phone
        _populate_property_fields(j, resp)
        _populate_preference_notes(j, resp)
        _populate_agreement_fields(j, resp)
        _populate_customer_tags(j, resp)
        items.append(resp)

    return PaginatedJobResponse(
        items=items,
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
    _user: CurrentActiveUser,
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

    Validates: Requirement 6.1, 12.1, 12.3, 19.1-19.4
    """
    _endpoints.log_started("get_job", job_id=str(job_id))

    try:
        result = await service.get_job(job_id, include_relationships=True)
    except JobNotFoundError as e:
        _endpoints.log_rejected("get_job", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    else:
        _endpoints.log_completed("get_job", job_id=str(job_id))
        resp = JobResponse.model_validate(result)
        if hasattr(result, "customer") and result.customer is not None:
            first = result.customer.first_name
            last = result.customer.last_name
            resp.customer_name = f"{first} {last}"
            resp.customer_phone = result.customer.phone
        _populate_property_fields(result, resp)
        _populate_preference_notes(result, resp)
        _populate_agreement_fields(result, resp)
        _populate_customer_tags(result, resp)
        return resp  # type: ignore[no-any-return]


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
    _user: CurrentActiveUser,
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
    except JobTargetDateEditNotAllowedError as e:
        _endpoints.log_rejected(
            "update_job",
            reason="target_date_edit_not_allowed",
            current_status=e.current_status,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
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
    _user: CurrentActiveUser,
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
    _user: CurrentActiveUser,
    service: Annotated[JobService, Depends(get_job_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
        # Clear on-site timestamps when job is cancelled (Req 2.1)
        if data.status == JobStatus.CANCELLED:
            result.on_my_way_at = None
            result.started_at = None
            result.completed_at = None
            await session.flush()

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
    _user: CurrentActiveUser,
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


# =============================================================================
# POST /api/v1/jobs/{job_id}/complete - Mark job as complete (Req 21.2, 27.3-27.7)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{job_id}/complete",
    response_model=JobCompleteResponse,
    summary="Mark job as complete with payment warning",
    description=(
        "Transition job status to COMPLETED. Returns a warning if no "
        "payment/invoice exists. Use force=true to complete anyway."
    ),
)
async def complete_job(
    job_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[JobService, Depends(get_job_service)],
    body: JobCompleteRequest | None = None,
) -> JobCompleteResponse:
    """Mark a job as complete with payment/invoice check.

    Validates: Requirement 21.2, 27.3, 27.4, 27.5, 27.6, 27.7
    """
    from grins_platform.models.invoice import Invoice  # noqa: PLC0415
    from grins_platform.models.job import Job  # noqa: PLC0415

    _endpoints.log_started("complete_job", job_id=str(job_id))
    force = body.force if body else False

    # Load job
    stmt = sa_select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    # (1) Check service agreement — skip warning if active (Req 7.1, 7.2, 7.6)
    skip_payment_warning = False
    if job.service_agreement_id:
        from grins_platform.models.service_agreement import (  # noqa: PLC0415
            ServiceAgreement,
        )

        agreement = await session.get(ServiceAgreement, job.service_agreement_id)
        if (
            agreement
            and agreement.status == "active"
            and (agreement.end_date is None or agreement.end_date >= date.today())
            and agreement.cancelled_at is None
        ):
            skip_payment_warning = True

    # (2) Check payment collected on site, (3) check invoice exists (Req 27.3, 27.4)
    has_payment = bool(job.payment_collected_on_site)
    has_invoice = False
    if not skip_payment_warning and not has_payment:
        inv_stmt = (
            sa_select(sa_func.count())
            .select_from(Invoice)
            .where(
                Invoice.job_id == job_id,
            )
        )
        inv_result = await session.execute(inv_stmt)
        has_invoice = (inv_result.scalar() or 0) > 0
    else:
        has_invoice = True

    # (4) Show warning only if none of the above conditions are met
    if not skip_payment_warning and not has_payment and not has_invoice and not force:
        _endpoints.log_completed(
            "complete_job",
            job_id=str(job_id),
            warning="no_payment_or_invoice",
        )
        return JobCompleteResponse(
            completed=False,
            warning="No Payment or Invoice on File",
            job=None,
        )

    # Complete the job via service
    try:
        updated = await service.update_status(
            job_id,
            JobStatusUpdate(status=JobStatus.COMPLETED),
        )
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {e.job_id}",
        ) from e
    except InvalidStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {e.current_status.value} "
            f"to {e.requested_status.value}",
        ) from e

    # Compute time tracking metadata (Req 27.6)
    now = datetime.now(tz=timezone.utc)
    tracking: dict[str, object] = {"job_type": job.job_type}
    if job.on_my_way_at and job.started_at:
        tracking["travel_minutes"] = round(
            (job.started_at - job.on_my_way_at).total_seconds() / 60,
            1,
        )
    if job.started_at:
        tracking["work_minutes"] = round(
            (now - job.started_at).total_seconds() / 60,
            1,
        )
    if job.on_my_way_at:
        tracking["total_minutes"] = round(
            (now - job.on_my_way_at).total_seconds() / 60,
            1,
        )

    # Refresh to get the updated job and store metadata
    await session.refresh(job)
    job.time_tracking_metadata = tracking  # type: ignore[assignment]
    await session.flush()

    # Also complete the active appointment (Req 3.4, 3.7)
    appointment = await get_active_appointment_for_job(session, job_id)
    if appointment and appointment.status not in (
        AppointmentStatus.COMPLETED.value,
        AppointmentStatus.CANCELLED.value,
        AppointmentStatus.NO_SHOW.value,
    ):
        appointment.status = AppointmentStatus.COMPLETED.value
        await session.flush()

    await session.refresh(job)

    # Write audit log when the job completes without actual payment
    # (Req 27.5). Two cases — force-complete bypass (no payment, no
    # invoice) and the invoice-skip path (has_invoice=True but not
    # actually paid). Previously only the force path was audited; the
    # invoice-skip path silently skipped the warning without trace
    # (bughunt L-9).
    if not skip_payment_warning and not has_payment:
        from grins_platform.services.audit_service import AuditService  # noqa: PLC0415

        audit = AuditService()
        if force and not has_invoice:
            _ = await audit.log_action(
                session,
                action="job.complete_without_payment",
                resource_type="job",
                resource_id=job_id,
                details={
                    "override": True,
                    "reason": "Admin force-completed without payment or invoice",
                },
            )
        elif has_invoice:
            _ = await audit.log_action(
                session,
                action="job.complete_without_payment",
                resource_type="job",
                resource_id=job_id,
                details={
                    "override": False,
                    "reason": "Completed with invoice on file but no payment collected",
                },
            )

    resp = JobResponse.model_validate(updated)
    _populate_property_fields(job, resp)
    _populate_agreement_fields(job, resp)
    _populate_customer_tags(job, resp)
    _endpoints.log_completed("complete_job", job_id=str(job_id))
    return JobCompleteResponse(completed=True, warning=None, job=resp)


# =============================================================================
# POST /api/v1/jobs/{job_id}/invoice - Create invoice from job (Req 21.1)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{job_id}/invoice",
    response_model=InvoiceResponse,
    summary="Create invoice from job",
    description="Generate an invoice for the job.",
)
async def create_job_invoice(
    job_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvoiceResponse:
    """Create an invoice from a job.

    Validates: Requirement 21.1
    """
    from grins_platform.repositories.invoice_repository import (  # noqa: PLC0415
        InvoiceRepository,
    )
    from grins_platform.services.invoice_service import (  # noqa: PLC0415
        InvoiceService,
    )

    _endpoints.log_started("create_job_invoice", job_id=str(job_id))
    invoice_repo = InvoiceRepository(session=session)
    job_repo = JobRepository(session=session)
    invoice_service = InvoiceService(
        invoice_repository=invoice_repo,
        job_repository=job_repo,
    )
    try:
        result = await invoice_service.generate_from_job(job_id)
    except InvalidInvoiceOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed(
            "create_job_invoice",
            job_id=str(job_id),
        )
        return result  # type: ignore[return-value]


# =============================================================================
# On-Site Operation Endpoints (Req 26, 27)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{job_id}/on-my-way",
    response_model=JobResponse,
    summary="Send On My Way SMS and log timestamp",
    description="Send an On My Way SMS to the customer and log the timestamp.",
)
async def on_my_way(
    job_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobResponse:
    """Send On My Way SMS and log timestamp.

    Validates: Requirement 27.1
    """
    from grins_platform.models.customer import Customer  # noqa: PLC0415
    from grins_platform.models.job import Job  # noqa: PLC0415
    from grins_platform.services.sms.recipient import Recipient  # noqa: PLC0415
    from grins_platform.services.sms_service import SMSService  # noqa: PLC0415

    _endpoints.log_started("on_my_way", job_id=str(job_id))

    stmt = sa_select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # bughunt L-2: persist the on_my_way_at timestamp only after the SMS
    # actually goes out. Rollback on send failure so a later retry doesn't
    # look like a duplicate "already on my way" to downstream observers.
    prev_on_my_way_at = job.on_my_way_at
    now_ts = datetime.now(tz=timezone.utc)

    cust_stmt = sa_select(Customer).where(Customer.id == job.customer_id)
    cust_result = await session.execute(cust_stmt)
    customer = cust_result.scalar_one_or_none()

    if customer and customer.phone:
        recipient = Recipient.from_customer(customer)
        sms_service = SMSService(session)
        job.on_my_way_at = now_ts
        sms_succeeded = False
        try:
            send_result = await sms_service.send_message(
                recipient=recipient,
                message=(
                    "We're on our way! Your technician is heading to your location now."
                ),
                message_type=MessageType.ON_MY_WAY,
                consent_type="transactional",
                job_id=job_id,
            )
            sms_succeeded = bool(send_result.get("success"))
        except Exception:
            _endpoints.log_failed(
                "on_my_way_sms",
                error=None,
                job_id=str(job_id),
            )

        if not sms_succeeded:
            # Rollback the stale timestamp so a future successful send
            # gets recorded, not the earlier failed attempt.
            job.on_my_way_at = prev_on_my_way_at
    else:
        # No phone: still stamp the timestamp so admin's action is recorded
        # (same behaviour as before — there was nothing to fail on).
        job.on_my_way_at = now_ts

    await session.flush()
    await session.refresh(job)

    # Transition appointment to EN_ROUTE (Req 3.1, 3.2)
    appointment = await get_active_appointment_for_job(session, job_id)
    if appointment and appointment.status in (
        AppointmentStatus.CONFIRMED.value,
        AppointmentStatus.SCHEDULED.value,
    ):
        appointment.status = AppointmentStatus.EN_ROUTE.value
        await session.flush()

    await session.refresh(job)
    _endpoints.log_completed("on_my_way", job_id=str(job_id))
    return JobResponse.model_validate(job)  # type: ignore[no-any-return]


@router.post(  # type: ignore[untyped-decorator]
    "/{job_id}/started",
    response_model=JobResponse,
    summary="Log job started timestamp",
    description="Log the timestamp when the technician starts work on the job.",
)
async def job_started(
    job_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    """Log job started timestamp and transition status to in_progress.

    Validates: Requirement 27.2, Bug #7 fix
    """
    from grins_platform.models.job import Job  # noqa: PLC0415

    _endpoints.log_started("job_started", job_id=str(job_id))

    stmt = sa_select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    job.started_at = datetime.now(tz=timezone.utc)
    await session.flush()

    # Transition job to IN_PROGRESS if currently to_be_scheduled or scheduled
    if job.status in (
        JobStatus.TO_BE_SCHEDULED.value,
        JobStatus.SCHEDULED.value,
    ):
        await service.update_status(
            job_id,
            JobStatusUpdate(status=JobStatus.IN_PROGRESS),
        )

    # Transition appointment to IN_PROGRESS (Req 3.3)
    appointment = await get_active_appointment_for_job(session, job_id)
    if appointment and appointment.status in (
        AppointmentStatus.SCHEDULED.value,  # Skip scenario: customer never replied Y
        AppointmentStatus.CONFIRMED.value,  # Skip scenario: On My Way was skipped
        AppointmentStatus.EN_ROUTE.value,
    ):
        appointment.status = AppointmentStatus.IN_PROGRESS.value
        await session.flush()

    await session.refresh(job)
    _endpoints.log_completed("job_started", job_id=str(job_id))
    return JobResponse.model_validate(job)  # type: ignore[no-any-return]


@router.post(  # type: ignore[untyped-decorator]
    "/{job_id}/notes",
    response_model=JobNoteResponse,
    summary="Add note to job and sync to customer",
    description="Add a note to the job and sync it to the customer record.",
)
async def add_job_note(
    job_id: UUID,
    body: JobNoteCreate,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobNoteResponse:
    """Add a note to a job and sync to customer record.

    Validates: Requirement 26.3
    """
    from grins_platform.models.customer import Customer  # noqa: PLC0415
    from grins_platform.models.job import Job  # noqa: PLC0415

    _endpoints.log_started("add_job_note", job_id=str(job_id))

    stmt = sa_select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Append note to job
    timestamp = datetime.now(tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M",
    )
    entry = f"[{timestamp}] {body.note}"
    job.notes = f"{job.notes}\n{entry}" if job.notes else entry

    # Sync to customer internal_notes
    synced = False
    cust_stmt = sa_select(Customer).where(Customer.id == job.customer_id)
    cust_result = await session.execute(cust_stmt)
    customer = cust_result.scalar_one_or_none()
    if customer is not None:
        job_ref = f"[Job {job_id}] {entry}"
        customer.internal_notes = (
            f"{customer.internal_notes}\n{job_ref}"
            if customer.internal_notes
            else job_ref
        )
        synced = True

    await session.flush()
    _endpoints.log_completed("add_job_note", job_id=str(job_id), synced=synced)
    return JobNoteResponse(
        job_id=job_id,
        note=body.note,
        synced_to_customer=synced,
    )


@router.post(  # type: ignore[untyped-decorator]
    "/{job_id}/photos",
    response_model=CustomerPhotoResponse,
    summary="Upload photo linked to job",
    description="Upload a photo via PhotoService and link to job_id.",
)
async def upload_job_photo(
    job_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    photo_service: Annotated[PhotoService, Depends(get_photo_service)],
    file: Annotated[UploadFile, File(description="Photo file to upload")],
    caption: str | None = Query(
        default=None,
        max_length=500,
        description="Optional photo caption",
    ),
) -> CustomerPhotoResponse:
    """Upload a photo linked to a job.

    Validates: Requirement 26.3
    """
    from grins_platform.models.customer_photo import CustomerPhoto  # noqa: PLC0415
    from grins_platform.models.job import Job  # noqa: PLC0415

    _endpoints.log_started("upload_job_photo", job_id=str(job_id))

    stmt = sa_select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    file_data = await file.read()
    file_name = file.filename or "photo"

    try:
        upload_result = photo_service.upload_file(
            data=file_data,
            file_name=file_name,
            context=UploadContext.CUSTOMER_PHOTO,
        )
    except ValueError as e:
        # bughunt M-16: size cap exceeded → 413 Payload Too Large.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        ) from e
    except TypeError as e:
        # bughunt M-16: MIME not in allow-list → 415 Unsupported Media Type.
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        ) from e

    photo = CustomerPhoto(
        customer_id=job.customer_id,
        file_key=upload_result.file_key,
        file_name=upload_result.file_name,
        file_size=upload_result.file_size,
        content_type=upload_result.content_type,
        caption=caption,
        job_id=job_id,
    )
    session.add(photo)
    await session.flush()
    await session.refresh(photo)

    download_url = photo_service.generate_presigned_url(photo.file_key)

    _endpoints.log_completed(
        "upload_job_photo",
        job_id=str(job_id),
        photo_id=str(photo.id),
    )
    return CustomerPhotoResponse(
        id=photo.id,
        customer_id=photo.customer_id,
        file_key=photo.file_key,
        file_name=photo.file_name,
        file_size=photo.file_size,
        content_type=photo.content_type,
        caption=photo.caption,
        uploaded_by=photo.uploaded_by,
        download_url=download_url,
        created_at=photo.created_at,
    )


@router.post(  # type: ignore[untyped-decorator]
    "/{job_id}/review-push",
    response_model=JobReviewPushResponse,
    summary="Send Google review request SMS",
    description="Send a Google review request SMS to the customer.",
)
async def review_push(
    job_id: UUID,
    _user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobReviewPushResponse:
    """Send a Google review request SMS.

    Validates: Requirement 26.4
    """
    from grins_platform.models.customer import Customer  # noqa: PLC0415
    from grins_platform.models.job import Job  # noqa: PLC0415
    from grins_platform.services.sms.recipient import Recipient  # noqa: PLC0415
    from grins_platform.services.sms_service import SMSService  # noqa: PLC0415

    _endpoints.log_started("review_push", job_id=str(job_id))

    stmt = sa_select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    cust_stmt = sa_select(Customer).where(Customer.id == job.customer_id)
    cust_result = await session.execute(cust_stmt)
    customer = cust_result.scalar_one_or_none()
    if customer is None or not customer.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer has no phone number for review push",
        )

    review_url = os.environ.get(
        "GOOGLE_REVIEW_URL",
        "https://g.page/r/grins-irrigations/review",
    )
    # bughunt M-6: spec §4/§10 wording verbatim. ``customer`` is unused
    # here intentionally — the spec wording is brand-only, no first-name
    # personalization.
    message = (
        "Thanks for choosing Grins Irrigation! "
        f"We'd appreciate a quick review: {review_url}"
    )

    recipient = Recipient.from_customer(customer)
    sms_service = SMSService(session)
    message_id = None
    sms_sent = False
    try:
        send_result = await sms_service.send_message(
            recipient=recipient,
            message=message,
            message_type=MessageType.GOOGLE_REVIEW_REQUEST,
            consent_type="transactional",
            job_id=job_id,
        )
        sms_sent = send_result.get("success", False)
        mid = send_result.get("message_id")
        if mid:
            message_id = UUID(mid) if isinstance(mid, str) else mid
    except Exception:
        _endpoints.log_failed(
            "review_push_sms",
            error=None,
            job_id=str(job_id),
        )

    _endpoints.log_completed(
        "review_push",
        job_id=str(job_id),
        sms_sent=sms_sent,
    )
    return JobReviewPushResponse(
        job_id=job_id,
        sms_sent=sms_sent,
        message_id=message_id,
    )
