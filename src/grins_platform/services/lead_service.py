"""
Lead service for business logic operations.

This module provides the LeadService class for all lead-related
business operations including submission, duplicate detection,
status workflow, conversion to customer, and dashboard metrics.

Validates: Requirements 1-8, 13, 15
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
    IntakeTag,
    LeadSituation,
    LeadSource,
    LeadSourceExtended,
    LeadStatus,
)
from grins_platform.schemas.ai import MessageType
from grins_platform.schemas.customer import CustomerCreate
from grins_platform.schemas.job import JobCreate
from grins_platform.schemas.lead import (
    FollowUpQueueItem,
    FromCallSubmission,
    LeadConversionRequest,
    LeadConversionResponse,
    LeadListParams,
    LeadMetricsBySourceResponse,
    LeadResponse,
    LeadSourceCount,
    LeadSubmission,
    LeadSubmissionResponse,
    LeadUpdate,
    PaginatedFollowUpQueueResponse,
    PaginatedLeadResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.lead import Lead
    from grins_platform.repositories.lead_repository import LeadRepository
    from grins_platform.repositories.staff_repository import StaffRepository
    from grins_platform.services.compliance_service import ComplianceService
    from grins_platform.services.customer_service import CustomerService
    from grins_platform.services.email_service import EmailService
    from grins_platform.services.job_service import JobService
    from grins_platform.services.sms_service import SMSService


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
        sms_service: SMSService | None = None,
        email_service: EmailService | None = None,
        compliance_service: ComplianceService | None = None,
    ) -> None:
        """Initialize service with dependencies.

        Args:
            lead_repository: LeadRepository for lead database operations
            customer_service: CustomerService for customer creation
            job_service: JobService for job creation
            staff_repository: StaffRepository for staff validation
            sms_service: Optional SMSService for SMS confirmations
            email_service: Optional EmailService for email confirmations
            compliance_service: Optional ComplianceService for consent records
        """
        super().__init__()
        self.lead_repository = lead_repository
        self.customer_service = customer_service
        self.job_service = job_service
        self.staff_repository = staff_repository
        self.sms_service = sms_service
        self.email_service = email_service
        self.compliance_service = compliance_service

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

    async def _send_sms_confirmation(self, lead: Lead) -> None:
        """Send SMS confirmation for a new lead.

        Gated on sms_consent=true AND phone present. Skips and logs
        if conditions not met or service unavailable.

        Validates: Requirements 54.1, 54.2, 54.3, 54.4
        """
        if not self.sms_service:
            self.logger.info(
                "lead.sms_confirmation.skipped",
                lead_id=str(lead.id),
                reason="sms_service_unavailable",
            )
            return

        if not lead.sms_consent:
            self.logger.info(
                "lead.sms_confirmation.skipped",
                lead_id=str(lead.id),
                reason="no_sms_consent",
            )
            return

        if not lead.phone:
            self.logger.info(
                "lead.sms_confirmation.skipped",
                lead_id=str(lead.id),
                reason="no_phone",
            )
            return

        first_name, _ = self.split_name(lead.name)
        message = (
            f"Hi {first_name}! Your request has been received by "
            "Grins Irrigation. We'll be in touch within 2 hours "
            "during business hours."
        )

        try:
            _ = await self.sms_service.send_message(
                customer_id=lead.id,
                phone=lead.phone,
                message=message,
                message_type=MessageType.LEAD_CONFIRMATION,
                sms_opt_in=True,
            )
            self.logger.info(
                "lead.sms_confirmation.sent",
                lead_id=str(lead.id),
            )
        except Exception as e:
            self.logger.warning(
                "lead.sms_confirmation.failed",
                lead_id=str(lead.id),
                error=str(e),
            )

    def _send_email_confirmation(self, lead: Lead) -> None:
        """Send email confirmation for a new lead.

        Sent when lead has an email address. Skips and logs if no email
        or service unavailable.

        Validates: Requirements 55.1, 55.2, 55.3
        """
        if not self.email_service:
            self.logger.info(
                "lead.email_confirmation.skipped",
                lead_id=str(lead.id),
                reason="email_service_unavailable",
            )
            return

        if not lead.email:
            self.logger.info(
                "lead.email_confirmation.skipped",
                lead_id=str(lead.id),
                reason="no_email",
            )
            return

        try:
            _ = self.email_service.send_lead_confirmation(lead)
            self.logger.info(
                "lead.email_confirmation.sent",
                lead_id=str(lead.id),
            )
        except Exception as e:
            self.logger.warning(
                "lead.email_confirmation.failed",
                lead_id=str(lead.id),
                error=str(e),
            )

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

        Validates: Requirements 1, 2, 3, 15.1, 15.4, 45.1, 45.2, 48.1, 48.2
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

        # Resolve lead_source and intake_tag defaults
        lead_source = (
            data.lead_source.value
            if data.lead_source
            else LeadSourceExtended.WEBSITE.value
        )
        source_detail = data.source_detail
        intake_tag = (
            data.intake_tag.value if data.intake_tag else IntakeTag.SCHEDULE.value
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
            lead_source=lead_source,
            source_detail=source_detail,
            intake_tag=intake_tag,
        )

        # Step 5: Log (no PII)
        self.logger.info(
            "lead.submitted",
            lead_id=str(lead.id),
            source_site=data.source_site,
        )

        # Step 6: Send confirmations (Req 54, 55)
        await self._send_sms_confirmation(lead)
        self._send_email_confirmation(lead)

        return LeadSubmissionResponse(
            success=True,
            message="Thank you! We'll be in touch within 24 hours.",
            lead_id=lead.id,
        )

    async def create_from_call(self, data: FromCallSubmission) -> LeadResponse:
        """Create a lead from an inbound phone call (admin-only).

        Args:
            data: FromCallSubmission schema with call data

        Returns:
            LeadResponse with created lead data

        Validates: Requirements 45.4, 45.5
        """
        self.log_started("create_from_call")

        lead_source = data.lead_source.value
        source_detail = data.source_detail if data.source_detail else "Inbound call"
        intake_tag = data.intake_tag.value if data.intake_tag else None

        lead = await self.lead_repository.create(
            name=data.name,
            phone=data.phone,
            email=data.email,
            zip_code=data.zip_code,
            situation=data.situation.value,
            notes=data.notes,
            source_site="admin",
            status=LeadStatus.NEW.value,
            lead_source=lead_source,
            source_detail=source_detail,
            intake_tag=intake_tag,
        )

        self.logger.info(
            "lead.from_call_created",
            lead_id=str(lead.id),
        )

        # Send confirmations (Req 54, 55)
        await self._send_sms_confirmation(lead)
        self._send_email_confirmation(lead)

        self.log_completed("create_from_call", lead_id=str(lead.id))
        response: LeadResponse = LeadResponse.model_validate(lead)
        return response

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
                current_status_enum,
                set(),
            )
            if new_status_enum not in valid_transitions:
                raise InvalidLeadStatusTransitionError(
                    current_status_enum,
                    new_status_enum,
                )

            # Auto-set contacted_at
            if new_status_enum == LeadStatus.CONTACTED and lead.contacted_at is None:
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

        # Convert intake_tag enum to string for storage
        if "intake_tag" in update_data and update_data["intake_tag"] is not None:
            update_data["intake_tag"] = update_data["intake_tag"].value

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

        Carries over consent fields from lead to customer:
        - sms_consent=true → sms_opt_in + sms_consent_record
        - terms_accepted=true → terms_accepted + terms_accepted_at
        - email present → email_opt_in_at + email_opt_in_source

        Args:
            lead_id: UUID of the lead to convert
            data: LeadConversionRequest with conversion options

        Returns:
            LeadConversionResponse with customer and job IDs

        Raises:
            LeadNotFoundError: If lead not found
            LeadAlreadyConvertedError: If lead is already converted

        Validates: Requirement 7, 15.3, 57.1, 57.2, 57.3, 68.3
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
            sms_opt_in=lead.sms_consent,
        )
        customer = await self.customer_service.create_customer(customer_data)

        # Step 5: Carry over consent fields (Req 57.1, 57.2, 57.3, 68.3)
        now = datetime.now(tz=timezone.utc)
        consent_updates: dict[str, Any] = {}

        if lead.sms_consent:
            consent_updates["sms_opt_in_at"] = now
            consent_updates["sms_opt_in_source"] = "lead_form"
            # Create sms_consent_record via ComplianceService
            if self.compliance_service:
                await self.compliance_service.create_sms_consent(
                    phone=lead.phone,
                    consent_given=True,
                    method="lead_form",
                    language_shown="Standard SMS consent from lead form",
                    customer_id=customer.id,
                )

        if lead.terms_accepted:
            consent_updates["terms_accepted"] = True
            consent_updates["terms_accepted_at"] = now

        if lead.email:
            consent_updates["email_opt_in_at"] = now
            consent_updates["email_opt_in_source"] = "lead_form"

        if consent_updates:
            await self.customer_service.repository.update(
                customer.id,
                consent_updates,
            )

        # Step 6: Optionally create job
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

        # Step 7: Update lead
        await self.lead_repository.update(
            lead_id,
            {
                "status": LeadStatus.CONVERTED.value,
                "converted_at": datetime.now(tz=timezone.utc),
                "customer_id": customer.id,
            },
        )

        # Step 8: Log conversion (no PII)
        self.logger.info(
            "lead.converted",
            lead_id=str(lead_id),
            customer_id=str(customer.id),
            job_id=str(job_id) if job_id else None,
            sms_consent_carried=lead.sms_consent,
            terms_carried=lead.terms_accepted,
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

    async def get_follow_up_queue(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedFollowUpQueueResponse:
        """Get paginated follow-up queue.

        Returns leads with intake_tag=FOLLOW_UP and active status,
        sorted by created_at ASC, with computed time_since_created.

        Args:
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            PaginatedFollowUpQueueResponse

        Validates: Requirements 50.1, 50.2, 50.3, 50.4
        """
        self.log_started("get_follow_up_queue", page=page, page_size=page_size)

        leads, total = await self.lead_repository.get_follow_up_queue(
            page=page,
            page_size=page_size,
        )

        now = datetime.now(tz=timezone.utc)
        items: list[FollowUpQueueItem] = []
        for lead in leads:
            created = lead.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            hours = (now - created).total_seconds() / 3600.0
            lead_data = FollowUpQueueItem.model_validate(lead)
            lead_data.time_since_created = round(hours, 1)
            items.append(lead_data)

        total_pages = ceil(total / page_size) if total > 0 else 0

        self.log_completed("get_follow_up_queue", count=len(items), total=total)
        return PaginatedFollowUpQueueResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

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

    async def get_metrics_by_source(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> LeadMetricsBySourceResponse:
        """Get lead counts grouped by source for a date range.

        Args:
            date_from: Start of date range. Defaults to 30 days ago.
            date_to: End of date range. Defaults to now.

        Returns:
            LeadMetricsBySourceResponse with counts per source

        Validates: Requirement 61.3
        """
        self.log_started("get_metrics_by_source")

        now = datetime.now(tz=timezone.utc)
        effective_to = date_to or now
        effective_from = date_from or (now - timedelta(days=30))

        rows = await self.lead_repository.count_by_source(
            effective_from,
            effective_to,
        )

        items = [LeadSourceCount(lead_source=src, count=cnt) for src, cnt in rows]
        total = sum(item.count for item in items)

        self.log_completed("get_metrics_by_source", total=total, groups=len(items))
        return LeadMetricsBySourceResponse(
            items=items,
            total=total,
            date_from=effective_from,
            date_to=effective_to,
        )
