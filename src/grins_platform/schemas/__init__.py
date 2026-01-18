"""
Pydantic schemas for the Grin's Irrigation Platform.

This module exports all schema classes for request/response validation
and serialization in the API layer.

Phase 1: Customer Management schemas
Phase 2: Field Operations schemas (Service Offerings, Jobs, Staff)
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
from grins_platform.schemas.job import (
    JobCreate,
    JobDetailResponse,
    JobListParams,
    JobResponse,
    JobStatusHistoryResponse,
    JobStatusUpdate,
    JobUpdate,
    PaginatedJobResponse,
    PriceCalculationResponse,
)
from grins_platform.schemas.property import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
)
from grins_platform.schemas.service_offering import (
    PaginatedServiceResponse,
    ServiceListParams,
    ServiceOfferingCreate,
    ServiceOfferingResponse,
    ServiceOfferingUpdate,
)
from grins_platform.schemas.staff import (
    PaginatedStaffResponse,
    StaffAvailabilityUpdate,
    StaffCreate,
    StaffListParams,
    StaffResponse,
    StaffUpdate,
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
    "JobCreate",
    "JobDetailResponse",
    "JobListParams",
    "JobResponse",
    "JobStatusHistoryResponse",
    "JobStatusUpdate",
    "JobUpdate",
    "PaginatedCustomerResponse",
    "PaginatedJobResponse",
    "PaginatedServiceResponse",
    "PaginatedStaffResponse",
    "PriceCalculationResponse",
    "PropertyCreate",
    "PropertyResponse",
    "PropertyUpdate",
    "ServiceHistorySummary",
    "ServiceListParams",
    "ServiceOfferingCreate",
    "ServiceOfferingResponse",
    "ServiceOfferingUpdate",
    "StaffAvailabilityUpdate",
    "StaffCreate",
    "StaffListParams",
    "StaffResponse",
    "StaffUpdate",
]
