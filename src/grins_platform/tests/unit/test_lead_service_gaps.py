"""Unit tests for Lead_Service integration gap changes.

Tests duplicate detection, consent records, new fields,
and lead conversion updates.

Validates: Requirements 2.2, 2.3, 5.2, 6.1-6.4, 7.1, 7.3-7.5
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import DuplicateLeadError
from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.schemas.lead import LeadConversionRequest, LeadSubmission
from grins_platform.services.lead_service import LeadService


def _make_lead_mock(
    *,
    lead_id: object | None = None,
    name: str = "John Doe",
    phone: str = "6125550123",
    email: str | None = None,
    sms_consent: bool = False,
    terms_accepted: bool = False,
    email_marketing_consent: bool = False,
    page_url: str | None = None,
    status: str = LeadStatus.NEW.value,
) -> MagicMock:
    lead = MagicMock()
    lead.id = lead_id or uuid4()
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.sms_consent = sms_consent
    lead.terms_accepted = terms_accepted
    lead.email_marketing_consent = email_marketing_consent
    lead.page_url = page_url
    lead.status = status
    lead.situation = LeadSituation.REPAIR.value
    lead.assigned_to = None
    lead.customer_id = None
    lead.contacted_at = None
    lead.converted_at = None
    lead.created_at = datetime.now(tz=timezone.utc)
    lead.updated_at = datetime.now(tz=timezone.utc)
    lead.zip_code = "55424"
    lead.notes = None
    lead.source_site = "residential"
    lead.lead_source = "website"
    lead.source_detail = None
    lead.intake_tag = "schedule"
    lead.city = None
    lead.state = None
    lead.address = None
    lead.action_tags = None
    lead.customer_type = None
    lead.property_type = None
    lead.moved_to = None
    lead.moved_at = None
    lead.last_contacted_at = None
    lead.job_requested = None
    return lead


def _build_service(
    *,
    lead_repo: AsyncMock | None = None,
    customer_service: AsyncMock | None = None,
    compliance_service: AsyncMock | None = None,
) -> LeadService:
    return LeadService(
        lead_repository=lead_repo or AsyncMock(),
        customer_service=customer_service or AsyncMock(),
        job_service=AsyncMock(),
        staff_repository=AsyncMock(),
        compliance_service=compliance_service,
    )


# =============================================================================
# Duplicate detection tests (Req 6.1-6.4)
# =============================================================================


@pytest.mark.unit
class TestDuplicateLeadDetection:
    """Tests for 24-hour duplicate lead detection."""

    @pytest.mark.asyncio
    async def test_same_phone_within_24h_raises_409(self) -> None:
        """Same phone within 24h → DuplicateLeadError."""
        existing = _make_lead_mock()
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = existing
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550123",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )

        with pytest.raises(DuplicateLeadError):
            await svc.submit_lead(data)

        repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_same_email_within_24h_raises_409(self) -> None:
        """Same email within 24h → DuplicateLeadError."""
        existing = _make_lead_mock(email="test@example.com")
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = existing
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125559999",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            email="test@example.com",
        )

        with pytest.raises(DuplicateLeadError):
            await svc.submit_lead(data)

    @pytest.mark.asyncio
    async def test_same_phone_after_24h_allowed(self) -> None:
        """Same phone after 24h → allowed (no recent duplicate)."""
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550123",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_phone_and_email_allowed(self) -> None:
        """Different phone and email → allowed."""
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125559999",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            email="different@example.com",
        )
        result = await svc.submit_lead(data)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_duplicate_error_has_correct_detail(self) -> None:
        """DuplicateLeadError has correct detail and message."""
        existing = _make_lead_mock()
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = existing
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550123",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )

        with pytest.raises(DuplicateLeadError) as exc_info:
            await svc.submit_lead(data)

        assert exc_info.value.detail == "duplicate_lead"
        assert "recently submitted" in exc_info.value.message


# =============================================================================
# SmsConsentRecord creation tests (Req 7.1, 7.3, 7.4)
# =============================================================================


@pytest.mark.unit
class TestSmsConsentRecordCreation:
    """Tests for SmsConsentRecord creation at lead submission."""

    @pytest.mark.asyncio
    async def test_consent_record_created_with_all_metadata(
        self,
    ) -> None:
        """SmsConsentRecord created with all metadata fields."""
        lead = _make_lead_mock(sms_consent=True)
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = lead

        compliance = AsyncMock()
        svc = _build_service(lead_repo=repo, compliance_service=compliance)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            sms_consent=True,
            consent_ip="10.0.0.1",
            consent_user_agent="TestBrowser/1.0",
            consent_language_version="v1.0",
        )
        await svc.submit_lead(data)

        compliance.create_sms_consent.assert_awaited_once()
        kwargs = compliance.create_sms_consent.call_args[1]
        assert kwargs["consent_given"] is True
        assert kwargs["method"] == "lead_form"
        assert kwargs["lead_id"] == lead.id
        assert kwargs["ip_address"] == "10.0.0.1"
        assert kwargs["user_agent"] == "TestBrowser/1.0"
        assert kwargs.get("customer_id") is None

    @pytest.mark.asyncio
    async def test_consent_record_with_sms_false(self) -> None:
        """SmsConsentRecord created even when sms_consent=false."""
        lead = _make_lead_mock(sms_consent=False)
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = lead

        compliance = AsyncMock()
        svc = _build_service(lead_repo=repo, compliance_service=compliance)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            sms_consent=False,
        )
        await svc.submit_lead(data)

        kwargs = compliance.create_sms_consent.call_args[1]
        assert kwargs["consent_given"] is False

    @pytest.mark.asyncio
    async def test_consent_version_validated(self) -> None:
        """Consent language version is validated when provided."""
        lead = _make_lead_mock()
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = lead

        compliance = AsyncMock()
        svc = _build_service(lead_repo=repo, compliance_service=compliance)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            consent_language_version="v1.0",
        )
        await svc.submit_lead(data)

        compliance.validate_consent_language_version.assert_awaited_once_with(
            "v1.0",
        )

    @pytest.mark.asyncio
    async def test_no_compliance_service_skips_gracefully(self) -> None:
        """No compliance service → consent record skipped."""
        lead = _make_lead_mock()
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = lead

        svc = _build_service(lead_repo=repo, compliance_service=None)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        result = await svc.submit_lead(data)

        assert result.success is True


# =============================================================================
# Lead conversion tests (Req 2.3, 7.5)
# =============================================================================


@pytest.mark.unit
class TestLeadConversionUpdates:
    """Tests for lead conversion email_marketing_consent and consent record."""

    @pytest.mark.asyncio
    async def test_email_marketing_consent_true_sets_customer_opt_in(
        self,
    ) -> None:
        """email_marketing_consent=true → customer email_opt_in=true."""
        lead = _make_lead_mock(
            email_marketing_consent=True,
            status=LeadStatus.NEW.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = lead

        customer = MagicMock()
        customer.id = uuid4()
        customer_svc = AsyncMock()
        customer_svc.create_customer.return_value = customer
        customer_svc.repository = AsyncMock()

        compliance = AsyncMock()
        compliance.session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        compliance.session.execute.return_value = mock_result

        svc = LeadService(
            lead_repository=repo,
            customer_service=customer_svc,
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
            compliance_service=compliance,
        )

        await svc.convert_lead(
            lead.id,
            LeadConversionRequest(create_job=False, force=True),
        )

        update_data = customer_svc.repository.update.call_args[0][1]
        assert update_data["email_opt_in"] is True
        assert update_data["email_opt_in_source"] == "lead_form"
        assert "email_opt_in_at" in update_data

    @pytest.mark.asyncio
    async def test_consent_record_customer_id_updated(self) -> None:
        """SmsConsentRecord customer_id updated on conversion."""
        lead_id = uuid4()
        lead = _make_lead_mock(
            lead_id=lead_id,
            status=LeadStatus.NEW.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = lead

        customer = MagicMock()
        customer.id = uuid4()
        customer_svc = AsyncMock()
        customer_svc.create_customer.return_value = customer
        customer_svc.repository = AsyncMock()

        consent_record = MagicMock()
        consent_record.lead_id = lead_id
        consent_record.customer_id = None

        compliance = AsyncMock()
        compliance.session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            consent_record,
        ]
        compliance.session.execute.return_value = mock_result

        svc = LeadService(
            lead_repository=repo,
            customer_service=customer_svc,
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
            compliance_service=compliance,
        )

        await svc.convert_lead(
            lead.id,
            LeadConversionRequest(create_job=False, force=True),
        )

        assert consent_record.customer_id == customer.id
        compliance.session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_no_duplicate_consent_record_on_conversion(
        self,
    ) -> None:
        """No duplicate SmsConsentRecord created — only customer_id updated."""
        lead_id = uuid4()
        lead = _make_lead_mock(
            lead_id=lead_id,
            sms_consent=True,
            status=LeadStatus.NEW.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = lead

        customer = MagicMock()
        customer.id = uuid4()
        customer_svc = AsyncMock()
        customer_svc.create_customer.return_value = customer
        customer_svc.repository = AsyncMock()

        existing_record = MagicMock()
        existing_record.lead_id = lead_id
        existing_record.customer_id = None

        compliance = AsyncMock()
        compliance.session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            existing_record,
        ]
        compliance.session.execute.return_value = mock_result

        svc = LeadService(
            lead_repository=repo,
            customer_service=customer_svc,
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
            compliance_service=compliance,
        )

        await svc.convert_lead(
            lead.id,
            LeadConversionRequest(create_job=False, force=True),
        )

        # The existing record's customer_id should be updated
        assert existing_record.customer_id == customer.id
        # create_sms_consent is still called for sms_consent=true
        # (existing behavior), but the lead_id record is updated
        compliance.create_sms_consent.assert_awaited_once()


# =============================================================================
# New fields in submit_lead tests (Req 2.2, 5.2)
# =============================================================================


@pytest.mark.unit
class TestNewFieldsInSubmitLead:
    """Tests for new fields passed through submit_lead."""

    @pytest.mark.asyncio
    async def test_email_marketing_consent_stored(self) -> None:
        """email_marketing_consent passed to repository."""
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = _make_lead_mock(
            email_marketing_consent=True,
        )
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            email_marketing_consent=True,
        )
        await svc.submit_lead(data)

        kwargs = repo.create.call_args[1]
        assert kwargs["email_marketing_consent"] is True

    @pytest.mark.asyncio
    async def test_page_url_stored(self) -> None:
        """page_url passed to repository."""
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = _make_lead_mock(
            page_url="https://example.com/landing",
        )
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            page_url="https://example.com/landing",
        )
        await svc.submit_lead(data)

        kwargs = repo.create.call_args[1]
        assert kwargs["page_url"] == "https://example.com/landing"

    @pytest.mark.asyncio
    async def test_sms_consent_stored(self) -> None:
        """sms_consent passed to repository."""
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = _make_lead_mock(sms_consent=True)
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            address="123 Main St, Denver, CO 80209",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            sms_consent=True,
        )
        await svc.submit_lead(data)

        kwargs = repo.create.call_args[1]
        assert kwargs["sms_consent"] is True
