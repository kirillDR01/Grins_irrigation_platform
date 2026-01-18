"""
Property API endpoints.

This module provides REST API endpoints for property management including
CRUD operations and primary flag management.

Validates: Requirement 2.1-2.11
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID  # noqa: TC003 - Required at runtime for FastAPI path params

from fastapi import APIRouter, Depends, HTTPException, status

from grins_platform.api.v1.dependencies import get_property_service
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.property import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
)
from grins_platform.services.property_service import (
    PropertyNotFoundError,
    PropertyService,
)

router = APIRouter()


class PropertyEndpoints(LoggerMixin):
    """Property API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = PropertyEndpoints()


# =============================================================================
# Task 9.1: POST /api/v1/customers/{customer_id}/properties - Add Property
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/customers/{customer_id}/properties",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add property to customer",
    description="Add a new property to a customer. If marked as primary or "
    "if this is the first property, it will be set as the primary property.",
)
async def add_property(
    customer_id: UUID,
    data: PropertyCreate,
    service: Annotated[PropertyService, Depends(get_property_service)],
) -> PropertyResponse:
    """Add a property to a customer.

    Args:
        customer_id: UUID of the customer
        data: PropertyCreate schema with property information
        service: Injected PropertyService

    Returns:
        PropertyResponse with created property data

    Validates: Requirement 2.1, 2.7-2.11
    """
    _endpoints.log_started(
        "add_property",
        customer_id=str(customer_id),
        city=data.city,
    )

    result = await service.add_property(customer_id, data)

    _endpoints.log_completed(
        "add_property",
        property_id=str(result.id),
        customer_id=str(customer_id),
    )
    return result


# =============================================================================
# Task 9.2: GET /api/v1/customers/{customer_id}/properties - List Properties
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/customers/{customer_id}/properties",
    response_model=list[PropertyResponse],
    summary="List customer properties",
    description="List all properties for a customer, ordered by primary flag "
    "and creation date.",
)
async def list_customer_properties(
    customer_id: UUID,
    service: Annotated[PropertyService, Depends(get_property_service)],
) -> list[PropertyResponse]:
    """List all properties for a customer.

    Args:
        customer_id: UUID of the customer
        service: Injected PropertyService

    Returns:
        List of PropertyResponse objects

    Validates: Requirement 2.5
    """
    _endpoints.log_started("list_customer_properties", customer_id=str(customer_id))

    result = await service.get_customer_properties(customer_id)

    _endpoints.log_completed(
        "list_customer_properties",
        customer_id=str(customer_id),
        count=len(result),
    )
    return result


# =============================================================================
# Task 9.3: GET /api/v1/properties/{id} - Get Property
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/properties/{property_id}",
    response_model=PropertyResponse,
    summary="Get property by ID",
    description="Retrieve a property by its unique identifier.",
)
async def get_property(
    property_id: UUID,
    service: Annotated[PropertyService, Depends(get_property_service)],
) -> PropertyResponse:
    """Get property by ID.

    Args:
        property_id: UUID of the property
        service: Injected PropertyService

    Returns:
        PropertyResponse with property data

    Raises:
        HTTPException: 404 if property not found

    Validates: Requirement 2.5
    """
    _endpoints.log_started("get_property", property_id=str(property_id))

    try:
        result = await service.get_property(property_id)
    except PropertyNotFoundError as e:
        _endpoints.log_rejected("get_property", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property not found: {e.property_id}",
        ) from e
    else:
        _endpoints.log_completed("get_property", property_id=str(property_id))
        return result


# =============================================================================
# Task 9.4: PUT /api/v1/properties/{id} - Update Property
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/properties/{property_id}",
    response_model=PropertyResponse,
    summary="Update property",
    description="Update property information. Only provided fields will be updated.",
)
async def update_property(
    property_id: UUID,
    data: PropertyUpdate,
    service: Annotated[PropertyService, Depends(get_property_service)],
) -> PropertyResponse:
    """Update property information.

    Args:
        property_id: UUID of the property to update
        data: PropertyUpdate schema with fields to update
        service: Injected PropertyService

    Returns:
        PropertyResponse with updated property data

    Raises:
        HTTPException: 404 if property not found

    Validates: Requirement 2.2-2.4, 2.8-2.11
    """
    _endpoints.log_started("update_property", property_id=str(property_id))

    try:
        result = await service.update_property(property_id, data)
    except PropertyNotFoundError as e:
        _endpoints.log_rejected("update_property", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property not found: {e.property_id}",
        ) from e
    else:
        _endpoints.log_completed("update_property", property_id=str(property_id))
        return result


# =============================================================================
# Task 9.5: DELETE /api/v1/properties/{id} - Delete Property
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/properties/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete property",
    description="Delete a property. If the deleted property was primary, "
    "another property will be automatically set as primary.",
)
async def delete_property(
    property_id: UUID,
    service: Annotated[PropertyService, Depends(get_property_service)],
) -> None:
    """Delete a property.

    Args:
        property_id: UUID of the property to delete
        service: Injected PropertyService

    Raises:
        HTTPException: 404 if property not found

    Validates: Requirement 2.6
    """
    _endpoints.log_started("delete_property", property_id=str(property_id))

    try:
        await service.delete_property(property_id)
    except PropertyNotFoundError as e:
        _endpoints.log_rejected("delete_property", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property not found: {e.property_id}",
        ) from e
    else:
        _endpoints.log_completed("delete_property", property_id=str(property_id))


# =============================================================================
# Task 9.6: PUT /api/v1/properties/{id}/primary - Set Primary
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/properties/{property_id}/primary",
    response_model=PropertyResponse,
    summary="Set property as primary",
    description="Set a property as the primary property for its customer. "
    "This will clear the primary flag from all other properties of the same customer.",
)
async def set_primary_property(
    property_id: UUID,
    service: Annotated[PropertyService, Depends(get_property_service)],
) -> PropertyResponse:
    """Set property as primary.

    Args:
        property_id: UUID of the property to set as primary
        service: Injected PropertyService

    Returns:
        PropertyResponse with updated property data

    Raises:
        HTTPException: 404 if property not found

    Validates: Requirement 2.7
    """
    _endpoints.log_started("set_primary_property", property_id=str(property_id))

    try:
        result = await service.set_primary(property_id)
    except PropertyNotFoundError as e:
        _endpoints.log_rejected("set_primary_property", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property not found: {e.property_id}",
        ) from e
    else:
        _endpoints.log_completed("set_primary_property", property_id=str(property_id))
        return result
