"""Property-based tests for Lead_Service integration gap changes.

Properties:
  P3:  Lead field persistence round-trip
  P9:  Duplicate lead detection within 24-hour window
  P10: SmsConsentRecord created at lead submission
  P4:  Email marketing consent carries over on lead conversion
  P11: SmsConsentRecord customer_id updated on lead conversion
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

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
    return lead


def _build_service(
    *,
    lead_repo: AsyncMock | None = None,
    compliance_service: AsyncMock | None = None,
) -> LeadService:
    return LeadService(
        lead_repository=lead_repo or AsyncMock(),
        customer_service=AsyncMock(),
        job_service=AsyncMock(),
        staff_repository=AsyncMock(),
        compliance_service=compliance_service,
    )


# -------------------------------------------------------------------
# Property 3: Lead field persistence round-trip
# -------------------------------------------------------------------


@pytest.mark.unit
class TestProperty3LeadFieldPersistence:
    """Validates: Requirements 2.2, 5.2."""

    @given(
        email_marketing=st.booleans(),
        page_url=st.one_of(
            st.none(),
            st.text(min_size=1, max_size=100).map(
                lambda s: f"https://example.com/{s}",
            ),
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_new_fields_passed_to_repository(
        self,
        email_marketing: bool,
        page_url: str | None,
    ) -> None:
        """PBT P3: email_marketing_consent and page_url are stored."""
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = _make_lead_mock(
            email_marketing_consent=email_marketing,
            page_url=page_url,
        )
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            email_marketing_consent=email_marketing,
            page_url=page_url,
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        kwargs = repo.create.call_args[1]
        assert kwargs["email_marketing_consent"] == email_marketing
        assert kwargs["page_url"] == page_url


# -------------------------------------------------------------------
# Property 9: Duplicate lead detection within 24-hour window
# -------------------------------------------------------------------


@pytest.mark.unit
class TestProperty9DuplicateDetection:
    """Validates: Requirements 6.1, 6.2, 6.3, 6.4."""

    @given(sms_consent=st.booleans())
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_recent_duplicate_raises_409(
        self,
        sms_consent: bool,
    ) -> None:
        """PBT P9: Second submission within 24h is rejected."""
        existing = _make_lead_mock()
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = existing
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            sms_consent=sms_consent,
        )

        with pytest.raises(DuplicateLeadError):
            await svc.submit_lead(data)

        repo.create.assert_not_called()

    @given(sms_consent=st.booleans())
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_no_recent_duplicate_allows_creation(
        self,
        sms_consent: bool,
    ) -> None:
        """PBT P9: No recent duplicate allows lead creation."""
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = _make_lead_mock()
        svc = _build_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            sms_consent=sms_consent,
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        repo.create.assert_called_once()


# -------------------------------------------------------------------
# Property 10: SmsConsentRecord created at lead submission
# -------------------------------------------------------------------


@pytest.mark.unit
class TestProperty10ConsentRecordAtSubmission:
    """Validates: Requirements 7.1, 7.3, 7.4."""

    @given(sms_consent=st.booleans())
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_consent_record_mirrors_sms_consent(
        self,
        sms_consent: bool,
    ) -> None:
        """PBT P10: SmsConsentRecord.consent_given matches sms_consent."""
        lead = _make_lead_mock(sms_consent=sms_consent)
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None
        repo.create.return_value = lead

        compliance = AsyncMock()
        svc = _build_service(lead_repo=repo, compliance_service=compliance)

        data = LeadSubmission(
            name="Test User",
            phone="6125550100",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            sms_consent=sms_consent,
        )
        await svc.submit_lead(data)

        compliance.create_sms_consent.assert_awaited_once()
        call_kwargs = compliance.create_sms_consent.call_args[1]
        assert call_kwargs["consent_given"] == sms_consent
        assert call_kwargs["method"] == "lead_form"
        assert call_kwargs.get("customer_id") is None
        assert call_kwargs["lead_id"] == lead.id

    @given(
        ip=st.one_of(st.none(), st.just("192.168.1.1")),
        ua=st.one_of(st.none(), st.just("Mozilla/5.0")),
    )
    @settings(max_examples=10)
    @pytest.mark.asyncio
    async def test_consent_metadata_passed(
        self,
        ip: str | None,
        ua: str | None,
    ) -> None:
        """PBT P10: Consent metadata fields are passed through."""
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
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            consent_ip=ip,
            consent_user_agent=ua,
        )
        await svc.submit_lead(data)

        call_kwargs = compliance.create_sms_consent.call_args[1]
        assert call_kwargs["ip_address"] == ip
        assert call_kwargs["user_agent"] == ua


# -------------------------------------------------------------------
# Property 4: Email marketing consent carries over on conversion
# -------------------------------------------------------------------


@pytest.mark.unit
class TestProperty4EmailMarketingConsentConversion:
    """Validates: Requirements 2.3."""

    @given(email_marketing=st.booleans())
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_email_marketing_consent_carried_to_customer(
        self,
        email_marketing: bool,
    ) -> None:
        """PBT P4: email_marketing_consent carries to customer."""
        lead = _make_lead_mock(
            email_marketing_consent=email_marketing,
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
        # Mock the select query to return empty list
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
            LeadConversionRequest(create_job=False),
        )

        if email_marketing:
            update_data = customer_svc.repository.update.call_args[0][1]
            assert update_data.get("email_opt_in") is True
            assert update_data.get("email_opt_in_source") == "lead_form"
            assert "email_opt_in_at" in update_data
        # When False, email_opt_in should not be set
        # (unless lead has email, which sets email_opt_in_at)


# -------------------------------------------------------------------
# Property 11: SmsConsentRecord customer_id updated on conversion
# -------------------------------------------------------------------


@pytest.mark.unit
class TestProperty11ConsentRecordCustomerIdUpdate:
    """Validates: Requirements 7.5."""

    @given(sms_consent=st.booleans())
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_consent_record_customer_id_updated(
        self,
        sms_consent: bool,
    ) -> None:
        """PBT P11: SmsConsentRecord.customer_id updated on conversion."""
        lead_id = uuid4()
        lead = _make_lead_mock(
            lead_id=lead_id,
            sms_consent=sms_consent,
            status=LeadStatus.NEW.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = lead

        customer = MagicMock()
        customer.id = uuid4()
        customer_svc = AsyncMock()
        customer_svc.create_customer.return_value = customer
        customer_svc.repository = AsyncMock()

        # Mock compliance service with consent record
        consent_record = MagicMock()
        consent_record.lead_id = lead_id
        consent_record.customer_id = None

        compliance = AsyncMock()
        compliance.session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [consent_record]
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
            LeadConversionRequest(create_job=False),
        )

        # Verify customer_id was set on the consent record
        assert consent_record.customer_id == customer.id
        compliance.session.flush.assert_awaited()
