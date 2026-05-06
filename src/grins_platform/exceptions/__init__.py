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
    WebAuthnChallengeNotFoundError,
    WebAuthnCredentialNotFoundError,
    WebAuthnDuplicateCredentialError,
    WebAuthnVerificationError,
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


class MergeConflictError(CustomerError):
    """Raised when a customer merge would create data inconsistency.

    Validates: CRM Gap Closure Req 7.2
    """

    def __init__(self, message: str) -> None:
        """Initialize with conflict description.

        Args:
            message: Description of the merge conflict
        """
        super().__init__(message)


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


class JobTargetDateEditNotAllowedError(FieldOperationsError):
    """Raised when an admin tries to move a job's target week but the
    job is no longer in the 'to_be_scheduled' state.

    Changing the target window on an already-scheduled / in-progress /
    completed job can leave attached appointments out of sync, so that
    flow is blocked at the service layer. A dedicated reschedule flow
    would be needed to move those jobs.
    """

    def __init__(self, job_id: UUID, current_status: str) -> None:
        """Initialize with job ID and the status that blocked the edit."""
        self.job_id = job_id
        self.current_status = current_status
        super().__init__(
            "Cannot edit target dates on a job with status"
            f" '{current_status}'; only 'to_be_scheduled' jobs can be"
            " rewindowed from the admin Jobs tab.",
        )


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


class AppointmentOnFinishedJobError(FieldOperationsError):
    """Raised when trying to schedule an appointment on a COMPLETED or
    CANCELLED job. Previously silently allowed — admins could attach a
    new appointment to a finished job and draft-mode would proceed.

    Validates: bughunt H-4
    """

    def __init__(self, job_id: UUID, job_status: str) -> None:
        self.job_id = job_id
        self.job_status = job_status
        super().__init__(
            f"Cannot schedule an appointment on a job in status "
            f"'{job_status}' (job_id={job_id})"
        )


class CustomerHasNoPhoneError(FieldOperationsError):
    """Raised when a customer-facing SMS path runs but the customer row
    has no phone number on file. Previously the send path returned
    silently and the caller still transitioned the appointment to
    ``SCHEDULED`` as if the SMS had gone out.

    Validates: bughunt M-9
    """

    def __init__(self, customer_id: UUID) -> None:
        self.customer_id = customer_id
        super().__init__(
            f"Customer {customer_id} has no phone number; cannot send SMS."
        )


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


class LeadHasReferencesError(FieldOperationsError):
    """Raised when a lead cannot be deleted due to FK references.

    Validates: bughunt 2026-05-04 B-6.
    """

    def __init__(self, lead_id: UUID) -> None:
        self.lead_id = lead_id
        super().__init__(
            f"Cannot delete lead {lead_id}: associated SMS consent or "
            f"campaign records prevent deletion (FK).",
        )


class NoContactMethodError(FieldOperationsError):
    """Raised when an invoice has no deliverable contact method.

    The invoice's customer has neither a phone (or has hard-STOPped SMS)
    nor a deliverable email. The Stripe Payment Link cannot be sent.

    Validates: Stripe Payment Links plan §Phase 2.7.
    """

    def __init__(self, invoice_id: UUID) -> None:
        """Initialize with the invoice ID.

        Args:
            invoice_id: UUID of the invoice that has no contact method.
        """
        self.invoice_id = invoice_id
        super().__init__(
            f"Invoice {invoice_id} has no deliverable contact method "
            "(no phone and no email).",
        )


class LeadOnlyInvoiceError(FieldOperationsError):
    """Raised when a Payment Link is requested for a Lead-only invoice.

    Lead-only appointments are blocked from the card-payment flow at the
    UI level (D12). This is the backend safety net: if the customer
    cannot be resolved (null / Lead-only record), the send-link path
    refuses rather than silently succeeding.

    Validates: Stripe Payment Links plan §Phase 2.7.
    """

    def __init__(self, invoice_id: UUID) -> None:
        """Initialize with the invoice ID.

        Args:
            invoice_id: UUID of the invoice whose customer cannot be resolved.
        """
        self.invoice_id = invoice_id
        super().__init__(
            f"Invoice {invoice_id} has no resolvable customer "
            "(Lead-only invoices cannot send a Payment Link). "
            "Convert the lead to a customer first.",
        )


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
        self,
        current_status: LeadStatus,
        requested_status: LeadStatus,
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


