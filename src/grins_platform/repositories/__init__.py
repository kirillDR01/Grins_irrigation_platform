"""
Repository layer for database operations.

This module provides repository classes for data access operations,
following the repository pattern for clean separation of concerns.
"""

from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.property_repository import PropertyRepository

__all__ = [
    "CustomerRepository",
    "PropertyRepository",
]
