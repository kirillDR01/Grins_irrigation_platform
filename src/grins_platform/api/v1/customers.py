"""
Customer API endpoints.

This module provides REST API endpoints for customer management including
CRUD operations, lookups, flag management, bulk operations, duplicate
detection, merge, photos, invoice history, and payment methods.

Validates: Requirement 1.1-1.6, 3.1-3.6, 4.1-4.7, 6.6, 7.1-7.6, 8.1-8.5,
           9.2-9.4, 10.1-10.7, 11.1-11.6, 12.1-12.5, 56.2-56.3
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.dependencies import (
    get_customer_service,
    get_db_session,
    get_photo_service,
)
from grins_platform.exceptions import (
    BulkOperationError,
    CustomerNotFoundError,
    DuplicateCustomerError,
    MergeConflictError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    CustomerStatus,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.schemas.customer import (
    BulkPreferencesUpdate,
    BulkUpdateResponse,
    ChargeRequest,
    ChargeResponse,
    CustomerCreate,
    CustomerDetailResponse,
    CustomerFlagsUpdate,
    CustomerListParams,
    CustomerPhotoResponse,
    CustomerResponse,
    CustomerUpdate,
    DuplicateGroup,
    MergeCustomersRequest,
    PaginatedCustomerResponse,
    PaymentMethodResponse,
    ServiceHistorySummary,
)
from grins_platform.services.customer_service import (
    CustomerService,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.services.photo_service import (
    PhotoService,
    UploadContext,
)

router = APIRouter()


class CustomerEndpoints(LoggerMixin):
    """Customer API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = CustomerEndpoints()


