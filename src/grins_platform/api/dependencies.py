"""
FastAPI dependency injection for services and repositories.

This module provides dependency functions for injecting services
and repositories into API endpoints.

Validates: Requirement 10.5-10.7
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.database import get_db_session
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.property_service import PropertyService


async def get_customer_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AsyncGenerator[CustomerRepository, None]:
    """Get CustomerRepository instance with database session.

    Args:
        session: Database session from dependency injection

    Yields:
        CustomerRepository instance
    """
    yield CustomerRepository(session)


async def get_property_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AsyncGenerator[PropertyRepository, None]:
    """Get PropertyRepository instance with database session.

    Args:
        session: Database session from dependency injection

    Yields:
        PropertyRepository instance
    """
    yield PropertyRepository(session)


async def get_customer_service(
    repository: Annotated[CustomerRepository, Depends(get_customer_repository)],
) -> AsyncGenerator[CustomerService, None]:
    """Get CustomerService instance with repository.

    Args:
        repository: CustomerRepository from dependency injection

    Yields:
        CustomerService instance
    """
    yield CustomerService(repository)


async def get_property_service(
    repository: Annotated[PropertyRepository, Depends(get_property_repository)],
) -> AsyncGenerator[PropertyService, None]:
    """Get PropertyService instance with repository.

    Args:
        repository: PropertyRepository from dependency injection

    Yields:
        PropertyService instance
    """
    yield PropertyService(repository)


# Type aliases for cleaner endpoint signatures
CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]
PropertyServiceDep = Annotated[PropertyService, Depends(get_property_service)]
