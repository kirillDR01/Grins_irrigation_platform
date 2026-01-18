"""
Pydantic schemas for the Grin's Irrigation Platform.

This module exports all schema classes for request/response validation
and serialization in the API layer.
"""

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
from grins_platform.schemas.property import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
)

__all__ = [
    "BulkPreferencesUpdate",
    "BulkUpdateResponse",
    "CustomerCreate",
    "CustomerDetailResponse",
    "CustomerFlagsUpdate",
    "CustomerListParams",
    "CustomerResponse",
    "CustomerUpdate",
    "PaginatedCustomerResponse",
    "PropertyCreate",
    "PropertyResponse",
    "PropertyUpdate",
    "ServiceHistorySummary",
]