class DuplicateLeadError(LeadError):
    """Raised when a duplicate lead is submitted within 24 hours.

    Validates: Integration Gap Requirement 6.3
    """

    def __init__(self) -> None:
        """Initialize with standard duplicate message."""
        self.detail = "duplicate_lead"
        self.message = (
            "A request with this contact information was recently submitted. "
            "We'll be in touch soon."
        )
        super().__init__(self.message)


class AgreementError(Exception):
    """Base exception for agreement operations."""


class AgreementNotFoundError(AgreementError):
    """Raised when a service agreement is not found."""

    def __init__(self, agreement_id: UUID) -> None:
        """Initialize with agreement ID."""
        self.agreement_id = agreement_id
        super().__init__(f"Agreement not found: {agreement_id}")


class InvalidAgreementStatusTransitionError(AgreementError):
    """Raised when an invalid agreement status transition is attempted.

    Validates: Requirement 5.2
    """

    def __init__(self, current_status: str, requested_status: str) -> None:
        """Initialize with status transition details."""
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Invalid agreement status transition from '{current_status}' "
            f"to '{requested_status}'",
        )


class MidSeasonTierChangeError(AgreementError):
    """Raised when a tier change is attempted on an active agreement.

    Validates: Requirement 18.1
    """

    def __init__(self, agreement_id: UUID) -> None:
        """Initialize with agreement ID."""
        self.agreement_id = agreement_id
        super().__init__(
            f"Tier changes are not permitted while agreement {agreement_id} "
            f"is ACTIVE. Tier changes are only allowed at renewal.",
        )


class InactiveTierError(AgreementError):
    """Raised when an inactive tier is used for agreement creation.

    Validates: Requirement 1.4
    """

    def __init__(self, tier_id: UUID) -> None:
        """Initialize with tier ID."""
        self.tier_id = tier_id
        super().__init__(f"Tier {tier_id} is inactive and cannot be used")


class ConsentValidationError(AgreementError):
    """Raised when pre-checkout consent validation fails.

    Validates: Requirement 30.5
    """

    def __init__(self, missing_fields: list[str]) -> None:
        """Initialize with missing consent fields."""
        self.missing_fields = missing_fields
        super().__init__(
            f"Pre-checkout consent validation failed: {', '.join(missing_fields)} "
            f"must be true",
        )


# =========================================================================
# Estimate Errors
# =========================================================================


class EstimateError(Exception):
    """Base exception for estimate operations."""


class EstimateNotFoundError(EstimateError):
    """Raised when an estimate ID or token is not found.

    Validates: CRM Gap Closure Design — EstimateService errors
    """

    def __init__(self, identifier: UUID | str) -> None:
        """Initialize with estimate identifier."""
        self.identifier = identifier
        super().__init__(f"Estimate not found: {identifier}")


class EstimateAlreadyApprovedError(EstimateError):
    """Raised when attempting to approve/reject an already-decided estimate.

    Validates: CRM Gap Closure Design — EstimateService errors
    """

    def __init__(self, estimate_id: UUID) -> None:
        """Initialize with estimate ID."""
        self.estimate_id = estimate_id
        super().__init__(
            f"Estimate {estimate_id} has already been approved or rejected",
        )


class EstimateTokenExpiredError(EstimateError):
    """Raised when a portal token is past expiration.

    Validates: CRM Gap Closure Design — EstimateService errors
    """

    def __init__(self, token: UUID) -> None:
        """Initialize with token."""
        self.token = token
        super().__init__(f"Portal token has expired: {token}")


class InvalidPromotionCodeError(EstimateError):
    """Raised when a promotion code is not found or expired.

    Validates: CRM Gap Closure Design — EstimateService errors
    """

    def __init__(self, code: str) -> None:
        """Initialize with promotion code."""
        self.code = code
        super().__init__(f"Invalid or expired promotion code: {code}")


class EstimateTemplateNotFoundError(EstimateError):
    """Raised when an estimate template is not found.

    Validates: CRM Gap Closure Req 17.3
    """

    def __init__(self, template_id: UUID) -> None:
        """Initialize with template ID."""
        self.template_id = template_id
        super().__init__(f"Estimate template not found: {template_id}")


# =============================================================================
# Appointment Service Errors (CRM Gap Closure Req 24, 35, 36)
# =============================================================================


