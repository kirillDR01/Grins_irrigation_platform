"""
FastAPI dependency injection for API v1.

This module provides dependency injection functions for services
and other shared resources used by API endpoints.

Validates: Requirement 10.5-10.7
"""

from __future__ import annotations

from collections.abc import (
    AsyncGenerator,
)
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI
)

from grins_platform.database import get_db_session as db_session_generator
from grins_platform.repositories.appointment_repository import AppointmentRepository
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.services.appointment_service import AppointmentService
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.dashboard_service import DashboardService
from grins_platform.services.job_service import JobService
from grins_platform.services.property_service import PropertyService
from grins_platform.services.service_offering_service import ServiceOfferingService
from grins_platform.services.staff_availability_service import StaffAvailabilityService
from grins_platform.services.staff_service import StaffService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency.

    Yields:
        AsyncSession for database operations
    """
    async for session in db_session_generator():
        yield session


async def get_customer_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerService:
    """Get CustomerService dependency.

    This creates a CustomerService with a CustomerRepository using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        CustomerService instance
    """
    repository = CustomerRepository(session=session)
    return CustomerService(repository=repository)


async def get_property_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PropertyService:
    """Get PropertyService dependency.

    This creates a PropertyService with a PropertyRepository using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        PropertyService instance
    """
    repository = PropertyRepository(session=session)
    return PropertyService(repository=repository)


async def get_service_offering_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceOfferingService:
    """Get ServiceOfferingService dependency.

    This creates a ServiceOfferingService with a ServiceOfferingRepository using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        ServiceOfferingService instance
    """
    repository = ServiceOfferingRepository(session=session)
    return ServiceOfferingService(repository=repository)


async def get_staff_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffService:
    """Get StaffService dependency.

    This creates a StaffService with a StaffRepository using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        StaffService instance
    """
    repository = StaffRepository(session=session)
    return StaffService(repository=repository)


async def get_job_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobService:
    """Get JobService dependency.

    This creates a JobService with all required repositories using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        JobService instance
    """
    job_repository = JobRepository(session=session)
    customer_repository = CustomerRepository(session=session)
    property_repository = PropertyRepository(session=session)
    service_repository = ServiceOfferingRepository(session=session)
    return JobService(
        job_repository=job_repository,
        customer_repository=customer_repository,
        property_repository=property_repository,
        service_repository=service_repository,
    )


async def get_appointment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AppointmentService:
    """Get AppointmentService dependency.

    This creates an AppointmentService with all required repositories using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        AppointmentService instance
    """
    appointment_repository = AppointmentRepository(session=session)
    job_repository = JobRepository(session=session)
    staff_repository = StaffRepository(session=session)
    return AppointmentService(
        appointment_repository=appointment_repository,
        job_repository=job_repository,
        staff_repository=staff_repository,
    )


async def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardService:
    """Get DashboardService dependency.

    This creates a DashboardService with all required repositories using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        DashboardService instance
    """
    customer_repository = CustomerRepository(session=session)
    job_repository = JobRepository(session=session)
    staff_repository = StaffRepository(session=session)
    appointment_repository = AppointmentRepository(session=session)
    return DashboardService(
        customer_repository=customer_repository,
        job_repository=job_repository,
        staff_repository=staff_repository,
        appointment_repository=appointment_repository,
    )


async def get_staff_availability_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffAvailabilityService:
    """Get StaffAvailabilityService dependency.

    This creates a StaffAvailabilityService using the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        StaffAvailabilityService instance
    """
    return StaffAvailabilityService(session=session)


__all__ = [
    "get_appointment_service",
    "get_customer_service",
    "get_dashboard_service",
    "get_db_session",
    "get_job_service",
    "get_property_service",
    "get_service_offering_service",
    "get_staff_availability_service",
    "get_staff_service",
]
