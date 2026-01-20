"""
FastAPI dependency injection for API v1.

This module provides dependency injection functions for services
and other shared resources used by API endpoints.

Validates: Requirement 10.5-10.7
"""

from __future__ import annotations

from collections.abc import (
    AsyncGenerator,  # noqa: TC003 - Required at runtime for FastAPI
)
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI
)

from grins_platform.database import get_db_session as db_session_generator
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.property_service import PropertyService
from grins_platform.services.service_offering_service import ServiceOfferingService
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


__all__ = [
    "get_customer_service",
    "get_db_session",
    "get_property_service",
    "get_service_offering_service",
    "get_staff_service",
]
