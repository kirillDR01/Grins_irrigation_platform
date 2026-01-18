"""
API v1 router configuration.

This module sets up the main API v1 router and includes all sub-routers.

Validates: Requirement 10.5-10.7
"""

from fastapi import APIRouter

from grins_platform.api.v1.customers import router as customers_router

api_router = APIRouter(prefix="/api/v1")

# Include customer endpoints
api_router.include_router(
    customers_router,
    prefix="/customers",
    tags=["customers"],
)

__all__ = ["api_router"]
