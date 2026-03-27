"""Unit tests for LeadService extensions.

Tests source tracking, intake tagging, follow-up queue, SMS/email
confirmations, consent carry-over, and metrics by source.

Validates: Requirements 45.1-45.5, 48.1-48.5, 50.1-50.4, 52.1-52.5,
           54.1-54.4, 55.1-55.3, 57.1-57.3, 63.1
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    IntakeTag,
    LeadSituation,
    LeadSourceExtended,
    LeadStatus,
)
from grins_platform.schemas.lead import (
    FromCallSubmission,
    LeadConversionRequest,
    LeadSubmission,
)
from grins_platform.services.lead_service import LeadService

# =============================================================================
# Helpers
# =============================================================================


def _make_lead_mock(
    *,
    lead_id: object | None = None,
    name: str = "John Doe",
    phone: str = "6125550123",
    email: str | None = None,
    zip_code: str = "55424",
    situation: str = LeadSituation.NEW_SYSTEM.value,
    notes: str | None = None,
    source_site: str = "residential",
    lead_source: str = "website",
    source_detail: str | None = None,
    intake_tag: str | None = "schedule",
    sms_consent: bool = False,
    terms_accepted: bool = False,
    status: str = LeadStatus.NEW.value,
    created_at: datetime | None = None,
    email_marketing_consent: bool = False,
    city: str | None = None,
    state: str | None = None,
    address: str | None = None,
    action_tags: list[str] | None = None,
) -> MagicMock:
    lead = MagicMock()
    lead.id = lead_id or uuid4()
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.zip_code = zip_code
    lead.situation = situation
    lead.notes = notes
    lead.source_site = source_site
    lead.lead_source = lead_source
    lead.source_detail = source_detail
    lead.intake_tag = intake_tag
    lead.sms_consent = sms_consent
    lead.terms_accepted = terms_accepted
    lead.email_marketing_consent = email_marketing_consent
    lead.status = status
    lead.assigned_to = None
    lead.customer_id = None
    lead.contacted_at = None
    lead.converted_at = None
    lead.created_at = created_at or datetime.now(tz=timezone.utc)
    lead.updated_at = datetime.now(tz=timezone.utc)
    lead.city = city
    lead.state = state
    lead.address = address
    lead.action_tags = action_tags
    lead.customer_type = None
    lead.property_type = None
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
) -> LeadService:
    return LeadService(
        lead_repository=lead_repo or AsyncMock(),
        customer_service=customer_service or AsyncMock(),
        job_service=job_service or AsyncMock(),
        staff_repository=staff_repo or AsyncMock(),
        sms_service=sms_service,
        email_service=email_service,
        compliance_service=compliance_service,
    )


# =============================================================================
# Source tracking tests (Req 45.1-45.5)
# =============================================================================


@pytest.mark.unit
class TestLeadSourceTracking:
    """Tests for lead creation with all LeadSource values."""

    @pytest.mark.asyncio
    async def test_submit_lead_defaults_source_to_website(self) -> None:
        """Lead submission without explicit lead_source defaults to WEBSITE."""
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.submit_lead(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["lead_source"] == LeadSourceExtended.WEBSITE.value

    @pytest.mark.asyncio
    async def test_submit_lead_with_explicit_source(self) -> None:
        """Lead submission with explicit lead_source uses provided value."""
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            lead_source=LeadSourceExtended.GOOGLE_AD,
            source_detail="Spring campaign",
        )
        await svc.submit_lead(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["lead_source"] == LeadSourceExtended.GOOGLE_AD.value
        assert create_kwargs["source_detail"] == "Spring campaign"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "source",
        list(LeadSourceExtended),
        ids=[s.value for s in LeadSourceExtended],
    )
    async def test_submit_lead_accepts_all_source_values(
        self,
        source: LeadSourceExtended,
    ) -> None:
        """Lead submission accepts every LeadSourceExtended value."""
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            lead_source=source,
        )
        await svc.submit_lead(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["lead_source"] == source.value

    @pytest.mark.asyncio
    async def test_from_call_defaults_source_to_phone_call(self) -> None:
        """From-call creation defaults lead_source to PHONE_CALL."""
        repo = AsyncMock()
        repo.create.return_value = _make_lead_mock(lead_source="phone_call")
        svc = _build_service(lead_repo=repo)

        data = FromCallSubmission(
            name="Caller Name",
            phone="6125550200",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.create_from_call(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["lead_source"] == LeadSourceExtended.PHONE_CALL.value

    @pytest.mark.asyncio
    async def test_from_call_source_detail_defaults_to_inbound_call(self) -> None:
        """From-call without source_detail defaults to 'Inbound call'."""
        repo = AsyncMock()
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = FromCallSubmission(
            name="Caller Name",
            phone="6125550200",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.create_from_call(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["source_detail"] == "Inbound call"

    @pytest.mark.asyncio
    async def test_from_call_with_explicit_source_detail(self) -> None:
        """From-call with explicit source_detail uses provided value."""
        repo = AsyncMock()
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = FromCallSubmission(
            name="Caller Name",
            phone="6125550200",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            source_detail="Referred by neighbor",
        )
        await svc.create_from_call(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["source_detail"] == "Referred by neighbor"


# =============================================================================
# Intake tag defaulting tests (Req 48.1-48.5)
# =============================================================================


@pytest.mark.unit
class TestIntakeTagDefaulting:
    """Tests for intake tag defaulting behavior."""

    @pytest.mark.asyncio
    async def test_website_submission_defaults_intake_tag_to_schedule(self) -> None:
        """Website form submission defaults intake_tag to SCHEDULE."""
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.submit_lead(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["intake_tag"] == IntakeTag.SCHEDULE.value

    @pytest.mark.asyncio
    async def test_website_submission_with_explicit_follow_up_tag(self) -> None:
        """Website form with explicit FOLLOW_UP intake_tag uses it."""
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            intake_tag=IntakeTag.FOLLOW_UP,
        )
        await svc.submit_lead(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["intake_tag"] == IntakeTag.FOLLOW_UP.value

    @pytest.mark.asyncio
    async def test_from_call_defaults_intake_tag_to_none(self) -> None:
        """From-call creation defaults intake_tag to NULL."""
        repo = AsyncMock()
        repo.create.return_value = _make_lead_mock(intake_tag=None)
        svc = _build_service(lead_repo=repo)

        data = FromCallSubmission(
            name="Caller Name",
            phone="6125550200",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.create_from_call(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["intake_tag"] is None

    @pytest.mark.asyncio
    async def test_from_call_with_explicit_follow_up_tag(self) -> None:
        """From-call with explicit FOLLOW_UP intake_tag uses it."""
        repo = AsyncMock()
        repo.create.return_value = _make_lead_mock(intake_tag="follow_up")
        svc = _build_service(lead_repo=repo)

        data = FromCallSubmission(
            name="Caller Name",
            phone="6125550200",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            intake_tag=IntakeTag.FOLLOW_UP,
        )
        await svc.create_from_call(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["intake_tag"] == IntakeTag.FOLLOW_UP.value


# =============================================================================
# Follow-up queue tests (Req 50.1-50.4)
# =============================================================================


@pytest.mark.unit
class TestFollowUpQueue:
    """Tests for follow-up queue filtering and sorting."""

    @pytest.mark.asyncio
    async def test_returns_follow_up_leads_with_time_since_created(self) -> None:
        """Follow-up queue returns items with computed time_since_created."""
        two_hours_ago = datetime.now(tz=timezone.utc) - timedelta(hours=2)
        lead = _make_lead_mock(
            intake_tag="follow_up",
            status=LeadStatus.NEW.value,
            created_at=two_hours_ago,
        )
        repo = AsyncMock()
        repo.get_follow_up_queue.return_value = ([lead], 1)
        svc = _build_service(lead_repo=repo)

        result = await svc.get_follow_up_queue(page=1, page_size=20)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].time_since_created >= 1.9  # ~2 hours

    @pytest.mark.asyncio
    async def test_empty_queue_returns_zero(self) -> None:
        """Empty follow-up queue returns zero items and total."""
        repo = AsyncMock()
        repo.get_follow_up_queue.return_value = ([], 0)
        svc = _build_service(lead_repo=repo)

        result = await svc.get_follow_up_queue()

        assert result.total == 0
        assert result.total_pages == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_pagination_metadata(self) -> None:
        """Follow-up queue returns correct pagination metadata."""
        leads = [
            _make_lead_mock(intake_tag="follow_up", status=LeadStatus.NEW.value)
            for _ in range(5)
        ]
        repo = AsyncMock()
        repo.get_follow_up_queue.return_value = (leads, 25)
        svc = _build_service(lead_repo=repo)

        result = await svc.get_follow_up_queue(page=2, page_size=5)

        assert result.page == 2
        assert result.page_size == 5
        assert result.total == 25
        assert result.total_pages == 5

    @pytest.mark.asyncio
    async def test_passes_pagination_to_repository(self) -> None:
        """Follow-up queue passes page/page_size to repository."""
        repo = AsyncMock()
        repo.get_follow_up_queue.return_value = ([], 0)
        svc = _build_service(lead_repo=repo)

        await svc.get_follow_up_queue(page=3, page_size=10)

        repo.get_follow_up_queue.assert_awaited_once_with(page=3, page_size=10)


# =============================================================================
# SMS confirmation consent gating tests (Req 54.1-54.4)
# =============================================================================


@pytest.mark.unit
class TestSmsConfirmationGating:
    """Tests for SMS confirmation consent gating on lead creation."""

    @pytest.mark.asyncio
    async def test_sms_deferred_when_consent_and_phone_present(self) -> None:
        """SMS deferred (not sent) when sms_consent=true AND phone present.

        After BUG #11/12/13 fix: leads bypass sms_service.send_message()
        because SentMessage requires customer_id FK, not lead_id.
        """
        lead = _make_lead_mock(sms_consent=True, phone="6125550100")
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        sms = AsyncMock()
        svc = _build_service(lead_repo=repo, sms_service=sms)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.submit_lead(data)

        sms.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sms_skipped_when_no_consent(self) -> None:
        """SMS skipped when sms_consent=false."""
        lead = _make_lead_mock(sms_consent=False, phone="6125550100")
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        sms = AsyncMock()
        svc = _build_service(lead_repo=repo, sms_service=sms)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.submit_lead(data)

        sms.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sms_skipped_when_no_phone(self) -> None:
        """SMS skipped when phone is empty/None."""
        lead = _make_lead_mock(sms_consent=True, phone="")
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        sms = AsyncMock()
        svc = _build_service(lead_repo=repo, sms_service=sms)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.submit_lead(data)

        sms.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sms_skipped_when_service_unavailable(self) -> None:
        """SMS skipped when sms_service is None."""
        lead = _make_lead_mock(sms_consent=True, phone="6125550100")
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        svc = _build_service(lead_repo=repo, sms_service=None)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.submit_lead(data)
        # No exception raised — graceful skip

    @pytest.mark.asyncio
    async def test_sms_failure_does_not_raise(self) -> None:
        """SMS send failure is caught and logged, not raised."""
        lead = _make_lead_mock(sms_consent=True, phone="6125550100")
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        sms = AsyncMock()
        sms.send_automated_message.side_effect = RuntimeError("Twilio down")
        svc = _build_service(lead_repo=repo, sms_service=sms)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        # Should not raise
        result = await svc.submit_lead(data)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_from_call_sends_sms_when_consent(self) -> None:
        """From-call sends SMS via send_automated_message when consent is given.

        Validates: Requirement 46.1
        """
        lead = _make_lead_mock(sms_consent=True, phone="6125550200")
        repo = AsyncMock()
        repo.create.return_value = lead
        sms = AsyncMock()
        sms.send_automated_message = AsyncMock(
            return_value={"success": True},
        )
        svc = _build_service(lead_repo=repo, sms_service=sms)

        data = FromCallSubmission(
            name="Caller",
            phone="6125550200",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.create_from_call(data)

        sms.send_message.assert_not_awaited()
        sms.send_automated_message.assert_awaited_once()


# =============================================================================
# Email confirmation tests (Req 55.1-55.3)
# =============================================================================


@pytest.mark.unit
class TestEmailConfirmation:
    """Tests for email confirmation on lead creation."""

    @pytest.mark.asyncio
    async def test_email_sent_when_email_present(self) -> None:
        """Email confirmation sent when lead has email."""
        lead = _make_lead_mock(email="test@example.com")
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        email_svc = MagicMock()
        svc = _build_service(lead_repo=repo, email_service=email_svc)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.submit_lead(data)

        email_svc.send_lead_confirmation.assert_called_once_with(lead)

    @pytest.mark.asyncio
    async def test_email_skipped_when_no_email(self) -> None:
        """Email confirmation skipped when lead has no email."""
        lead = _make_lead_mock(email=None)
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        email_svc = MagicMock()
        svc = _build_service(lead_repo=repo, email_service=email_svc)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        await svc.submit_lead(data)

        email_svc.send_lead_confirmation.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_skipped_when_service_unavailable(self) -> None:
        """Email confirmation skipped when email_service is None."""
        lead = _make_lead_mock(email="test@example.com")
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        svc = _build_service(lead_repo=repo, email_service=None)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        result = await svc.submit_lead(data)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_email_failure_does_not_raise(self) -> None:
        """Email send failure is caught and logged, not raised."""
        lead = _make_lead_mock(email="test@example.com")
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = lead
        email_svc = MagicMock()
        email_svc.send_lead_confirmation.side_effect = RuntimeError("SMTP down")
        svc = _build_service(lead_repo=repo, email_service=email_svc)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        result = await svc.submit_lead(data)
        assert result.success is True


# =============================================================================
# Consent carry-over on conversion tests (Req 57.1-57.3, 68.3)
# =============================================================================


@pytest.mark.unit
class TestConsentCarryOver:
    """Tests for consent field carry-over during lead-to-customer conversion."""

    @pytest.mark.asyncio
    async def test_sms_consent_carried_to_customer(self) -> None:
        """sms_consent=true creates sms_consent_record and sets sms_opt_in_at."""
        lead = _make_lead_mock(
            sms_consent=True,
            terms_accepted=False,
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
        svc = _build_service(
            lead_repo=repo,
            customer_service=customer_svc,
            compliance_service=compliance,
        )

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        # Verify sms_consent_record created
        compliance.create_sms_consent.assert_awaited_once()
        call_kwargs = compliance.create_sms_consent.call_args[1]
        assert call_kwargs["phone"] == lead.phone
        assert call_kwargs["consent_given"] is True
        assert call_kwargs["method"] == "lead_form"
        assert call_kwargs["customer_id"] == customer.id

        # Verify customer updated with sms_opt_in_at
        update_call = customer_svc.repository.update.call_args
        update_data = update_call[0][1]
        assert "sms_opt_in_at" in update_data
        assert update_data["sms_opt_in_source"] == "lead_form"

    @pytest.mark.asyncio
    async def test_terms_accepted_carried_to_customer(self) -> None:
        """terms_accepted=true sets terms_accepted + terms_accepted_at."""
        lead = _make_lead_mock(
            sms_consent=False,
            terms_accepted=True,
            status=LeadStatus.NEW.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = lead

        customer = MagicMock()
        customer.id = uuid4()
        customer_svc = AsyncMock()
        customer_svc.create_customer.return_value = customer
        customer_svc.repository = AsyncMock()

        svc = _build_service(lead_repo=repo, customer_service=customer_svc)

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        update_data = customer_svc.repository.update.call_args[0][1]
        assert update_data["terms_accepted"] is True
        assert "terms_accepted_at" in update_data

    @pytest.mark.asyncio
    async def test_email_consent_carried_to_customer(self) -> None:
        """Lead with email sets email_opt_in_at + email_opt_in_source."""
        lead = _make_lead_mock(
            email="test@example.com",
            sms_consent=False,
            terms_accepted=False,
            status=LeadStatus.NEW.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = lead

        customer = MagicMock()
        customer.id = uuid4()
        customer_svc = AsyncMock()
        customer_svc.create_customer.return_value = customer
        customer_svc.repository = AsyncMock()

        svc = _build_service(lead_repo=repo, customer_service=customer_svc)

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        update_data = customer_svc.repository.update.call_args[0][1]
        assert "email_opt_in_at" in update_data
        assert update_data["email_opt_in_source"] == "lead_form"

    @pytest.mark.asyncio
    async def test_no_consent_no_update(self) -> None:
        """Lead with no consent fields does not update customer consent."""
        lead = _make_lead_mock(
            email=None,
            sms_consent=False,
            terms_accepted=False,
            status=LeadStatus.NEW.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = lead

        customer = MagicMock()
        customer.id = uuid4()
        customer_svc = AsyncMock()
        customer_svc.create_customer.return_value = customer
        customer_svc.repository = AsyncMock()

        svc = _build_service(lead_repo=repo, customer_service=customer_svc)

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        # No consent updates → repository.update not called for consent
        customer_svc.repository.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_all_consent_fields_carried(self) -> None:
        """Lead with all consent fields carries all to customer."""
        lead = _make_lead_mock(
            email="test@example.com",
            sms_consent=True,
            terms_accepted=True,
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
        svc = _build_service(
            lead_repo=repo,
            customer_service=customer_svc,
            compliance_service=compliance,
        )

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        update_data = customer_svc.repository.update.call_args[0][1]
        assert "sms_opt_in_at" in update_data
        assert "terms_accepted" in update_data
        assert "email_opt_in_at" in update_data
        compliance.create_sms_consent.assert_awaited_once()


# =============================================================================
# Metrics by source tests (Req 61.3)
# =============================================================================


@pytest.mark.unit
class TestMetricsBySource:
    """Tests for lead metrics grouped by source."""

    @pytest.mark.asyncio
    async def test_returns_counts_per_source(self) -> None:
        """Returns correct counts grouped by source."""
        repo = AsyncMock()
        repo.count_by_source.return_value = [
            ("website", 10),
            ("phone_call", 5),
            ("google_form", 3),
        ]
        svc = _build_service(lead_repo=repo)

        result = await svc.get_metrics_by_source()

        assert result.total == 18
        assert len(result.items) == 3
        assert result.items[0].lead_source == "website"
        assert result.items[0].count == 10

    @pytest.mark.asyncio
    async def test_defaults_to_trailing_30_days(self) -> None:
        """Defaults date range to trailing 30 days when not specified."""
        repo = AsyncMock()
        repo.count_by_source.return_value = []
        svc = _build_service(lead_repo=repo)

        result = await svc.get_metrics_by_source()

        call_args = repo.count_by_source.call_args[0]
        date_from, date_to = call_args
        assert (date_to - date_from).days >= 29
        assert (date_to - date_from).days <= 31
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_custom_date_range(self) -> None:
        """Uses provided date range."""
        repo = AsyncMock()
        repo.count_by_source.return_value = [("website", 2)]
        svc = _build_service(lead_repo=repo)

        now = datetime.now(tz=timezone.utc)
        from_date = now - timedelta(days=7)

        result = await svc.get_metrics_by_source(
            date_from=from_date,
            date_to=now,
        )

        call_args = repo.count_by_source.call_args[0]
        assert call_args[0] == from_date
        assert call_args[1] == now
        assert result.total == 2

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        """Empty results return zero total."""
        repo = AsyncMock()
        repo.count_by_source.return_value = []
        svc = _build_service(lead_repo=repo)

        result = await svc.get_metrics_by_source()

        assert result.total == 0
        assert len(result.items) == 0


# =============================================================================
# Work request auto-promotion tests (Req 52.1-52.5)
# =============================================================================


@pytest.mark.unit
class TestWorkRequestAutoPromotion:
    """Tests for work request auto-promotion to lead.

    Note: The actual auto-promotion logic lives in GoogleSheetsService.
    These tests verify the LeadService side: that leads created from
    work requests have correct source and detail fields.
    """

    @pytest.mark.asyncio
    async def test_google_form_source_accepted(self) -> None:
        """Lead created with GOOGLE_FORM source is accepted."""
        repo = AsyncMock()
        repo.get_by_phone_and_active_status.return_value = None
        repo.get_recent_by_phone_or_email.return_value = None
        repo.create.return_value = _make_lead_mock(
            lead_source=LeadSourceExtended.GOOGLE_FORM.value,
        )
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Work Request User",
            phone="6125550300",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            lead_source=LeadSourceExtended.GOOGLE_FORM,
            source_detail="New client work request",
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["lead_source"] == LeadSourceExtended.GOOGLE_FORM.value
        assert create_kwargs["source_detail"] == "New client work request"
