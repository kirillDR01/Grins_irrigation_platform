"""
API v1 router configuration.

This module sets up the main API v1 router and includes all sub-routers.

Validates: Requirement 10.5-10.7
"""

from fastapi import APIRouter

from grins_platform.api.v1.ai import router as ai_router
from grins_platform.api.v1.appointments import router as appointments_router
from grins_platform.api.v1.auth import router as auth_router
from grins_platform.api.v1.conflict_resolution import router as conflict_router
from grins_platform.api.v1.customers import router as customers_router
from grins_platform.api.v1.dashboard import router as dashboard_router
from grins_platform.api.v1.invoices import router as invoices_router
from grins_platform.api.v1.jobs import router as jobs_router
from grins_platform.api.v1.leads import router as leads_router
from grins_platform.api.v1.properties import router as properties_router
from grins_platform.api.v1.schedule import router as schedule_router
from grins_platform.api.v1.schedule_clear import router as schedule_clear_router
from grins_platform.api.v1.services import router as services_router
from grins_platform.api.v1.sms import (
    communications_router,
    router as sms_router,
)
from grins_platform.api.v1.staff import router as staff_router
from grins_platform.api.v1.staff_availability import router as staff_availability_router
from grins_platform.api.v1.staff_reassignment import router as reassignment_router

api_router = APIRouter(prefix="/api/v1")

# Include authentication endpoints
api_router.include_router(auth_router)

# Include customer endpoints
api_router.include_router(
    customers_router,
    prefix="/customers",
    tags=["customers"],
)

# Include property endpoints (note: some routes are under /customers/{id}/properties)
api_router.include_router(
    properties_router,
    tags=["properties"],
)

# Include service offering endpoints
api_router.include_router(
    services_router,
    prefix="/services",
    tags=["services"],
)

# Include staff endpoints
api_router.include_router(
    staff_router,
    prefix="/staff",
    tags=["staff"],
)

# Include staff availability endpoints
api_router.include_router(
    staff_availability_router,
    prefix="/staff",
    tags=["staff-availability"],
)

# Include job endpoints
api_router.include_router(
    jobs_router,
    prefix="/jobs",
    tags=["jobs"],
)

# Include lead endpoints
api_router.include_router(
    leads_router,
    prefix="/leads",
    tags=["leads"],
)

# Include appointment endpoints
api_router.include_router(
    appointments_router,
    prefix="/appointments",
    tags=["appointments"],
)

# Include dashboard endpoints
api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["dashboard"],
)

# Include schedule generation endpoints
api_router.include_router(
    schedule_router,
    tags=["schedule"],
)

# Include schedule clear endpoints
api_router.include_router(
    schedule_clear_router,
    tags=["schedule-clear"],
)

# Include invoice endpoints
api_router.include_router(
    invoices_router,
    tags=["invoices"],
)

# Include conflict resolution endpoints
api_router.include_router(
    conflict_router,
    tags=["conflict-resolution"],
)

# Include staff reassignment endpoints
api_router.include_router(
    reassignment_router,
    tags=["staff-reassignment"],
)

# Include AI assistant endpoints
api_router.include_router(
    ai_router,
    tags=["ai-assistant"],
)

# Include SMS endpoints
api_router.include_router(
    sms_router,
    tags=["sms"],
)

# Include Communications endpoints
api_router.include_router(
    communications_router,
    tags=["communications"],
)

__all__ = ["api_router"]
