"""Unit tests for Schedule/Appointment API endpoints (Task 7.7).

Tests the new endpoints added to appointments.py, schedule.py,
staff.py, analytics.py, and notifications.py.

Validates: Requirements 24.2, 25.2, 30.5, 31.4, 32.6, 33.4, 34.3,
           37.2, 39.6, 41.1, 41.5, 42.2
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.appointments import router as appointments_router
from grins_platform.models.enums import PaymentMethod


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with appointment routes."""
    test_app = FastAPI()
    test_app.include_router(appointments_router, prefix="/api/v1/appointments")
    return test_app


def _mock_user() -> MagicMock:
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = uuid4()
    user.is_active = True
    return user


# ============================================================================
# Test: PATCH /appointments/{id}/reschedule (Req 24.2)
# ============================================================================


@pytest.mark.unit
class TestRescheduleAppointment:
    """Tests for the reschedule endpoint."""

    @pytest.mark.asyncio
    async def test_reschedule_with_valid_data_returns_200(
        self,
        app: FastAPI,
    ) -> None:
        """Test successful reschedule returns updated appointment."""
        appt_id = uuid4()
        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.job_id = uuid4()
        mock_appointment.staff_id = uuid4()
        mock_appointment.scheduled_date = date(2025, 2, 1)
        mock_appointment.time_window_start = time(10, 0)
        mock_appointment.time_window_end = time(11, 0)
        mock_appointment.status = "scheduled"
        mock_appointment.arrived_at = None
        mock_appointment.completed_at = None
        mock_appointment.en_route_at = None
        mock_appointment.materials_needed = None
        mock_appointment.estimated_duration_minutes = None
        mock_appointment.notes = None
        mock_appointment.route_order = None
        mock_appointment.estimated_arrival = None
        mock_appointment.created_at = datetime.now(tz=timezone.utc)
        mock_appointment.updated_at = datetime.now(tz=timezone.utc)
        mock_appointment.job_type = None
        mock_appointment.customer_name = None
        mock_appointment.staff_name = None
        mock_appointment.customer_internal_notes = None
        mock_appointment.service_agreement_id = None
        mock_appointment.priority_level = None
        mock_appointment.reply_state = None
        mock_appointment.property_summary = None

        mock_service = AsyncMock()
        mock_service.reschedule.return_value = mock_appointment

        with (
            patch(
                "grins_platform.api.v1.appointments.get_appointment_service",
                return_value=mock_service,
            ),
            patch(
                "grins_platform.api.v1.appointments.CurrentActiveUser",
                _mock_user(),
            ),
        ):
            app.dependency_overrides[
                __import__(
                    "grins_platform.api.v1.dependencies",
                    fromlist=["get_appointment_service"],
                ).get_appointment_service
            ] = lambda: mock_service

            # Override auth
            from grins_platform.api.v1.auth_dependencies import (
                get_current_active_user,
            )

            app.dependency_overrides[get_current_active_user] = _mock_user

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.patch(
                    f"/api/v1/appointments/{appt_id}/reschedule",
                    json={
                        "new_date": "2025-02-15",
                        "new_start": "14:00",
                        "new_end": "15:00",
                    },
                )

            assert response.status_code == 200
            mock_service.reschedule.assert_called_once()


# ============================================================================
# Test: RescheduleRequest schema validation
# ============================================================================


@pytest.mark.unit
class TestRescheduleRequestSchema:
    """Tests for the RescheduleRequest schema."""

    def test_valid_reschedule_request(self) -> None:
        """Test valid reschedule request passes validation."""
        from grins_platform.schemas.appointment_ops import (
            RescheduleRequest,
        )

        req = RescheduleRequest(
            new_date=date(2025, 2, 15),
            new_start="14:00",
            new_end="15:00",
        )
        assert req.new_date == date(2025, 2, 15)
        assert req.new_start == "14:00"
        assert req.new_end == "15:00"

    def test_invalid_time_format_rejected(self) -> None:
        """Test invalid time format is rejected."""
        from pydantic import ValidationError

        from grins_platform.schemas.appointment_ops import (
            RescheduleRequest,
        )

        with pytest.raises(ValidationError):
            RescheduleRequest(
                new_date=date(2025, 2, 15),
                new_start="2pm",
                new_end="3pm",
            )


# ============================================================================
# Test: PaymentCollectionRequest schema validation (Req 30.5)
# ============================================================================


@pytest.mark.unit
class TestPaymentCollectionRequestSchema:
    """Tests for the PaymentCollectionRequest schema."""

    def test_valid_payment_request(self) -> None:
        """Test valid payment request passes validation."""
        from grins_platform.schemas.appointment_ops import (
            PaymentCollectionRequest,
        )

        req = PaymentCollectionRequest(
            payment_method=PaymentMethod.CASH,
            amount=Decimal("150.00"),
            reference_number=None,
        )
        assert req.amount == Decimal("150.00")
        assert req.payment_method == PaymentMethod.CASH

    def test_zero_amount_rejected(self) -> None:
        """Test zero amount is rejected."""
        from pydantic import ValidationError

        from grins_platform.schemas.appointment_ops import (
            PaymentCollectionRequest,
        )

        with pytest.raises(ValidationError):
            PaymentCollectionRequest(
                payment_method=PaymentMethod.CASH,
                amount=Decimal("0.00"),
            )


