"""
Lead service for business logic operations.

This module provides the LeadService class for all lead-related
business operations including submission, duplicate detection,
status workflow, conversion to customer, and dashboard metrics.

Validates: Requirements 1-8, 13, 15
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import TYPE_CHECKING, Any, ClassVar

from grins_platform.exceptions import (
    InvalidLeadStatusTransitionError,
    LeadAlreadyConvertedError,
    LeadNotFoundError,
    StaffNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    VALID_LEAD_STATUS_TRANSITIONS,
    LeadSituation,
    LeadSource,
    LeadStatus,
)
from grins_platform.schemas.customer import CustomerCreate
from grins_platform.schemas.job import JobCreate
from grins_platform.schemas.lead import (
    LeadConversionRequest,
    LeadConversionResponse,
    LeadListParams,
    LeadResponse,
    LeadSubmission,
    LeadSubmissionResponse,
    LeadUpdate,
    PaginatedLeadResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.repositories.lead_repository import LeadRepository
    from grins_platform.repositories.staff_repository import StaffRepository
    from grins_platform.services.customer_service import CustomerService
    from grins_platform.services.job_service import JobService


class LeadService(LoggerMixin):
    """Service for lead management business logic.

    This class handles all business logic for leads including submission,
    honeypot detection, duplicate detection, status workflow, conversion
    to customer/job, and dashboard metrics.

    Attributes:
        lead_repository: LeadRepository for lead database operations
        customer_service: CustomerService for customer creation during conversion
        job_service: JobService for job creation during conversion
        staff_repository: StaffRepository for staff validation

    Validates: Requirements 1-8, 13, 15
    """

    DOMAIN = "lead"

    # Mapping from LeadSituation to (job_category, job_description)
    SITUATION_JOB_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        LeadSituation.NEW_SYSTEM.value: ("requires_estimate", "Installation Estimate"),
        LeadSituation.UPGRADE.value: ("requires_estimate", "System Upgrade Estimate"),
        LeadSituation.REPAIR.value: ("ready_to_schedule", "Repair Request"),
        LeadSituation.EXPLORING.value: ("requires_estimate", "Consultation"),
    }

    def __init__(
        self,
        lead_repository: LeadRepository,
        customer_service: CustomerService,
        job_service: JobService,
        staff_repository: StaffRepository,
    ) -> None:
        """Initialize service with dependencies.

        Args:
            lead_repository: LeadRepository for lead database operations
            customer_service: CustomerService for customer creation
            job_service: JobService for job creation
            staff_repository: StaffRepository for staff validation
        """
        super().__init__()
        self.lead_repository = lead_repository
        self.customer_service = customer_service
        self.job_service = job_service
        self.staff_repository = staff_repository

    @staticmethod
    def split_name(full_name: str) -> tuple[str, str]:
        """Split full name into (first_name, last_name).

        Splits on the first space. Single-word names produce (word, "").
        Multi-word names produce (first_word, rest_of_name).

        Args:
            full_name: Full name string

        Returns:
            Tuple of (first_name, last_name)

        Validates: Requirement 7.1-7.2
        """
        parts = full_name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        return first_name, last_name

    async def submit_lead(self, data: LeadSubmission) -> LeadSubmissionResponse:
        """Process a public form submission.

        Steps:
        1. Check honeypot — if filled, return fake 201 without storing
        2. Check for duplicate by phone + active status
        3. If duplicate found: update existing lead (merge fields)
        4. If no duplicate: create new lead with status "new"
        5. Log lead.submitted event (lead_id + source_site only, no PII)

        Args:
            data: LeadSubmission schema with form data

        Returns:
            LeadSubmissionResponse with success status and lead_id

        Validates: Requirements 1, 2, 3, 15.1, 15.4
        """
        # Step 1: Honeypot check
        if data.website is not None and data.website != "":
            self.logger.warning(
                "lead.spam_detected",
                source_site=data.source_site,
            )
            return LeadSubmissionResponse(
                success=True,
                message="Thank you! We'll be in touch within 24 hours.",
                lead_id=None,
            )

        # Step 2: Check for duplicate by phone + active status
        existing_lead = await self.lead_repository.get_by_phone_and_active_status(
            data.phone,
        )

        if existing_lead is not None:
            # Step 3: Update existing lead (merge fields)
            update_data: dict[str, Any] = {}

            # Merge email: only if new email is not None and existing is None
            if data.email is not None and existing_lead.email is None:
                update_data["email"] = data.email

            # Merge notes: append if both exist
            if data.notes is not None:
                if existing_lead.notes:
                    update_data["notes"] = f"{existing_lead.notes}\n{data.notes}"
                else:
                    update_data["notes"] = data.notes

            # Update situation if different
            if data.situation.value != existing_lead.situation:
                update_data["situation"] = data.situation.value

            await self.lead_repository.update(existing_lead.id, update_data)

            self.logger.info(
                "lead.submitted",
                lead_id=str(existing_lead.id),
                source_site=data.source_site,
            )

            return LeadSubmissionResponse(
                success=True,
                message="Thank you! We'll be in touch within 24 hours.",
                lead_id=existing_lead.id,
            )

        # Step 4: Create new lead
        lead = await self.lead_repository.create(
            name=data.name,
            phone=data.phone,
            email=data.email,
            zip_code=data.zip_code,
            situation=data.situation.value,
            notes=data.notes,
            source_site=data.source_site,
            status=LeadStatus.NEW.value,
        )

        # Step 5: Log (no PII)
        self.logger.info(
            "lead.submitted",
            lead_id=str(lead.id),
            source_site=data.source_site,
        )

        return LeadSubmissionResponse(
            success=True,
            message="Thank you! We'll be in touch within 24 hours.",
            lead_id=lead.id,
        )

    async def get_lead(self, lead_id: UUID) -> LeadResponse:
        """Get a single lead by ID.

        Args:
            lead_id: UUID of the lead

        Returns:
            LeadResponse with lead data

        Raises:
            LeadNotFoundError: If lead not found

        Validates: Requirement 5.8
        """
        lead = await self.lead_repository.get_by_id(lead_id)
        if not lead:
            raise LeadNotFoundError(lead_id)

        response: LeadResponse = LeadResponse.model_validate(lead)
        return response

    async def list_leads(self, params: LeadListParams) -> PaginatedLeadResponse:
        """List leads with filtering and pagination.

        Args:
            params: Query parameters for filtering and pagination

        Returns:
            PaginatedLeadResponse with leads and pagination info

        Validates: Requirement 5.1-5.5
        """
        leads, total = await self.lead_repository.list_with_filters(params)

        total_pages = ceil(total / params.page_size) if total > 0 else 0

        return PaginatedLeadResponse(
            items=[LeadResponse.model_validate(lead) for lead in leads],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    async def update_lead(
        self,
        lead_id: UUID,
        data: LeadUpdate,
    ) -> LeadResponse:
        """Update a lead's status, assignment, or notes.

        Args:
            lead_id: UUID of the lead to update
            data: LeadUpdate schema with fields to update

        Returns:
            LeadResponse with updated lead data

        Raises:
            LeadNotFoundError: If lead not found
            InvalidLeadStatusTransitionError: If status transition is invalid
            StaffNotFoundError: If assigned staff member not found

        Validates: Requirements 5.6-5.7, 6, 15.2
        """
        # Fetch lead
        lead = await self.lead_repository.get_by_id(lead_id)
        if not lead:
            raise LeadNotFoundError(lead_id)

        # Build update data
        update_data = data.model_dump(exclude_unset=True)
        old_status: str | None = None

        # Handle status change
        if "status" in update_data and update_data["status"] is not None:
            current_status_enum = LeadStatus(lead.status)
            new_status_enum = update_data["status"]

            # Validate transition
            valid_transitions = VALID_LEAD_STATUS_TRANSITIONS.get(
                current_status_enum, set(),
            )
            if new_status_enum not in valid_transitions:
                raise InvalidLeadStatusTransitionError(
                    current_status_enum,
                    new_status_enum,
                )

            # Auto-set contacted_at
            if (
                new_status_enum == LeadStatus.CONTACTED
                and lead.contacted_at is None
            ):
                update_data["contacted_at"] = datetime.now(tz=timezone.utc)

            # Auto-set converted_at
            if new_status_enum == LeadStatus.CONVERTED:
                update_data["converted_at"] = datetime.now(tz=timezone.utc)

            # Convert enum to string for storage
            old_status = lead.status
            update_data["status"] = new_status_enum.value

        # Validate staff assignment
        if "assigned_to" in update_data and update_data["assigned_to"] is not None:
            staff = await self.staff_repository.get_by_id(update_data["assigned_to"])
            if not staff:
                raise StaffNotFoundError(update_data["assigned_to"])

        # Perform update
        updated_lead = await self.lead_repository.update(lead_id, update_data)

        # Log status change
        if old_status is not None and data.status is not None:
            self.logger.info(
                "lead.status_changed",
                lead_id=str(lead_id),
                old_status=old_status,
                new_status=data.status.value,
            )

        response: LeadResponse = LeadResponse.model_validate(updated_lead)
        return response

    async def convert_lead(
        self,
        lead_id: UUID,
        data: LeadConversionRequest,
    ) -> LeadConversionResponse:
        """Convert a lead to a customer and optionally a job.

        Args:
            lead_id: UUID of the lead to convert
            data: LeadConversionRequest with conversion options

        Returns:
            LeadConversionResponse with customer and job IDs

        Raises:
            LeadNotFoundError: If lead not found
            LeadAlreadyConvertedError: If lead is already converted

        Validates: Requirement 7, 15.3
        """
        # Step 1: Fetch lead
        lead = await self.lead_repository.get_by_id(lead_id)
        if not lead:
            raise LeadNotFoundError(lead_id)

        # Step 2: Check if already converted
        if lead.status == LeadStatus.CONVERTED.value:
            raise LeadAlreadyConvertedError(lead_id)

        # Step 3: Split name or use overrides
        if data.first_name is not None and data.last_name is not None:
            first_name = data.first_name
            last_name = data.last_name
        else:
            first_name, last_name = self.split_name(lead.name)

        # Step 4: Create customer via CustomerService
        # CustomerCreate requires last_name min_length=1,
        # so use first_name as fallback for single-word names
        customer_last_name = last_name if last_name else first_name
        customer_data = CustomerCreate(
            first_name=first_name,
            last_name=customer_last_name,
            phone=lead.phone,
            email=lead.email,
            lead_source=LeadSource.WEBSITE,
        )
        customer = await self.customer_service.create_customer(customer_data)

        # Step 5: Optionally create job
        job_id = None
        if data.create_job:
            # Map situation to job type and description
            situation_key = lead.situation
            _category, default_description = self.SITUATION_JOB_MAP.get(
                situation_key,
                ("requires_estimate", "Consultation"),
            )

            description = data.job_description or default_description

            job_data = JobCreate(
                customer_id=customer.id,
                job_type=_category,
                description=description,
            )
            job = await self.job_service.create_job(job_data)
            job_id = job.id

        # Step 6: Update lead
        await self.lead_repository.update(
            lead_id,
            {
                "status": LeadStatus.CONVERTED.value,
                "converted_at": datetime.now(tz=timezone.utc),
                "customer_id": customer.id,
            },
        )

        # Step 7: Log conversion (no PII)
        self.logger.info(
            "lead.converted",
            lead_id=str(lead_id),
            customer_id=str(customer.id),
            job_id=str(job_id) if job_id else None,
        )

        return LeadConversionResponse(
            success=True,
            lead_id=lead_id,
            customer_id=customer.id,
            job_id=job_id,
            message="Lead converted successfully",
        )

    async def delete_lead(self, lead_id: UUID) -> None:
        """Delete a lead record.

        Args:
            lead_id: UUID of the lead to delete

        Raises:
            LeadNotFoundError: If lead not found

        Validates: Requirement 5.9
        """
        lead = await self.lead_repository.get_by_id(lead_id)
        if not lead:
            raise LeadNotFoundError(lead_id)

        await self.lead_repository.delete(lead_id)

    async def get_dashboard_metrics(self) -> dict[str, int]:
        """Get lead metrics for dashboard integration.

        Returns:
            Dictionary with new_leads_today and uncontacted_leads counts

        Validates: Requirement 8.1-8.2
        """
        new_leads_today = await self.lead_repository.count_new_today()
        uncontacted_leads = await self.lead_repository.count_uncontacted()

        return {
            "new_leads_today": new_leads_today,
            "uncontacted_leads": uncontacted_leads,
        }
