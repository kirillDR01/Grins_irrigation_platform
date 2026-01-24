"""
Unit tests for Staff Availability Pydantic schemas.

Tests validation logic for staff availability creation, updates, and responses.

Validates: Requirements 1.1, 1.6, 1.7 (Route Optimization)
"""

from datetime import date, datetime, time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.schemas.staff_availability import (
    AvailableStaffOnDateResponse,
    StaffAvailabilityCreate,
    StaffAvailabilityListParams,
    StaffAvailabilityResponse,
    StaffAvailabilityUpdate,
    StaffWithAvailability,
)


class TestStaffAvailabilityCreate:
    """Tests for StaffAvailabilityCreate schema."""

    def test_create_with_minimal_fields(self) -> None:
        """Test creating availability with only required fields."""
        data = StaffAvailabilityCreate(date=date(2025, 1, 23))

        assert data.date == date(2025, 1, 23)
        assert data.start_time == time(7, 0)
        assert data.end_time == time(17, 0)
        assert data.is_available is True
        assert data.lunch_start == time(12, 0)
        assert data.lunch_duration_minutes == 30
        assert data.notes is None

    def test_create_with_all_fields(self) -> None:
        """Test creating availability with all fields specified."""
        data = StaffAvailabilityCreate(
            date=date(2025, 1, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
            is_available=True,
            lunch_start=time(12, 30),
            lunch_duration_minutes=45,
            notes="Working from home",
        )

        assert data.date == date(2025, 1, 23)
        assert data.start_time == time(8, 0)
        assert data.end_time == time(16, 0)
        assert data.is_available is True
        assert data.lunch_start == time(12, 30)
        assert data.lunch_duration_minutes == 45
        assert data.notes == "Working from home"

    def test_create_unavailable(self) -> None:
        """Test creating unavailable entry."""
        data = StaffAvailabilityCreate(
            date=date(2025, 1, 23),
            is_available=False,
        )

        assert data.is_available is False

    def test_create_no_lunch(self) -> None:
        """Test creating availability without lunch break."""
        data = StaffAvailabilityCreate(
            date=date(2025, 1, 23),
            lunch_start=None,
            lunch_duration_minutes=0,
        )

        assert data.lunch_start is None
        assert data.lunch_duration_minutes == 0


class TestStaffAvailabilityCreateValidation:
    """Tests for StaffAvailabilityCreate validation.

    Validates: Requirements 1.6, 1.7
    """

    def test_start_time_must_be_before_end_time(self) -> None:
        """Test that start_time must be before end_time.

        Requirement 1.6: Start time must be before end time.
        """
        with pytest.raises(ValidationError) as exc_info:
            StaffAvailabilityCreate(
                date=date(2025, 1, 23),
                start_time=time(17, 0),
                end_time=time(8, 0),
            )

        assert "start_time must be before end_time" in str(exc_info.value)

    def test_start_time_equal_to_end_time_rejected(self) -> None:
        """Test that start_time equal to end_time is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            StaffAvailabilityCreate(
                date=date(2025, 1, 23),
                start_time=time(12, 0),
                end_time=time(12, 0),
            )

        assert "start_time must be before end_time" in str(exc_info.value)

    def test_lunch_start_must_be_within_window(self) -> None:
        """Test that lunch_start must be within availability window.

        Requirement 1.7: Lunch time must be within availability window.
        """
        # Lunch before start_time
        with pytest.raises(ValidationError) as exc_info:
            StaffAvailabilityCreate(
                date=date(2025, 1, 23),
                start_time=time(9, 0),
                end_time=time(17, 0),
                lunch_start=time(8, 0),
            )

        assert "lunch_start must be at or after start_time" in str(exc_info.value)

    def test_lunch_start_at_or_after_end_time_rejected(self) -> None:
        """Test that lunch_start at or after end_time is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            StaffAvailabilityCreate(
                date=date(2025, 1, 23),
                start_time=time(9, 0),
                end_time=time(17, 0),
                lunch_start=time(17, 0),
            )

        assert "lunch_start must be before end_time" in str(exc_info.value)

    def test_lunch_break_must_end_before_end_time(self) -> None:
        """Test that lunch break must end before end_time."""
        with pytest.raises(ValidationError) as exc_info:
            StaffAvailabilityCreate(
                date=date(2025, 1, 23),
                start_time=time(9, 0),
                end_time=time(17, 0),
                lunch_start=time(16, 30),
                lunch_duration_minutes=60,  # Would end at 17:30
            )

        assert "lunch break must end before end_time" in str(exc_info.value)

    def test_lunch_duration_bounds(self) -> None:
        """Test lunch duration must be between 0 and 120 minutes."""
        # Valid: 0 minutes
        data = StaffAvailabilityCreate(
            date=date(2025, 1, 23),
            lunch_duration_minutes=0,
        )
        assert data.lunch_duration_minutes == 0

        # Valid: 120 minutes
        data = StaffAvailabilityCreate(
            date=date(2025, 1, 23),
            lunch_duration_minutes=120,
        )
        assert data.lunch_duration_minutes == 120

        # Invalid: negative
        with pytest.raises(ValidationError):
            StaffAvailabilityCreate(
                date=date(2025, 1, 23),
                lunch_duration_minutes=-1,
            )

        # Invalid: > 120
        with pytest.raises(ValidationError):
            StaffAvailabilityCreate(
                date=date(2025, 1, 23),
                lunch_duration_minutes=121,
            )


class TestStaffAvailabilityUpdate:
    """Tests for StaffAvailabilityUpdate schema."""

    def test_update_with_no_fields(self) -> None:
        """Test update with no fields specified."""
        data = StaffAvailabilityUpdate()

        assert data.start_time is None
        assert data.end_time is None
        assert data.is_available is None
        assert data.lunch_start is None
        assert data.lunch_duration_minutes is None
        assert data.notes is None

    def test_update_with_some_fields(self) -> None:
        """Test update with some fields specified."""
        data = StaffAvailabilityUpdate(
            start_time=time(8, 0),
            is_available=False,
        )

        assert data.start_time == time(8, 0)
        assert data.is_available is False
        assert data.end_time is None

    def test_update_time_range_validation(self) -> None:
        """Test that time range is validated when both times provided."""
        with pytest.raises(ValidationError) as exc_info:
            StaffAvailabilityUpdate(
                start_time=time(17, 0),
                end_time=time(8, 0),
            )

        assert "start_time must be before end_time" in str(exc_info.value)

    def test_update_single_time_no_validation(self) -> None:
        """Test that single time field doesn't trigger validation."""
        # Only start_time - should be valid
        data = StaffAvailabilityUpdate(start_time=time(17, 0))
        assert data.start_time == time(17, 0)

        # Only end_time - should be valid
        data = StaffAvailabilityUpdate(end_time=time(8, 0))
        assert data.end_time == time(8, 0)


class TestStaffAvailabilityResponse:
    """Tests for StaffAvailabilityResponse schema."""

    def test_response_from_dict(self) -> None:
        """Test creating response from dictionary."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "staff_id": uuid4(),
            "date": date(2025, 1, 23),
            "start_time": time(7, 0),
            "end_time": time(17, 0),
            "is_available": True,
            "lunch_start": time(12, 0),
            "lunch_duration_minutes": 30,
            "notes": "Test note",
            "available_minutes": 570,
            "created_at": now,
            "updated_at": now,
        }

        response = StaffAvailabilityResponse(**data)

        assert response.date == date(2025, 1, 23)
        assert response.start_time == time(7, 0)
        assert response.end_time == time(17, 0)
        assert response.is_available is True
        assert response.available_minutes == 570


class TestStaffAvailabilityListParams:
    """Tests for StaffAvailabilityListParams schema."""

    def test_list_params_defaults(self) -> None:
        """Test list params with defaults."""
        params = StaffAvailabilityListParams()

        assert params.start_date is None
        assert params.end_date is None
        assert params.is_available is None

    def test_list_params_with_date_range(self) -> None:
        """Test list params with date range."""
        params = StaffAvailabilityListParams(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        assert params.start_date == date(2025, 1, 1)
        assert params.end_date == date(2025, 1, 31)

    def test_list_params_date_range_validation(self) -> None:
        """Test that start_date must be before or equal to end_date."""
        with pytest.raises(ValidationError) as exc_info:
            StaffAvailabilityListParams(
                start_date=date(2025, 1, 31),
                end_date=date(2025, 1, 1),
            )

        assert "start_date must be before or equal to end_date" in str(exc_info.value)

    def test_list_params_same_date_valid(self) -> None:
        """Test that same start and end date is valid."""
        params = StaffAvailabilityListParams(
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
        )

        assert params.start_date == params.end_date


class TestStaffWithAvailability:
    """Tests for StaffWithAvailability schema."""

    def test_staff_with_availability(self) -> None:
        """Test creating staff with availability response."""
        now = datetime.now()
        availability_data = {
            "id": uuid4(),
            "staff_id": uuid4(),
            "date": date(2025, 1, 23),
            "start_time": time(7, 0),
            "end_time": time(17, 0),
            "is_available": True,
            "lunch_start": time(12, 0),
            "lunch_duration_minutes": 30,
            "notes": None,
            "available_minutes": 570,
            "created_at": now,
            "updated_at": now,
        }

        data = StaffWithAvailability(
            id=uuid4(),
            name="John Doe",
            availability=StaffAvailabilityResponse(**availability_data),
        )

        assert data.name == "John Doe"
        assert data.availability.is_available is True


class TestAvailableStaffOnDateResponse:
    """Tests for AvailableStaffOnDateResponse schema."""

    def test_available_staff_response(self) -> None:
        """Test creating available staff on date response."""
        now = datetime.now()
        staff_id = uuid4()
        availability_data = {
            "id": uuid4(),
            "staff_id": staff_id,
            "date": date(2025, 1, 23),
            "start_time": time(7, 0),
            "end_time": time(17, 0),
            "is_available": True,
            "lunch_start": time(12, 0),
            "lunch_duration_minutes": 30,
            "notes": None,
            "available_minutes": 570,
            "created_at": now,
            "updated_at": now,
        }

        staff_with_avail = StaffWithAvailability(
            id=staff_id,
            name="John Doe",
            availability=StaffAvailabilityResponse(**availability_data),
        )

        response = AvailableStaffOnDateResponse(
            date=date(2025, 1, 23),
            available_staff=[staff_with_avail],
            total_available=1,
        )

        assert response.date == date(2025, 1, 23)
        assert len(response.available_staff) == 1
        assert response.total_available == 1
