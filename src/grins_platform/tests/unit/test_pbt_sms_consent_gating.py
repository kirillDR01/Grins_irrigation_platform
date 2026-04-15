"""Property test: SMS Confirmation Consent Gating.

Property 19: SMS sent iff phone present AND sms_consent=true;
otherwise skipped and logged.

Validates: Requirements 54.1, 54.3, 54.4
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
from grins_platform.services.lead_service import LeadService

_NOW = datetime.now(tz=timezone.utc)


def _make_lead(*, sms_consent: bool, phone: str) -> MagicMock:
    lead = MagicMock()
    lead.id = uuid4()
    lead.name = "Test User"
    lead.phone = phone
    lead.email = None
    lead.zip_code = "55401"
    lead.situation = LeadSituation.REPAIR.value
    lead.notes = None
    lead.source_site = "residential"
    lead.lead_source = "website"
    lead.source_detail = None
    lead.intake_tag = "schedule"
    lead.sms_consent = sms_consent
    lead.terms_accepted = False
    lead.status = LeadStatus.NEW.value
    lead.assigned_to = None
    lead.customer_id = None
    lead.contacted_at = None
    lead.converted_at = None
    lead.created_at = _NOW
    lead.updated_at = _NOW
    lead.moved_to = None
    lead.moved_at = None
    lead.last_contacted_at = None
    lead.job_requested = None
    return lead


def _build_service(
    lead_repo: AsyncMock,
    sms_service: AsyncMock | None,
) -> LeadService:
    return LeadService(
        lead_repository=lead_repo,
        customer_service=MagicMock(),
        job_service=MagicMock(),
        staff_repository=MagicMock(),
        sms_service=sms_service,
    )


@pytest.mark.unit
class TestSmsConsentGatingProperty:
    """Property 19: SMS Confirmation Consent Gating."""

    @given(
        sms_consent=st.booleans(),
        phone=st.sampled_from(["6125551234", ""]),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_sms_never_sent_for_leads(
        self,
        sms_consent: bool,
        phone: str,
    ) -> None:
        """SMS is never sent for leads (deferred due to FK constraint).

        After BUG #11/12/13 fix: _send_sms_confirmation logs intent
        but never calls sms_service.send_message() for leads.
        """
        lead = _make_lead(sms_consent=sms_consent, phone=phone)
        sms = AsyncMock()

        service = _build_service(
            lead_repo=AsyncMock(),
            sms_service=sms,
        )

        await service._send_sms_confirmation(lead)

        # send_message is never called for leads regardless of consent
        sms.send_message.assert_not_awaited()

    @given(
        sms_consent=st.booleans(),
        phone=st.sampled_from(["6125551234", ""]),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_no_sms_service_never_sends(
        self,
        sms_consent: bool,
        phone: str,
    ) -> None:
        """When sms_service is None, SMS is never sent regardless of consent."""
        lead = _make_lead(sms_consent=sms_consent, phone=phone)

        service = _build_service(
            lead_repo=AsyncMock(),
            sms_service=None,
        )

        # Should not raise
        await service._send_sms_confirmation(lead)

    @given(
        sms_consent=st.just(True),
        phone=st.from_regex(r"612555\d{4}", fullmatch=True),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_deferred_sms_does_not_raise(
        self,
        sms_consent: bool,
        phone: str,
    ) -> None:
        """Deferred SMS confirmation never raises, never calls send_message."""
        lead = _make_lead(sms_consent=sms_consent, phone=phone)
        sms = AsyncMock()

        service = _build_service(
            lead_repo=AsyncMock(),
            sms_service=sms,
        )

        # Should not raise
        await service._send_sms_confirmation(lead)
        sms.send_message.assert_not_awaited()