class StaffConflictError(Exception):
    """Raised when rescheduling conflicts with an existing appointment.

    Validates: CRM Gap Closure Req 24.5
    """

    def __init__(
        self,
        staff_id: UUID,
        conflicting_appointment_id: UUID,
    ) -> None:
        """Initialize with staff and conflicting appointment IDs."""
        self.staff_id = staff_id
        self.conflicting_appointment_id = conflicting_appointment_id
        super().__init__(
            f"Staff {staff_id} has a conflicting appointment: "
            f"{conflicting_appointment_id}",
        )


class PaymentRequiredError(Exception):
    """Raised when completion is blocked because no payment/invoice exists.

    Validates: CRM Gap Closure Req 36.1, 36.2
    """

    def __init__(self, appointment_id: UUID) -> None:
        """Initialize with appointment ID."""
        self.appointment_id = appointment_id
        super().__init__(
            "Please collect payment or send an invoice before completing this job",
        )


class ReviewAlreadyRequestedError(Exception):
    """Raised when a Google review was already requested within 30 days.

    Validates: CRM Gap Closure Req 34.6
    """

    def __init__(self, customer_id: UUID, last_requested_at: str) -> None:
        """Initialize with customer ID and last request date."""
        self.customer_id = customer_id
        self.last_requested_at = last_requested_at
        super().__init__(
            f"Review already requested for customer {customer_id} "
            f"on {last_requested_at}. 30-day dedup applies.",
        )


class ConsentRequiredError(Exception):
    """Raised when SMS consent is required but not granted.

    Validates: CRM Gap Closure Req 34.2
    """

    def __init__(self, customer_id: UUID) -> None:
        """Initialize with customer ID."""
        self.customer_id = customer_id
        super().__init__(
            f"SMS consent not granted for customer {customer_id}",
        )


# =========================================================================
# Sales Pipeline Errors (CRM Changes Update 2 Req 14, 16)
# =========================================================================


class SalesEntryNotFoundError(Exception):
    """Raised when a sales entry is not found.

    Validates: CRM Changes Update 2 Req 14.1
    """

    def __init__(self, entry_id: UUID) -> None:
        """Initialize with entry ID."""
        self.entry_id = entry_id
        super().__init__(f"Sales entry not found: {entry_id}")


class InvalidSalesTransitionError(Exception):
    """Raised when a sales pipeline status transition is invalid.

    Validates: CRM Changes Update 2 Req 14.3, 33.1
    """

    def __init__(self, current_status: str, target_status: str) -> None:
        """Initialize with current and target statuses."""
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Cannot transition from {current_status} to {target_status}",
        )


class SignatureRequiredError(Exception):
    """Raised when convert-to-job is blocked by missing signature.

    Validates: CRM Changes Update 2 Req 16.1
    """

    def __init__(self, entry_id: UUID) -> None:
        """Initialize with entry ID."""
        self.entry_id = entry_id
        super().__init__(
            f"Sales entry {entry_id}: waiting for customer signature. "
            "Use force=True to override.",
        )


class MissingSigningDocumentError(Exception):
    """Raised when a sales entry tries to advance to ``pending_approval``
    without a SignWell document on file.

    Deprecated as of the Q-B fix in the estimate approval email portal
    feature: the gate that raised this exception was removed because it
    conflated *estimate approval* (a portal click) with *contract
    signature* (SignWell). No code path raises this exception today;
    the class is retained for back-compat with any external imports.

    Validates: bughunt M-10 (now superseded).
    """

    def __init__(self, entry_id: UUID) -> None:
        self.entry_id = entry_id
        super().__init__(
            f"Sales entry {entry_id}: upload an estimate before advancing to "
            "pending_approval.",
        )


class SalesCalendarEventNotFoundError(Exception):
    """Raised when a sales calendar event (estimate visit) is not found.

    Validates: sales-pipeline-estimate-visit-confirmation-lifecycle.
    """

    def __init__(self, event_id: UUID) -> None:
        """Initialize with event ID."""
        self.event_id = event_id
        super().__init__(f"Sales calendar event not found: {event_id}")


class EstimateNotConfirmedError(Exception):
    """Raised when programmatic ``advance_status`` is blocked because the
    latest sales calendar event has not yet been confirmed by the customer.

    The manual override path bypasses this guard so an admin can still
    push the entry forward when needed.

    Validates: sales-pipeline-estimate-visit-confirmation-lifecycle (OQ-6).
    """

    def __init__(self, entry_id: UUID, current_status: str | None = None) -> None:
        """Initialize with entry ID and the latest event status."""
        self.entry_id = entry_id
        self.current_status = current_status
        suffix = (
            f" (latest event status: {current_status})"
            if current_status is not None
            else ""
        )
        super().__init__(
            f"Sales entry {entry_id}: cannot advance to send_estimate "
            f"until the customer confirms the estimate visit{suffix}.",
        )


