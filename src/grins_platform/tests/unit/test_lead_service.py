"""Unit tests for LeadService.

This module tests all LeadService methods using mocked dependencies
(LeadRepository, CustomerService, JobService, StaffRepository).

Validates: Requirements 1-8, 13, 15
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    InvalidLeadStatusTransitionError,
    LeadAlreadyConvertedError,
    LeadNotFoundError,
    StaffNotFoundError,
)
from grins_platform.models.enums import (
    LeadSituation,
    LeadStatus,
)
from grins_platform.schemas.lead import (
    LeadConversionRequest,
    LeadListParams,
    LeadSubmission,
    LeadUpdate,
)
from grins_platform.services.lead_service import LeadService

# =============================================================================
# Fixtures
# =============================================================================


def _make_lead_mock(
    *,
    lead_id: None | object = None,
    name: str = "John Doe",
    phone: str = "6125550123",
    email: str | None = None,
    zip_code: str = "55424",
    situation: str = LeadSituation.NEW_SYSTEM.value,
    notes: str | None = None,
    source_site: str = "residential",
    status: str = LeadStatus.NEW.value,
    assigned_to: None | object = None,
    customer_id: None | object = None,
    contacted_at: datetime | None = None,
    converted_at: datetime | None = None,
) -> MagicMock:
    """Create a mock Lead object with given attributes."""
    lead = MagicMock()
    lead.id = lead_id or uuid4()
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.zip_code = zip_code
    lead.situation = situation
    lead.notes = notes
    lead.source_site = source_site
    lead.status = status
    lead.assigned_to = assigned_to
    lead.customer_id = customer_id
    lead.contacted_at = contacted_at
    lead.converted_at = converted_at
    lead.created_at = datetime.now(tz=timezone.utc)
    lead.updated_at = datetime.now(tz=timezone.utc)
    return lead


# =============================================================================
# split_name tests
# =============================================================================


@pytest.mark.unit
class TestSplitName:
    """Tests for LeadService.split_name static method."""

    def test_single_word_returns_word_and_empty(self) -> None:
        """Single-word name → (word, '')."""
        first, last = LeadService.split_name("Viktor")
        assert first == "Viktor"
        assert last == ""

    def test_two_words_returns_first_and_last(self) -> None:
        """Two-word name → (first, last)."""
        first, last = LeadService.split_name("John Doe")
        assert first == "John"
        assert last == "Doe"

    def test_three_words_returns_first_and_rest(self) -> None:
        """Three+ word name → (first, rest)."""
        first, last = LeadService.split_name("John Michael Doe")
        assert first == "John"
        assert last == "Michael Doe"

    def test_leading_trailing_whitespace_stripped(self) -> None:
        """Whitespace is stripped before splitting."""
        first, last = LeadService.split_name("  Jane Smith  ")
        assert first == "Jane"
        assert last == "Smith"

    def test_empty_string_returns_empty_and_empty(self) -> None:
        """Empty string → ('', '')."""
        first, last = LeadService.split_name("")
        assert first == ""
        assert last == ""


# =============================================================================
# submit_lead tests
# =============================================================================


@pytest.mark.unit
class TestSubmitLead:
    """Tests for LeadService.submit_lead method."""

    @pytest.fixture
    def mock_lead_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_customer_service(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_job_service(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
        mock_job_service: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> LeadService:
        return LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=mock_staff_repo,
        )

    @pytest.mark.asyncio
    async def test_happy_path_creates_new_lead(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """New lead is created when no duplicate exists."""
        mock_lead_repo.get_by_phone_and_active_status.return_value = None
        new_lead = _make_lead_mock()
        mock_lead_repo.create.return_value = new_lead

        data = LeadSubmission(
            name="John Doe",
            phone="(612) 555-0123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )

        result = await service.submit_lead(data)

        assert result.success is True
        assert result.lead_id == new_lead.id
        mock_lead_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_honeypot_rejection_returns_fake_success(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Non-empty honeypot returns fake 201 without storing."""
        data = LeadSubmission(
            name="Bot User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            website="http://spam.com",
        )

        result = await service.submit_lead(data)

        assert result.success is True
        assert result.lead_id is None
        mock_lead_repo.create.assert_not_awaited()
        mock_lead_repo.get_by_phone_and_active_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_duplicate_detection_updates_existing(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Duplicate phone with active status updates existing lead."""
        existing = _make_lead_mock(
            status=LeadStatus.NEW.value,
            email=None,
            notes=None,
        )
        mock_lead_repo.get_by_phone_and_active_status.return_value = existing

        data = LeadSubmission(
            name="John Doe",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.UPGRADE,
            email="john@example.com",
            notes="New notes",
        )

        result = await service.submit_lead(data)

        assert result.success is True
        assert result.lead_id == existing.id
        mock_lead_repo.create.assert_not_awaited()
        mock_lead_repo.update.assert_awaited_once()

        # Verify update data
        update_call = mock_lead_repo.update.call_args
        update_data = update_call[0][1]
        assert update_data["email"] == "john@example.com"
        assert update_data["notes"] == "New notes"
        assert update_data["situation"] == LeadSituation.UPGRADE.value

    @pytest.mark.asyncio
    async def test_duplicate_does_not_overwrite_existing_email(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Duplicate detection does not overwrite existing email with new one."""
        existing = _make_lead_mock(
            status=LeadStatus.CONTACTED.value,
            email="existing@example.com",
            notes="Old notes",
        )
        mock_lead_repo.get_by_phone_and_active_status.return_value = existing

        data = LeadSubmission(
            name="John Doe",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            email="new@example.com",
            notes="Additional notes",
        )

        await service.submit_lead(data)

        update_data = mock_lead_repo.update.call_args[0][1]
        # Email should NOT be in update_data since existing already has one
        assert "email" not in update_data
        # Notes should be appended
        assert update_data["notes"] == "Old notes\nAdditional notes"

    @pytest.mark.asyncio
    async def test_empty_honeypot_processes_normally(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Empty honeypot field processes lead normally."""
        mock_lead_repo.get_by_phone_and_active_status.return_value = None
        new_lead = _make_lead_mock()
        mock_lead_repo.create.return_value = new_lead

        data = LeadSubmission(
            name="Real User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.EXPLORING,
            website="",
        )

        result = await service.submit_lead(data)

        assert result.success is True
        assert result.lead_id == new_lead.id
        mock_lead_repo.create.assert_awaited_once()


# =============================================================================
# get_lead tests
# =============================================================================


@pytest.mark.unit
class TestGetLead:
    """Tests for LeadService.get_lead method."""

    @pytest.fixture
    def service(self) -> LeadService:
        return LeadService(
            lead_repository=AsyncMock(),
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_found_returns_lead_response(self, service: LeadService) -> None:
        """Existing lead returns LeadResponse."""
        lead = _make_lead_mock()
        service.lead_repository.get_by_id.return_value = lead  # type: ignore[attr-defined]

        result = await service.get_lead(lead.id)

        assert result.id == lead.id
        assert result.name == lead.name

    @pytest.mark.asyncio
    async def test_not_found_raises_error(self, service: LeadService) -> None:
        """Missing lead raises LeadNotFoundError."""
        service.lead_repository.get_by_id.return_value = None  # type: ignore[attr-defined]
        lead_id = uuid4()

        with pytest.raises(LeadNotFoundError) as exc_info:
            await service.get_lead(lead_id)

        assert exc_info.value.lead_id == lead_id


# =============================================================================
# list_leads tests
# =============================================================================


@pytest.mark.unit
class TestListLeads:
    """Tests for LeadService.list_leads method."""

    @pytest.fixture
    def service(self) -> LeadService:
        return LeadService(
            lead_repository=AsyncMock(),
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_basic_pagination(self, service: LeadService) -> None:
        """Returns paginated response with correct metadata."""
        leads = [_make_lead_mock() for _ in range(3)]
        service.lead_repository.list_with_filters.return_value = (leads, 25)  # type: ignore[attr-defined]

        params = LeadListParams(page=1, page_size=10)
        result = await service.list_leads(params)

        assert len(result.items) == 3
        assert result.total == 25
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 3  # ceil(25/10)

    @pytest.mark.asyncio
    async def test_empty_results(self, service: LeadService) -> None:
        """Empty results return zero total_pages."""
        service.lead_repository.list_with_filters.return_value = ([], 0)  # type: ignore[attr-defined]

        params = LeadListParams(page=1, page_size=20)
        result = await service.list_leads(params)

        assert len(result.items) == 0
        assert result.total == 0
        assert result.total_pages == 0


# =============================================================================
# update_lead tests
# =============================================================================


@pytest.mark.unit
class TestUpdateLead:
    """Tests for LeadService.update_lead method."""

    @pytest.fixture
    def mock_lead_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_staff_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_lead_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> LeadService:
        return LeadService(
            lead_repository=mock_lead_repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=mock_staff_repo,
        )

    @pytest.mark.asyncio
    async def test_valid_status_transition(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Valid status transition succeeds."""
        lead = _make_lead_mock(status=LeadStatus.NEW.value)
        mock_lead_repo.get_by_id.return_value = lead
        updated_lead = _make_lead_mock(status=LeadStatus.CONTACTED.value)
        mock_lead_repo.update.return_value = updated_lead

        data = LeadUpdate(status=LeadStatus.CONTACTED)
        result = await service.update_lead(lead.id, data)

        assert result.status == LeadStatus.CONTACTED
        mock_lead_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_status_transition_raises_error(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Invalid status transition raises InvalidLeadStatusTransitionError."""
        lead = _make_lead_mock(status=LeadStatus.CONVERTED.value)
        mock_lead_repo.get_by_id.return_value = lead

        data = LeadUpdate(status=LeadStatus.NEW)

        with pytest.raises(InvalidLeadStatusTransitionError) as exc_info:
            await service.update_lead(lead.id, data)

        assert exc_info.value.current_status == LeadStatus.CONVERTED
        assert exc_info.value.requested_status == LeadStatus.NEW

    @pytest.mark.asyncio
    async def test_contacted_auto_sets_contacted_at(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Transitioning to 'contacted' auto-sets contacted_at when null."""
        lead = _make_lead_mock(
            status=LeadStatus.NEW.value,
            contacted_at=None,
        )
        mock_lead_repo.get_by_id.return_value = lead
        updated_lead = _make_lead_mock(status=LeadStatus.CONTACTED.value)
        mock_lead_repo.update.return_value = updated_lead

        data = LeadUpdate(status=LeadStatus.CONTACTED)
        await service.update_lead(lead.id, data)

        update_data = mock_lead_repo.update.call_args[0][1]
        assert "contacted_at" in update_data
        assert isinstance(update_data["contacted_at"], datetime)

    @pytest.mark.asyncio
    async def test_contacted_does_not_overwrite_existing_contacted_at(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Transitioning to 'contacted' does not overwrite existing contacted_at.

        Note: This tests the case where a lead goes lost → new → contacted
        and already has a contacted_at from a previous cycle.
        We need to set up a valid transition: new → contacted.
        """
        existing_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        lead = _make_lead_mock(
            status=LeadStatus.NEW.value,
            contacted_at=existing_time,
        )
        mock_lead_repo.get_by_id.return_value = lead
        updated_lead = _make_lead_mock(status=LeadStatus.CONTACTED.value)
        mock_lead_repo.update.return_value = updated_lead

        data = LeadUpdate(status=LeadStatus.CONTACTED)
        await service.update_lead(lead.id, data)

        update_data = mock_lead_repo.update.call_args[0][1]
        # contacted_at should NOT be in update_data since it already exists
        assert "contacted_at" not in update_data

    @pytest.mark.asyncio
    async def test_staff_validation_on_assignment(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Assigning to non-existent staff raises StaffNotFoundError."""
        lead = _make_lead_mock(status=LeadStatus.NEW.value)
        mock_lead_repo.get_by_id.return_value = lead
        mock_staff_repo.get_by_id.return_value = None

        staff_id = uuid4()
        data = LeadUpdate(assigned_to=staff_id)

        with pytest.raises(StaffNotFoundError) as exc_info:
            await service.update_lead(lead.id, data)

        assert exc_info.value.staff_id == staff_id

    @pytest.mark.asyncio
    async def test_staff_validation_passes_for_existing_staff(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_staff_repo: AsyncMock,
    ) -> None:
        """Assigning to existing staff succeeds."""
        lead = _make_lead_mock(status=LeadStatus.NEW.value)
        mock_lead_repo.get_by_id.return_value = lead
        mock_staff_repo.get_by_id.return_value = MagicMock()
        updated_lead = _make_lead_mock(status=LeadStatus.NEW.value)
        mock_lead_repo.update.return_value = updated_lead

        staff_id = uuid4()
        data = LeadUpdate(assigned_to=staff_id)
        result = await service.update_lead(lead.id, data)

        assert result is not None
        mock_lead_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_found_raises_error(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Updating non-existent lead raises LeadNotFoundError."""
        mock_lead_repo.get_by_id.return_value = None
        lead_id = uuid4()

        data = LeadUpdate(status=LeadStatus.CONTACTED)

        with pytest.raises(LeadNotFoundError):
            await service.update_lead(lead_id, data)

    @pytest.mark.asyncio
    async def test_converted_auto_sets_converted_at(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Transitioning to 'converted' auto-sets converted_at."""
        lead = _make_lead_mock(status=LeadStatus.QUALIFIED.value)
        mock_lead_repo.get_by_id.return_value = lead
        updated_lead = _make_lead_mock(status=LeadStatus.CONVERTED.value)
        mock_lead_repo.update.return_value = updated_lead

        data = LeadUpdate(status=LeadStatus.CONVERTED)
        await service.update_lead(lead.id, data)

        update_data = mock_lead_repo.update.call_args[0][1]
        assert "converted_at" in update_data
        assert isinstance(update_data["converted_at"], datetime)


# =============================================================================
# convert_lead tests
# =============================================================================


@pytest.mark.unit
class TestConvertLead:
    """Tests for LeadService.convert_lead method."""

    @pytest.fixture
    def mock_lead_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_customer_service(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_job_service(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> LeadService:
        return LeadService(
            lead_repository=mock_lead_repo,
            customer_service=mock_customer_service,
            job_service=mock_job_service,
            staff_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_happy_path_with_job(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Convert lead creates customer and job."""
        lead = _make_lead_mock(
            name="John Doe",
            status=LeadStatus.QUALIFIED.value,
            situation=LeadSituation.NEW_SYSTEM.value,
        )
        mock_lead_repo.get_by_id.return_value = lead

        customer_response = MagicMock()
        customer_response.id = uuid4()
        mock_customer_service.create_customer.return_value = customer_response

        job_mock = MagicMock()
        job_mock.id = uuid4()
        mock_job_service.create_job.return_value = job_mock

        data = LeadConversionRequest(create_job=True)
        result = await service.convert_lead(lead.id, data)

        assert result.success is True
        assert result.customer_id == customer_response.id
        assert result.job_id == job_mock.id
        assert result.lead_id == lead.id

        mock_customer_service.create_customer.assert_awaited_once()
        mock_job_service.create_job.assert_awaited_once()
        mock_lead_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_happy_path_without_job(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Convert lead creates customer but no job when create_job=False."""
        lead = _make_lead_mock(
            name="Jane Smith",
            status=LeadStatus.NEW.value,
            situation=LeadSituation.EXPLORING.value,
        )
        mock_lead_repo.get_by_id.return_value = lead

        customer_response = MagicMock()
        customer_response.id = uuid4()
        mock_customer_service.create_customer.return_value = customer_response

        data = LeadConversionRequest(create_job=False)
        result = await service.convert_lead(lead.id, data)

        assert result.success is True
        assert result.customer_id == customer_response.id
        assert result.job_id is None

        mock_job_service.create_job.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_already_converted_raises_error(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Converting already-converted lead raises LeadAlreadyConvertedError."""
        lead = _make_lead_mock(status=LeadStatus.CONVERTED.value)
        mock_lead_repo.get_by_id.return_value = lead

        data = LeadConversionRequest()

        with pytest.raises(LeadAlreadyConvertedError) as exc_info:
            await service.convert_lead(lead.id, data)

        assert exc_info.value.lead_id == lead.id

    @pytest.mark.asyncio
    async def test_name_splitting_default(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Auto-splits name when no overrides provided."""
        lead = _make_lead_mock(
            name="John Michael Doe",
            status=LeadStatus.NEW.value,
        )
        mock_lead_repo.get_by_id.return_value = lead

        customer_response = MagicMock()
        customer_response.id = uuid4()
        mock_customer_service.create_customer.return_value = customer_response

        data = LeadConversionRequest(create_job=False)
        await service.convert_lead(lead.id, data)

        # Verify customer was created with split name
        create_call = mock_customer_service.create_customer.call_args
        customer_data = create_call[0][0]
        assert customer_data.first_name == "John"
        assert customer_data.last_name == "Michael Doe"

    @pytest.mark.asyncio
    async def test_name_override(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Uses provided first_name/last_name overrides."""
        lead = _make_lead_mock(
            name="John Doe",
            status=LeadStatus.NEW.value,
        )
        mock_lead_repo.get_by_id.return_value = lead

        customer_response = MagicMock()
        customer_response.id = uuid4()
        mock_customer_service.create_customer.return_value = customer_response

        data = LeadConversionRequest(
            first_name="Jonathan",
            last_name="Doe-Smith",
            create_job=False,
        )
        await service.convert_lead(lead.id, data)

        create_call = mock_customer_service.create_customer.call_args
        customer_data = create_call[0][0]
        assert customer_data.first_name == "Jonathan"
        assert customer_data.last_name == "Doe-Smith"

    @pytest.mark.asyncio
    async def test_single_word_name_uses_first_as_last(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
    ) -> None:
        """Single-word name uses first_name as last_name fallback."""
        lead = _make_lead_mock(
            name="Viktor",
            status=LeadStatus.NEW.value,
        )
        mock_lead_repo.get_by_id.return_value = lead

        customer_response = MagicMock()
        customer_response.id = uuid4()
        mock_customer_service.create_customer.return_value = customer_response

        data = LeadConversionRequest(create_job=False)
        await service.convert_lead(lead.id, data)

        create_call = mock_customer_service.create_customer.call_args
        customer_data = create_call[0][0]
        assert customer_data.first_name == "Viktor"
        # last_name should be "Viktor" (fallback since split produces "")
        assert customer_data.last_name == "Viktor"

    @pytest.mark.asyncio
    async def test_not_found_raises_error(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Converting non-existent lead raises LeadNotFoundError."""
        mock_lead_repo.get_by_id.return_value = None
        lead_id = uuid4()

        data = LeadConversionRequest()

        with pytest.raises(LeadNotFoundError):
            await service.convert_lead(lead_id, data)

    @pytest.mark.asyncio
    async def test_situation_maps_to_correct_job_type(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Repair situation maps to ready_to_schedule job type."""
        lead = _make_lead_mock(
            name="John Doe",
            status=LeadStatus.NEW.value,
            situation=LeadSituation.REPAIR.value,
        )
        mock_lead_repo.get_by_id.return_value = lead

        customer_response = MagicMock()
        customer_response.id = uuid4()
        mock_customer_service.create_customer.return_value = customer_response

        job_mock = MagicMock()
        job_mock.id = uuid4()
        mock_job_service.create_job.return_value = job_mock

        data = LeadConversionRequest(create_job=True)
        await service.convert_lead(lead.id, data)

        job_create_call = mock_job_service.create_job.call_args
        job_data = job_create_call[0][0]
        assert job_data.job_type == "ready_to_schedule"
        assert job_data.description == "Repair Request"

    @pytest.mark.asyncio
    async def test_job_description_override(
        self,
        service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Custom job_description overrides default."""
        lead = _make_lead_mock(
            name="John Doe",
            status=LeadStatus.NEW.value,
            situation=LeadSituation.NEW_SYSTEM.value,
        )
        mock_lead_repo.get_by_id.return_value = lead

        customer_response = MagicMock()
        customer_response.id = uuid4()
        mock_customer_service.create_customer.return_value = customer_response

        job_mock = MagicMock()
        job_mock.id = uuid4()
        mock_job_service.create_job.return_value = job_mock

        data = LeadConversionRequest(
            create_job=True,
            job_description="Custom install for large property",
        )
        await service.convert_lead(lead.id, data)

        job_create_call = mock_job_service.create_job.call_args
        job_data = job_create_call[0][0]
        assert job_data.description == "Custom install for large property"


# =============================================================================
# delete_lead tests
# =============================================================================


@pytest.mark.unit
class TestDeleteLead:
    """Tests for LeadService.delete_lead method."""

    @pytest.fixture
    def service(self) -> LeadService:
        return LeadService(
            lead_repository=AsyncMock(),
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_found_deletes_lead(self, service: LeadService) -> None:
        """Existing lead is deleted."""
        lead = _make_lead_mock()
        service.lead_repository.get_by_id.return_value = lead  # type: ignore[attr-defined]

        await service.delete_lead(lead.id)

        service.lead_repository.delete.assert_awaited_once_with(lead.id)  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_not_found_raises_error(self, service: LeadService) -> None:
        """Deleting non-existent lead raises LeadNotFoundError."""
        service.lead_repository.get_by_id.return_value = None  # type: ignore[attr-defined]
        lead_id = uuid4()

        with pytest.raises(LeadNotFoundError):
            await service.delete_lead(lead_id)


# =============================================================================
# get_dashboard_metrics tests
# =============================================================================


@pytest.mark.unit
class TestGetDashboardMetrics:
    """Tests for LeadService.get_dashboard_metrics method."""

    @pytest.fixture
    def service(self) -> LeadService:
        return LeadService(
            lead_repository=AsyncMock(),
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_returns_correct_dict(self, service: LeadService) -> None:
        """Returns dict with new_leads_today and uncontacted_leads."""
        service.lead_repository.count_new_today.return_value = 5  # type: ignore[attr-defined]
        service.lead_repository.count_uncontacted.return_value = 12  # type: ignore[attr-defined]

        result = await service.get_dashboard_metrics()

        assert result == {
            "new_leads_today": 5,
            "uncontacted_leads": 12,
        }
