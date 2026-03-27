"""Functional tests for lead operations.

Tests lead creation with address fields, action tag lifecycle,
bulk outreach, attachment management, and work request migration
with mocked repositories and external services.

Validates: Requirements 12.7, 13.10, 14.7, 15.7, 19.8
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    ActionTag,
    LeadSituation,
    LeadSourceExtended,
    LeadStatus,
)
from grins_platform.schemas.lead import (
    FromCallSubmission,
    LeadSubmission,
)
from grins_platform.services.lead_service import LeadService
from grins_platform.services.photo_service import (
    PhotoService,
    UploadContext,
    UploadResult,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_lead(**overrides: Any) -> MagicMock:
    """Create a mock Lead with all fields."""
    lead = MagicMock()
    lead.id = overrides.get("id", uuid4())
    lead.name = overrides.get("name", "Test User")
    lead.phone = overrides.get("phone", "5125551234")
    lead.email = overrides.get("email")
    lead.zip_code = overrides.get("zip_code", "78701")
    lead.situation = overrides.get("situation", LeadSituation.NEW_SYSTEM.value)
    lead.notes = overrides.get("notes")
    lead.source_site = overrides.get("source_site", "residential")
    lead.lead_source = overrides.get("lead_source", "website")
    lead.source_detail = overrides.get("source_detail")
    lead.intake_tag = overrides.get("intake_tag", "schedule")
    lead.sms_consent = overrides.get("sms_consent", True)
    lead.terms_accepted = overrides.get("terms_accepted", False)
    lead.email_marketing_consent = overrides.get(
        "email_marketing_consent",
        False,
    )
    lead.page_url = overrides.get("page_url")
    lead.city = overrides.get("city")
    lead.state = overrides.get("state")
    lead.address = overrides.get("address")
    lead.action_tags = overrides.get("action_tags", [ActionTag.NEEDS_CONTACT.value])
    lead.status = overrides.get("status", LeadStatus.NEW.value)
    lead.assigned_to = overrides.get("assigned_to")
    lead.customer_id = overrides.get("customer_id")
    lead.contacted_at = overrides.get("contacted_at")
    lead.converted_at = overrides.get("converted_at")
    lead.created_at = overrides.get(
        "created_at",
        datetime.now(tz=timezone.utc),
    )
    lead.customer_type = overrides.get("customer_type")
    lead.property_type = overrides.get("property_type")
    lead.updated_at = datetime.now(tz=timezone.utc)
    return lead


def _make_submission(**overrides: Any) -> MagicMock:
    """Create a mock GoogleSheetSubmission."""
    sub = MagicMock()
    sub.id = overrides.get("id", uuid4())
    sub.name = overrides.get("name", "John Doe")
    sub.phone = overrides.get("phone", "5125559999")
    sub.email = overrides.get("email", "john@example.com")
    sub.city = overrides.get("city", "Austin")
    sub.address = overrides.get("address", "100 Main St")
    sub.referral_source = overrides.get("referral_source", "Google")
    sub.client_type = overrides.get("client_type", "New")
    sub.new_system_install = overrides.get("new_system_install", "Yes")
    sub.addition_to_system = overrides.get("addition_to_system")
    sub.repair_existing = overrides.get("repair_existing")
    sub.spring_startup = overrides.get("spring_startup")
    sub.fall_blowout = overrides.get("fall_blowout")
    sub.summer_tuneup = overrides.get("summer_tuneup")
    sub.additional_services_info = overrides.get("additional_services_info")
    sub.date_work_needed_by = overrides.get("date_work_needed_by")
    sub.property_type = overrides.get("property_type")
    sub.landscape_hardscape = overrides.get("landscape_hardscape")
    sub.promoted_to_lead_id = overrides.get("promoted_to_lead_id")
    sub.promoted_at = overrides.get("promoted_at")
    sub.processing_status = overrides.get("processing_status", "imported")
    sub.created_at = overrides.get(
        "created_at",
        datetime.now(tz=timezone.utc),
    )
    return sub


def _build_service(
    *,
    lead_repo: AsyncMock | None = None,
    customer_service: AsyncMock | None = None,
    job_service: AsyncMock | None = None,
    staff_repo: AsyncMock | None = None,
    sms_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
    compliance_service: AsyncMock | None = None,
) -> tuple[LeadService, AsyncMock]:
    """Build a LeadService with mocked dependencies."""
    repo = lead_repo or AsyncMock()
    svc = LeadService(
        lead_repository=repo,
        customer_service=customer_service or AsyncMock(),
        job_service=job_service or AsyncMock(),
        staff_repository=staff_repo or AsyncMock(),
        sms_service=sms_service,
        email_service=email_service,
        compliance_service=compliance_service,
    )
    return svc, repo


def _build_mock_s3_client() -> MagicMock:
    """Build a mock S3 client for attachment operations."""
    client = MagicMock()
    client.put_object = MagicMock(return_value={"ETag": '"abc123"'})
    client.delete_object = MagicMock(return_value={})
    client.generate_presigned_url = MagicMock(
        return_value="https://s3.example.com/presigned-url",
    )
    paginator = MagicMock()
    paginator.paginate = MagicMock(return_value=[{"Contents": []}])
    client.get_paginator = MagicMock(return_value=paginator)
    return client


# =============================================================================
# 1. Lead Creation with Full Address Fields
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestLeadCreationWithAddressFields:
    """Test lead creation persists address, city, state, zip_code.

    Validates: Requirement 12.7
    """

    async def test_submit_lead_with_full_address_as_user_would_experience(
        self,
    ) -> None:
        """Website submission with address fields stores all location data."""
        svc, repo = _build_service()
        created = _make_lead(
            address="742 Evergreen Terrace",
            city="Austin",
            state="TX",
            zip_code="78701",
        )
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = created

        data = LeadSubmission(
            name="Homer Simpson",
            phone="(512) 555-1234",
            zip_code="78701",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
            address="742 Evergreen Terrace",
            city="Austin",
            state="TX",
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        call_kwargs = repo.create.call_args[1]
        assert call_kwargs["address"] == "742 Evergreen Terrace"
        assert call_kwargs["city"] == "Austin"
        assert call_kwargs["state"] == "TX"

    async def test_from_call_auto_populates_city_state_from_zip(
        self,
    ) -> None:
        """From-call creation auto-populates city/state via zip lookup."""
        svc, repo = _build_service()
        created = _make_lead(
            city="Austin",
            state="TX",
            zip_code="78701",
        )
        repo.create.return_value = created

        data = FromCallSubmission(
            name="Marge Simpson",
            phone="(512) 555-5678",
            zip_code="78701",
            situation=LeadSituation.REPAIR,
        )
        result = await svc.create_from_call(data)

        assert result.id == created.id
        call_kwargs = repo.create.call_args[1]
        # zip_code is passed through; city/state come from lookup
        assert "city" in call_kwargs
        assert "state" in call_kwargs

    async def test_submit_lead_without_address_still_succeeds(
        self,
    ) -> None:
        """Submission without address fields still creates lead."""
        svc, repo = _build_service()
        created = _make_lead(address=None, city=None, state=None)
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = created

        data = LeadSubmission(
            name="Bart Simpson",
            phone="(512) 555-9999",
            zip_code="78701",
            situation=LeadSituation.EXPLORING,
            source_site="residential",
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        assert result.lead_id == created.id


# =============================================================================
# 2. Full Tag Lifecycle: creation → contact → estimate → approval
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestActionTagLifecycle:
    """Test full action tag lifecycle as user would experience.

    Validates: Requirement 13.10
    """

    async def test_full_tag_lifecycle_creation_to_approval(self) -> None:
        """Lead progresses: NEEDS_CONTACT → NEEDS_ESTIMATE → PENDING → APPROVED."""
        lead_id = uuid4()
        svc, repo = _build_service()

        # Step 1: New lead created with NEEDS_CONTACT tag
        lead_v1 = _make_lead(
            id=lead_id,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )
        repo.create.return_value = lead_v1
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None

        data = LeadSubmission(
            name="Tag Lifecycle",
            phone="(512) 555-0001",
            zip_code="78701",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
        )
        submit_result = await svc.submit_lead(data)
        assert submit_result.success is True
        create_kwargs = repo.create.call_args[1]
        assert ActionTag.NEEDS_CONTACT.value in create_kwargs["action_tags"]

        # Step 2: Mark contacted — removes NEEDS_CONTACT
        lead_v2 = _make_lead(
            id=lead_id,
            action_tags=[],
            contacted_at=datetime.now(tz=timezone.utc),
        )
        repo.get_by_id.return_value = lead_v1
        repo.update.return_value = lead_v2

        repo.get_by_id.side_effect = [lead_v1, lead_v2]
        contacted = await svc.mark_contacted(lead_id)
        assert contacted.contacted_at is not None

        # Verify NEEDS_CONTACT was removed
        update_call = repo.update.call_args
        update_data = update_call[0][1]
        assert ActionTag.NEEDS_CONTACT.value not in update_data["action_tags"]

        # Step 3: Add NEEDS_ESTIMATE tag
        lead_v3 = _make_lead(
            id=lead_id,
            action_tags=[ActionTag.NEEDS_ESTIMATE.value],
        )
        repo.get_by_id.side_effect = [lead_v2, lead_v3]
        repo.update.return_value = lead_v3

        result = await svc.update_action_tags(
            lead_id,
            add_tags=[ActionTag.NEEDS_ESTIMATE],
        )
        assert ActionTag.NEEDS_ESTIMATE.value in result.action_tags

        # Step 4: Transition to ESTIMATE_PENDING
        lead_v4 = _make_lead(
            id=lead_id,
            action_tags=[ActionTag.ESTIMATE_PENDING.value],
        )
        repo.get_by_id.side_effect = [lead_v3, lead_v4]
        repo.update.return_value = lead_v4

        result = await svc.update_action_tags(
            lead_id,
            add_tags=[ActionTag.ESTIMATE_PENDING],
            remove_tags=[ActionTag.NEEDS_ESTIMATE],
        )
        assert ActionTag.ESTIMATE_PENDING.value in result.action_tags
        assert ActionTag.NEEDS_ESTIMATE.value not in result.action_tags

        # Step 5: Estimate approved (remove ESTIMATE_PENDING, add ESTIMATE_APPROVED)
        lead_v5 = _make_lead(
            id=lead_id,
            action_tags=[ActionTag.ESTIMATE_APPROVED.value],
        )
        repo.get_by_id.side_effect = [lead_v4, lead_v5]
        repo.update.return_value = lead_v5

        result = await svc.update_action_tags(
            lead_id,
            add_tags=[ActionTag.ESTIMATE_APPROVED],
            remove_tags=[ActionTag.ESTIMATE_PENDING],
        )
        assert ActionTag.ESTIMATE_APPROVED.value in result.action_tags
        assert ActionTag.ESTIMATE_PENDING.value not in result.action_tags

    async def test_add_duplicate_tag_is_idempotent(self) -> None:
        """Adding a tag that already exists does not create duplicates."""
        lead_id = uuid4()
        svc, repo = _build_service()

        lead = _make_lead(
            id=lead_id,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )
        repo.get_by_id.side_effect = [lead, lead]

        await svc.update_action_tags(
            lead_id,
            add_tags=[ActionTag.NEEDS_CONTACT],
        )

        update_data = repo.update.call_args[0][1]
        # Should still have exactly one NEEDS_CONTACT
        assert (
            update_data["action_tags"].count(
                ActionTag.NEEDS_CONTACT.value,
            )
            == 1
        )

    async def test_remove_nonexistent_tag_is_safe(self) -> None:
        """Removing a tag that doesn't exist does not error."""
        lead_id = uuid4()
        svc, repo = _build_service()

        lead = _make_lead(
            id=lead_id,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )
        repo.get_by_id.side_effect = [lead, lead]

        await svc.update_action_tags(
            lead_id,
            remove_tags=[ActionTag.ESTIMATE_APPROVED],
        )

        update_data = repo.update.call_args[0][1]
        assert ActionTag.NEEDS_CONTACT.value in update_data["action_tags"]


