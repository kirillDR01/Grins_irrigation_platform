"""
Custom exceptions for the Grin's Irrigation Platform.

This module defines custom exception classes for handling business logic
errors, validation failures, and resource not found scenarios.

Validates: Requirement 6.1-6.5, 10.2-10.4
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID


class CustomerError(Exception):
    """Base exception for customer operations.

    All customer-related exceptions inherit from this class.
    """



class CustomerNotFoundError(CustomerError):
    """Raised when a customer is not found.

    Validates: Requirement 10.3
    """

    def __init__(self, customer_id: UUID) -> None:
        """Initialize with customer ID.

        Args:
            customer_id: UUID of the customer that was not found
        """
        self.customer_id = customer_id
        super().__init__(f"Customer not found: {customer_id}")


class DuplicateCustomerError(CustomerError):
    """Raised when attempting to create a customer with duplicate phone.

    Validates: Requirement 6.6
    """

    def __init__(self, existing_id: UUID, phone: str | None = None) -> None:
        """Initialize with existing customer ID.

        Args:
            existing_id: UUID of the existing customer with the same phone
            phone: The duplicate phone number (optional, for logging)
        """
        self.existing_id = existing_id
        self.phone = phone
        super().__init__(f"Customer already exists with ID: {existing_id}")


class PropertyNotFoundError(CustomerError):
    """Raised when a property is not found.

    Validates: Requirement 10.3
    """

    def __init__(self, property_id: UUID) -> None:
        """Initialize with property ID.

        Args:
            property_id: UUID of the property that was not found
        """
        self.property_id = property_id
        super().__init__(f"Property not found: {property_id}")


class ValidationError(CustomerError):
    """Raised when validation fails.

    Validates: Requirement 10.2
    """

    def __init__(
        self,
        field: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize with validation error details.

        Args:
            field: The field that failed validation
            message: Description of the validation error
            details: Additional error details (optional)
        """
        self.field = field
        self.message = message
        self.details = details or {}
        super().__init__(f"Validation error on {field}: {message}")


class BulkOperationError(CustomerError):
    """Raised when a bulk operation fails or exceeds limits.

    Validates: Requirement 12.4
    """

    def __init__(
        self,
        message: str,
        record_count: int | None = None,
        max_allowed: int | None = None,
    ) -> None:
        """Initialize with bulk operation error details.

        Args:
            message: Description of the error
            record_count: Number of records attempted
            max_allowed: Maximum allowed records
        """
        self.record_count = record_count
        self.max_allowed = max_allowed
        super().__init__(message)


__all__ = [
    "BulkOperationError",
    "CustomerError",
    "CustomerNotFoundError",
    "DuplicateCustomerError",
    "PropertyNotFoundError",
    "ValidationError",
]
