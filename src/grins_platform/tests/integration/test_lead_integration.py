"""
Integration tests for lead capture feature.

Tests cover end-to-end flows through the service layer:
- Lead submission → dashboard metrics
- Lead lifecycle (submit → list → update → convert)
- Duplicate detection across submissions

Validates: Requirements 1, 3, 5, 6, 7, 8, 14.3
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.schemas.lead import (
    LeadConversionRequest,
    LeadListParams,
    LeadSubmission,
    LeadUpdate,
)
from grins_platform.services.lead_service import LeadService


def _make_lead_model(**overrides: Any) -> MagicMock:
    """Create a mock Lead model instance."""
    lead_id = overrides.get("id", uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    lead = MagicMock()
    lead.id = lead_id
    lead.name = overrides.get("name", "Test User")
    lead.phone = overrides.get("phone", "6125551234")
    lead.email = overrides.get("email")
    lead.zip_code = overrides.get("zip_code", "55424")
    lead.situation = overrides.get("situation", LeadSituation.NEW_SYSTEM.value)
    lead.notes = overrides.get("notes")
    lead.source_site = overrides.get("source_site", "residential")
    lead.status = overrides.get("status", LeadStatus.NEW.value)
    lead.assigned_to = overrides.get("assigned_to")
    lead.customer_id = overrides.get("customer_id")
    lead.contacted_at = overrides.get("contacted_at")
    lead.converted_at = overrides.get("converted_at")
    lead.created_at = overrides.get("created_at", now)
    lead.updated_at = overrides.get("updated_at", now)
    return lead


@pytest.fixture
def mock_lead_repo() -> AsyncMock:
    """Create mock LeadRepository."""
    repo = AsyncMock()
    repo.count_new_today = AsyncMock(return_value=0)
    repo.count_uncontacted = AsyncMock(return_value=0)
    repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_customer_service() -> AsyncMock:
    """Create mock CustomerService."""
    svc = AsyncMock()
    customer = MagicMock()
    customer.id = uuid.uuid4()
    customer.first_name = "Test"
    customer.last_name = "User"
    svc.create_customer = AsyncMock(return_value=customer)
    return svc


@pytest.fixture
def mock_job_service() -> AsyncMock:
    """Create mock JobService."""
    svc = AsyncMock()
    job = MagicMock()
    job.id = uuid.uuid4()
    svc.create_job = AsyncMock(return_value=job)
    return svc


@pytest.fixture
def mock_staff_repo() -> AsyncMock:
    """Create mock StaffRepository."""
    return AsyncMock()


@pytest.fixture
def lead_service(
    mock_lead_repo: AsyncMock,
    mock_customer_service: AsyncMock,
    mock_job_service: AsyncMock,
    mock_staff_repo: AsyncMock,
) -> LeadService:
    """Create LeadService with mocked dependencies."""
    return LeadService(
        lead_repository=mock_lead_repo,
        customer_service=mock_customer_service,
        job_service=mock_job_service,
        staff_repository=mock_staff_repo,
    )


@pytest.mark.integration
class TestLeadSubmissionDashboardMetrics:
    """Test 8.1: Lead submission → dashboard metrics integration.

    Validates: Requirement 8, 14.3
    """

    @pytest.mark.asyncio
    async def test_submit_lead_then_dashboard_reflects_new_lead(
        self,
        lead_service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Submit a lead, then verify dashboard metrics reflect it."""
        # Create a lead model that will be "created"
        new_lead = _make_lead_model(status=LeadStatus.NEW.value)
        mock_lead_repo.create = AsyncMock(return_value=new_lead)

        # Submit the lead
        submission = LeadSubmission(
            name="Jane Smith",
            phone="(612) 555-9876",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
        )
        result = await lead_service.submit_lead(submission)
        assert result.success is True
        assert result.lead_id == new_lead.id

        # Now simulate dashboard metrics reflecting the new lead
        mock_lead_repo.count_new_today = AsyncMock(return_value=1)
        mock_lead_repo.count_uncontacted = AsyncMock(return_value=1)

        metrics = await lead_service.get_dashboard_metrics()
        assert metrics["new_leads_today"] == 1
        assert metrics["uncontacted_leads"] == 1

    @pytest.mark.asyncio
    async def test_honeypot_submission_does_not_affect_dashboard(
        self,
        lead_service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Honeypot submissions should not create leads or affect metrics."""
        submission = LeadSubmission(
            name="Bot User",
            phone="(612) 555-0000",
            zip_code="55424",
            situation=LeadSituation.EXPLORING,
            source_site="residential",
            website="http://spam.com",  # honeypot filled
        )
        result = await lead_service.submit_lead(submission)
        assert result.success is True
        assert result.lead_id is None

        # Repository create should NOT have been called
        mock_lead_repo.create.assert_not_called()

        # Dashboard metrics should still be 0
        metrics = await lead_service.get_dashboard_metrics()
        assert metrics["new_leads_today"] == 0
        assert metrics["uncontacted_leads"] == 0


@pytest.mark.integration
class TestLeadLifecycle:
    """Test 8.2: Full lead lifecycle integration.

    Submit → list → update status → convert to customer.

    Validates: Requirements 1, 5, 6, 7, 14.3
    """

    @pytest.mark.asyncio
    async def test_full_lifecycle_submit_to_convert(
        self,
        lead_service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Test complete lifecycle: submit → list → update → convert."""
        lead_id = uuid.uuid4()
        customer_id = mock_customer_service.create_customer.return_value.id
        job_id = mock_job_service.create_job.return_value.id

        # --- Step 1: Submit lead ---
        new_lead = _make_lead_model(id=lead_id, name="Viktor Grin", phone="6125551234")
        mock_lead_repo.create = AsyncMock(return_value=new_lead)

        submission = LeadSubmission(
            name="Viktor Grin",
            phone="(612) 555-1234",
            zip_code="55346",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
        )
        submit_result = await lead_service.submit_lead(submission)
        assert submit_result.success is True

        # --- Step 2: List leads ---
        mock_lead_repo.list_with_filters = AsyncMock(
            return_value=([new_lead], 1),
        )
        params = LeadListParams(page=1, page_size=20)
        list_result = await lead_service.list_leads(params)
        assert list_result.total == 1
        assert len(list_result.items) == 1

        # --- Step 3: Update status to contacted ---
        contacted_lead = _make_lead_model(
            id=lead_id,
            name="Viktor Grin",
            phone="6125551234",
            status=LeadStatus.CONTACTED.value,
            contacted_at=datetime.now(tz=timezone.utc),
        )
        mock_lead_repo.get_by_id = AsyncMock(return_value=new_lead)
        mock_lead_repo.update = AsyncMock(return_value=contacted_lead)

        update_data = LeadUpdate(status=LeadStatus.CONTACTED)
        update_result = await lead_service.update_lead(lead_id, update_data)
        assert update_result.status == LeadStatus.CONTACTED

        # --- Step 4: Update status to qualified ---
        qualified_lead = _make_lead_model(
            id=lead_id,
            name="Viktor Grin",
            phone="6125551234",
            status=LeadStatus.QUALIFIED.value,
        )
        mock_lead_repo.get_by_id = AsyncMock(return_value=contacted_lead)
        mock_lead_repo.update = AsyncMock(return_value=qualified_lead)

        update_data2 = LeadUpdate(status=LeadStatus.QUALIFIED)
        update_result2 = await lead_service.update_lead(lead_id, update_data2)
        assert update_result2.status == LeadStatus.QUALIFIED

        # --- Step 5: Convert to customer ---
        mock_lead_repo.get_by_id = AsyncMock(return_value=qualified_lead)
        converted_lead = _make_lead_model(
            id=lead_id,
            status=LeadStatus.CONVERTED.value,
            customer_id=customer_id,
        )
        mock_lead_repo.update = AsyncMock(return_value=converted_lead)

        conversion = LeadConversionRequest(create_job=True)
        convert_result = await lead_service.convert_lead(lead_id, conversion)

        assert convert_result.success is True
        assert convert_result.customer_id == customer_id
        assert convert_result.job_id == job_id
        mock_customer_service.create_customer.assert_called_once()
        mock_job_service.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_convert_without_job(
        self,
        lead_service: LeadService,
        mock_lead_repo: AsyncMock,
        mock_customer_service: AsyncMock,  # noqa: ARG002
        mock_job_service: AsyncMock,
    ) -> None:
        """Test conversion without creating a job."""
        lead_id = uuid.uuid4()
        lead = _make_lead_model(
            id=lead_id,
            name="Simple Lead",
            status=LeadStatus.QUALIFIED.value,
        )
        mock_lead_repo.get_by_id = AsyncMock(return_value=lead)
        mock_lead_repo.update = AsyncMock(
            return_value=_make_lead_model(
                id=lead_id,
                status=LeadStatus.CONVERTED.value,
            ),
        )

        conversion = LeadConversionRequest(create_job=False)
        result = await lead_service.convert_lead(lead_id, conversion)

        assert result.success is True
        assert result.job_id is None
        mock_job_service.create_job.assert_not_called()


@pytest.mark.integration
class TestDuplicateDetection:
    """Test 8.3: Duplicate detection integration.

    Validates: Requirement 3, 14.3
    """

    @pytest.mark.asyncio
    async def test_duplicate_phone_updates_existing_lead(
        self,
        lead_service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Submit same phone twice — second should update, not create."""
        lead_id = uuid.uuid4()
        existing_lead = _make_lead_model(
            id=lead_id,
            name="First Submission",
            phone="6125559999",
            email=None,
            notes=None,
            situation=LeadSituation.REPAIR.value,
        )

        # First submission: no existing lead
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        mock_lead_repo.create = AsyncMock(return_value=existing_lead)

        sub1 = LeadSubmission(
            name="First Submission",
            phone="(612) 555-9999",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            source_site="residential",
        )
        result1 = await lead_service.submit_lead(sub1)
        assert result1.success is True
        mock_lead_repo.create.assert_called_once()

        # Second submission: existing lead found
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(
            return_value=existing_lead,
        )
        mock_lead_repo.create.reset_mock()
        mock_lead_repo.update = AsyncMock(return_value=existing_lead)

        sub2 = LeadSubmission(
            name="First Submission",
            phone="(612) 555-9999",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            email="new@email.com",
            notes="Additional info",
            source_site="residential",
        )
        result2 = await lead_service.submit_lead(sub2)
        assert result2.success is True
        assert result2.lead_id == lead_id

        # Should have updated, not created
        mock_lead_repo.create.assert_not_called()
        mock_lead_repo.update.assert_called_once()

        # Verify update merged fields correctly
        update_call_args = mock_lead_repo.update.call_args
        update_data = update_call_args[0][1]
        assert update_data["email"] == "new@email.com"
        assert update_data["notes"] == "Additional info"
        assert update_data["situation"] == LeadSituation.NEW_SYSTEM.value

    @pytest.mark.asyncio
    async def test_new_lead_after_converted_creates_new(
        self,
        lead_service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """After converting a lead, same phone should create a new lead."""
        # No active lead found (previous was converted → terminal status)
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        new_lead = _make_lead_model(phone="6125559999")
        mock_lead_repo.create = AsyncMock(return_value=new_lead)

        submission = LeadSubmission(
            name="Returning Customer",
            phone="(612) 555-9999",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            source_site="residential",
        )
        result = await lead_service.submit_lead(submission)

        assert result.success is True
        mock_lead_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_preserves_existing_email(
        self,
        lead_service: LeadService,
        mock_lead_repo: AsyncMock,
    ) -> None:
        """Duplicate submission should not overwrite existing email."""
        existing = _make_lead_model(
            phone="6125558888",
            email="original@email.com",
        )
        mock_lead_repo.get_by_phone_and_active_status = AsyncMock(
            return_value=existing,
        )
        mock_lead_repo.update = AsyncMock(return_value=existing)

        submission = LeadSubmission(
            name="Test",
            phone="(612) 555-8888",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            email="new@email.com",
            source_site="residential",
        )
        await lead_service.submit_lead(submission)

        # Email should NOT be in update_data since existing already has one
        update_call_args = mock_lead_repo.update.call_args
        update_data = update_call_args[0][1]
        assert "email" not in update_data
