"""
FastAPI dependency injection for API v1.

This module provides dependency injection functions for services
and other shared resources used by API endpoints.

Validates: Requirement 10.5-10.7
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from grins_platform.database import get_db_session as db_session_generator
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.services.customer_service import CustomerService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession


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


__all__ = [
    "get_customer_service",
    "get_db_session",
]
