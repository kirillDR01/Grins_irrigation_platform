"""Unit tests for payment warning enhancement — service agreement skip logic.

Tests that the job completion endpoint correctly skips the payment warning
for jobs covered by an active service agreement, and still shows the warning
for expired/cancelled agreements and non-agreement jobs.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import get_db_session, get_job_service
from grins_platform.app import create_app
from grins_platform.models.enums import AppointmentStatus, JobStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(
    *,
    job_status: str = JobStatus.IN_PROGRESS.value,
    payment_collected_on_site: bool = False,
    service_agreement_id: object | None = None,
) -> Mock:
    """Create a mock Job with all fields needed by JobResponse."""
    job = Mock()
    job.id = uuid4()
    job.customer_id = uuid4()
    job.property_id = uuid4()
    job.service_offering_id = None
    job.service_agreement_id = service_agreement_id
    job.job_type = "spring_startup"
    job.category = "ready_to_schedule"
    job.status = job_status
    job.description = "Test"
    job.estimated_duration_minutes = 60
    job.priority_level = 0
    job.weather_sensitive = False
    job.staffing_required = 1
    job.equipment_required = None
    job.materials_required = None
    job.quoted_amount = Decimal("100.00")
    job.final_amount = Decimal("100.00")
    job.payment_collected_on_site = payment_collected_on_site
    job.source = None
    job.source_details = None
    job.target_start_date = None
    job.target_end_date = None
    job.requested_at = datetime.now(tz=timezone.utc)
    job.approved_at = None
    job.scheduled_at = None
    job.on_my_way_at = None
    job.started_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
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
    job.service_agreement_name = None
    job.service_agreement_active = None
    job.service_agreement = None
    job.is_deleted = False
    job.created_at = datetime.now(tz=timezone.utc)
    job.updated_at = datetime.now(tz=timezone.utc)
    return job


def _make_appointment(
    *,
    appt_status: str = AppointmentStatus.IN_PROGRESS.value,
    job_id: object | None = None,
) -> Mock:
    """Create a mock Appointment."""
    appt = Mock()
    appt.id = uuid4()
    appt.job_id = job_id or uuid4()
    appt.status = appt_status
    appt.en_route_at = None
    appt.arrived_at = None
    appt.completed_at = None
    appt.created_at = datetime.now(tz=timezone.utc)
    return appt


def _make_service_agreement(
    *,
    agreement_id: object | None = None,
    agreement_status: str = "active",
    end_date: date | None = None,
    cancelled_at: datetime | None = None,
) -> Mock:
    """Create a mock ServiceAgreement."""
    agreement = Mock()
    agreement.id = agreement_id or uuid4()
    agreement.status = agreement_status
    agreement.end_date = end_date
    agreement.cancelled_at = cancelled_at
    agreement.agreement_number = "SA-001"
    tier = Mock()
    tier.name = "Professional"
    agreement.tier = tier
    return agreement


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.get = AsyncMock(return_value=None)
    return session


@pytest.fixture()
def mock_job_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def app(mock_session: AsyncMock, mock_job_service: AsyncMock) -> object:
    application = create_app()
    application.dependency_overrides[get_db_session] = lambda: mock_session
    application.dependency_overrides[get_job_service] = lambda: mock_job_service
    return application


@pytest.fixture()
def client(app: object) -> TestClient:
    return TestClient(app)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: Service Agreement Payment Warning Skip (Req 7.1, 7.2, 7.6)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestServiceAgreementPaymentWarning:
    """Test payment warning skip logic for service agreement jobs.

    Validates: Requirements 7.1, 7.2, 7.6
    """

    def test_active_service_agreement_skips_warning(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Job with active service agreement completes without warning (force=false).

        Validates: Requirement 7.1
        """
        agreement_id = uuid4()
        job = _make_job(
            service_agreement_id=agreement_id,
            payment_collected_on_site=False,
        )
        agreement = _make_service_agreement(
            agreement_id=agreement_id,
            agreement_status="active",
            end_date=date.today() + timedelta(days=365),
        )
        appt = _make_appointment(job_id=job.id)

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        # session.execute returns job query, then appointment query
        mock_session.execute = AsyncMock(
            side_effect=[job_result, appt_result],
        )
        # session.get returns the agreement for the service_agreement_id lookup
        mock_session.get = AsyncMock(return_value=agreement)
        mock_job_service.update_status.return_value = job

        response = client.post(f"/api/v1/jobs/{job.id}/complete")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["completed"] is True
        assert data["warning"] is None

    def test_expired_service_agreement_shows_warning(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Job with expired service agreement still shows payment warning.

        Validates: Requirement 7.2
        """
        agreement_id = uuid4()
        job = _make_job(
            service_agreement_id=agreement_id,
            payment_collected_on_site=False,
        )
        agreement = _make_service_agreement(
            agreement_id=agreement_id,
            agreement_status="active",
            end_date=date.today() - timedelta(days=30),  # Expired
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        # Invoice count query returns 0
        inv_result = Mock()
        inv_result.scalar.return_value = 0

        # session.execute: job query, then invoice count query
        mock_session.execute = AsyncMock(
            side_effect=[job_result, inv_result],
        )
        # session.get returns the expired agreement
        mock_session.get = AsyncMock(return_value=agreement)

        response = client.post(f"/api/v1/jobs/{job.id}/complete")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["completed"] is False
        assert data["warning"] == "No Payment or Invoice on File"

    def test_no_agreement_no_payment_no_invoice_shows_warning(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """Job with no service agreement, no payment, no invoice shows warning.

        Validates: Requirement 7.6
        """
        job = _make_job(
            service_agreement_id=None,
            payment_collected_on_site=False,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        inv_result = Mock()
        inv_result.scalar.return_value = 0

        mock_session.execute = AsyncMock(
            side_effect=[job_result, inv_result],
        )

        response = client.post(f"/api/v1/jobs/{job.id}/complete")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["completed"] is False
        assert data["warning"] == "No Payment or Invoice on File"

    def test_no_agreement_invoice_exists_no_warning(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Job with no service agreement but invoice exists completes without warning.

        Validates: Requirement 7.6
        """
        job = _make_job(
            service_agreement_id=None,
            payment_collected_on_site=False,
        )
        appt = _make_appointment(job_id=job.id)

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        inv_result = Mock()
        inv_result.scalar.return_value = 1  # One invoice exists
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, inv_result, appt_result],
        )
        mock_job_service.update_status.return_value = job

        response = client.post(f"/api/v1/jobs/{job.id}/complete")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["completed"] is True
        assert data["warning"] is None

    def test_no_agreement_payment_collected_no_warning(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Job with no service agreement but payment collected completes without warning.

        Validates: Requirement 7.6
        """
        job = _make_job(
            service_agreement_id=None,
            payment_collected_on_site=True,
        )
        appt = _make_appointment(job_id=job.id)

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, appt_result],
        )
        mock_job_service.update_status.return_value = job

        response = client.post(f"/api/v1/jobs/{job.id}/complete")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["completed"] is True
        assert data["warning"] is None
