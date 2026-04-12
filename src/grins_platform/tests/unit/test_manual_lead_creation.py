"""Unit tests for manual lead creation.

Tests ManualLeadCreate schema validation and LeadService.create_manual_lead method.

Validates: Requirements 7.1-7.5
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.schemas.lead import ManualLeadCreate
from grins_platform.services.lead_service import LeadService

# =============================================================================
# Helpers
# =============================================================================


def _make_lead_mock(
    *,
    name: str = "John Doe",
    phone: str = "6125550123",
    email: str | None = None,
    zip_code: str | None = None,
    situation: str = LeadSituation.EXPLORING.value,
    notes: str | None = None,
    lead_source: str = "manual",
    source_detail: str | None = "Manual CRM entry",
    city: str | None = None,
    state: str | None = None,
    address: str | None = None,
) -> MagicMock:
    """Create a mock Lead object."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.zip_code = zip_code
    lead.situation = situation
    lead.notes = notes
    lead.source_site = "admin"
    lead.lead_source = lead_source
    lead.source_detail = source_detail
    lead.intake_tag = None
    lead.sms_consent = False
    lead.terms_accepted = False
    lead.email_marketing_consent = False
    lead.status = LeadStatus.NEW.value
    lead.assigned_to = None
    lead.customer_id = None
    lead.contacted_at = None
    lead.converted_at = None
    lead.created_at = datetime.now(tz=timezone.utc)
    lead.updated_at = datetime.now(tz=timezone.utc)
    lead.city = city
    lead.state = state
    lead.address = address
    lead.action_tags = ["needs_contact"]
    lead.customer_type = None
    lead.property_type = None
    lead.moved_to = None
    lead.moved_at = None
    lead.last_contacted_at = None
    lead.job_requested = None
    return lead


# =============================================================================
# ManualLeadCreate Schema Validation Tests
# =============================================================================


@pytest.mark.unit
class TestManualLeadCreateSchema:
    """Tests for ManualLeadCreate Pydantic schema validation."""

    def test_valid_minimal_fields(self) -> None:
        """Name and phone are sufficient for creation."""
        data = ManualLeadCreate(name="John Doe", phone="6125550123")
        assert data.name == "John Doe"
        assert data.phone == "6125550123"
        assert data.email is None
        assert data.situation == LeadSituation.EXPLORING

    def test_valid_all_fields(self) -> None:
        """All fields can be provided."""
        data = ManualLeadCreate(
            name="Jane Smith",
            phone="6125559999",
            email="jane@example.com",
            address="123 Main St",
            city="Minneapolis",
            state="MN",
            zip_code="55401",
            situation=LeadSituation.REPAIR,
            notes="Walk-in customer",
        )
        assert data.name == "Jane Smith"
        assert data.email == "jane@example.com"
        assert data.city == "Minneapolis"
        assert data.zip_code == "55401"
        assert data.situation == LeadSituation.REPAIR
        assert data.notes == "Walk-in customer"

    def test_missing_name_raises_validation_error(self) -> None:
        """Name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ManualLeadCreate(name="", phone="6125550123")
        assert "name" in str(exc_info.value).lower()

    def test_missing_phone_raises_validation_error(self) -> None:
        """Phone is required."""
        with pytest.raises(ValidationError):
            ManualLeadCreate(name="John Doe", phone="")

    def test_phone_normalization(self) -> None:
        """Phone is normalized to 10 digits."""
        data = ManualLeadCreate(name="Test", phone="(612) 555-0123")
        assert data.phone == "6125550123"

    def test_invalid_zip_code_raises_error(self) -> None:
        """Zip code must be exactly 5 digits."""
        with pytest.raises(ValidationError):
            ManualLeadCreate(name="Test", phone="6125550123", zip_code="123")

    def test_valid_zip_code_normalized(self) -> None:
        """Zip code digits are extracted."""
        data = ManualLeadCreate(name="Test", phone="6125550123", zip_code="55401")
        assert data.zip_code == "55401"

    def test_html_stripped_from_name(self) -> None:
        """HTML tags are stripped from name."""
        data = ManualLeadCreate(name="<b>John</b> Doe", phone="6125550123")
        assert data.name == "John Doe"

    def test_html_stripped_from_notes(self) -> None:
        """HTML tags are stripped from notes."""
        data = ManualLeadCreate(
            name="Test",
            phone="6125550123",
            notes="<script>alert('xss')</script>Hello",
        )
        assert data.notes == "alert('xss')Hello"

    def test_default_situation_is_exploring(self) -> None:
        """Default situation is 'exploring'."""
        data = ManualLeadCreate(name="Test", phone="6125550123")
        assert data.situation == LeadSituation.EXPLORING


# =============================================================================
# LeadService.create_manual_lead Tests
# =============================================================================


@pytest.mark.unit
class TestCreateManualLead:
    """Tests for LeadService.create_manual_lead method."""

    @pytest.fixture
    def mock_lead_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_lead_repo: AsyncMock) -> LeadService:
        return LeadService(
            lead_repository=mock_lead_repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_creates_lead_with_manual_source(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Manual lead is created with lead_source='manual'."""
        mock_lead = _make_lead_mock(name="John Doe", phone="6125550123")
        mock_lead_repo.create.return_value = mock_lead

        data = ManualLeadCreate(name="John Doe", phone="6125550123")
        result = await service.create_manual_lead(data)

        assert result.id == mock_lead.id
        mock_lead_repo.create.assert_awaited_once()

        call_kwargs = mock_lead_repo.create.call_args[1]
        assert call_kwargs["lead_source"] == "manual"
        assert call_kwargs["source_detail"] == "Manual CRM entry"
        assert call_kwargs["source_site"] == "admin"
        assert call_kwargs["status"] == LeadStatus.NEW.value

    @pytest.mark.asyncio
    async def test_creates_lead_with_all_fields(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """All provided fields are passed to the repository."""
        mock_lead = _make_lead_mock(
            name="Jane Smith",
            phone="6125559999",
            email="jane@example.com",
            city="Minneapolis",
            state="MN",
            address="123 Main St",
        )
        mock_lead_repo.create.return_value = mock_lead

        data = ManualLeadCreate(
            name="Jane Smith",
            phone="6125559999",
            email="jane@example.com",
            address="123 Main St",
            city="Minneapolis",
            state="MN",
            zip_code="55401",
            situation=LeadSituation.REPAIR,
            notes="Walk-in",
        )
        result = await service.create_manual_lead(data)

        assert result.id == mock_lead.id
        call_kwargs = mock_lead_repo.create.call_args[1]
        assert call_kwargs["name"] == "Jane Smith"
        assert call_kwargs["phone"] == "6125559999"
        assert call_kwargs["email"] == "jane@example.com"
        assert call_kwargs["address"] == "123 Main St"
        assert call_kwargs["notes"] == "Walk-in"
        assert call_kwargs["situation"] == LeadSituation.REPAIR.value

    @pytest.mark.asyncio
    async def test_sets_needs_contact_action_tag(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """New manual leads get NEEDS_CONTACT action tag."""
        mock_lead = _make_lead_mock()
        mock_lead_repo.create.return_value = mock_lead

        data = ManualLeadCreate(name="Test", phone="6125550123")
        await service.create_manual_lead(data)

        call_kwargs = mock_lead_repo.create.call_args[1]
        assert "needs_contact" in call_kwargs["action_tags"]
