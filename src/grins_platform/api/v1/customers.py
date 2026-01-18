"""
Customer API endpoints.

This module provides REST API endpoints for customer management including
CRUD operations, lookups, flag management, and bulk operations.

Validates: Requirement 1.1-1.6, 3.1-3.6, 4.1-4.7, 6.6, 10.1-10.7, 11.1-11.6, 12.1-12.5
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID  # noqa: TC003 - Required at runtime for FastAPI path params

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from grins_platform.api.v1.dependencies import get_customer_service
from grins_platform.exceptions import (
    BulkOperationError,
    CustomerNotFoundError,
    DuplicateCustomerError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    CustomerStatus,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.schemas.customer import (
    BulkPreferencesUpdate,
    BulkUpdateResponse,
    CustomerCreate,
    CustomerDetailResponse,
    CustomerFlagsUpdate,
    CustomerListParams,
    CustomerResponse,
    CustomerUpdate,
    PaginatedCustomerResponse,
    ServiceHistorySummary,
)
from grins_platform.services.customer_service import (
    CustomerService,  # noqa: TC001 - Required at runtime for FastAPI DI
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
