"""Unit tests for lead SMS confirmation deferral (BUG #11/12/13 fix).

Tests that _send_sms_confirmation bypasses sms_service.send_message()
for leads, logging intent instead of creating SentMessage records
that would violate FK and CHECK constraints.

Validates: Requirements 54.1, 54.2, 54.3, 54.4
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.schemas.lead import LeadSubmission
from grins_platform.services.lead_service import LeadService

# =============================================================================
# Helpers
# =============================================================================


def _make_lead_mock(
    *,
    sms_consent: bool = False,
    phone: str = "6125550123",
    name: str = "John Doe",
) -> MagicMock:
    """Create a mock Lead object."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.name = name
    lead.phone = phone
    lead.email = None
    lead.zip_code = "55424"
    lead.situation = LeadSituation.NEW_SYSTEM.value
    lead.notes = None
    lead.source_site = "residential"
    lead.lead_source = "website"
    lead.source_detail = None
    lead.intake_tag = "schedule"
    lead.sms_consent = sms_consent
    lead.terms_accepted = False
    lead.email_marketing_consent = False
    lead.status = LeadStatus.NEW.value
    lead.assigned_to = None
    lead.customer_id = None
    lead.contacted_at = None
    lead.converted_at = None
    lead.created_at = datetime.now(tz=timezone.utc)
    lead.updated_at = datetime.now(tz=timezone.utc)
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
    sms_service: AsyncMock | None = None,
) -> tuple[LeadService, AsyncMock]:
    """Build LeadService with mocked dependencies."""
    repo = lead_repo or AsyncMock()
    sms_svc = sms_service or AsyncMock()
    service = LeadService(
        lead_repository=repo,
        customer_service=AsyncMock(),
        job_service=AsyncMock(),
        staff_repository=AsyncMock(),
        sms_service=sms_svc,
    )
    return service, sms_svc


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.unit
class TestLeadSmsDeferred:
    """Tests for _send_sms_confirmation deferral (BUG #11/12/13 fix)."""

    @pytest.mark.asyncio
    async def test_sms_consent_true_does_not_call_send_message(self) -> None:
        """Lead with sms_consent=True calls send_automated_message."""
        service, sms_svc = _build_service()
        sms_svc.send_automated_message = AsyncMock(
            return_value={"success": True},
        )
        lead = _make_lead_mock(sms_consent=True, phone="6125559999")

        await service._send_sms_confirmation(lead)

        sms_svc.send_message.assert_not_awaited()
        sms_svc.send_automated_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sms_consent_false_skips_and_does_not_call_send_message(
        self,
    ) -> None:
        """Lead with sms_consent=False should skip without calling send_message."""
        service, sms_svc = _build_service()
        lead = _make_lead_mock(sms_consent=False)

        await service._send_sms_confirmation(lead)

        sms_svc.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sms_confirmation_logs_sent(self) -> None:
        """_send_sms_confirmation logs 'lead.confirmation.sms_sent'
        when lead has sms_consent and phone and send succeeds."""
        sms_svc = AsyncMock()
        sms_svc.send_automated_message = AsyncMock(
            return_value={"success": True},
        )
        service, _ = _build_service(sms_service=sms_svc)
        lead = _make_lead_mock(sms_consent=True, phone="6125559999")

        with patch.object(service, "logger") as mock_logger:
            await service._send_sms_confirmation(lead)

            # Find the sent log call
            sent_calls = [
                call
                for call in mock_logger.info.call_args_list
                if call.args[0] == "lead.confirmation.sms_sent"
            ]
            assert len(sent_calls) == 1
            call_kwargs = sent_calls[0].kwargs
            assert call_kwargs["lead_id"] == str(lead.id)

    @pytest.mark.asyncio
    async def test_no_sms_service_logs_skipped(self) -> None:
        """When sms_service is None, logs skipped with sms_service_unavailable."""
        service = LeadService(
            lead_repository=AsyncMock(),
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
            sms_service=None,
        )
        lead = _make_lead_mock(sms_consent=True)

        with patch.object(service, "logger") as mock_logger:
            await service._send_sms_confirmation(lead)

            skipped_calls = [
                call
                for call in mock_logger.info.call_args_list
                if call.args[0] == "lead.sms_confirmation.skipped"
            ]
            assert len(skipped_calls) == 1
            assert skipped_calls[0].kwargs["reason"] == "sms_service_unavailable"

    @pytest.mark.asyncio
    async def test_no_phone_logs_skipped(self) -> None:
        """When lead has no phone, logs skipped with no_phone."""
        service, _ = _build_service()
        lead = _make_lead_mock(sms_consent=True, phone="")
        lead.phone = None

        with patch.object(service, "logger") as mock_logger:
            await service._send_sms_confirmation(lead)

            skipped_calls = [
                call
                for call in mock_logger.info.call_args_list
                if call.args[0] == "lead.sms_confirmation.skipped"
            ]
            assert len(skipped_calls) == 1
            assert skipped_calls[0].kwargs["reason"] == "no_phone"


@pytest.mark.unit
class TestSubmitLeadSmsIntegration:
    """Tests that submit_lead correctly integrates with the deferred SMS path."""

    @pytest.mark.asyncio
    async def test_submit_lead_with_sms_consent_true_persists_lead(self) -> None:
        """submit_lead with sms_consent=True creates lead and does NOT
        call sms_service.send_message."""
        sms_svc = AsyncMock()
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None

        new_lead = _make_lead_mock(sms_consent=True, phone="6125559999")
        repo.create.return_value = new_lead

        service = LeadService(
            lead_repository=repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
            sms_service=sms_svc,
        )

        data = LeadSubmission(
            name="SMS Test User",
            phone="6125559999",
            address="123 Main St, Denver, CO 80209",
            zip_code="55401",
            situation=LeadSituation.NEW_SYSTEM,
            sms_consent=True,
            source_site="residential",
        )

        result = await service.submit_lead(data)

        assert result.success is True
        assert result.lead_id == new_lead.id
        repo.create.assert_awaited_once()
        sms_svc.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_submit_lead_with_sms_consent_false_persists_lead(self) -> None:
        """submit_lead with sms_consent=False creates lead and does NOT
        call sms_service.send_message."""
        sms_svc = AsyncMock()
        repo = AsyncMock()
        repo.get_recent_by_phone_or_email.return_value = None
        repo.get_by_phone_and_active_status.return_value = None

        new_lead = _make_lead_mock(sms_consent=False, phone="6125550001")
        repo.create.return_value = new_lead

        service = LeadService(
            lead_repository=repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
            sms_service=sms_svc,
        )

        data = LeadSubmission(
            name="No SMS User",
            phone="6125550001",
            address="123 Main St, Denver, CO 80209",
            zip_code="55401",
            situation=LeadSituation.EXPLORING,
            sms_consent=False,
            source_site="residential",
        )

        result = await service.submit_lead(data)

        assert result.success is True
        assert result.lead_id == new_lead.id
        repo.create.assert_awaited_once()
        sms_svc.send_message.assert_not_awaited()
