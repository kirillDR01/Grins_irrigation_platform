"""
Pydantic schemas for the Grin's Irrigation Platform.

This module exports all schema classes for request/response validation
and serialization in the API layer.

Phase 1: Customer Management schemas
Phase 2: Field Operations schemas (Service Offerings, Jobs, Staff)
Phase 3: Admin Dashboard schemas (Appointments, Dashboard Metrics)
"""

from grins_platform.schemas.appointment import (
    AppointmentCreate,
    AppointmentListParams,
    AppointmentPaginatedResponse,
    AppointmentResponse,
    AppointmentUpdate,
    DailyScheduleResponse,
    StaffDailyScheduleResponse,
    WeeklyScheduleResponse,
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
from grins_platform.schemas.dashboard import (
    DashboardMetrics,
    JobsByStatusResponse,
    PaymentStatusOverview,
    RecentActivityItem,
    RecentActivityResponse,
    RequestVolumeMetrics,
    ScheduleOverview,
    TodayScheduleResponse,
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
    "AppointmentCreate",
    "AppointmentListParams",
    "AppointmentPaginatedResponse",
    "AppointmentResponse",
    "AppointmentUpdate",
    "BulkPreferencesUpdate",
    "BulkUpdateResponse",
    "CustomerCreate",
    "CustomerDetailResponse",
    "CustomerFlagsUpdate",
    "CustomerListParams",
    "CustomerResponse",
    "CustomerUpdate",
    "DailyScheduleResponse",
    "DashboardMetrics",
    "JobCreate",
    "JobDetailResponse",
    "JobListParams",
    "JobResponse",
    "JobStatusHistoryResponse",
    "JobStatusUpdate",
    "JobUpdate",
    "JobsByStatusResponse",
    "PaginatedCustomerResponse",
    "PaginatedJobResponse",
    "PaginatedServiceResponse",
    "PaginatedStaffResponse",
    "PaymentStatusOverview",
    "PriceCalculationResponse",
    "PropertyCreate",
    "PropertyResponse",
    "PropertyUpdate",
    "RecentActivityItem",
    "RecentActivityResponse",
    "RequestVolumeMetrics",
    "ScheduleOverview",
    "ServiceHistorySummary",
    "ServiceListParams",
    "ServiceOfferingCreate",
    "ServiceOfferingResponse",
    "ServiceOfferingUpdate",
    "StaffAvailabilityUpdate",
    "StaffCreate",
    "StaffDailyScheduleResponse",
    "StaffListParams",
    "StaffResponse",
    "StaffUpdate",
    "TodayScheduleResponse",
    "WeeklyScheduleResponse",
]
