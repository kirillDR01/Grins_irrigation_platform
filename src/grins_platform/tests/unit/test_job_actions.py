"""Unit tests for job-level actions: complete and invoice.

Validates: Requirements 21.1, 21.2
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import (
    get_db_session,
    get_job_service,
)
from grins_platform.app import create_app
from grins_platform.exceptions import (
    InvalidInvoiceOperationError,
    InvalidStatusTransitionError,
)
from grins_platform.models.enums import JobCategory, JobStatus
from grins_platform.schemas.invoice import InvoiceResponse


@pytest.fixture()
def mock_job() -> Mock:
    """Create a mock job object."""
    job = Mock()
    job.id = uuid4()
    job.customer_id = uuid4()
    job.property_id = uuid4()
    job.service_offering_id = None
    job.service_agreement_id = None
    job.job_type = "spring_startup"
    job.category = JobCategory.READY_TO_SCHEDULE.value
    job.status = JobStatus.IN_PROGRESS.value
    job.description = "Test job"
    job.estimated_duration_minutes = 60
    job.priority_level = 0
    job.weather_sensitive = False
    job.staffing_required = 1
    job.equipment_required = None
    job.materials_required = None
    job.quoted_amount = Decimal("150.00")
    job.final_amount = Decimal("150.00")
    job.payment_collected_on_site = False
    job.source = None
    job.source_details = None
    job.target_start_date = None
    job.target_end_date = None
    job.requested_at = datetime.now()
    job.approved_at = None
    job.scheduled_at = None
    job.on_my_way_at = None
    job.started_at = None
    job.completed_at = None
    job.closed_at = None
    job.notes = None
    job.summary = None
    job.customer_name = "Test Customer"
    job.customer_phone = None
    job.customer = None
    job.job_property = None
    job.property_address = None
    job.property_city = None
    job.property_type = None
    job.property_is_hoa = None
    job.property_is_subscription = None
    job.time_tracking_metadata = None
    job.service_preference_notes = None
    job.service_agreement = None
    job.service_agreement_name = None
    job.service_agreement_active = None
    job.created_at = datetime.now()
    job.updated_at = datetime.now()
    return job


@pytest.fixture()
def mock_job_service() -> AsyncMock:
    """Create a mock job service."""
    return AsyncMock()


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Create a mock DB session."""
    return AsyncMock()


@pytest.fixture()
def app(
    mock_job_service: AsyncMock,
    mock_session: AsyncMock,
) -> object:
    """Create test application with mocked dependencies."""
    application = create_app()
    application.dependency_overrides[get_job_service] = lambda: mock_job_service
    application.dependency_overrides[get_db_session] = lambda: mock_session
    return application


@pytest.fixture()
def client(app: object) -> TestClient:
    """Create test client."""
    return TestClient(app)  # type: ignore[arg-type]


