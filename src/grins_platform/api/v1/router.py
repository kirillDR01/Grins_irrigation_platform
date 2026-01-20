"""
API v1 router configuration.

This module sets up the main API v1 router and includes all sub-routers.

Validates: Requirement 10.5-10.7
"""

from fastapi import APIRouter

from grins_platform.api.v1.customers import router as customers_router
from grins_platform.api.v1.jobs import router as jobs_router
from grins_platform.api.v1.properties import router as properties_router
from grins_platform.api.v1.services import router as services_router
from grins_platform.api.v1.staff import router as staff_router

api_router = APIRouter(prefix="/api/v1")

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

# Include job endpoints
api_router.include_router(
    jobs_router,
    prefix="/jobs",
    tags=["jobs"],
)

__all__ = ["api_router"]
