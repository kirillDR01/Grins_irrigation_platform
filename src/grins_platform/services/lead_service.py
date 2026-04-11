"""
Lead service for business logic operations.

This module provides the LeadService class for all lead-related
business operations including submission, duplicate detection,
status workflow, conversion to customer, dashboard metrics,
bulk outreach, reverse flow, and work request migration.

Validates: Requirements 1-8, 12, 13, 14, 15, 18, 19, 46
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import select

from grins_platform.exceptions import (
    DuplicateLeadError,
    InvalidLeadStatusTransitionError,
    LeadAlreadyConvertedError,
    LeadNotFoundError,
    StaffNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    VALID_LEAD_STATUS_TRANSITIONS,
    ActionTag,
    IntakeTag,
    LeadSituation,
    LeadSource,
    LeadSourceExtended,
    LeadStatus,
)
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.schemas.customer import CustomerCreate
from grins_platform.schemas.job import JobCreate
from grins_platform.schemas.lead import (
    BulkOutreachSummary,
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
    ManualLeadCreate,
    MigrationSummary,
    PaginatedFollowUpQueueResponse,
    PaginatedLeadResponse,
)
from grins_platform.utils.zip_lookup import extract_zip_from_address, lookup_zip

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.google_sheet_submission import (
        GoogleSheetSubmission,
    )
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
        """Send SMS confirmation for new leads with consent.

        Sends via SMSService.send_automated_message which enforces
        time window restrictions (8 AM - 9 PM Central).

        Validates: Requirements 46.1, 46.2, 46.3
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

        try:
            confirmation_msg = (
                "Thanks for reaching out to Grins Irrigation! "
                "We received your request and will be in touch soon."
            )
            result = await self.sms_service.send_automated_message(
                phone=lead.phone,
                message=confirmation_msg,
                message_type="lead_confirmation",
            )
            if result.get("success"):
                if result.get("deferred"):
                    self.logger.info(
                        "lead.confirmation.sms_deferred",
                        lead_id=str(lead.id),
                        scheduled_for=result.get("scheduled_for"),
                    )
                else:
                    self.logger.info(
                        "lead.confirmation.sms_sent",
                        lead_id=str(lead.id),
                    )
            else:
                self.logger.info(
                    "lead.confirmation.sms_skipped",
                    lead_id=str(lead.id),
                    reason=result.get("reason", "unknown"),
                )
        except Exception as e:
            self.logger.warning(
                "lead.confirmation.sms_failed",
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
        2. Check for duplicate by phone OR email within 24 hours
        3. If duplicate found within 24h: raise DuplicateLeadError (409)
        4. Check for existing active lead by phone (merge behavior)
        5. If active duplicate found: update existing lead (merge fields)
        6. If no duplicate: create new lead with status "new"
        7. Create SmsConsentRecord for the lead
        8. Log lead.submitted event (lead_id + source_site only, no PII)
        9. Send confirmations

        Args:
            data: LeadSubmission schema with form data

        Returns:
            LeadSubmissionResponse with success status and lead_id

        Raises:
            DuplicateLeadError: If matching lead submitted within 24 hours

        Validates: Requirements 1, 2, 3, 6.1-6.4, 7.1-7.4,
            15.1, 15.4, 45.1, 45.2, 48.1, 48.2
        """
        # Step 1: Honeypot check
        if data.website is not None and data.website != "":
            self.logger.warning(
                "lead.spam_detected",
                source_site=data.source_site,
            )
            return LeadSubmissionResponse(
                success=True,
                message="Thank you! We'll reach out within 1-2 business days.",
                lead_id=None,
            )

        # Step 2: 24-hour duplicate detection by phone OR email
        recent_dup = await self.lead_repository.get_recent_by_phone_or_email(
            phone=data.phone,
            email=data.email,
        )
        if recent_dup is not None:
            self.logger.info(
                "lead.duplicate_detected",
                existing_lead_id=str(recent_dup.id),
                source_site=data.source_site,
            )
            raise DuplicateLeadError()

        # Step 3: Check for existing active lead by phone (merge behavior)
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
            # Step 4: Update existing lead (merge fields)
            update_data: dict[str, Any] = {}

            if data.email is not None and existing_lead.email is None:
                update_data["email"] = data.email

            if data.address and not existing_lead.address:
                update_data["address"] = data.address

            if data.notes is not None:
                if existing_lead.notes:
                    update_data["notes"] = f"{existing_lead.notes}\n{data.notes}"
                else:
                    update_data["notes"] = data.notes

            if data.situation.value != existing_lead.situation:
                update_data["situation"] = data.situation.value

            if data.terms_accepted and not existing_lead.terms_accepted:
                update_data["terms_accepted"] = True

            await self.lead_repository.update(existing_lead.id, update_data)

            self.logger.info(
                "lead.submitted",
                lead_id=str(existing_lead.id),
                source_site=data.source_site,
            )

            return LeadSubmissionResponse(
                success=True,
                message="Thank you! We'll reach out within 1-2 business days.",
                lead_id=existing_lead.id,
            )

        # Step 5: Extract zip from address if not provided
        zip_code = data.zip_code
        if not zip_code and data.address:
            zip_code = extract_zip_from_address(data.address)

        # Auto-populate city/state from zip if not provided (Req 12.5)
        city = data.city
        state = data.state
        if zip_code and not city and not state:
            looked_up_city, looked_up_state = lookup_zip(zip_code)
            if looked_up_city:
                city = looked_up_city
            if looked_up_state:
                state = looked_up_state

        # Step 5b: Create new lead with new fields
        lead = await self.lead_repository.create(
            name=data.name,
            phone=data.phone,
            email=data.email,
            zip_code=zip_code,
            situation=data.situation.value,
            notes=data.notes,
            source_site=data.source_site,
            status=LeadStatus.NEW.value,
            lead_source=lead_source,
            source_detail=source_detail,
            intake_tag=intake_tag,
            sms_consent=data.sms_consent,
            terms_accepted=data.terms_accepted,
            email_marketing_consent=data.email_marketing_consent,
            page_url=data.page_url,
            city=city,
            state=state,
            address=data.address,
            customer_type=data.customer_type,
            property_type=data.property_type,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        # Step 6: Create SmsConsentRecord for the lead
        await self._create_lead_consent_record(lead, data)

        # Step 7: Log (no PII)
        self.logger.info(
            "lead.submitted",
            lead_id=str(lead.id),
            source_site=data.source_site,
        )

        # Step 8: Send confirmations (Req 54, 55)
        await self._send_sms_confirmation(lead)
        self._send_email_confirmation(lead)

        return LeadSubmissionResponse(
            success=True,
            message="Thank you! We'll reach out within 1-2 business days.",
            lead_id=lead.id,
        )

    async def _create_lead_consent_record(
        self,
        lead: Lead,
        data: LeadSubmission,
    ) -> None:
        """Create SmsConsentRecord for a newly created lead.

        Validates: Requirements 7.1, 7.3, 7.4
        """
        if not self.compliance_service:
            self.logger.info(
                "lead.consent_record.skipped",
                lead_id=str(lead.id),
                reason="compliance_service_unavailable",
            )
            return

        try:
            await self.compliance_service.create_sms_consent(
                phone=lead.phone,
                consent_given=data.sms_consent,
                method="lead_form",
                language_shown="Standard SMS consent from lead form",
                lead_id=lead.id,
                ip_address=data.consent_ip,
                user_agent=data.consent_user_agent,
            )
            # Store consent_form_version if provided
            if data.consent_language_version:
                await self.compliance_service.validate_consent_language_version(
                    data.consent_language_version,
                )
            self.logger.info(
                "lead.consent_record.created",
                lead_id=str(lead.id),
                consent_given=data.sms_consent,
            )
        except Exception as e:
            self.logger.warning(
                "lead.consent_record.failed",
                lead_id=str(lead.id),
                error=str(e),
            )

    async def _update_consent_record_customer_id(
        self,
        lead_id: UUID,
        customer_id: UUID,
    ) -> None:
        """Update SmsConsentRecord customer_id for a converted lead.

        Finds existing SmsConsentRecord by lead_id and sets customer_id.
        No duplicate record is created.

        Validates: Requirement 7.5
        """
        if not self.compliance_service:
            return

        try:
            stmt = select(SmsConsentRecord).where(
                SmsConsentRecord.lead_id == lead_id,  # type: ignore[arg-type]
            )
            result = await self.compliance_service.session.execute(stmt)
            records = list(result.scalars().all())

            for record in records:
                record.customer_id = customer_id  # type: ignore[assignment]

            if records:
                await self.compliance_service.session.flush()
                self.logger.info(
                    "lead.consent_record.customer_linked",
                    lead_id=str(lead_id),
                    customer_id=str(customer_id),
                    records_updated=len(records),
                )
        except Exception as e:
            self.logger.warning(
                "lead.consent_record.customer_link_failed",
                lead_id=str(lead_id),
                error=str(e),
            )

    async def create_from_call(self, data: FromCallSubmission) -> LeadResponse:
        """Create a lead from an inbound phone call (admin-only).

        Args:
            data: FromCallSubmission schema with call data

        Returns:
            LeadResponse with created lead data

        Validates: Requirements 12.5, 13.2, 45.4, 45.5, 46.1
        """
        self.log_started("create_from_call")

        lead_source = data.lead_source.value
        source_detail = data.source_detail if data.source_detail else "Inbound call"
        intake_tag = data.intake_tag.value if data.intake_tag else None

        # Extract zip from address if not provided
        zip_code = data.zip_code
        if not zip_code and data.address:
            zip_code = extract_zip_from_address(data.address)

        # Auto-populate city/state from zip if not provided (Req 12.5)
        city: str | None = None
        state: str | None = None
        if zip_code:
            city, state = lookup_zip(zip_code)

        lead = await self.lead_repository.create(
            name=data.name,
            phone=data.phone,
            email=data.email,
            zip_code=zip_code,
            situation=data.situation.value,
            notes=data.notes,
            source_site="admin",
            status=LeadStatus.NEW.value,
            lead_source=lead_source,
            source_detail=source_detail,
            intake_tag=intake_tag,
            city=city,
            state=state,
            address=data.address,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
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

    async def create_manual_lead(self, data: ManualLeadCreate) -> LeadResponse:
        """Create a lead manually from the CRM interface.

        Args:
            data: ManualLeadCreate schema with lead data

        Returns:
            LeadResponse with created lead data

        Validates: Requirements 7.1-7.5
        """
        self.log_started("create_manual_lead")

        # Extract zip from address if not provided
        zip_code = data.zip_code
        if not zip_code and data.address:
            zip_code = extract_zip_from_address(data.address)

        # Auto-populate city/state from zip if not provided
        city = data.city
        state = data.state
        if zip_code and not city and not state:
            city, state = lookup_zip(zip_code)

        lead = await self.lead_repository.create(
            name=data.name,
            phone=data.phone,
            email=data.email,
            zip_code=zip_code,
            situation=data.situation.value,
            notes=data.notes,
            source_site="admin",
            status=LeadStatus.NEW.value,
            lead_source="manual",
            source_detail="Manual CRM entry",
            intake_tag=None,
            city=city,
            state=state,
            address=data.address,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        self.logger.info(
            "lead.manual_created",
            lead_id=str(lead.id),
        )

        self.log_completed("create_manual_lead", lead_id=str(lead.id))
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

        # Step 5: Carry over consent fields (Req 57.1, 57.2, 57.3, 68.3, 2.3, 7.5)
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

        # Carry email_marketing_consent to customer (Req 2.3)
        if lead.email_marketing_consent:
            consent_updates["email_opt_in"] = True
            consent_updates["email_opt_in_at"] = now
            consent_updates["email_opt_in_source"] = "lead_form"

        if consent_updates:
            await self.customer_service.repository.update(
                customer.id,
                consent_updates,
            )

        # Update existing SmsConsentRecord (by lead_id) to set customer_id (Req 7.5)
        if self.compliance_service:
            await self._update_consent_record_customer_id(lead.id, customer.id)

        # Step 6: Optionally create job
        job_id = None
        if data.create_job:
            # Map situation to job type and description
            situation_key = lead.situation
            _category, default_description = self.SITUATION_JOB_MAP.get(
                situation_key,
                ("requires_estimate", "Consultation"),
            )

            description = (
                data.job_description
                if data.job_description is not None
                else default_description
            )

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

    # ------------------------------------------------------------------ #
    # CRM Gap Closure: New methods (Req 12, 13, 14, 18, 19, 46)
    # ------------------------------------------------------------------ #

    async def update_action_tags(
        self,
        lead_id: UUID,
        add_tags: list[ActionTag] | None = None,
        remove_tags: list[ActionTag] | None = None,
    ) -> LeadResponse:
        """Atomically update action tags on a lead's JSONB field.

        Args:
            lead_id: UUID of the lead to update.
            add_tags: Tags to add (duplicates ignored).
            remove_tags: Tags to remove (missing tags ignored).

        Returns:
            LeadResponse with updated lead data.

        Raises:
            LeadNotFoundError: If lead not found.

        Validates: Requirements 13.2, 13.3, 13.4, 13.5, 13.6
        """
        self.log_started(
            "update_action_tags",
            lead_id=str(lead_id),
            add_tags=[t.value for t in (add_tags or [])],
            remove_tags=[t.value for t in (remove_tags or [])],
        )

        lead = await self.lead_repository.get_by_id(lead_id)
        if not lead:
            raise LeadNotFoundError(lead_id)

        current_tags: list[str] = list(lead.action_tags or [])

        # Remove tags first
        if remove_tags:
            remove_values = {t.value for t in remove_tags}
            current_tags = [t for t in current_tags if t not in remove_values]

        # Add tags (no duplicates)
        if add_tags:
            existing = set(current_tags)
            for tag in add_tags:
                if tag.value not in existing:
                    current_tags.append(tag.value)
                    existing.add(tag.value)

        await self.lead_repository.update(lead_id, {"action_tags": current_tags})

        self.logger.info(
            "lead.action_tags.updated",
            lead_id=str(lead_id),
            tags=current_tags,
        )

        self.log_completed("update_action_tags", lead_id=str(lead_id))
        updated_lead = await self.lead_repository.get_by_id(lead_id)
        return LeadResponse.model_validate(updated_lead)

    async def mark_contacted(self, lead_id: UUID) -> LeadResponse:
        """Mark a lead as contacted: remove NEEDS_CONTACT, set contacted_at.

        Args:
            lead_id: UUID of the lead.

        Returns:
            LeadResponse with updated lead data.

        Raises:
            LeadNotFoundError: If lead not found.

        Validates: Requirements 13.3
        """
        self.log_started("mark_contacted", lead_id=str(lead_id))

        lead = await self.lead_repository.get_by_id(lead_id)
        if not lead:
            raise LeadNotFoundError(lead_id)

        # Remove NEEDS_CONTACT tag
        current_tags: list[str] = list(lead.action_tags or [])
        current_tags = [t for t in current_tags if t != ActionTag.NEEDS_CONTACT.value]

        now = datetime.now(tz=timezone.utc)
        await self.lead_repository.update(
            lead_id,
            {
                "action_tags": current_tags,
                "contacted_at": now,
            },
        )

        self.logger.info(
            "lead.contacted",
            lead_id=str(lead_id),
            contacted_at=now.isoformat(),
        )

        self.log_completed("mark_contacted", lead_id=str(lead_id))
        updated_lead = await self.lead_repository.get_by_id(lead_id)
        return LeadResponse.model_validate(updated_lead)

    async def bulk_outreach(
        self,
        lead_ids: list[UUID],
        template: str,
        channel: str = "sms",
    ) -> BulkOutreachSummary:
        """Send bulk outreach to multiple leads, respecting consent.

        For SMS: skips leads without sms_consent.
        For email: skips leads without email address.
        For both: attempts both channels per lead.

        Args:
            lead_ids: List of lead UUIDs to contact.
            template: Message template text.
            channel: Communication channel (sms, email, both).

        Returns:
            BulkOutreachSummary with sent/skipped/failed counts.

        Validates: Requirements 14.1, 14.3, 14.4, 14.5
        """
        self.log_started(
            "bulk_outreach",
            lead_count=len(lead_ids),
            channel=channel,
        )

        sent = 0
        skipped = 0
        failed = 0

        for lid in lead_ids:
            lead = await self.lead_repository.get_by_id(lid)
            if not lead:
                self.logger.warning(
                    "lead.outreach.skipped",
                    lead_id=str(lid),
                    reason="not_found",
                )
                skipped += 1
                continue

            lead_sent = False

            # SMS channel
            if channel in ("sms", "both"):
                if not lead.sms_consent:
                    self.logger.info(
                        "lead.outreach.skipped",
                        lead_id=str(lead.id),
                        channel="sms",
                        reason="no_sms_consent",
                    )
                    if channel == "sms":
                        skipped += 1
                        continue
                elif not lead.phone:
                    self.logger.info(
                        "lead.outreach.skipped",
                        lead_id=str(lead.id),
                        channel="sms",
                        reason="no_phone",
                    )
                    if channel == "sms":
                        skipped += 1
                        continue
                else:
                    try:
                        if self.sms_service:
                            await self.sms_service.send_automated_message(
                                phone=lead.phone,
                                message=template,
                                message_type="campaign",
                            )
                        self.logger.info(
                            "lead.outreach.sent",
                            lead_id=str(lead.id),
                            channel="sms",
                        )
                        lead_sent = True
                    except Exception as e:
                        self.logger.warning(
                            "lead.outreach.failed",
                            lead_id=str(lead.id),
                            channel="sms",
                            error=str(e),
                        )
                        if channel == "sms":
                            failed += 1
                            continue

            # Email channel
            if channel in ("email", "both"):
                if not lead.email:
                    self.logger.info(
                        "lead.outreach.skipped",
                        lead_id=str(lead.id),
                        channel="email",
                        reason="no_email",
                    )
                    if channel == "email" and not lead_sent:
                        skipped += 1
                        continue
                else:
                    try:
                        if self.email_service:
                            self.email_service.send_lead_confirmation(lead)
                        self.logger.info(
                            "lead.outreach.sent",
                            lead_id=str(lead.id),
                            channel="email",
                        )
                        lead_sent = True
                    except Exception as e:
                        self.logger.warning(
                            "lead.outreach.failed",
                            lead_id=str(lead.id),
                            channel="email",
                            error=str(e),
                        )
                        if not lead_sent:
                            failed += 1
                            continue

            if lead_sent:
                sent += 1
            elif channel == "both":
                # Both channels failed/skipped
                skipped += 1

        summary = BulkOutreachSummary(
            sent_count=sent,
            skipped_count=skipped,
            failed_count=failed,
            total=len(lead_ids),
        )

        self.log_completed(
            "bulk_outreach",
            sent=sent,
            skipped=skipped,
            failed=failed,
        )
        return summary

    async def create_lead_from_estimate(
        self,
        customer_id: UUID,
        estimate_id: UUID,
    ) -> LeadResponse:
        """Reverse flow: create or reactivate a lead with ESTIMATE_PENDING tag.

        When an estimate requires customer approval, this creates a lead
        entry so the estimate appears in the leads pipeline.

        If an active lead already exists for this customer, reactivate it
        by adding the ESTIMATE_PENDING tag.

        Args:
            customer_id: UUID of the customer.
            estimate_id: UUID of the estimate.

        Returns:
            LeadResponse with the created/reactivated lead.

        Validates: Requirements 18.1, 18.2
        """
        self.log_started(
            "create_lead_from_estimate",
            customer_id=str(customer_id),
            estimate_id=str(estimate_id),
        )

        # Check for existing active lead for this customer
        from grins_platform.models.lead import Lead as LeadModel  # noqa: PLC0415

        stmt = (
            select(LeadModel)
            .where(LeadModel.customer_id == customer_id)
            .where(
                LeadModel.status.in_(
                    [
                        LeadStatus.NEW.value,
                        LeadStatus.CONTACTED.value,
                        LeadStatus.QUALIFIED.value,
                    ],
                ),
            )
            .order_by(LeadModel.created_at.desc())
            .limit(1)
        )
        result = await self.lead_repository.session.execute(stmt)
        existing_lead: Lead | None = result.scalar_one_or_none()

        if existing_lead:
            # Reactivate: add ESTIMATE_PENDING tag
            current_tags: list[str] = list(existing_lead.action_tags or [])
            if ActionTag.ESTIMATE_PENDING.value not in current_tags:
                current_tags.append(ActionTag.ESTIMATE_PENDING.value)
            await self.lead_repository.update(
                existing_lead.id,
                {"action_tags": current_tags},
            )
            self.logger.info(
                "lead.from_estimate.reactivated",
                lead_id=str(existing_lead.id),
                customer_id=str(customer_id),
                estimate_id=str(estimate_id),
            )
            self.log_completed(
                "create_lead_from_estimate",
                lead_id=str(existing_lead.id),
            )
            updated = await self.lead_repository.get_by_id(existing_lead.id)
            return LeadResponse.model_validate(updated)

        # Create new lead from customer data
        # Fetch customer info
        customer_detail = await self.customer_service.get_customer(
            customer_id,
            include_properties=False,
            include_service_history=False,
        )
        name = f"{customer_detail.first_name} {customer_detail.last_name}"
        phone = customer_detail.phone or ""

        lead = await self.lead_repository.create(
            name=name,
            phone=phone,
            email=customer_detail.email,
            zip_code=None,
            situation=LeadSituation.EXPLORING.value,
            notes=f"Created from estimate {estimate_id}",
            source_site="admin",
            status=LeadStatus.NEW.value,
            lead_source=LeadSourceExtended.REFERRAL.value,
            source_detail="Estimate reverse flow",
            customer_id=customer_id,
            action_tags=[ActionTag.ESTIMATE_PENDING.value],
        )

        self.logger.info(
            "lead.from_estimate.created",
            lead_id=str(lead.id),
            customer_id=str(customer_id),
            estimate_id=str(estimate_id),
        )
        self.log_completed(
            "create_lead_from_estimate",
            lead_id=str(lead.id),
        )
        return LeadResponse.model_validate(lead)

    async def migrate_work_requests(self) -> MigrationSummary:
        """One-time migration of GoogleSheetSubmission records to Lead records.

        Maps GoogleSheetSubmission fields to Lead fields:
        - name → name
        - phone → phone
        - email → email
        - city → city
        - address → address
        - client_type → source_detail
        - referral_source → lead_source (mapped)
        - service columns → situation + notes

        Skips submissions already linked to a lead (promoted_to_lead_id).

        Returns:
            MigrationSummary with counts.

        Validates: Requirements 19.1, 19.4, 19.5, 19.6
        """
        self.log_started("migrate_work_requests")

        from grins_platform.models.google_sheet_submission import (  # noqa: PLC0415
            GoogleSheetSubmission,
        )

        # Fetch all unprocessed submissions
        stmt = (
            select(GoogleSheetSubmission)
            .where(GoogleSheetSubmission.promoted_to_lead_id.is_(None))
            .order_by(GoogleSheetSubmission.created_at.asc())
        )
        result = await self.lead_repository.session.execute(stmt)
        submissions = list(result.scalars().all())

        total = len(submissions)
        migrated = 0
        skipped = 0
        errors: list[str] = []

        for sub in submissions:
            try:
                # Skip if no name or phone
                if not sub.name or not sub.phone:
                    skipped += 1
                    self.logger.info(
                        "lead.migration.skipped",
                        submission_id=str(sub.id),
                        reason="missing_name_or_phone",
                    )
                    continue

                # Determine situation from service columns
                situation = self._determine_situation_from_submission(sub)

                # Build notes from service columns
                notes = self._build_notes_from_submission(sub)

                # Determine intake tag
                intake_tag = (
                    IntakeTag.FOLLOW_UP.value
                    if situation
                    in (
                        LeadSituation.NEW_SYSTEM.value,
                        LeadSituation.UPGRADE.value,
                        LeadSituation.EXPLORING.value,
                    )
                    else IntakeTag.SCHEDULE.value
                )

                # Auto-populate city/state from zip if available
                city = sub.city
                state: str | None = None

                lead = await self.lead_repository.create(
                    name=sub.name,
                    phone=sub.phone,
                    email=sub.email,
                    zip_code=None,
                    situation=situation,
                    notes=notes,
                    source_site="google_sheets",
                    status=LeadStatus.NEW.value,
                    lead_source=LeadSourceExtended.GOOGLE_FORM.value,
                    source_detail=sub.referral_source,
                    intake_tag=intake_tag,
                    city=city,
                    state=state,
                    address=sub.address,
                    action_tags=[ActionTag.NEEDS_CONTACT.value],
                )

                # Link submission to lead
                sub.promoted_to_lead_id = lead.id
                sub.promoted_at = datetime.now(tz=timezone.utc)
                sub.processing_status = "migrated"
                await self.lead_repository.session.flush()

                migrated += 1
                self.logger.info(
                    "lead.migration.completed",
                    submission_id=str(sub.id),
                    lead_id=str(lead.id),
                )

            except Exception as e:
                error_msg = f"Submission {sub.id}: {e}"
                errors.append(error_msg)
                self.logger.warning(
                    "lead.migration.failed",
                    submission_id=str(sub.id),
                    error=str(e),
                )

        summary = MigrationSummary(
            total_submissions=total,
            migrated_count=migrated,
            skipped_count=skipped,
            error_count=len(errors),
            errors=errors,
        )

        self.log_completed(
            "migrate_work_requests",
            total=total,
            migrated=migrated,
            skipped=skipped,
            errors=len(errors),
        )
        return summary

    @staticmethod
    def _determine_situation_from_submission(
        sub: GoogleSheetSubmission,
    ) -> str:
        """Map GoogleSheetSubmission service columns to LeadSituation.

        Args:
            sub: GoogleSheetSubmission instance.

        Returns:
            Situation string value.
        """
        if sub.new_system_install:
            return LeadSituation.NEW_SYSTEM.value
        if sub.addition_to_system:
            return LeadSituation.UPGRADE.value
        if sub.repair_existing:
            return LeadSituation.REPAIR.value
        if sub.spring_startup or sub.fall_blowout or sub.summer_tuneup:
            return LeadSituation.REPAIR.value
        return LeadSituation.EXPLORING.value

    @staticmethod
    def _build_notes_from_submission(
        sub: GoogleSheetSubmission,
    ) -> str | None:
        """Build notes string from GoogleSheetSubmission service columns.

        Args:
            sub: GoogleSheetSubmission instance.

        Returns:
            Combined notes string or None.
        """
        parts: list[str] = []
        if sub.spring_startup:
            parts.append(f"Spring Startup: {sub.spring_startup}")
        if sub.fall_blowout:
            parts.append(f"Fall Blowout: {sub.fall_blowout}")
        if sub.summer_tuneup:
            parts.append(f"Summer Tuneup: {sub.summer_tuneup}")
        if sub.repair_existing:
            parts.append(f"Repair: {sub.repair_existing}")
        if sub.new_system_install:
            parts.append(f"New System: {sub.new_system_install}")
        if sub.addition_to_system:
            parts.append(f"Addition: {sub.addition_to_system}")
        if sub.additional_services_info:
            parts.append(f"Additional: {sub.additional_services_info}")
        if sub.date_work_needed_by:
            parts.append(f"Needed by: {sub.date_work_needed_by}")
        if sub.property_type:
            parts.append(f"Property: {sub.property_type}")
        if sub.landscape_hardscape:
            parts.append(f"Landscape: {sub.landscape_hardscape}")
        return "; ".join(parts) if parts else None
