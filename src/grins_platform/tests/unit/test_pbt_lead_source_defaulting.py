"""Property test: Lead Source Defaulting.

Property 17: POST /api/v1/leads without explicit lead_source defaults to WEBSITE;
POST /api/v1/leads/from-call without explicit lead_source defaults to PHONE_CALL.

Validates: Requirements 45.2, 45.4
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import (
    LeadSourceExtended,
    LeadStatus,
)
from grins_platform.schemas.lead import FromCallSubmission, LeadSubmission
from grins_platform.services.lead_service import LeadService

_NOW = datetime.now(tz=timezone.utc)


def _make_mock_lead(**overrides: object) -> MagicMock:
    """Create a minimal mock lead returned by repository.create."""
    lead = MagicMock()
    lead.id = overrides.get("id", uuid4())
    lead.name = overrides.get("name", "Test User")
    lead.phone = overrides.get("phone", "6125551234")
    lead.email = overrides.get("email")
    lead.zip_code = overrides.get("zip_code", "55401")
    lead.situation = overrides.get("situation", "repair")
    lead.notes = overrides.get("notes")
    lead.status = overrides.get("status", LeadStatus.NEW.value)
    lead.lead_source = overrides.get("lead_source", LeadSourceExtended.WEBSITE.value)
    lead.source_detail = overrides.get("source_detail")
    lead.intake_tag = overrides.get("intake_tag")
    lead.source_site = overrides.get("source_site", "residential")
    lead.sms_consent = overrides.get("sms_consent", False)
    lead.terms_accepted = overrides.get("terms_accepted", False)
    lead.assigned_to = None
    lead.customer_id = None
    lead.created_at = overrides.get("created_at", _NOW)
    lead.updated_at = overrides.get("updated_at", _NOW)
    return lead


def _build_service(mock_repo: AsyncMock) -> LeadService:
    return LeadService(
        lead_repository=mock_repo,
        customer_service=MagicMock(),
        job_service=MagicMock(),
        staff_repository=MagicMock(),
    )


@pytest.mark.unit
class TestLeadSourceDefaultingProperty:
    """Property 17: Lead Source Defaulting."""

    @given(
        source_site=st.sampled_from(["residential", "commercial", "landing"]),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_submit_lead_without_lead_source_defaults_to_website(
        self,
        source_site: str,
    ) -> None:
        """Website form submission without lead_source defaults to WEBSITE."""
        data = LeadSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="55401",
            situation="repair",
            source_site=source_site,
        )

        mock_lead = _make_mock_lead(lead_source=LeadSourceExtended.WEBSITE.value)
        mock_repo = AsyncMock()
        mock_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=mock_lead)

        service = _build_service(mock_repo)

        with (
            patch.object(service, "_send_sms_confirmation", new_callable=AsyncMock),
            patch.object(service, "_send_email_confirmation"),
        ):
            await service.submit_lead(data)

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["lead_source"] == LeadSourceExtended.WEBSITE.value

    @given(
        explicit_source=st.sampled_from(list(LeadSourceExtended)),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_submit_lead_with_explicit_source_uses_provided(
        self,
        explicit_source: LeadSourceExtended,
    ) -> None:
        """Website form with explicit lead_source uses the provided value."""
        data = LeadSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="55401",
            situation="repair",
            lead_source=explicit_source,
        )

        mock_lead = _make_mock_lead(lead_source=explicit_source.value)
        mock_repo = AsyncMock()
        mock_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=mock_lead)

        service = _build_service(mock_repo)

        with (
            patch.object(service, "_send_sms_confirmation", new_callable=AsyncMock),
            patch.object(service, "_send_email_confirmation"),
        ):
            await service.submit_lead(data)

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["lead_source"] == explicit_source.value

    @given(
        notes=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_from_call_without_lead_source_defaults_to_phone_call(
        self,
        notes: str | None,
    ) -> None:
        """From-call creation without lead_source defaults to PHONE_CALL."""
        data = FromCallSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="55401",
            situation="repair",
            notes=notes,
        )

        assert data.lead_source == LeadSourceExtended.PHONE_CALL

        mock_lead = _make_mock_lead(lead_source=LeadSourceExtended.PHONE_CALL.value)
        mock_repo = AsyncMock()
        mock_repo.create = AsyncMock(return_value=mock_lead)

        service = _build_service(mock_repo)

        with (
            patch.object(service, "_send_sms_confirmation", new_callable=AsyncMock),
            patch.object(service, "_send_email_confirmation"),
        ):
            await service.create_from_call(data)

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["lead_source"] == LeadSourceExtended.PHONE_CALL.value

    @given(
        explicit_source=st.sampled_from(list(LeadSourceExtended)),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_from_call_with_explicit_source_uses_provided(
        self,
        explicit_source: LeadSourceExtended,
    ) -> None:
        """From-call with explicit lead_source uses the provided value."""
        data = FromCallSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="55401",
            situation="repair",
            lead_source=explicit_source,
        )

        mock_lead = _make_mock_lead(lead_source=explicit_source.value)
        mock_repo = AsyncMock()
        mock_repo.create = AsyncMock(return_value=mock_lead)

        service = _build_service(mock_repo)

        with (
            patch.object(service, "_send_sms_confirmation", new_callable=AsyncMock),
            patch.object(service, "_send_email_confirmation"),
        ):
            await service.create_from_call(data)

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["lead_source"] == explicit_source.value
