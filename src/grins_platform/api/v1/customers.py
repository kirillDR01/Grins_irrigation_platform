"""
Customer API endpoints.

This module provides REST API endpoints for customer management including
CRUD operations, lookups, flag management, and bulk operations.

Validates: Requirement 1.1-1.6, 3.1-3.6, 4.1-4.7, 6.6, 10.1-10.7, 11.1-11.6, 12.1-12.5
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID  # noqa: TC003 - Required at runtime for FastAPI path params

from fastapi import APIRouter, Depends, HTTPException, Query, status

from grins_platform.api.v1.dependencies import get_customer_service
from grins_platform.exceptions import (
    CustomerNotFoundError,
    DuplicateCustomerError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    CustomerStatus,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.schemas.customer import (
    CustomerCreate,
    CustomerDetailResponse,
    CustomerFlagsUpdate,
    CustomerListParams,
    CustomerResponse,
    CustomerUpdate,
    PaginatedCustomerResponse,
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