# =========================================================================
# CRM Changes Update 2 — Domain-Specific Exceptions (Task 18.1)
# =========================================================================


class MergeBlockerError(CustomerError):
    """Raised when a customer merge is blocked by a business rule.

    Validates: CRM Changes Update 2 Req 6.7
    """

    def __init__(self, message: str) -> None:
        """Initialize with blocker description.

        Args:
            message: Description of the merge blocker
        """
        super().__init__(message)


class ConfirmationCorrelationError(Exception):
    """Raised when an inbound SMS cannot be correlated to a confirmation.

    Validates: CRM Changes Update 2 Req 24.2
    """

    def __init__(self, thread_id: str) -> None:
        """Initialize with thread ID.

        Args:
            thread_id: The thread_id that could not be correlated
        """
        self.thread_id = thread_id
        super().__init__(
            f"No appointment confirmation found for thread: {thread_id}",
        )


class RenewalProposalNotFoundError(Exception):
    """Raised when a contract renewal proposal is not found.

    Validates: CRM Changes Update 2 Req 31.5
    """

    def __init__(self, proposal_id: UUID) -> None:
        """Initialize with proposal ID.

        Args:
            proposal_id: UUID of the proposal that was not found
        """
        self.proposal_id = proposal_id
        super().__init__(f"Renewal proposal not found: {proposal_id}")


class DocumentUploadError(Exception):
    """Raised when a document upload fails validation or processing.

    Validates: CRM Changes Update 2 Req 17.2
    """

    def __init__(self, message: str) -> None:
        """Initialize with error message.

        Args:
            message: Description of the upload failure
        """
        super().__init__(message)


__all__ = [
    "AccountLockedError",
    "AgreementError",
    "AgreementNotFoundError",
    "AppointmentNotFoundError",
    "AppointmentOnFinishedJobError",
    "AuthenticationError",
    "BulkOperationError",
    "ConfirmationCorrelationError",
    "ConsentRequiredError",
    "ConsentValidationError",
    "CustomerError",
    "CustomerHasNoPhoneError",
    "CustomerNotFoundError",
    "DocumentUploadError",
    "DuplicateCustomerError",
    "DuplicateLeadError",
    "EstimateAlreadyApprovedError",
    "EstimateError",
    "EstimateNotConfirmedError",
    "EstimateNotFoundError",
    "EstimateTemplateNotFoundError",
    "EstimateTokenExpiredError",
    "FieldOperationsError",
    "InactiveTierError",
    "InvalidAgreementStatusTransitionError",
    "InvalidCredentialsError",
    "InvalidInvoiceOperationError",
    "InvalidLeadStatusTransitionError",
    "InvalidPromotionCodeError",
    "InvalidSalesTransitionError",
    "InvalidStatusTransitionError",
    "InvalidTokenError",
    "InvoiceNotFoundError",
    "JobNotFoundError",
    "LeadAlreadyConvertedError",
    "LeadError",
    "LeadHasReferencesError",
    "LeadNotFoundError",
    "LeadOnlyInvoiceError",
    "MergeBlockerError",
    "MidSeasonTierChangeError",
    "MissingSigningDocumentError",
    "NoContactMethodError",
    "PaymentRequiredError",
    "PropertyCustomerMismatchError",
    "PropertyNotFoundError",
    "RenewalProposalNotFoundError",
    "ReviewAlreadyRequestedError",
    "SalesCalendarEventNotFoundError",
    "SalesEntryNotFoundError",
    "ScheduleClearAuditNotFoundError",
    "ServiceOfferingInactiveError",
    "ServiceOfferingNotFoundError",
    "SignatureRequiredError",
    "StaffAvailabilityNotFoundError",
    "StaffConflictError",
    "StaffNotFoundError",
    "TokenExpiredError",
    "UserNotFoundError",
    "ValidationError",
    "WebAuthnChallengeNotFoundError",
    "WebAuthnCredentialNotFoundError",
    "WebAuthnDuplicateCredentialError",
    "WebAuthnVerificationError",
]
