"""Property test: Intake Tag Defaulting.

Property 18: Website form without explicit intake_tag defaults to SCHEDULE;
from-call without explicit intake_tag remains NULL.

Validates: Requirements 48.2, 48.3
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
    IntakeTag,
    LeadSourceExtended,
    LeadStatus,
)
from grins_platform.schemas.lead import FromCallSubmission, LeadSubmission
from grins_platform.services.lead_service import LeadService

_NOW = datetime.now(tz=timezone.utc)


def _make_mock_lead(**overrides: object) -> MagicMock:
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
    lead.contacted_at = None
    lead.converted_at = None
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
class TestIntakeTagDefaultingProperty:
    """Property 18: Intake Tag Defaulting."""

    @given(
        source_site=st.sampled_from(["residential", "commercial", "landing"]),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_website_form_without_intake_tag_defaults_to_schedule(
        self,
        source_site: str,
    ) -> None:
        """Website form without explicit intake_tag defaults to SCHEDULE."""
        data = LeadSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="55401",
            situation="repair",
            source_site=source_site,
        )

        mock_lead = _make_mock_lead(intake_tag=IntakeTag.SCHEDULE.value)
        mock_repo = AsyncMock()
        mock_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
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
        assert call_kwargs["intake_tag"] == IntakeTag.SCHEDULE.value

    @given(
        explicit_tag=st.sampled_from(list(IntakeTag)),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_website_form_with_explicit_tag_uses_provided(
        self,
        explicit_tag: IntakeTag,
    ) -> None:
        """Website form with explicit intake_tag uses the provided value."""
        data = LeadSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="55401",
            situation="repair",
            intake_tag=explicit_tag,
        )

        mock_lead = _make_mock_lead(intake_tag=explicit_tag.value)
        mock_repo = AsyncMock()
        mock_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
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
        assert call_kwargs["intake_tag"] == explicit_tag.value

    @given(
        notes=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_from_call_without_intake_tag_remains_null(
        self,
        notes: str | None,
    ) -> None:
        """From-call without explicit intake_tag remains NULL."""
        data = FromCallSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="55401",
            situation="repair",
            notes=notes,
        )

        assert data.intake_tag is None

        mock_lead = _make_mock_lead(intake_tag=None)
        mock_repo = AsyncMock()
        mock_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=mock_lead)

        service = _build_service(mock_repo)

        with (
            patch.object(service, "_send_sms_confirmation", new_callable=AsyncMock),
            patch.object(service, "_send_email_confirmation"),
        ):
            await service.create_from_call(data)

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["intake_tag"] is None

    @given(
        explicit_tag=st.sampled_from(list(IntakeTag)),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_from_call_with_explicit_tag_uses_provided(
        self,
        explicit_tag: IntakeTag,
    ) -> None:
        """From-call with explicit intake_tag uses the provided value."""
        data = FromCallSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="55401",
            situation="repair",
            intake_tag=explicit_tag,
        )

        mock_lead = _make_mock_lead(intake_tag=explicit_tag.value)
        mock_repo = AsyncMock()
        mock_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=mock_lead)

        service = _build_service(mock_repo)

        with (
            patch.object(service, "_send_sms_confirmation", new_callable=AsyncMock),
            patch.object(service, "_send_email_confirmation"),
        ):
            await service.create_from_call(data)

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["intake_tag"] == explicit_tag.value