# =============================================================================
# 3. Bulk Outreach Sends to Multiple Leads
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestBulkOutreachWorkflow:
    """Test bulk outreach sends to multiple leads with correct summary.

    Validates: Requirement 14.7
    """

    async def test_bulk_outreach_sends_sms_to_consented_leads(
        self,
    ) -> None:
        """Bulk SMS outreach sends to leads with consent and returns counts."""
        sms_svc = AsyncMock()
        sms_svc.send_automated_message = AsyncMock(
            return_value={"success": True},
        )
        svc, repo = _build_service(sms_service=sms_svc)

        lead1 = _make_lead(sms_consent=True, phone="5125550001")
        lead2 = _make_lead(sms_consent=True, phone="5125550002")
        lead3 = _make_lead(sms_consent=True, phone="5125550003")

        repo.get_by_id.side_effect = [lead1, lead2, lead3]

        summary = await svc.bulk_outreach(
            lead_ids=[lead1.id, lead2.id, lead3.id],
            template="Spring special! 20% off irrigation check.",
            channel="sms",
        )

        assert summary.sent_count == 3
        assert summary.skipped_count == 0
        assert summary.failed_count == 0
        assert summary.total == 3
        assert sms_svc.send_automated_message.call_count == 3

    async def test_bulk_outreach_skips_leads_without_consent(
        self,
    ) -> None:
        """Leads without SMS consent are skipped in bulk outreach."""
        sms_svc = AsyncMock()
        sms_svc.send_automated_message = AsyncMock(
            return_value={"success": True},
        )
        svc, repo = _build_service(sms_service=sms_svc)

        consented = _make_lead(sms_consent=True, phone="5125550001")
        no_consent = _make_lead(sms_consent=False, phone="5125550002")
        no_phone = _make_lead(sms_consent=True, phone="")

        repo.get_by_id.side_effect = [consented, no_consent, no_phone]

        summary = await svc.bulk_outreach(
            lead_ids=[consented.id, no_consent.id, no_phone.id],
            template="Check-up reminder",
            channel="sms",
        )

        assert summary.sent_count == 1
        assert summary.skipped_count == 2
        assert summary.total == 3

    async def test_bulk_outreach_handles_send_failures(self) -> None:
        """Failed SMS sends are counted in failed_count."""
        sms_svc = AsyncMock()
        sms_svc.send_automated_message = AsyncMock(
            side_effect=[
                {"success": True},
                Exception("Twilio error"),
            ],
        )
        svc, repo = _build_service(sms_service=sms_svc)

        lead1 = _make_lead(sms_consent=True, phone="5125550001")
        lead2 = _make_lead(sms_consent=True, phone="5125550002")

        repo.get_by_id.side_effect = [lead1, lead2]

        summary = await svc.bulk_outreach(
            lead_ids=[lead1.id, lead2.id],
            template="Promo message",
            channel="sms",
        )

        assert summary.sent_count == 1
        assert summary.failed_count == 1
        assert summary.total == 2

    async def test_bulk_outreach_skips_not_found_leads(self) -> None:
        """Leads that don't exist are counted as skipped."""
        sms_svc = AsyncMock()
        sms_svc.send_automated_message = AsyncMock(
            return_value={"success": True},
        )
        svc, repo = _build_service(sms_service=sms_svc)

        real_lead = _make_lead(sms_consent=True, phone="5125550001")
        missing_id = uuid4()

        repo.get_by_id.side_effect = [real_lead, None]

        summary = await svc.bulk_outreach(
            lead_ids=[real_lead.id, missing_id],
            template="Hello!",
            channel="sms",
        )

        assert summary.sent_count == 1
        assert summary.skipped_count == 1
        assert summary.total == 2


