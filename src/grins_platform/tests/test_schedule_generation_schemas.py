"""Tests for schedule generation schemas with coordinate fields."""

from datetime import date, time
from uuid import uuid4

import pytest

from grins_platform.schemas.schedule_generation import (
    ScheduleGenerateResponse,
    ScheduleJobAssignment,
    ScheduleStaffAssignment,
)


@pytest.mark.unit
class TestScheduleJobAssignment:
    """Tests for ScheduleJobAssignment schema."""

    def test_coordinate_fields_exist(self) -> None:
        """Test that latitude and longitude fields exist in schema."""
        fields = ScheduleJobAssignment.model_fields
        assert "latitude" in fields
        assert "longitude" in fields

    def test_coordinate_fields_optional(self) -> None:
        """Test that coordinate fields are optional (can be None)."""
        job = ScheduleJobAssignment(
            job_id=uuid4(),
            customer_name="Test Customer",
            service_type="Spring Startup",
            start_time=time(9, 0),
            end_time=time(10, 0),
            duration_minutes=60,
            travel_time_minutes=15,
            sequence_index=1,
        )
        assert job.latitude is None
        assert job.longitude is None

    def test_coordinate_fields_with_values(self) -> None:
        """Test that coordinate fields accept float values."""
        job = ScheduleJobAssignment(
            job_id=uuid4(),
            customer_name="Test Customer",
            service_type="Spring Startup",
            start_time=time(9, 0),
            end_time=time(10, 0),
            duration_minutes=60,
            travel_time_minutes=15,
            sequence_index=1,
            latitude=44.8547,
            longitude=-93.4708,
        )
        assert job.latitude == 44.8547
        assert job.longitude == -93.4708

    def test_all_fields_populated(self) -> None:
        """Test schema with all fields populated."""
        job = ScheduleJobAssignment(
            job_id=uuid4(),
            customer_name="John Doe",
            address="123 Main St",
            city="Eden Prairie",
            latitude=44.8547,
            longitude=-93.4708,
            service_type="Winterization",
            start_time=time(10, 0),
            end_time=time(11, 0),
            duration_minutes=60,
            travel_time_minutes=20,
            sequence_index=2,
        )
        assert job.customer_name == "John Doe"
        assert job.address == "123 Main St"
        assert job.city == "Eden Prairie"
        assert job.latitude == 44.8547
        assert job.longitude == -93.4708


@pytest.mark.unit
class TestScheduleStaffAssignment:
    """Tests for ScheduleStaffAssignment schema."""

    def test_start_location_fields_exist(self) -> None:
        """Test that start_lat and start_lng fields exist in schema."""
        fields = ScheduleStaffAssignment.model_fields
        assert "start_lat" in fields
        assert "start_lng" in fields

    def test_start_location_fields_optional(self) -> None:
        """Test that start location fields are optional (can be None)."""
        assignment = ScheduleStaffAssignment(
            staff_id=uuid4(),
            staff_name="Viktor",
        )
        assert assignment.start_lat is None
        assert assignment.start_lng is None

    def test_start_location_fields_with_values(self) -> None:
        """Test that start location fields accept float values."""
        assignment = ScheduleStaffAssignment(
            staff_id=uuid4(),
            staff_name="Viktor",
            start_lat=44.9778,
            start_lng=-93.2650,
        )
        assert assignment.start_lat == 44.9778
        assert assignment.start_lng == -93.2650

    def test_staff_assignment_with_jobs(self) -> None:
        """Test staff assignment with job list including coordinates."""
        job = ScheduleJobAssignment(
            job_id=uuid4(),
            customer_name="Test Customer",
            latitude=44.8547,
            longitude=-93.4708,
            service_type="Spring Startup",
            start_time=time(9, 0),
            end_time=time(10, 0),
            duration_minutes=60,
            travel_time_minutes=15,
            sequence_index=1,
        )
        assignment = ScheduleStaffAssignment(
            staff_id=uuid4(),
            staff_name="Vas",
            start_lat=44.9778,
            start_lng=-93.2650,
            jobs=[job],
            total_jobs=1,
            total_travel_minutes=15,
            first_job_start=time(9, 0),
            last_job_end=time(10, 0),
        )
        assert len(assignment.jobs) == 1
        assert assignment.jobs[0].latitude == 44.8547
        assert assignment.start_lat == 44.9778


@pytest.mark.unit
class TestScheduleGenerateResponse:
    """Tests for ScheduleGenerateResponse schema."""

    def test_response_with_coordinates(self) -> None:
        """Test full response includes coordinate data."""
        job = ScheduleJobAssignment(
            job_id=uuid4(),
            customer_name="Test Customer",
            latitude=44.8547,
            longitude=-93.4708,
            service_type="Spring Startup",
            start_time=time(9, 0),
            end_time=time(10, 0),
            duration_minutes=60,
            travel_time_minutes=15,
            sequence_index=1,
        )
        staff = ScheduleStaffAssignment(
            staff_id=uuid4(),
            staff_name="Viktor",
            start_lat=44.9778,
            start_lng=-93.2650,
            jobs=[job],
            total_jobs=1,
            total_travel_minutes=15,
            first_job_start=time(9, 0),
            last_job_end=time(10, 0),
        )
        response = ScheduleGenerateResponse(
            schedule_date=date(2026, 1, 24),
            is_feasible=True,
            hard_score=0,
            soft_score=-100,
            assignments=[staff],
            total_jobs=1,
            total_assigned=1,
            total_travel_minutes=15,
            optimization_time_seconds=1.5,
        )
        assert response.assignments[0].start_lat == 44.9778
        assert response.assignments[0].jobs[0].latitude == 44.8547
