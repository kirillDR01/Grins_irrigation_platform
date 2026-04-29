"""Unit tests for on-site status progression (On My Way → Started → Complete).

Tests the full lifecycle of job and appointment status transitions through
the on-site operation endpoints, including skip scenarios and edge cases.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import get_db_session, get_job_service
from grins_platform.app import create_app
from grins_platform.models.enums import AppointmentStatus, JobStatus, MessageType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(
    *,
    job_status: str = JobStatus.TO_BE_SCHEDULED.value,
    on_my_way_at: datetime | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
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
    job.on_my_way_at = on_my_way_at
    job.started_at = started_at
    job.completed_at = completed_at
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
    job.is_deleted = False
    job.created_at = datetime.now(tz=timezone.utc)
    job.updated_at = datetime.now(tz=timezone.utc)
    return job


def _make_appointment(
    *,
    appt_status: str = AppointmentStatus.CONFIRMED.value,
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


def _make_customer(*, phone: str | None = "+16125551234") -> Mock:
    c = Mock()
    c.id = uuid4()
    c.first_name = "Jane"
    c.last_name = "Doe"
    c.phone = phone
    c.email = "jane@example.com"
    c.sms_opt_in = True
    c.email_opt_in = True
    c.sms_consent_type = "transactional"
    c.internal_notes = None
    return c


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
    svc = AsyncMock()
    return svc


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
# Happy Path: On My Way → Started → Complete (Req 3.1, 3.3, 3.4)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestFullHappyPath:
    """Test the full on-site status progression: On My Way → Started → Complete.

    Validates: Requirements 3.1, 3.3, 3.4, 3.6, 3.8
    """

    def test_on_my_way_transitions_appointment_to_en_route(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """On My Way transitions CONFIRMED appointment to EN_ROUTE.

        Validates: Requirement 3.1
        """
        job = _make_job()
        customer = _make_customer()
        appt = _make_appointment(
            appt_status=AppointmentStatus.CONFIRMED.value,
            job_id=job.id,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, cust_result, appt_result],
        )

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            response = client.post(f"/api/v1/jobs/{job.id}/on-my-way")

        assert response.status_code == status.HTTP_200_OK
        assert job.on_my_way_at is not None
        assert appt.status == AppointmentStatus.EN_ROUTE.value

    def test_started_transitions_job_and_appointment_to_in_progress(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Job Started transitions job to IN_PROGRESS and appointment to IN_PROGRESS.

        Validates: Requirement 3.3
        """
        job = _make_job(job_status=JobStatus.TO_BE_SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.EN_ROUTE.value,
            job_id=job.id,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, appt_result],
        )
        mock_job_service.update_status.return_value = job

        response = client.post(f"/api/v1/jobs/{job.id}/started")

        assert response.status_code == status.HTTP_200_OK
        assert job.started_at is not None
        mock_job_service.update_status.assert_called_once()
        assert appt.status == AppointmentStatus.IN_PROGRESS.value

    def test_complete_transitions_job_and_appointment_to_completed(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Job Complete transitions both job and appointment to COMPLETED.

        Validates: Requirements 3.4, 3.8
        """
        job = _make_job(
            job_status=JobStatus.IN_PROGRESS.value,
            payment_collected_on_site=True,
        )
        appt = _make_appointment(
            appt_status=AppointmentStatus.IN_PROGRESS.value,
            job_id=job.id,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        # Invoice count query returns 0
        inv_result = Mock()
        inv_result.scalar.return_value = 0
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
        mock_job_service.update_status.assert_called_once()
        assert appt.status == AppointmentStatus.COMPLETED.value


# ---------------------------------------------------------------------------
# Skip Scenarios (Req 3.7)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestSkipScenarios:
    """Test skip scenarios where steps in the progression are skipped.

    Validates: Requirements 3.3, 3.4, 3.7
    """

    def test_complete_without_started_skips_to_completed(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Complete without Started — appointment goes directly to COMPLETED.

        Validates: Requirement 3.7
        """
        job = _make_job(
            job_status=JobStatus.TO_BE_SCHEDULED.value,
            payment_collected_on_site=True,
        )
        appt = _make_appointment(
            appt_status=AppointmentStatus.EN_ROUTE.value,
            job_id=job.id,
        )

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
        assert appt.status == AppointmentStatus.COMPLETED.value

    def test_complete_without_on_my_way_skips_to_completed(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Complete without On My Way — appointment goes from CONFIRMED to COMPLETED.

        Validates: Requirement 3.7
        """
        job = _make_job(
            job_status=JobStatus.TO_BE_SCHEDULED.value,
            payment_collected_on_site=True,
        )
        appt = _make_appointment(
            appt_status=AppointmentStatus.CONFIRMED.value,
            job_id=job.id,
        )

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
        assert appt.status == AppointmentStatus.COMPLETED.value

    def test_started_without_on_my_way_transitions_confirmed_to_in_progress(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Started without On My Way — appointment goes from CONFIRMED to IN_PROGRESS.

        Validates: Requirement 3.3
        """
        job = _make_job(job_status=JobStatus.TO_BE_SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.CONFIRMED.value,
            job_id=job.id,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, appt_result],
        )
        mock_job_service.update_status.return_value = job

        response = client.post(f"/api/v1/jobs/{job.id}/started")

        assert response.status_code == status.HTTP_200_OK
        assert appt.status == AppointmentStatus.IN_PROGRESS.value


# ---------------------------------------------------------------------------
# On My Way from SCHEDULED (unconfirmed) appointment (Req 3.2, 3.5)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestOnMyWayFromScheduled:
    """Test On My Way on SCHEDULED (unconfirmed) and CONFIRMED appointments.

    Validates: Requirements 3.2, 3.5
    """

    def test_on_my_way_on_scheduled_appointment_transitions_to_en_route(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """On My Way on SCHEDULED (unconfirmed) appointment → EN_ROUTE.

        Validates: Requirements 3.2, 3.5
        """
        job = _make_job()
        customer = _make_customer()
        appt = _make_appointment(
            appt_status=AppointmentStatus.SCHEDULED.value,
            job_id=job.id,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, cust_result, appt_result],
        )

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            response = client.post(f"/api/v1/jobs/{job.id}/on-my-way")

        assert response.status_code == status.HTTP_200_OK
        assert appt.status == AppointmentStatus.EN_ROUTE.value

    def test_on_my_way_on_confirmed_appointment_transitions_to_en_route(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """On My Way on CONFIRMED appointment → EN_ROUTE.

        Validates: Requirements 3.1, 3.5
        """
        job = _make_job()
        customer = _make_customer()
        appt = _make_appointment(
            appt_status=AppointmentStatus.CONFIRMED.value,
            job_id=job.id,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, cust_result, appt_result],
        )

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            response = client.post(f"/api/v1/jobs/{job.id}/on-my-way")

        assert response.status_code == status.HTTP_200_OK
        assert appt.status == AppointmentStatus.EN_ROUTE.value


# ---------------------------------------------------------------------------
# Existing Behavior Preserved (Req 3.6, 3.8)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestExistingBehaviorPreserved:
    """Test that existing behavior is preserved alongside new status transitions.

    Validates: Requirements 3.6, 3.8
    """

    def test_on_my_way_still_logs_timestamp(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """On My Way still logs on_my_way_at timestamp.

        Validates: Requirement 3.6
        """
        job = _make_job()
        customer = _make_customer()
        appt = _make_appointment(job_id=job.id)

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, cust_result, appt_result],
        )

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            response = client.post(f"/api/v1/jobs/{job.id}/on-my-way")

        assert response.status_code == status.HTTP_200_OK
        assert job.on_my_way_at is not None

    def test_on_my_way_still_sends_sms(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """On My Way still sends SMS to customer.

        Validates: Requirement 3.6
        """
        job = _make_job()
        customer = _make_customer()
        appt = _make_appointment(job_id=job.id)

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, cust_result, appt_result],
        )

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            return_value={"success": True},
        ) as mock_sms:
            response = client.post(f"/api/v1/jobs/{job.id}/on-my-way")

        assert response.status_code == status.HTTP_200_OK
        mock_sms.assert_called_once()
        call_kwargs = mock_sms.call_args
        assert call_kwargs.kwargs["message_type"] == MessageType.ON_MY_WAY

    def test_complete_payment_warning_still_works(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Complete without payment or invoice still returns warning.

        Validates: Requirement 3.8
        """
        job = _make_job(
            job_status=JobStatus.IN_PROGRESS.value,
            payment_collected_on_site=False,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        # Invoice count query returns 0
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

    def test_started_still_logs_timestamp(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Job Started still logs started_at timestamp.

        Validates: Requirement 3.6
        """
        job = _make_job(job_status=JobStatus.TO_BE_SCHEDULED.value)
        appt = _make_appointment(
            appt_status=AppointmentStatus.EN_ROUTE.value,
            job_id=job.id,
        )

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = appt

        mock_session.execute = AsyncMock(
            side_effect=[job_result, appt_result],
        )
        mock_job_service.update_status.return_value = job

        response = client.post(f"/api/v1/jobs/{job.id}/started")

        assert response.status_code == status.HTTP_200_OK
        assert job.started_at is not None

    def test_on_my_way_no_active_appointment_still_succeeds(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """On My Way with no active appointment still logs timestamp and sends SMS.

        Validates: Requirement 3.6
        """
        job = _make_job()
        customer = _make_customer()

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(
            side_effect=[job_result, cust_result, appt_result],
        )

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            response = client.post(f"/api/v1/jobs/{job.id}/on-my-way")

        assert response.status_code == status.HTTP_200_OK
        assert job.on_my_way_at is not None
