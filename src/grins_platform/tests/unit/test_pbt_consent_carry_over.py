"""Property test: Consent Field Carry-Over on Conversion.

Property 20: Lead with sms_consent=true → Customer has sms_consent +
sms_consent_record; lead with terms_accepted=true → Customer has
terms_accepted + terms_accepted_at.

Validates: Requirements 57.2, 57.3
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

from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.schemas.lead import LeadConversionRequest
from grins_platform.services.lead_service import LeadService

_NOW = datetime.now(tz=timezone.utc)


def _make_lead(
    *,
    sms_consent: bool,
    terms_accepted: bool,
    email: str | None = None,
) -> MagicMock:
    lead = MagicMock()
    lead.id = uuid4()
    lead.name = "Test User"
    lead.phone = "6125551234"
    lead.email = email
    lead.zip_code = "55401"
    lead.situation = LeadSituation.REPAIR.value
    lead.notes = None
    lead.source_site = "residential"
    lead.lead_source = "website"
    lead.source_detail = None
    lead.intake_tag = "schedule"
    lead.sms_consent = sms_consent
    lead.terms_accepted = terms_accepted
    lead.email_marketing_consent = False
    lead.status = LeadStatus.NEW.value
    lead.assigned_to = None
    lead.customer_id = None
    lead.contacted_at = None
    lead.converted_at = None
    lead.created_at = _NOW
    lead.updated_at = _NOW
    return lead


def _build_service(
    lead_repo: AsyncMock,
    customer_svc: AsyncMock,
    compliance: AsyncMock | None = None,
) -> LeadService:
    return LeadService(
        lead_repository=lead_repo,
        customer_service=customer_svc,
        job_service=MagicMock(),
        staff_repository=MagicMock(),
        compliance_service=compliance,
    )


def _setup_mocks(
    lead: MagicMock,
) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    repo = AsyncMock()
    repo.get_by_id.return_value = lead

    customer = MagicMock()
    customer.id = uuid4()
    customer_svc = AsyncMock()
    customer_svc.create_customer.return_value = customer
    customer_svc.repository = AsyncMock()

    compliance = AsyncMock()
    return repo, customer_svc, compliance


@pytest.mark.unit
class TestConsentCarryOverProperty:
    """Property 20: Consent Field Carry-Over on Conversion."""

    @given(sms_consent=st.just(True), terms_accepted=st.booleans())
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_sms_consent_creates_record_and_sets_opt_in(
        self,
        sms_consent: bool,
        terms_accepted: bool,
    ) -> None:
        """sms_consent=true → sms_consent_record created + sms_opt_in_at set."""
        lead = _make_lead(sms_consent=sms_consent, terms_accepted=terms_accepted)
        repo, customer_svc, compliance = _setup_mocks(lead)
        svc = _build_service(repo, customer_svc, compliance)

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        # sms_consent_record must be created
        compliance.create_sms_consent.assert_awaited_once()
        kw = compliance.create_sms_consent.call_args[1]
        assert kw["phone"] == lead.phone
        assert kw["consent_given"] is True
        assert kw["method"] == "lead_form"
        assert kw["customer_id"] == customer_svc.create_customer.return_value.id

        # Customer updated with sms_opt_in_at
        update_data = customer_svc.repository.update.call_args[0][1]
        assert "sms_opt_in_at" in update_data
        assert update_data["sms_opt_in_source"] == "lead_form"

    @given(terms_accepted=st.just(True), sms_consent=st.booleans())
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_terms_accepted_sets_fields(
        self,
        terms_accepted: bool,
        sms_consent: bool,
    ) -> None:
        """terms_accepted=true → Customer has terms_accepted + terms_accepted_at."""
        lead = _make_lead(sms_consent=sms_consent, terms_accepted=terms_accepted)
        repo, customer_svc, compliance = _setup_mocks(lead)
        svc = _build_service(repo, customer_svc, compliance)

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        update_data = customer_svc.repository.update.call_args[0][1]
        assert update_data["terms_accepted"] is True
        assert "terms_accepted_at" in update_data

    @given(sms_consent=st.just(False), terms_accepted=st.just(False))
    @settings(max_examples=10)
    @pytest.mark.asyncio
    async def test_no_consent_no_records(
        self,
        sms_consent: bool,
        terms_accepted: bool,
    ) -> None:
        """No consent fields → no sms_consent_record, no consent updates."""
        lead = _make_lead(
            sms_consent=sms_consent,
            terms_accepted=terms_accepted,
            email=None,
        )
        repo, customer_svc, compliance = _setup_mocks(lead)
        svc = _build_service(repo, customer_svc, compliance)

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        compliance.create_sms_consent.assert_not_awaited()
        customer_svc.repository.update.assert_not_awaited()

    @given(
        sms_consent=st.booleans(),
        terms_accepted=st.booleans(),
        has_email=st.booleans(),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_consent_combination_invariants(
        self,
        sms_consent: bool,
        terms_accepted: bool,
        has_email: bool,
    ) -> None:
        """For any consent combination, carry-over matches lead fields exactly."""
        email = "test@example.com" if has_email else None
        lead = _make_lead(
            sms_consent=sms_consent,
            terms_accepted=terms_accepted,
            email=email,
        )
        repo, customer_svc, compliance = _setup_mocks(lead)
        svc = _build_service(repo, customer_svc, compliance)

        await svc.convert_lead(lead.id, LeadConversionRequest(create_job=False))

        has_any = sms_consent or terms_accepted or has_email

        if has_any:
            customer_svc.repository.update.assert_awaited_once()
            update_data = customer_svc.repository.update.call_args[0][1]

            assert ("sms_opt_in_at" in update_data) == sms_consent
            assert ("terms_accepted" in update_data) == terms_accepted
            assert ("email_opt_in_at" in update_data) == has_email
        else:
            customer_svc.repository.update.assert_not_awaited()

        if sms_consent:
            compliance.create_sms_consent.assert_awaited_once()
        else:
            compliance.create_sms_consent.assert_not_awaited()