# =============================================================================
# Task 7.2: POST /api/v1/customers - Create Customer
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
    description="Create a new customer with the provided information. "
    "Phone number must be unique across all active customers.",
)
async def create_customer(
    data: CustomerCreate,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerResponse:
    """Create a new customer.

    Args:
        data: CustomerCreate schema with customer information
        service: Injected CustomerService

    Returns:
        CustomerResponse with created customer data

    Raises:
        HTTPException: 400 if phone number already exists

    Validates: Requirement 1.1, 6.6, 8.5-8.7, 10.1
    """
    _endpoints.log_started("create_customer", phone=data.phone[-4:])

    try:
        result = await service.create_customer(data)
    except DuplicateCustomerError as e:
        _endpoints.log_rejected(
            "create_customer",
            reason="duplicate_phone",
            existing_id=str(e.existing_id),
        )
        detail = f"Customer with this phone already exists (ID: {e.existing_id})"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from e
    else:
        _endpoints.log_completed("create_customer", customer_id=str(result.id))
        return result


# =============================================================================
# CRM Gap Closure 7.3: GET /api/v1/customers/duplicates
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/duplicates",
    response_model=list[DuplicateGroup],
    summary="Get potential duplicate customer groups",
    description="Returns groups of potential duplicate customers identified "
    "by matching phone, email, or similar name.",
)
async def get_duplicates(
    service: Annotated[CustomerService, Depends(get_customer_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DuplicateGroup]:
    """Get potential duplicate customer groups.

    Args:
        service: Injected CustomerService
        db: Async database session

    Returns:
        List of DuplicateGroup with potential duplicates

    Validates: CRM Gap Closure Req 7.1
    """
    _endpoints.log_started("get_duplicates")

    result = await service.find_duplicates(db)

    _endpoints.log_completed("get_duplicates", group_count=len(result))
    return result


# =============================================================================
# CRM Gap Closure 7.3: POST /api/v1/customers/merge
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/merge",
    response_model=CustomerResponse,
    summary="Merge duplicate customers",
    description="Merge duplicate customers into a primary customer. "
    "All related records are reassigned and duplicates are soft-deleted.",
)
async def merge_customers(
    data: MergeCustomersRequest,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> CustomerResponse:
    """Merge duplicate customers into a primary customer.

    Args:
        data: MergeCustomersRequest with primary and duplicate IDs
        service: Injected CustomerService
        db: Async database session
        request: FastAPI request for IP address

    Returns:
        CustomerResponse of the primary customer after merge

    Raises:
        HTTPException: 404 if customer not found, 409 on merge conflict

    Validates: CRM Gap Closure Req 7.2
    """
    _endpoints.log_started(
        "merge_customers",
        primary_id=str(data.primary_customer_id),
        duplicate_count=len(data.duplicate_customer_ids),
    )

    # Extract actor_id — use a placeholder for now (no auth in this context)
    actor_id = data.primary_customer_id  # Admin performing the merge
    ip_address = request.client.host if request.client else "unknown"

    try:
        result = await service.merge_customers(
            db=db,
            primary_id=data.primary_customer_id,
            duplicate_ids=data.duplicate_customer_ids,
            actor_id=actor_id,
            ip_address=ip_address,
        )
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("merge_customers", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    except MergeConflictError as e:
        _endpoints.log_rejected("merge_customers", reason="conflict")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed(
            "merge_customers",
            primary_id=str(data.primary_customer_id),
        )
        return result


# =============================================================================
# Task 7.3: GET /api/v1/customers/{id} - Get Customer
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{customer_id}",
    response_model=CustomerDetailResponse,
    summary="Get customer by ID",
    description="Retrieve a customer with their properties and service history.",
)
async def get_customer(
    customer_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    include_properties: bool = Query(
        default=True,
        description="Include customer properties in response",
    ),
    include_service_history: bool = Query(
        default=True,
        description="Include service history summary in response",
    ),
) -> CustomerDetailResponse:
    """Get customer by ID with properties and service history.

    Args:
        customer_id: UUID of the customer to retrieve
        service: Injected CustomerService
        include_properties: Whether to include properties
        include_service_history: Whether to include service history

    Returns:
        CustomerDetailResponse with customer data

    Raises:
        HTTPException: 404 if customer not found

    Validates: Requirement 1.4, 3.5, 5.5
    """
    _endpoints.log_started("get_customer", customer_id=str(customer_id))

    try:
        result = await service.get_customer(
            customer_id,
            include_properties=include_properties,
            include_service_history=include_service_history,
        )
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("get_customer", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    else:
        _endpoints.log_completed("get_customer", customer_id=str(customer_id))
        return result


# =============================================================================
# Task 7.4: PUT /api/v1/customers/{id} - Update Customer
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer",
    description="Update customer information. Only provided fields will be updated.",
)
async def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerResponse:
    """Update customer information.

    Args:
        customer_id: UUID of the customer to update
        data: CustomerUpdate schema with fields to update
        service: Injected CustomerService

    Returns:
        CustomerResponse with updated customer data

    Raises:
        HTTPException: 404 if customer not found
        HTTPException: 400 if new phone number already exists

    Validates: Requirement 1.5, 6.1-6.5
    """
    _endpoints.log_started("update_customer", customer_id=str(customer_id))

    try:
        result = await service.update_customer(customer_id, data)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("update_customer", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    except DuplicateCustomerError as e:
        _endpoints.log_rejected(
            "update_customer",
            reason="duplicate_phone",
            existing_id=str(e.existing_id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phone number already in use by customer: {e.existing_id}",
        ) from e
    else:
        _endpoints.log_completed("update_customer", customer_id=str(customer_id))
        return result


# =============================================================================
# Task 7.5: DELETE /api/v1/customers/{id} - Delete Customer
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer",
    description="Soft delete a customer. Related data (properties) is preserved.",
)
async def delete_customer(
    customer_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> None:
    """Soft delete a customer.

    Args:
        customer_id: UUID of the customer to delete
        service: Injected CustomerService

    Raises:
        HTTPException: 404 if customer not found

    Validates: Requirement 1.6, 6.8
    """
    _endpoints.log_started("delete_customer", customer_id=str(customer_id))

    try:
        await service.delete_customer(customer_id)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("delete_customer", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    else:
        _endpoints.log_completed("delete_customer", customer_id=str(customer_id))


# =============================================================================
# Task 7.6: GET /api/v1/customers - List Customers
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=PaginatedCustomerResponse,
    summary="List customers",
    description="List customers with filtering, sorting, and pagination support.",
)
async def list_customers(
    service: Annotated[CustomerService, Depends(get_customer_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
    city: str | None = Query(
        default=None,
        description="Filter by city (customers with properties in this city)",
    ),
    status_filter: CustomerStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by customer status",
    ),
    is_priority: bool | None = Query(
        default=None,
        description="Filter by priority flag",
    ),
    is_red_flag: bool | None = Query(
        default=None,
        description="Filter by red flag",
    ),
    is_slow_payer: bool | None = Query(
        default=None,
        description="Filter by slow payer flag",
    ),
    search: str | None = Query(
        default=None,
        description="Search by name or email (case-insensitive)",
    ),
    sort_by: str = Query(
        default="last_name",
        description="Field to sort by",
    ),
    sort_order: str = Query(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
) -> PaginatedCustomerResponse:
    """List customers with filtering and pagination.

    Args:
        service: Injected CustomerService
        page: Page number (1-indexed)
        page_size: Number of items per page
        city: Filter by city
        status_filter: Filter by customer status
        is_priority: Filter by priority flag
        is_red_flag: Filter by red flag
        is_slow_payer: Filter by slow payer flag
        search: Search by name or email
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)

    Returns:
        PaginatedCustomerResponse with customers and pagination info

    Validates: Requirement 4.1-4.7
    """
    _endpoints.log_started(
        "list_customers",
        page=page,
        page_size=page_size,
        filters={
            "city": city,
            "status": status_filter.value if status_filter else None,
        },
    )

    params = CustomerListParams(
        page=page,
        page_size=page_size,
        city=city,
        status=status_filter,
        is_priority=is_priority,
        is_red_flag=is_red_flag,
        is_slow_payer=is_slow_payer,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    result = await service.list_customers(params)
    _endpoints.log_completed(
        "list_customers",
        count=len(result.items),
        total=result.total,
    )
    return result


# =============================================================================
# Task 8.1: PUT /api/v1/customers/{id}/flags - Update Flags
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{customer_id}/flags",
    response_model=CustomerResponse,
    summary="Update customer flags",
    description="Update customer flags (priority, red flag, slow payer, new customer).",
)
async def update_customer_flags(
    customer_id: UUID,
    flags: CustomerFlagsUpdate,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerResponse:
    """Update customer flags.

    Args:
        customer_id: UUID of the customer
        flags: CustomerFlagsUpdate with flag values to update
        service: Injected CustomerService

    Returns:
        CustomerResponse with updated customer data

    Raises:
        HTTPException: 404 if customer not found

    Validates: Requirement 3.1-3.6
    """
    _endpoints.log_started("update_flags", customer_id=str(customer_id))

    try:
        result = await service.update_flags(customer_id, flags)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("update_flags", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    else:
        _endpoints.log_completed("update_flags", customer_id=str(customer_id))
        return result


# =============================================================================
# Task 8.2: GET /api/v1/customers/lookup/phone/{phone} - Lookup by Phone
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/lookup/phone/{phone}",
    response_model=list[CustomerResponse],
    summary="Lookup customers by phone",
    description="Lookup customers by phone number with optional partial matching.",
)
async def lookup_by_phone(
    phone: str,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    partial: bool = Query(
        default=False,
        description="Enable partial phone number matching",
    ),
) -> list[CustomerResponse]:
    """Lookup customers by phone number.

    Args:
        phone: Phone number to search for
        service: Injected CustomerService
        partial: If True, search for partial matches

    Returns:
        List of matching CustomerResponse objects (empty if none found)

    Validates: Requirement 11.1, 11.3-11.5
    """
    phone_suffix = phone[-4:] if len(phone) >= 4 else phone
    _endpoints.log_started("lookup_by_phone", phone=phone_suffix, partial=partial)

    result = await service.lookup_by_phone(phone, partial_match=partial)

    _endpoints.log_completed("lookup_by_phone", count=len(result))
    return result


# =============================================================================
# Task 8.3: GET /api/v1/customers/lookup/email/{email} - Lookup by Email
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/lookup/email/{email}",
    response_model=list[CustomerResponse],
    summary="Lookup customers by email",
    description="Lookup customers by email address (case-insensitive).",
)
async def lookup_by_email(
    email: str,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> list[CustomerResponse]:
    """Lookup customers by email address.

    Args:
        email: Email address to search for
        service: Injected CustomerService

    Returns:
        List of matching CustomerResponse objects (empty if none found)

    Validates: Requirement 11.2, 11.3
    """
    _endpoints.log_started("lookup_by_email", email=email)

    result = await service.lookup_by_email(email)

    _endpoints.log_completed("lookup_by_email", count=len(result))
    return result


# =============================================================================
# Task 8.4: GET /api/v1/customers/{id}/service-history - Get Service History
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{customer_id}/service-history",
    response_model=ServiceHistorySummary,
    summary="Get customer service history",
    description="Get service history summary for a customer.",
)
async def get_service_history(
    customer_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> ServiceHistorySummary:
    """Get service history for a customer.

    Args:
        customer_id: UUID of the customer
        service: Injected CustomerService

    Returns:
        ServiceHistorySummary with job count, last service date, and revenue

    Raises:
        HTTPException: 404 if customer not found

    Validates: Requirement 7.1-7.8
    """
    _endpoints.log_started("get_service_history", customer_id=str(customer_id))

    try:
        result = await service.get_service_history(customer_id)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("get_service_history", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    else:
        _endpoints.log_completed("get_service_history", customer_id=str(customer_id))
        return result


# =============================================================================
# Task 12.12: GET /api/v1/customers/{id}/jobs - Get Customer Jobs
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{customer_id}/jobs",
    summary="Get customer jobs",
    description="Get all jobs for a customer with pagination.",
)
async def get_customer_jobs(
    customer_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
) -> dict[str, str]:
    """Get all jobs for a customer.

    This endpoint returns jobs for a specific customer. The actual job
    retrieval is handled by the JobService via the jobs API.

    Args:
        customer_id: UUID of the customer
        service: Injected CustomerService
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Paginated job response (redirects to jobs API internally)

    Raises:
        HTTPException: 404 if customer not found

    Validates: Requirement 6.4, 12.1
    """
    _endpoints.log_started("get_customer_jobs", customer_id=str(customer_id))

    # Verify customer exists
    try:
        await service.get_customer(customer_id, include_properties=False)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("get_customer_jobs", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e

    # Return redirect info - actual job retrieval should use /api/v1/jobs?customer_id=
    _endpoints.log_completed("get_customer_jobs", customer_id=str(customer_id))
    redirect_url = (
        f"/api/v1/jobs?customer_id={customer_id}&page={page}&page_size={page_size}"
    )
    return {
        "message": "Use /api/v1/jobs?customer_id={customer_id} for job listing",
        "customer_id": str(customer_id),
        "redirect_url": redirect_url,
    }


# =============================================================================
# Task 8.5: POST /api/v1/customers/export - Export Customers CSV
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/export",
    summary="Export customers to CSV",
    description="Export customers to CSV format with optional city filter.",
)
async def export_customers(
    service: Annotated[CustomerService, Depends(get_customer_service)],
    city: str | None = Query(
        default=None,
        description="Filter by city",
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=1000,
        description="Maximum records to export (max 1000)",
    ),
) -> Response:
    """Export customers to CSV.

    Args:
        service: Injected CustomerService
        city: Optional city filter
        limit: Maximum records to export

    Returns:
        CSV file response

    Validates: Requirement 12.1-12.2, 12.4
    """
    _endpoints.log_started("export_customers", city=city, limit=limit)

    try:
        csv_content = await service.export_customers_csv(city=city, limit=limit)
    except BulkOperationError as e:
        _endpoints.log_rejected("export_customers", reason="exceeds_limit")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed("export_customers")
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=customers.csv",
            },
        )


# =============================================================================
# Task 8.6: PUT /api/v1/customers/bulk/preferences - Bulk Update Preferences
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/bulk/preferences",
    response_model=BulkUpdateResponse,
    summary="Bulk update communication preferences",
    description="Update communication preferences for multiple customers at once.",
)
async def bulk_update_preferences(
    data: BulkPreferencesUpdate,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> BulkUpdateResponse:
    """Bulk update communication preferences.

    Args:
        data: BulkPreferencesUpdate with customer IDs and preference values
        service: Injected CustomerService

    Returns:
        BulkUpdateResponse with success/failure counts

    Raises:
        HTTPException: 400 if record count exceeds limit

    Validates: Requirement 12.3-12.5
    """
    _endpoints.log_started("bulk_update_preferences", count=len(data.customer_ids))

    try:
        result = await service.bulk_update_preferences(
            customer_ids=data.customer_ids,
            sms_opt_in=data.sms_opt_in,
            email_opt_in=data.email_opt_in,
        )
    except BulkOperationError as e:
        _endpoints.log_rejected("bulk_update_preferences", reason="exceeds_limit")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed(
            "bulk_update_preferences",
            updated_count=result["updated_count"],
            failed_count=result["failed_count"],
        )
        return BulkUpdateResponse(
            updated_count=result["updated_count"],
            failed_count=result["failed_count"],
            errors=result["errors"],
        )


# =============================================================================
# CRM Gap Closure 7.3: PATCH /api/v1/customers/{id} - Partial Update
# =============================================================================


@router.patch(  # type: ignore[untyped-decorator]
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Partially update customer",
    description="Partially update customer information including "
    "internal_notes and preferred_service_times.",
)
async def patch_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerResponse:
    """Partially update customer information.

    Supports updating internal_notes and preferred_service_times
    along with all other CustomerUpdate fields.

    Args:
        customer_id: UUID of the customer to update
        data: CustomerUpdate schema with fields to update
        service: Injected CustomerService

    Returns:
        CustomerResponse with updated customer data

    Raises:
        HTTPException: 404 if customer not found
        HTTPException: 400 if new phone number already exists

    Validates: CRM Gap Closure Req 8.4, 11.3
    """
    _endpoints.log_started("patch_customer", customer_id=str(customer_id))

    try:
        result = await service.update_customer(customer_id, data)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("patch_customer", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    except DuplicateCustomerError as e:
        _endpoints.log_rejected(
            "patch_customer",
            reason="duplicate_phone",
            existing_id=str(e.existing_id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phone number already in use by customer: {e.existing_id}",
        ) from e
    else:
        _endpoints.log_completed("patch_customer", customer_id=str(customer_id))
        return result


# =============================================================================
# CRM Gap Closure 7.3: POST /api/v1/customers/{id}/photos - Upload Photos
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{customer_id}/photos",
    response_model=CustomerPhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload customer photo",
    description="Upload a photo for a customer. Accepts JPEG, PNG, HEIC (max 10MB).",
)
async def upload_customer_photo(
    customer_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    photo_service: Annotated[PhotoService, Depends(get_photo_service)],
    file: Annotated[UploadFile, File(description="Photo file to upload")],
    caption: str | None = Query(
        default=None,
        max_length=500,
        description="Optional photo caption",
    ),
) -> CustomerPhotoResponse:
    """Upload a photo for a customer.

    Args:
        customer_id: UUID of the customer
        service: Injected CustomerService
        db: Async database session
        photo_service: Injected PhotoService
        file: Uploaded file
        caption: Optional caption

    Returns:
        CustomerPhotoResponse with photo metadata and download URL

    Raises:
        HTTPException: 404 if customer not found
        HTTPException: 400 if file validation fails

    Validates: CRM Gap Closure Req 9.2
    """
    from grins_platform.models.customer_photo import (  # noqa: PLC0415
        CustomerPhoto,
    )

    _endpoints.log_started(
        "upload_customer_photo",
        customer_id=str(customer_id),
        file_name=file.filename or "unknown",
    )

    # Verify customer exists
    try:
        await service.get_customer(customer_id, include_properties=False)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("upload_customer_photo", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e

    # Read file data
    file_data = await file.read()
    file_name = file.filename or "photo"

    # Upload via PhotoService
    try:
        upload_result = photo_service.upload_file(
            data=file_data,
            file_name=file_name,
            context=UploadContext.CUSTOMER_PHOTO,
        )
    except ValueError as e:
        _endpoints.log_rejected(
            "upload_customer_photo",
            reason="validation_failed",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Create DB record
    photo = CustomerPhoto(
        customer_id=customer_id,
        file_key=upload_result.file_key,
        file_name=upload_result.file_name,
        file_size=upload_result.file_size,
        content_type=upload_result.content_type,
        caption=caption,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)

    # Generate pre-signed URL
    download_url = photo_service.generate_presigned_url(photo.file_key)

    _endpoints.log_completed(
        "upload_customer_photo",
        customer_id=str(customer_id),
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


# =============================================================================
# CRM Gap Closure 7.3: GET /api/v1/customers/{id}/photos - List Photos
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{customer_id}/photos",
    response_model=list[CustomerPhotoResponse],
    summary="List customer photos",
    description="List all photos for a customer with pre-signed download URLs.",
)
async def list_customer_photos(
    customer_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    photo_service: Annotated[PhotoService, Depends(get_photo_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page",
    ),
) -> list[CustomerPhotoResponse]:
    """List photos for a customer with pre-signed download URLs.

    Args:
        customer_id: UUID of the customer
        service: Injected CustomerService
        db: Async database session
        photo_service: Injected PhotoService
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        List of CustomerPhotoResponse with download URLs

    Raises:
        HTTPException: 404 if customer not found

    Validates: CRM Gap Closure Req 9.3
    """
    from sqlalchemy import select  # noqa: PLC0415

    from grins_platform.models.customer_photo import (  # noqa: PLC0415
        CustomerPhoto,
    )

    _endpoints.log_started(
        "list_customer_photos",
        customer_id=str(customer_id),
    )

    # Verify customer exists
    try:
        await service.get_customer(customer_id, include_properties=False)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("list_customer_photos", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e

    # Query photos
    offset = (page - 1) * page_size
    stmt = (
        select(CustomerPhoto)
        .where(CustomerPhoto.customer_id == customer_id)
        .order_by(CustomerPhoto.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    photos = list(result.scalars().all())

    # Build responses with pre-signed URLs
    responses: list[CustomerPhotoResponse] = []
    for photo in photos:
        download_url = photo_service.generate_presigned_url(photo.file_key)
        responses.append(
            CustomerPhotoResponse(
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
            ),
        )

    _endpoints.log_completed(
        "list_customer_photos",
        customer_id=str(customer_id),
        count=len(responses),
    )
    return responses


# =============================================================================
# CRM Gap Closure 7.3: DELETE /api/v1/customers/{id}/photos/{photo_id}
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{customer_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer photo",
    description="Delete a customer photo from S3 and the database.",
)
async def delete_customer_photo(
    customer_id: UUID,
    photo_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    photo_service: Annotated[PhotoService, Depends(get_photo_service)],
) -> None:
    """Delete a customer photo.

    Args:
        customer_id: UUID of the customer
        photo_id: UUID of the photo to delete
        service: Injected CustomerService
        db: Async database session
        photo_service: Injected PhotoService

    Raises:
        HTTPException: 404 if customer or photo not found

    Validates: CRM Gap Closure Req 9.4
    """
    from sqlalchemy import select  # noqa: PLC0415

    from grins_platform.models.customer_photo import (  # noqa: PLC0415
        CustomerPhoto,
    )

    _endpoints.log_started(
        "delete_customer_photo",
        customer_id=str(customer_id),
        photo_id=str(photo_id),
    )

    # Verify customer exists
    try:
        await service.get_customer(customer_id, include_properties=False)
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("delete_customer_photo", reason="customer_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e

    # Find photo
    stmt = select(CustomerPhoto).where(
        CustomerPhoto.id == photo_id,
        CustomerPhoto.customer_id == customer_id,
    )
    result = await db.execute(stmt)
    photo = result.scalar_one_or_none()

    if not photo:
        _endpoints.log_rejected("delete_customer_photo", reason="photo_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photo not found: {photo_id}",
        )

    # Delete from S3
    try:
        photo_service.delete_file(photo.file_key)
    except Exception as e:
        _endpoints.log_failed(
            "delete_customer_photo",
            error=e,
            file_key=photo.file_key,
        )
        # Continue with DB deletion even if S3 fails

    # Delete from DB
    await db.delete(photo)
    await db.flush()

    _endpoints.log_completed(
        "delete_customer_photo",
        customer_id=str(customer_id),
        photo_id=str(photo_id),
    )


# =============================================================================
# CRM Gap Closure 7.3: GET /api/v1/customers/{id}/invoices
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{customer_id}/invoices",
    summary="Get customer invoice history",
    description="Get paginated invoice history for a customer, "
    "sorted by date descending.",
)
async def get_customer_invoices(
    customer_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page",
    ),
) -> dict[str, Any]:
    """Get customer invoice history.

    Args:
        customer_id: UUID of the customer
        service: Injected CustomerService
        db: Async database session
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Paginated invoice response

    Raises:
        HTTPException: 404 if customer not found

    Validates: CRM Gap Closure Req 10.3
    """
    _endpoints.log_started(
        "get_customer_invoices",
        customer_id=str(customer_id),
        page=page,
    )

    try:
        result = await service.get_customer_invoices(
            db=db,
            customer_id=customer_id,
            page=page,
            page_size=page_size,
        )
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("get_customer_invoices", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    else:
        _endpoints.log_completed(
            "get_customer_invoices",
            customer_id=str(customer_id),
            count=len(result["items"]),
        )
        return result


# =============================================================================
# CRM Gap Closure 7.3: GET /api/v1/customers/{id}/payment-methods
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{customer_id}/payment-methods",
    response_model=list[PaymentMethodResponse],
    summary="Get customer payment methods",
    description="List Stripe saved payment methods for a customer.",
)
async def get_payment_methods(
    customer_id: UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[PaymentMethodResponse]:
    """Get Stripe saved payment methods for a customer.

    Args:
        customer_id: UUID of the customer
        service: Injected CustomerService
        db: Async database session

    Returns:
        List of PaymentMethodResponse

    Raises:
        HTTPException: 404 if customer not found

    Validates: CRM Gap Closure Req 56.2
    """
    _endpoints.log_started(
        "get_payment_methods",
        customer_id=str(customer_id),
    )

    try:
        result = await service.get_payment_methods(
            db=db,
            customer_id=customer_id,
        )
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("get_payment_methods", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    else:
        _endpoints.log_completed(
            "get_payment_methods",
            customer_id=str(customer_id),
            count=len(result),
        )
        return result


# =============================================================================
# CRM Gap Closure 7.3: POST /api/v1/customers/{id}/charge
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{customer_id}/charge",
    response_model=ChargeResponse,
    summary="Charge customer's saved card",
    description="Create a Stripe PaymentIntent using the customer's "
    "default payment method on file.",
)
async def charge_customer(
    customer_id: UUID,
    data: ChargeRequest,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChargeResponse:
    """Charge a customer's saved payment method.

    Args:
        customer_id: UUID of the customer
        data: ChargeRequest with amount and description
        service: Injected CustomerService
        db: Async database session

    Returns:
        ChargeResponse with payment intent details

    Raises:
        HTTPException: 404 if customer not found
        HTTPException: 409 if no payment method or charge fails

    Validates: CRM Gap Closure Req 56.3
    """
    _endpoints.log_started(
        "charge_customer",
        customer_id=str(customer_id),
        amount=data.amount,
    )

    try:
        result = await service.charge_customer(
            db=db,
            customer_id=customer_id,
            amount=data.amount,
            description=data.description,
            invoice_id=data.invoice_id,
        )
    except CustomerNotFoundError as e:
        _endpoints.log_rejected("charge_customer", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {e.customer_id}",
        ) from e
    except MergeConflictError as e:
        _endpoints.log_rejected("charge_customer", reason="payment_error")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed(
            "charge_customer",
            customer_id=str(customer_id),
            payment_intent_id=result.payment_intent_id,
        )
        return result


# =============================================================================
# Customer Sent Messages — Req 82
# =============================================================================


@router.get(
    "/{customer_id}/sent-messages",
    summary="Get customer sent messages",
    description="Get outbound messages sent to a specific customer.",
)
async def get_customer_sent_messages(
    customer_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> dict[str, object]:
    """Get outbound messages for a specific customer.

    Validates: CRM Gap Closure Req 82.3
    """
    from grins_platform.repositories.sent_message_repository import (  # noqa: PLC0415
        SentMessageRepository,
    )
    from grins_platform.schemas.sent_message import (  # noqa: PLC0415
        SentMessageResponse,
    )

    _endpoints.log_started(
        "get_customer_sent_messages",
        customer_id=str(customer_id),
    )

    repo = SentMessageRepository(db)
    messages, total = await repo.list_with_filters(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
    )

    items = [SentMessageResponse.model_validate(m) for m in messages]
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    _endpoints.log_completed(
        "get_customer_sent_messages",
        customer_id=str(customer_id),
        count=len(items),
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