# =============================================================================
# 4. Lead Attachment Upload, List, and Delete
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestLeadAttachmentWorkflow:
    """Test lead attachment upload, list, and delete via PhotoService.

    Validates: Requirement 15.7
    """

    async def test_attachment_upload_stores_file_and_returns_metadata(
        self,
    ) -> None:
        """Uploading a lead attachment stores in S3 and returns metadata."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        # Minimal valid PDF
        pdf_data = b"%PDF-1.4" + b"\x00" * 100

        import magic as magic_mod  # noqa: PLC0415

        original_from_buffer = magic_mod.from_buffer

        def mock_from_buffer(
            data: bytes,
            mime: bool = False,
        ) -> str:
            if mime and data[:5] == b"%PDF-":
                return "application/pdf"
            return original_from_buffer(data, mime=mime)

        magic_mod.from_buffer = mock_from_buffer  # type: ignore[assignment]

        try:
            result = photo_svc.upload_file(
                data=pdf_data,
                file_name="estimate-draft.pdf",
                context=UploadContext.LEAD_ATTACHMENT,
            )

            assert isinstance(result, UploadResult)
            assert result.file_name == "estimate-draft.pdf"
            assert result.content_type == "application/pdf"
            assert result.file_key.startswith("lead-attachments/")
            assert result.file_size > 0
            s3_client.put_object.assert_called_once()
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]

    async def test_attachment_presigned_url_generation(self) -> None:
        """Listing attachments generates pre-signed download URLs."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        file_key = "lead-attachments/abc123.pdf"
        url = photo_svc.generate_presigned_url(file_key)

        assert url == "https://s3.example.com/presigned-url"
        s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": file_key},
            ExpiresIn=3600,
        )

    async def test_attachment_delete_removes_from_s3(self) -> None:
        """Deleting an attachment removes the S3 object."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        file_key = "lead-attachments/abc123.pdf"
        photo_svc.delete_file(file_key)

        s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=file_key,
        )

    async def test_full_attachment_lifecycle_upload_list_delete(
        self,
    ) -> None:
        """Full lifecycle: upload → get URL → delete as user would experience."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        pdf_data = b"%PDF-1.4" + b"\x00" * 100

        import magic as magic_mod  # noqa: PLC0415

        original_from_buffer = magic_mod.from_buffer

        def mock_from_buffer(
            data: bytes,
            mime: bool = False,
        ) -> str:
            if mime and data[:5] == b"%PDF-":
                return "application/pdf"
            return original_from_buffer(data, mime=mime)

        magic_mod.from_buffer = mock_from_buffer  # type: ignore[assignment]

        try:
            # Step 1: Upload
            result = photo_svc.upload_file(
                data=pdf_data,
                file_name="contract-v2.pdf",
                context=UploadContext.LEAD_ATTACHMENT,
            )
            assert result.file_key.startswith("lead-attachments/")

            # Step 2: Generate pre-signed URL (simulates listing)
            url = photo_svc.generate_presigned_url(result.file_key)
            assert url.startswith("https://")

            # Step 3: Delete
            photo_svc.delete_file(result.file_key)
            s3_client.delete_object.assert_called_once_with(
                Bucket="test-bucket",
                Key=result.file_key,
            )
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]


