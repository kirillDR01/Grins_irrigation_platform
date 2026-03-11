"""Functional tests for lead service extensions.

Tests full lead workflows with mocked repositories, verifying
cross-service interactions as a user would experience them.

Validates: Requirements 63.2
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    IntakeTag,
    LeadSituation,
    LeadSourceExtended,
    LeadStatus,
)
from grins_platform.repositories.google_sheet_submission_repository import (
    GoogleSheetSubmissionRepository,
)
from grins_platform.repositories.lead_repository import LeadRepository
from grins_platform.schemas.lead import (
    FromCallSubmission,
    LeadConversionRequest,
    LeadSubmission,
    LeadUpdate,
)
from grins_platform.services.google_sheets_service import GoogleSheetsService
from grins_platform.services.lead_service import LeadService

# =============================================================================
# Helpers
# =============================================================================


def _make_lead(**overrides: Any) -> MagicMock:
    lead = MagicMock()
    lead.id = overrides.get("id", uuid4())
    lead.name = overrides.get("name", "Test User")
    lead.phone = overrides.get("phone", "6125551234")
    lead.email = overrides.get("email")
    lead.zip_code = overrides.get("zip_code", "55424")
    lead.situation = overrides.get("situation", LeadSituation.NEW_SYSTEM.value)
    lead.notes = overrides.get("notes")
    lead.source_site = overrides.get("source_site", "residential")
    lead.lead_source = overrides.get("lead_source", "website")
    lead.source_detail = overrides.get("source_detail")
    lead.intake_tag = overrides.get("intake_tag", "schedule")
    lead.sms_consent = overrides.get("sms_consent", False)
    lead.terms_accepted = overrides.get("terms_accepted", False)
    lead.email_marketing_consent = overrides.get(
        "email_marketing_consent",
        False,
    )
    lead.status = overrides.get("status", LeadStatus.NEW.value)
    lead.assigned_to = overrides.get("assigned_to")
    lead.customer_id = overrides.get("customer_id")
    lead.contacted_at = overrides.get("contacted_at")
    lead.converted_at = overrides.get("converted_at")
    lead.created_at = overrides.get(
        "created_at",
        datetime.now(tz=timezone.utc),
    )
    lead.updated_at = datetime.now(tz=timezone.utc)
    return lead


def _build_service(
    *,
    lead_repo: AsyncMock | None = None,
    customer_service: AsyncMock | None = None,
    job_service: AsyncMock | None = None,
    staff_repo: AsyncMock | None = None,
    sms_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
    compliance_service: AsyncMock | None = None,
) -> tuple[LeadService, AsyncMock, AsyncMock, AsyncMock]:
    repo = lead_repo or AsyncMock()
    cust_svc = customer_service or AsyncMock()
    job_svc = job_service or AsyncMock()
    svc = LeadService(
        lead_repository=repo,
        customer_service=cust_svc,
        job_service=job_svc,
        staff_repository=staff_repo or AsyncMock(),
        sms_service=sms_service,
        email_service=email_service,
        compliance_service=compliance_service,
    )
    return svc, repo, cust_svc, job_svc


# =============================================================================
# Lead creation with source and intake tag persisted
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestLeadCreationSourceAndTag:
    """Test lead creation persists source and intake tag.

    Validates: Requirement 63.2
    """

    async def test_website_submission_persists_source_and_tag(self) -> None:
        """Website form submission stores WEBSITE source and SCHEDULE tag."""
        svc, repo, _, _ = _build_service()
        created = _make_lead(
            lead_source=LeadSourceExtended.WEBSITE.value,
            intake_tag=IntakeTag.SCHEDULE.value,
        )
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = created

        data = LeadSubmission(
            name="Jane Doe",
            phone="(612) 555-1234",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        call_kwargs = repo.create.call_args[1]
        assert call_kwargs["lead_source"] == LeadSourceExtended.WEBSITE.value
        assert call_kwargs["intake_tag"] == IntakeTag.SCHEDULE.value

    async def test_from_call_persists_phone_call_source_and_null_tag(
        self,
    ) -> None:
        """From-call creation stores PHONE_CALL source and NULL tag."""
        svc, repo, _, _ = _build_service()
        created = _make_lead(
            lead_source=LeadSourceExtended.PHONE_CALL.value,
            intake_tag=None,
        )
        repo.create.return_value = created

        data = FromCallSubmission(
            name="Bob Smith",
            phone="(612) 555-5678",
            zip_code="55346",
            situation=LeadSituation.REPAIR,
        )
        result = await svc.create_from_call(data)

        assert result.id == created.id
        call_kwargs = repo.create.call_args[1]
        assert call_kwargs["lead_source"] == LeadSourceExtended.PHONE_CALL.value
        assert call_kwargs["intake_tag"] is None

    async def test_explicit_source_overrides_default(self) -> None:
        """Explicit lead_source on submission overrides WEBSITE default."""
        svc, repo, _, _ = _build_service()
        created = _make_lead(
            lead_source=LeadSourceExtended.REFERRAL.value,
            intake_tag=IntakeTag.FOLLOW_UP.value,
        )
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = created

        data = LeadSubmission(
            name="Ref Lead",
            phone="(612) 555-9999",
            zip_code="55424",
            situation=LeadSituation.EXPLORING,
            source_site="residential",
            lead_source=LeadSourceExtended.REFERRAL,
            intake_tag=IntakeTag.FOLLOW_UP,
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        call_kwargs = repo.create.call_args[1]
        assert call_kwargs["lead_source"] == LeadSourceExtended.REFERRAL.value
        assert call_kwargs["intake_tag"] == IntakeTag.FOLLOW_UP.value


# =============================================================================
# Follow-up queue returns correct filtered/sorted results
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestFollowUpQueueFiltering:
    """Test follow-up queue returns correct filtered and sorted results.

    Validates: Requirement 63.2
    """

    async def test_follow_up_queue_returns_only_follow_up_leads(
        self,
    ) -> None:
        """Queue returns leads with FOLLOW_UP tag and active status."""
        svc, repo, _, _ = _build_service()

        old = _make_lead(
            intake_tag=IntakeTag.FOLLOW_UP.value,
            status=LeadStatus.NEW.value,
            created_at=datetime.now(tz=timezone.utc) - timedelta(hours=5),
        )
        recent = _make_lead(
            intake_tag=IntakeTag.FOLLOW_UP.value,
            status=LeadStatus.CONTACTED.value,
            created_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
        )
        # Repo returns sorted by created_at ASC (oldest first)
        repo.get_follow_up_queue.return_value = ([old, recent], 2)

        result = await svc.get_follow_up_queue(page=1, page_size=20)

        assert result.total == 2
        assert len(result.items) == 2
        # time_since_created computed
        assert result.items[0].time_since_created > result.items[1].time_since_created

    async def test_follow_up_queue_empty_when_no_follow_up_leads(
        self,
    ) -> None:
        """Queue returns empty when no FOLLOW_UP leads exist."""
        svc, repo, _, _ = _build_service()
        repo.get_follow_up_queue.return_value = ([], 0)

        result = await svc.get_follow_up_queue()

        assert result.total == 0
        assert len(result.items) == 0
        assert result.total_pages == 0

    async def test_follow_up_queue_pagination(self) -> None:
        """Queue respects pagination parameters."""
        svc, repo, _, _ = _build_service()
        leads = [
            _make_lead(
                intake_tag=IntakeTag.FOLLOW_UP.value,
                status=LeadStatus.NEW.value,
            )
            for _ in range(2)
        ]
        repo.get_follow_up_queue.return_value = (leads, 5)

        result = await svc.get_follow_up_queue(page=2, page_size=2)

        assert result.page == 2
        assert result.page_size == 2
        assert result.total == 5
        assert result.total_pages == 3
        repo.get_follow_up_queue.assert_called_once_with(page=2, page_size=2)


# =============================================================================
# Work request auto-promotion creating linked lead records
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestWorkRequestAutoPromotion:
    """Test work request auto-promotion creates linked lead records.

    Note: Auto-promotion logic lives in GoogleSheetsService.process_row.
    These tests verify the integration pattern with mocked repos.

    Validates: Requirement 63.2
    """

    async def test_new_client_work_request_creates_lead(self) -> None:
        """New client work request creates lead with GOOGLE_FORM source."""
        session = AsyncMock()
        gs_svc = GoogleSheetsService(submission_repo=None, lead_repo=None)

        sub_mock = MagicMock()
        sub_mock.id = uuid4()
        sub_mock.processing_status = "lead_created"
        sub_mock.lead_id = uuid4()

        lead_mock = _make_lead(
            lead_source=LeadSourceExtended.GOOGLE_FORM.value,
            source_detail="New client work request",
        )

        with pytest.MonkeyPatch.context() as mp:
            sub_repo = AsyncMock(spec=GoogleSheetSubmissionRepository)
            sub_repo.create.return_value = sub_mock
            sub_repo.update.return_value = None
            sub_repo.get_by_id.return_value = sub_mock

            lead_repo = AsyncMock(spec=LeadRepository)
            lead_repo.get_by_phone_and_active_status.return_value = None
            lead_repo.get_recent_by_phone_or_email.return_value = None
            lead_repo.create.return_value = lead_mock

            mp.setattr(
                "grins_platform.services.google_sheets_service"
                ".GoogleSheetSubmissionRepository",
                lambda _s: sub_repo,
            )
            mp.setattr(
                "grins_platform.services.google_sheets_service.LeadRepository",
                lambda _s: lead_repo,
            )

            row = [
                "2026-03-10",  # timestamp
                "Yes",  # spring_startup
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "John Doe",  # name
                "6125551234",  # phone
                "john@example.com",  # email
                "Minneapolis",  # city
                "123 Main St",  # address
                "New",  # client_type
                "Residential",  # property_type
                "",
                "",
            ]
            await gs_svc.process_row(row, 2, session)

            lead_repo.create.assert_called_once()
            create_kwargs = lead_repo.create.call_args[1]
            assert create_kwargs["lead_source"] == LeadSourceExtended.GOOGLE_FORM.value
            assert create_kwargs["source_detail"] == "New client work request"

            # Verify promoted_to_lead_id set
            update_call = sub_repo.update.call_args[0][1]
            assert update_call["promoted_to_lead_id"] is not None
            assert update_call["promoted_at"] is not None

    async def test_existing_client_work_request_creates_lead(self) -> None:
        """Existing client work request also creates lead (auto-promotion)."""
        session = AsyncMock()
        gs_svc = GoogleSheetsService(submission_repo=None, lead_repo=None)

        sub_mock = MagicMock()
        sub_mock.id = uuid4()
        sub_mock.processing_status = "lead_created"
        sub_mock.lead_id = uuid4()

        lead_mock = _make_lead(
            lead_source=LeadSourceExtended.GOOGLE_FORM.value,
            source_detail="Existing client work request",
        )

        with pytest.MonkeyPatch.context() as mp:
            sub_repo = AsyncMock(spec=GoogleSheetSubmissionRepository)
            sub_repo.create.return_value = sub_mock
            sub_repo.update.return_value = None
            sub_repo.get_by_id.return_value = sub_mock

            lead_repo = AsyncMock(spec=LeadRepository)
            lead_repo.get_by_phone_and_active_status.return_value = None
            lead_repo.get_recent_by_phone_or_email.return_value = None
            lead_repo.create.return_value = lead_mock

            mp.setattr(
                "grins_platform.services.google_sheets_service"
                ".GoogleSheetSubmissionRepository",
                lambda _s: sub_repo,
            )
            mp.setattr(
                "grins_platform.services.google_sheets_service.LeadRepository",
                lambda _s: lead_repo,
            )

            row = [
                "2026-03-10",
                "",
                "",
                "",
                "Yes",  # repair_existing
                "",
                "",
                "",
                "",
                "Jane Smith",
                "6125559876",
                "",
                "Edina",
                "456 Oak Ave",
                "Existing",  # client_type
                "Commercial",
                "",
                "",
            ]
            await gs_svc.process_row(row, 3, session)

            lead_repo.create.assert_called_once()
            create_kwargs = lead_repo.create.call_args[1]
            assert create_kwargs["source_detail"] == "Existing client work request"
            assert create_kwargs["lead_source"] == LeadSourceExtended.GOOGLE_FORM.value


# =============================================================================
# PATCH intake_tag changes tag and updates follow-up queue membership
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestIntakeTagPatch:
    """Test PATCH intake_tag changes tag and affects follow-up queue.

    Validates: Requirement 63.2
    """

    async def test_change_intake_tag_to_follow_up(self) -> None:
        """Changing intake_tag to FOLLOW_UP makes lead appear in queue."""
        svc, repo, _, _ = _build_service()

        original = _make_lead(intake_tag=IntakeTag.SCHEDULE.value)
        updated = _make_lead(
            id=original.id,
            intake_tag=IntakeTag.FOLLOW_UP.value,
        )
        repo.get_by_id.return_value = original
        repo.update.return_value = updated

        result = await svc.update_lead(
            original.id,
            LeadUpdate(intake_tag=IntakeTag.FOLLOW_UP),
        )

        assert result.intake_tag == IntakeTag.FOLLOW_UP
        update_data = repo.update.call_args[0][1]
        assert update_data["intake_tag"] == IntakeTag.FOLLOW_UP.value

    async def test_change_intake_tag_to_schedule_removes_from_queue(
        self,
    ) -> None:
        """Changing intake_tag to SCHEDULE removes lead from follow-up queue."""
        svc, repo, _, _ = _build_service()

        original = _make_lead(intake_tag=IntakeTag.FOLLOW_UP.value)
        updated = _make_lead(
            id=original.id,
            intake_tag=IntakeTag.SCHEDULE.value,
        )
        repo.get_by_id.return_value = original
        repo.update.return_value = updated

        result = await svc.update_lead(
            original.id,
            LeadUpdate(intake_tag=IntakeTag.SCHEDULE),
        )

        assert result.intake_tag == IntakeTag.SCHEDULE
        update_data = repo.update.call_args[0][1]
        assert update_data["intake_tag"] == IntakeTag.SCHEDULE.value

    async def test_tag_change_then_queue_reflects_update(self) -> None:
        """After tag change, follow-up queue reflects the update."""
        svc, repo, _, _ = _build_service()
        lead_id = uuid4()

        # Step 1: Lead starts as SCHEDULE
        original = _make_lead(
            id=lead_id,
            intake_tag=IntakeTag.SCHEDULE.value,
            status=LeadStatus.NEW.value,
        )
        updated = _make_lead(
            id=lead_id,
            intake_tag=IntakeTag.FOLLOW_UP.value,
            status=LeadStatus.NEW.value,
        )
        repo.get_by_id.return_value = original
        repo.update.return_value = updated

        # Step 2: Change to FOLLOW_UP
        await svc.update_lead(lead_id, LeadUpdate(intake_tag=IntakeTag.FOLLOW_UP))

        # Step 3: Follow-up queue now includes this lead
        repo.get_follow_up_queue.return_value = ([updated], 1)
        queue = await svc.get_follow_up_queue()

        assert queue.total == 1
        assert queue.items[0].id == lead_id


# =============================================================================
# Lead consent fields carry over to customer on conversion
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestConsentCarryOver:
    """Test consent fields carry over from lead to customer on conversion.

    Validates: Requirement 63.2
    """

    async def test_sms_consent_carries_to_customer(self) -> None:
        """Lead with sms_consent=true creates customer with consent record."""
        compliance = AsyncMock()
        cust_svc = AsyncMock()
        customer = MagicMock()
        customer.id = uuid4()
        cust_svc.create_customer.return_value = customer
        cust_svc.repository = AsyncMock()

        svc, repo, _, _ = _build_service(
            customer_service=cust_svc,
            compliance_service=compliance,
        )

        lead = _make_lead(
            sms_consent=True,
            terms_accepted=False,
            status=LeadStatus.QUALIFIED.value,
        )
        repo.get_by_id.return_value = lead
        repo.update.return_value = _make_lead(
            id=lead.id,
            status=LeadStatus.CONVERTED.value,
        )

        result = await svc.convert_lead(
            lead.id,
            LeadConversionRequest(create_job=False),
        )

        assert result.success is True
        # Verify sms_consent_record created
        compliance.create_sms_consent.assert_called_once()
        call_kwargs = compliance.create_sms_consent.call_args[1]
        assert call_kwargs["phone"] == lead.phone
        assert call_kwargs["consent_given"] is True
        assert call_kwargs["method"] == "lead_form"
        assert call_kwargs["customer_id"] == customer.id

        # Verify customer updated with sms_opt_in_at
        update_data = cust_svc.repository.update.call_args[0][1]
        assert "sms_opt_in_at" in update_data
        assert update_data["sms_opt_in_source"] == "lead_form"

    async def test_terms_accepted_carries_to_customer(self) -> None:
        """Lead with terms_accepted=true sets terms on customer."""
        cust_svc = AsyncMock()
        customer = MagicMock()
        customer.id = uuid4()
        cust_svc.create_customer.return_value = customer
        cust_svc.repository = AsyncMock()

        svc, repo, _, _ = _build_service(customer_service=cust_svc)

        lead = _make_lead(
            sms_consent=False,
            terms_accepted=True,
            status=LeadStatus.QUALIFIED.value,
        )
        repo.get_by_id.return_value = lead
        repo.update.return_value = _make_lead(
            id=lead.id,
            status=LeadStatus.CONVERTED.value,
        )

        await svc.convert_lead(
            lead.id,
            LeadConversionRequest(create_job=False),
        )

        update_data = cust_svc.repository.update.call_args[0][1]
        assert update_data["terms_accepted"] is True
        assert "terms_accepted_at" in update_data

    async def test_email_carries_opt_in_to_customer(self) -> None:
        """Lead with email sets email_opt_in_at on customer."""
        cust_svc = AsyncMock()
        customer = MagicMock()
        customer.id = uuid4()
        cust_svc.create_customer.return_value = customer
        cust_svc.repository = AsyncMock()

        svc, repo, _, _ = _build_service(customer_service=cust_svc)

        lead = _make_lead(
            email="test@example.com",
            status=LeadStatus.QUALIFIED.value,
        )
        repo.get_by_id.return_value = lead
        repo.update.return_value = _make_lead(
            id=lead.id,
            status=LeadStatus.CONVERTED.value,
        )

        await svc.convert_lead(
            lead.id,
            LeadConversionRequest(create_job=False),
        )

        update_data = cust_svc.repository.update.call_args[0][1]
        assert "email_opt_in_at" in update_data
        assert update_data["email_opt_in_source"] == "lead_form"

    async def test_no_consent_no_carry_over(self) -> None:
        """Lead with no consent fields does not update customer consent."""
        cust_svc = AsyncMock()
        customer = MagicMock()
        customer.id = uuid4()
        cust_svc.create_customer.return_value = customer
        cust_svc.repository = AsyncMock()

        svc, repo, _, _ = _build_service(customer_service=cust_svc)

        lead = _make_lead(
            sms_consent=False,
            terms_accepted=False,
            email=None,
            status=LeadStatus.QUALIFIED.value,
        )
        repo.get_by_id.return_value = lead
        repo.update.return_value = _make_lead(
            id=lead.id,
            status=LeadStatus.CONVERTED.value,
        )

        await svc.convert_lead(
            lead.id,
            LeadConversionRequest(create_job=False),
        )

        # No consent updates should be made
        cust_svc.repository.update.assert_not_called()

    async def test_full_consent_carry_over_pipeline(self) -> None:
        """Lead with all consent fields carries everything to customer."""
        compliance = AsyncMock()
        cust_svc = AsyncMock()
        customer = MagicMock()
        customer.id = uuid4()
        cust_svc.create_customer.return_value = customer
        cust_svc.repository = AsyncMock()

        job_svc = AsyncMock()
        job = MagicMock()
        job.id = uuid4()
        job_svc.create_job.return_value = job

        svc, repo, _, _ = _build_service(
            customer_service=cust_svc,
            job_service=job_svc,
            compliance_service=compliance,
        )

        lead = _make_lead(
            sms_consent=True,
            terms_accepted=True,
            email="full@example.com",
            status=LeadStatus.QUALIFIED.value,
        )
        repo.get_by_id.return_value = lead
        repo.update.return_value = _make_lead(
            id=lead.id,
            status=LeadStatus.CONVERTED.value,
            customer_id=customer.id,
        )

        result = await svc.convert_lead(
            lead.id,
            LeadConversionRequest(create_job=True),
        )

        assert result.success is True
        assert result.customer_id == customer.id
        assert result.job_id == job.id

        # All consent fields carried over
        update_data = cust_svc.repository.update.call_args[0][1]
        assert "sms_opt_in_at" in update_data
        assert update_data["sms_opt_in_source"] == "lead_form"
        assert update_data["terms_accepted"] is True
        assert "terms_accepted_at" in update_data
        assert "email_opt_in_at" in update_data
        assert update_data["email_opt_in_source"] == "lead_form"

        # SMS consent record created
        compliance.create_sms_consent.assert_called_once()
