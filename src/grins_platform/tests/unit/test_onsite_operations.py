"""Unit tests for on-site operation endpoints and week alignment.

Validates: Requirements 20.2, 27.1, 27.3, 27.4
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.app import create_app
from grins_platform.utils.week_alignment import align_to_week

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    return session


def _make_job(
    *,
    on_my_way_at: datetime | None = None,
    started_at: datetime | None = None,
    payment_collected_on_site: bool = False,
) -> Mock:
    job = Mock()
    job.id = uuid4()
    job.customer_id = uuid4()
    job.property_id = uuid4()
    job.service_offering_id = None
    job.service_agreement_id = None
    job.job_type = "spring_startup"
    job.category = "ready_to_schedule"
    job.status = "in_progress"
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
    job.customer_address = None
    job.property_tags = None
    job.is_deleted = False
    job.created_at = datetime.now(tz=timezone.utc)
    job.updated_at = datetime.now(tz=timezone.utc)
    return job


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


@pytest.fixture()
def app(mock_session: AsyncMock) -> object:
    application = create_app()
    application.dependency_overrides[get_db_session] = lambda: mock_session
    return application


@pytest.fixture()
def client(app: object) -> TestClient:
    return TestClient(app)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# On My Way (Req 27.1)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestOnMyWay:
    """Tests for POST /api/v1/jobs/{id}/on-my-way."""

    def test_on_my_way_logs_timestamp_and_sends_sms(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job = _make_job()
        customer = _make_customer()

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        # Third call: get_active_appointment_for_job returns None
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = None
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
        assert job.on_my_way_at is not None
        mock_sms.assert_called_once()

    def test_on_my_way_not_found(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=job_result)

        response = client.post(f"/api/v1/jobs/{uuid4()}/on-my-way")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_on_my_way_no_phone_skips_sms(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job = _make_job()
        customer = _make_customer(phone=None)

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        # Third call: get_active_appointment_for_job returns None
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(
            side_effect=[job_result, cust_result, appt_result],
        )

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
        ) as mock_sms:
            response = client.post(f"/api/v1/jobs/{job.id}/on-my-way")

        assert response.status_code == status.HTTP_200_OK
        mock_sms.assert_not_called()

    def test_on_my_way_sms_failure_still_succeeds(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        # bughunt L-2: when SMS dispatch fails, the route rolls back
        # on_my_way_at to its prior value so a later retry doesn't look
        # like a duplicate "already en-route". The endpoint itself still
        # returns 200 so the FE doesn't surface a transient SMS error.
        job = _make_job()
        # Pre-existing on_my_way_at so we can verify rollback restored it.
        prev = datetime(2026, 1, 1, tzinfo=timezone.utc)
        job.on_my_way_at = prev
        customer = _make_customer()

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        # Third call: get_active_appointment_for_job returns None
        appt_result = Mock()
        appt_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(
            side_effect=[job_result, cust_result, appt_result],
        )

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            side_effect=RuntimeError("SMS provider down"),
        ):
            response = client.post(f"/api/v1/jobs/{job.id}/on-my-way")

        assert response.status_code == status.HTTP_200_OK
        assert job.on_my_way_at == prev


# ---------------------------------------------------------------------------
# Job Started (Req 27.2)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestJobStarted:
    """Tests for POST /api/v1/jobs/{id}/started."""

    def test_job_started_logs_timestamp(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job = _make_job()
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        mock_session.execute = AsyncMock(return_value=job_result)

        response = client.post(f"/api/v1/jobs/{job.id}/started")

        assert response.status_code == status.HTTP_200_OK
        assert job.started_at is not None

    def test_job_started_not_found(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=job_result)

        response = client.post(f"/api/v1/jobs/{uuid4()}/started")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Add Job Note (Req 26.3)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestAddJobNote:
    """Tests for POST /api/v1/jobs/{id}/notes."""

    def test_add_note_syncs_to_customer(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job = _make_job()
        customer = _make_customer()

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        mock_session.execute = AsyncMock(side_effect=[job_result, cust_result])

        response = client.post(
            f"/api/v1/jobs/{job.id}/notes",
            json={"note": "Checked backflow preventer"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["synced_to_customer"] is True
        assert "Checked backflow preventer" in (job.notes or "")
        assert customer.internal_notes is not None

    def test_add_note_not_found(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=job_result)

        response = client.post(
            f"/api/v1/jobs/{uuid4()}/notes",
            json={"note": "test"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Review Push (Req 26.4)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestReviewPush:
    """Tests for POST /api/v1/jobs/{id}/review-push."""

    def test_review_push_sends_sms(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job = _make_job()
        customer = _make_customer()

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        mock_session.execute = AsyncMock(side_effect=[job_result, cust_result])

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            return_value={"success": True, "message_id": str(uuid4())},
        ) as mock_sms:
            response = client.post(f"/api/v1/jobs/{job.id}/review-push")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sms_sent"] is True
        mock_sms.assert_called_once()

    def test_review_push_uses_spec_exact_wording(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """bughunt M-6: spec §4/§10 wording verbatim — no first-name prefix,
        ``Grin's Irrigation`` (apostrophe canonicalization applied 2026-05-14).
        """
        job = _make_job()
        customer = _make_customer()

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        mock_session.execute = AsyncMock(side_effect=[job_result, cust_result])

        with patch(
            "grins_platform.services.sms_service.SMSService.send_message",
            new_callable=AsyncMock,
            return_value={"success": True, "message_id": str(uuid4())},
        ) as mock_sms:
            client.post(f"/api/v1/jobs/{job.id}/review-push")

        body = mock_sms.call_args.kwargs["message"]
        assert body.startswith("Thanks for choosing Grin's Irrigation!")
        assert "We'd appreciate a quick review:" in body
        # Negative assertions to lock the regression
        assert "Grin's Irrigations" not in body
        assert "Hi " not in body

    def test_review_push_no_phone(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job = _make_job()
        customer = _make_customer(phone=None)

        job_result = Mock()
        job_result.scalar_one_or_none.return_value = job
        cust_result = Mock()
        cust_result.scalar_one_or_none.return_value = customer
        mock_session.execute = AsyncMock(side_effect=[job_result, cust_result])

        response = client.post(f"/api/v1/jobs/{job.id}/review-push")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_review_push_not_found(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        job_result = Mock()
        job_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=job_result)

        response = client.post(f"/api/v1/jobs/{uuid4()}/review-push")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Week Alignment Unit Tests (Req 20.2)
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestAlignToWeek:
    """Deterministic unit tests for align_to_week utility."""

    def test_monday_input_returns_same_monday(self) -> None:
        d = date(2026, 4, 13)  # Monday
        monday, sunday = align_to_week(d)
        assert monday == d
        assert sunday == date(2026, 4, 19)

    def test_sunday_input_returns_previous_monday(self) -> None:
        d = date(2026, 4, 19)  # Sunday
        monday, sunday = align_to_week(d)
        assert monday == date(2026, 4, 13)
        assert sunday == d

    def test_midweek_input(self) -> None:
        d = date(2026, 4, 15)  # Wednesday
        monday, sunday = align_to_week(d)
        assert monday == date(2026, 4, 13)
        assert sunday == date(2026, 4, 19)

    def test_range_is_seven_days(self) -> None:
        monday, sunday = align_to_week(date(2026, 1, 1))
        assert (sunday - monday).days == 6

    def test_start_lte_end(self) -> None:
        monday, sunday = align_to_week(date(2026, 6, 15))
        assert monday <= sunday

    def test_year_boundary(self) -> None:
        # 2025-12-31 is a Wednesday
        monday, sunday = align_to_week(date(2025, 12, 31))
        assert monday == date(2025, 12, 29)
        assert sunday == date(2026, 1, 4)