# =============================================================================
# 5. Work Request Migration Converts All Existing Work Requests to Leads
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestWorkRequestMigration:
    """Test work request migration converts GoogleSheetSubmissions to leads.

    Validates: Requirement 19.8
    """

    async def test_migration_converts_all_submissions_to_leads(
        self,
    ) -> None:
        """All unprocessed submissions are migrated to lead records."""
        svc, repo = _build_service()

        sub1 = _make_submission(
            name="Alice Brown",
            phone="5125550001",
            email="alice@example.com",
            city="Austin",
            address="100 Oak St",
            new_system_install="Yes",
        )
        sub2 = _make_submission(
            name="Bob Green",
            phone="5125550002",
            city="Round Rock",
            address="200 Elm Ave",
            repair_existing="Yes",
            new_system_install=None,
        )
        sub3 = _make_submission(
            name="Carol White",
            phone="5125550003",
            spring_startup="Yes",
            new_system_install=None,
            repair_existing=None,
        )

        # Mock session.execute to return submissions
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sub1, sub2, sub3]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=result_mock)
        repo.session.flush = AsyncMock()

        # Each create returns a new lead
        lead1 = _make_lead(id=uuid4())
        lead2 = _make_lead(id=uuid4())
        lead3 = _make_lead(id=uuid4())
        repo.create.side_effect = [lead1, lead2, lead3]

        summary = await svc.migrate_work_requests()

        assert summary.total_submissions == 3
        assert summary.migrated_count == 3
        assert summary.skipped_count == 0
        assert summary.error_count == 0
        assert repo.create.call_count == 3

        # Verify each submission was linked to its lead
        assert sub1.promoted_to_lead_id == lead1.id
        assert sub2.promoted_to_lead_id == lead2.id
        assert sub3.promoted_to_lead_id == lead3.id

    async def test_migration_skips_submissions_without_name_or_phone(
        self,
    ) -> None:
        """Submissions missing name or phone are skipped."""
        svc, repo = _build_service()

        no_name = _make_submission(name=None, phone="5125550001")
        no_phone = _make_submission(name="Valid Name", phone=None)
        valid = _make_submission(
            name="Good Lead",
            phone="5125550003",
            new_system_install="Yes",
        )

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [no_name, no_phone, valid]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=result_mock)
        repo.session.flush = AsyncMock()

        lead = _make_lead(id=uuid4())
        repo.create.return_value = lead

        summary = await svc.migrate_work_requests()

        assert summary.total_submissions == 3
        assert summary.migrated_count == 1
        assert summary.skipped_count == 2
        assert repo.create.call_count == 1

    async def test_migration_maps_situation_from_service_columns(
        self,
    ) -> None:
        """Service columns map to correct LeadSituation values."""
        svc, repo = _build_service()

        new_install = _make_submission(
            name="Install Lead",
            phone="5125550001",
            new_system_install="Yes",
            repair_existing=None,
            addition_to_system=None,
            spring_startup=None,
            fall_blowout=None,
            summer_tuneup=None,
        )

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [new_install]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=result_mock)
        repo.session.flush = AsyncMock()

        lead = _make_lead(id=uuid4())
        repo.create.return_value = lead

        await svc.migrate_work_requests()

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["situation"] == LeadSituation.NEW_SYSTEM.value
        assert create_kwargs["lead_source"] == LeadSourceExtended.GOOGLE_FORM.value
        assert ActionTag.NEEDS_CONTACT.value in create_kwargs["action_tags"]

    async def test_migration_handles_errors_gracefully(self) -> None:
        """Errors on individual submissions are captured, not raised."""
        svc, repo = _build_service()

        good = _make_submission(
            name="Good Lead",
            phone="5125550001",
            new_system_install="Yes",
        )
        bad = _make_submission(
            name="Bad Lead",
            phone="5125550002",
            new_system_install="Yes",
        )

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [good, bad]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=result_mock)
        repo.session.flush = AsyncMock()

        lead = _make_lead(id=uuid4())
        repo.create.side_effect = [lead, Exception("DB constraint error")]

        summary = await svc.migrate_work_requests()

        assert summary.migrated_count == 1
        assert summary.error_count == 1
        assert len(summary.errors) == 1
        assert "DB constraint error" in summary.errors[0]

    async def test_migration_empty_submissions_returns_zero_counts(
        self,
    ) -> None:
        """No unprocessed submissions returns all-zero summary."""
        svc, repo = _build_service()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=result_mock)

        summary = await svc.migrate_work_requests()

        assert summary.total_submissions == 0
        assert summary.migrated_count == 0
        assert summary.skipped_count == 0
        assert summary.error_count == 0