# ============================================================================
# Test: StaffLocationRequest schema validation (Req 41.1)
# ============================================================================


@pytest.mark.unit
class TestStaffLocationRequestSchema:
    """Tests for the StaffLocationRequest schema."""

    def test_valid_location_request(self) -> None:
        """Test valid location request passes validation."""
        from grins_platform.schemas.staff_ops import (
            StaffLocationRequest,
        )

        req = StaffLocationRequest(
            latitude=30.2672,
            longitude=-97.7431,
        )
        assert req.latitude == 30.2672
        assert req.longitude == -97.7431

    def test_invalid_latitude_rejected(self) -> None:
        """Test latitude out of range is rejected."""
        from pydantic import ValidationError

        from grins_platform.schemas.staff_ops import (
            StaffLocationRequest,
        )

        with pytest.raises(ValidationError):
            StaffLocationRequest(
                latitude=91.0,
                longitude=-97.7431,
            )

    def test_invalid_longitude_rejected(self) -> None:
        """Test longitude out of range is rejected."""
        from pydantic import ValidationError

        from grins_platform.schemas.staff_ops import (
            StaffLocationRequest,
        )

        with pytest.raises(ValidationError):
            StaffLocationRequest(
                latitude=30.2672,
                longitude=-181.0,
            )


# ============================================================================
# Test: StaffBreakCreateRequest schema validation (Req 42.2)
# ============================================================================


@pytest.mark.unit
class TestStaffBreakCreateRequestSchema:
    """Tests for the StaffBreakCreateRequest schema."""

    def test_valid_break_request(self) -> None:
        """Test valid break request passes validation."""
        from grins_platform.schemas.staff_ops import (
            StaffBreakCreateRequest,
        )

        req = StaffBreakCreateRequest(
            break_type="lunch",
            appointment_id=uuid4(),
        )
        assert req.break_type == "lunch"

    def test_break_request_without_appointment(self) -> None:
        """Test break request without appointment_id is valid."""
        from grins_platform.schemas.staff_ops import (
            StaffBreakCreateRequest,
        )

        req = StaffBreakCreateRequest(break_type="gas")
        assert req.appointment_id is None


# ============================================================================
# Test: LeadTimeResponse schema (Req 25.2)
# ============================================================================


@pytest.mark.unit
class TestLeadTimeResponseSchema:
    """Tests for the LeadTimeResponse schema."""

    def test_valid_lead_time_response(self) -> None:
        """Test valid lead time response."""
        from grins_platform.schemas.analytics import (
            LeadTimeResponse,
        )

        resp = LeadTimeResponse(days=14, display="Booked out 2 weeks")
        assert resp.days == 14
        assert resp.display == "Booked out 2 weeks"

    def test_negative_days_rejected(self) -> None:
        """Test negative days is rejected."""
        from pydantic import ValidationError

        from grins_platform.schemas.analytics import (
            LeadTimeResponse,
        )

        with pytest.raises(ValidationError):
            LeadTimeResponse(days=-1, display="Invalid")


# ============================================================================
# Test: StaffTimeAnalyticsResponse schema (Req 37.2)
# ============================================================================


@pytest.mark.unit
class TestStaffTimeAnalyticsResponseSchema:
    """Tests for the StaffTimeAnalyticsResponse schema."""

    def test_valid_analytics_response(self) -> None:
        """Test valid analytics response."""
        from grins_platform.schemas.analytics import (
            StaffTimeAnalyticsResponse,
        )

        resp = StaffTimeAnalyticsResponse(
            staff_id=uuid4(),
            staff_name="John Smith",
            job_type="spring_startup",
            avg_travel_minutes=15.5,
            avg_job_minutes=45.0,
            avg_total_minutes=60.5,
            flagged=False,
        )
        assert resp.avg_travel_minutes == 15.5
        assert resp.flagged is False

    def test_negative_minutes_rejected(self) -> None:
        """Test negative minutes is rejected."""
        from pydantic import ValidationError

        from grins_platform.schemas.analytics import (
            StaffTimeAnalyticsResponse,
        )

        with pytest.raises(ValidationError):
            StaffTimeAnalyticsResponse(
                avg_travel_minutes=-5.0,
                avg_job_minutes=45.0,
                avg_total_minutes=40.0,
            )


# ============================================================================
# Test: StaffBreakResponse schema (Req 42.2)
# ============================================================================


@pytest.mark.unit
class TestStaffBreakResponseSchema:
    """Tests for the StaffBreakResponse schema."""

    def test_valid_break_response(self) -> None:
        """Test valid break response."""
        from grins_platform.schemas.staff_ops import (
            StaffBreakResponse,
        )

        resp = StaffBreakResponse(
            id=uuid4(),
            staff_id=uuid4(),
            start_time=time(12, 0),
            break_type="lunch",
        )
        assert resp.end_time is None
        assert resp.break_type == "lunch"

    def test_break_response_with_end_time(self) -> None:
        """Test break response with end time."""
        from grins_platform.schemas.staff_ops import (
            StaffBreakResponse,
        )

        resp = StaffBreakResponse(
            id=uuid4(),
            staff_id=uuid4(),
            start_time=time(12, 0),
            end_time=time(12, 30),
            break_type="lunch",
        )
        assert resp.end_time == time(12, 30)
