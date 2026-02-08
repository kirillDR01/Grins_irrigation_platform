"""
Custom exceptions for the Grin's Irrigation Platform.

This module defines custom exception classes for handling business logic
errors, validation failures, and resource not found scenarios.

Validates: Requirement 6.1-6.5, 10.2-10.4
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Import authentication exceptions
from grins_platform.exceptions.auth import (
    AccountLockedError,
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.enums import AppointmentStatus, JobStatus, LeadStatus


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


# ============================================================================
# Field Operations Exceptions (Phase 2)
# ============================================================================


class FieldOperationsError(Exception):
    """Base exception for field operations.

    All field operations-related exceptions inherit from this class.

    Validates: Requirement 10.1-10.5
    """


class ServiceOfferingNotFoundError(FieldOperationsError):
    """Raised when a service offering is not found.

    Validates: Requirement 10.10
    """

    def __init__(self, service_id: UUID) -> None:
        """Initialize with service offering ID.

        Args:
            service_id: UUID of the service offering that was not found
        """
        self.service_id = service_id
        super().__init__(f"Service offering not found: {service_id}")


class JobNotFoundError(FieldOperationsError):
    """Raised when a job is not found.

    Validates: Requirement 10.8
    """

    def __init__(self, job_id: UUID) -> None:
        """Initialize with job ID.

        Args:
            job_id: UUID of the job that was not found
        """
        self.job_id = job_id
        super().__init__(f"Job not found: {job_id}")


class InvalidStatusTransitionError(FieldOperationsError):
    """Raised when an invalid job/appointment status transition is attempted.

    Validates: Requirement 4.10, Admin Dashboard Requirement 1.2
    """

    def __init__(
        self,
        current_status: JobStatus | AppointmentStatus,
        requested_status: JobStatus | AppointmentStatus,
    ) -> None:
        """Initialize with status transition details.

        Args:
            current_status: The current status
            requested_status: The requested new status
        """
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Invalid status transition from {current_status.value} "
            f"to {requested_status.value}",
        )


class StaffNotFoundError(FieldOperationsError):
    """Raised when a staff member is not found.

    Validates: Requirement 8.4
    """

    def __init__(self, staff_id: UUID) -> None:
        """Initialize with staff ID.

        Args:
            staff_id: UUID of the staff member that was not found
        """
        self.staff_id = staff_id
        super().__init__(f"Staff member not found: {staff_id}")


class StaffAvailabilityNotFoundError(FieldOperationsError):
    """Raised when a staff availability entry is not found.

    Validates: Route Optimization Requirement 1.2
    """

    def __init__(self, availability_id: UUID | str) -> None:
        """Initialize with availability ID or message.

        Args:
            availability_id: UUID of the availability entry or error message
        """
        self.availability_id = availability_id
        if isinstance(availability_id, str):
            super().__init__(availability_id)
        else:
            super().__init__(f"Staff availability not found: {availability_id}")


class AppointmentNotFoundError(FieldOperationsError):
    """Raised when an appointment is not found.

    Validates: Admin Dashboard Requirement 1.3
    """

    def __init__(self, appointment_id: UUID) -> None:
        """Initialize with appointment ID.

        Args:
            appointment_id: UUID of the appointment that was not found
        """
        self.appointment_id = appointment_id
        super().__init__(f"Appointment not found: {appointment_id}")


class PropertyCustomerMismatchError(FieldOperationsError):
    """Raised when a property does not belong to the specified customer.

    Validates: Requirement 10.9
    """

    def __init__(self, property_id: UUID, customer_id: UUID) -> None:
        """Initialize with property and customer IDs.

        Args:
            property_id: UUID of the property
            customer_id: UUID of the customer
        """
        self.property_id = property_id
        self.customer_id = customer_id
        super().__init__(
            f"Property {property_id} does not belong to customer {customer_id}",
        )


class ServiceOfferingInactiveError(FieldOperationsError):
    """Raised when attempting to use an inactive service offering.

    Validates: Requirement 10.10
    """

    def __init__(self, service_id: UUID) -> None:
        """Initialize with service offering ID.

        Args:
            service_id: UUID of the inactive service offering
        """
        self.service_id = service_id
        super().__init__(f"Service offering is inactive: {service_id}")


# ============================================================================
# Schedule Clear Exceptions (Phase 8)
# ============================================================================


class ScheduleClearAuditNotFoundError(FieldOperationsError):
    """Raised when a schedule clear audit record is not found.

    Validates: Requirement 22.3
    """

    def __init__(self, audit_id: UUID) -> None:
        """Initialize with audit ID.

        Args:
            audit_id: UUID of the audit record that was not found
        """
        self.audit_id = audit_id
        super().__init__(f"Schedule clear audit not found: {audit_id}")


# ============================================================================
# Invoice Exceptions (Phase 8)
# ============================================================================


class InvoiceNotFoundError(FieldOperationsError):
    """Raised when an invoice is not found.

    Validates: Requirement 22.2
    """

    def __init__(self, invoice_id: UUID) -> None:
        """Initialize with invoice ID.

        Args:
            invoice_id: UUID of the invoice that was not found
        """
        self.invoice_id = invoice_id
        super().__init__(f"Invoice not found: {invoice_id}")


class InvalidInvoiceOperationError(FieldOperationsError):
    """Raised when an invalid invoice operation is attempted.

    Validates: Requirement 22.4
    """

    def __init__(self, message: str) -> None:
        """Initialize with error message.

        Args:
            message: Description of the invalid operation
        """
        super().__init__(message)


# ============================================================================
# Lead Capture Exceptions
# ============================================================================


class LeadError(Exception):
    """Base exception for lead operations."""


class LeadNotFoundError(LeadError):
    """Raised when a lead is not found.

    Validates: Lead Capture Requirement 13.1
    """

    def __init__(self, lead_id: UUID) -> None:
        """Initialize with lead ID.

        Args:
            lead_id: UUID of the lead that was not found
        """
        self.lead_id = lead_id
        super().__init__(f"Lead not found: {lead_id}")


class LeadAlreadyConvertedError(LeadError):
    """Raised when attempting to convert an already-converted lead.

    Validates: Lead Capture Requirement 13.2
    """

    def __init__(self, lead_id: UUID) -> None:
        """Initialize with lead ID.

        Args:
            lead_id: UUID of the lead that is already converted
        """
        self.lead_id = lead_id
        super().__init__(f"Lead already converted: {lead_id}")


class InvalidLeadStatusTransitionError(LeadError):
    """Raised when an invalid lead status transition is attempted.

    Validates: Lead Capture Requirement 13.3
    """

    def __init__(
        self, current_status: LeadStatus, requested_status: LeadStatus,
    ) -> None:
        """Initialize with status transition details.

        Args:
            current_status: The current lead status
            requested_status: The requested new lead status
        """
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Invalid lead status transition from {current_status.value} "
            f"to {requested_status.value}",
        )


__all__ = [
    "AccountLockedError",
    "AppointmentNotFoundError",
    "AuthenticationError",
    "BulkOperationError",
    "CustomerError",
    "CustomerNotFoundError",
    "DuplicateCustomerError",
    "FieldOperationsError",
    "InvalidCredentialsError",
    "InvalidInvoiceOperationError",
    "InvalidLeadStatusTransitionError",
    "InvalidStatusTransitionError",
    "InvalidTokenError",
    "InvoiceNotFoundError",
    "JobNotFoundError",
    "LeadAlreadyConvertedError",
    "LeadError",
    "LeadNotFoundError",
    "PropertyCustomerMismatchError",
    "PropertyNotFoundError",
    "ScheduleClearAuditNotFoundError",
    "ServiceOfferingInactiveError",
    "ServiceOfferingNotFoundError",
    "StaffAvailabilityNotFoundError",
    "StaffNotFoundError",
    "TokenExpiredError",
    "UserNotFoundError",
    "ValidationError",
]