@pytest.mark.unit()
class TestCompleteJob:
    """Tests for POST /api/v1/jobs/{id}/complete."""

    def test_complete_job_success_with_payment(
        self,
        client: TestClient,
        mock_job: Mock,
        mock_job_service: AsyncMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful job completion when payment collected on site."""
        mock_job.status = JobStatus.COMPLETED.value
        mock_job.completed_at = datetime.now()
        mock_job.payment_collected_on_site = True
        mock_job.time_tracking_metadata = None

        # Mock session.execute for job lookup + appointment lookup
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = mock_job
        # Second call: get_active_appointment_for_job returns None
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(
            side_effect=[job_result, appt_result],
        )
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_job_service.update_status.return_value = mock_job

        response = client.post(
            f"/api/v1/jobs/{mock_job.id}/complete",
            json={"force": False},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["completed"] is True
        assert data["warning"] is None
        assert data["job"] is not None

    def test_complete_job_warning_no_payment(
        self,
        client: TestClient,
        mock_job: Mock,
        mock_session: AsyncMock,
    ) -> None:
        """Test warning when no payment or invoice exists."""
        mock_job.payment_collected_on_site = False

        # Mock session.execute: first for job lookup, second for invoice count
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = mock_job
        inv_result = Mock()
        inv_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[job_result, inv_result])

        response = client.post(
            f"/api/v1/jobs/{mock_job.id}/complete",
            json={"force": False},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["completed"] is False
        assert data["warning"] == "No Payment or Invoice on File"

    def test_complete_job_force_without_payment(
        self,
        client: TestClient,
        mock_job: Mock,
        mock_job_service: AsyncMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test force completion without payment writes audit log."""
        mock_job.payment_collected_on_site = False
        mock_job.status = JobStatus.COMPLETED.value
        mock_job.completed_at = datetime.now()
        mock_job.time_tracking_metadata = None

        # Mock session.execute: job lookup, invoice count
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = mock_job
        inv_result = Mock()
        inv_result.scalar.return_value = 0
        # Third call: get_active_appointment_for_job returns None
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(
            side_effect=[job_result, inv_result, appt_result],
        )
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_job_service.update_status.return_value = mock_job

        with patch(
            "grins_platform.services.audit_service.AuditService.log_action",
            new_callable=AsyncMock,
        ) as mock_audit:
            response = client.post(
                f"/api/v1/jobs/{mock_job.id}/complete",
                json={"force": True},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["completed"] is True
        mock_audit.assert_called_once()

    def test_complete_job_not_found(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """Test completing a non-existent job."""
        job_id = uuid4()
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = job_result

        response = client.post(
            f"/api/v1/jobs/{job_id}/complete",
            json={"force": False},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_complete_job_invalid_transition(
        self,
        client: TestClient,
        mock_job: Mock,
        mock_job_service: AsyncMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test completing a job with invalid status transition."""
        mock_job.payment_collected_on_site = True

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute.return_value = job_result

        mock_job_service.update_status.side_effect = InvalidStatusTransitionError(
            JobStatus.COMPLETED,
            JobStatus.COMPLETED,
        )

        response = client.post(
            f"/api/v1/jobs/{mock_job.id}/complete",
            json={"force": False},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit()
class TestJobStarted:
    """Tests for POST /api/v1/jobs/{id}/started — Bug #7 fix."""

    def test_job_started_transitions_to_in_progress(
        self,
        mock_job: Mock,
        mock_job_service: AsyncMock,
        mock_session: AsyncMock,
        client: TestClient,
    ) -> None:
        """Bug #7: job_started should transition status to in_progress."""
        mock_job.status = JobStatus.TO_BE_SCHEDULED.value

        # Mock the DB query to return the job
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Mock update_status to succeed
        mock_job_service.update_status = AsyncMock(return_value=mock_job)

        response = client.post(f"/api/v1/jobs/{mock_job.id}/started")

        assert response.status_code == status.HTTP_200_OK
        # Verify update_status was called with IN_PROGRESS
        mock_job_service.update_status.assert_awaited_once()
        call_args = mock_job_service.update_status.call_args
        assert call_args[0][0] == mock_job.id
        assert call_args[0][1].status == JobStatus.IN_PROGRESS

    def test_job_started_already_in_progress_skips_transition(
        self,
        mock_job: Mock,
        mock_job_service: AsyncMock,
        mock_session: AsyncMock,
        client: TestClient,
    ) -> None:
        """Bug #7 idempotent: already in_progress skips status update."""
        mock_job.status = JobStatus.IN_PROGRESS.value

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        response = client.post(f"/api/v1/jobs/{mock_job.id}/started")

        assert response.status_code == status.HTTP_200_OK
        # Should NOT call update_status since already in_progress
        mock_job_service.update_status.assert_not_awaited()


@pytest.mark.unit()
class TestCreateJobInvoice:
    """Tests for POST /api/v1/jobs/{id}/invoice."""

    def test_create_invoice_success(
        self,
        client: TestClient,
        mock_job: Mock,
    ) -> None:
        """Test successful invoice creation from job."""
        now = datetime.now()
        invoice_resp = InvoiceResponse(
            id=uuid4(),
            job_id=mock_job.id,
            customer_id=mock_job.customer_id,
            invoice_number="INV-001",
            amount=Decimal("150.00"),
            late_fee_amount=Decimal(0),
            total_amount=Decimal("150.00"),
            invoice_date=date.today(),
            due_date=date.today(),
            status="draft",  # type: ignore[arg-type]
            reminder_count=0,
            lien_eligible=False,
            created_at=now,
            updated_at=now,
        )

        with patch(
            "grins_platform.services.invoice_service.InvoiceService.generate_from_job",
            new_callable=AsyncMock,
            return_value=invoice_resp,
        ):
            response = client.post(
                f"/api/v1/jobs/{mock_job.id}/invoice",
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["invoice_number"] == "INV-001"

    def test_create_invoice_job_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test invoice creation for non-existent job."""
        job_id = uuid4()

        with patch(
            "grins_platform.services.invoice_service.InvoiceService.generate_from_job",
            new_callable=AsyncMock,
            side_effect=InvalidInvoiceOperationError(
                "Job not found",
            ),
        ):
            response = client.post(
                f"/api/v1/jobs/{job_id}/invoice",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_invoice_payment_collected(
        self,
        client: TestClient,
        mock_job: Mock,
    ) -> None:
        """Test invoice creation when payment already collected."""
        with patch(
            "grins_platform.services.invoice_service.InvoiceService.generate_from_job",
            new_callable=AsyncMock,
            side_effect=InvalidInvoiceOperationError(
                "Cannot generate invoice - payment was collected on site",
            ),
        ):
            response = client.post(
                f"/api/v1/jobs/{mock_job.id}/invoice",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
