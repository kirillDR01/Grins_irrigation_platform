"""Unit tests for schedule explanation schemas.

Tests all schemas in schedule_explanation.py for:
- Valid data acceptance
- Invalid data rejection
- Field validation
- Default values
- Type coercion

Validates: Schedule AI Updates Requirements 2.1, 3.1, 4.1, 9.1
"""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.schemas.schedule_explanation import (
    JobReadyToSchedule,
    JobsReadyToScheduleResponse,
    ParseConstraintsRequest,
    ParseConstraintsResponse,
    ParsedConstraint,
    ScheduleExplanationRequest,
    ScheduleExplanationResponse,
    StaffAssignmentSummary,
    UnassignedJobExplanationRequest,
    UnassignedJobExplanationResponse,
)


@pytest.mark.unit
class TestStaffAssignmentSummary:
    """Test StaffAssignmentSummary schema."""

    def test_valid_data(self) -> None:
        """Test valid staff assignment summary."""
        data = StaffAssignmentSummary(
            staff_id=uuid4(),
            staff_name="Viktor",
            job_count=5,
            total_minutes=240,
            cities=["Eden Prairie", "Plymouth"],
            job_types=["startup", "repair"],
        )
        assert data.staff_name == "Viktor"
        assert data.job_count == 5
        assert len(data.cities) == 2

    def test_empty_lists(self) -> None:
        """Test with empty cities and job_types."""
        data = StaffAssignmentSummary(
            staff_id=uuid4(),
            staff_name="Dad",
            job_count=0,
            total_minutes=0,
            cities=[],
            job_types=[],
        )
        assert data.job_count == 0
        assert data.cities == []


@pytest.mark.unit
class TestScheduleExplanationRequest:
    """Test ScheduleExplanationRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid schedule explanation request."""
        data = ScheduleExplanationRequest(
            schedule_date=date(2025, 5, 15),
            staff_assignments=[
                StaffAssignmentSummary(
                    staff_id=uuid4(),
                    staff_name="Viktor",
                    job_count=5,
                    total_minutes=240,
                    cities=["Eden Prairie"],
                    job_types=["startup"],
                ),
            ],
            unassigned_job_count=2,
        )
        assert data.schedule_date == date(2025, 5, 15)
        assert len(data.staff_assignments) == 1
        assert data.unassigned_job_count == 2

    def test_empty_assignments(self) -> None:
        """Test with no staff assignments."""
        data = ScheduleExplanationRequest(
            schedule_date=date(2025, 5, 15),
            staff_assignments=[],
            unassigned_job_count=10,
        )
        assert data.staff_assignments == []
        assert data.unassigned_job_count == 10


@pytest.mark.unit
class TestScheduleExplanationResponse:
    """Test ScheduleExplanationResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid schedule explanation response."""
        data = ScheduleExplanationResponse(
            explanation="Schedule optimized for route efficiency",
            highlights=["Viktor handles Eden Prairie", "Dad covers Plymouth"],
        )
        assert "optimized" in data.explanation
        assert len(data.highlights) == 2

    def test_default_highlights(self) -> None:
        """Test default empty highlights list."""
        data = ScheduleExplanationResponse(
            explanation="Simple schedule",
        )
        assert data.highlights == []


@pytest.mark.unit
class TestUnassignedJobExplanationRequest:
    """Test UnassignedJobExplanationRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid unassigned job explanation request."""
        data = UnassignedJobExplanationRequest(
            job_id=uuid4(),
            job_type="startup",
            customer_name="John Doe",
            city="Eden Prairie",
            estimated_duration_minutes=60,
            priority="high",
            requires_equipment=["compressor"],
            constraint_violations=["No staff available"],
        )
        assert data.job_type == "startup"
        assert data.priority == "high"
        assert len(data.requires_equipment) == 1

    def test_default_lists(self) -> None:
        """Test default empty lists."""
        data = UnassignedJobExplanationRequest(
            job_id=uuid4(),
            job_type="repair",
            customer_name="Jane Smith",
            city="Plymouth",
            estimated_duration_minutes=30,
            priority="medium",
        )
        assert data.requires_equipment == []
        assert data.constraint_violations == []


@pytest.mark.unit
class TestUnassignedJobExplanationResponse:
    """Test UnassignedJobExplanationResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid unassigned job explanation response."""
        data = UnassignedJobExplanationResponse(
            reason="No staff available with required equipment",
            suggestions=["Schedule for next day", "Assign to Viktor"],
            alternative_dates=[date(2025, 5, 16), date(2025, 5, 17)],
        )
        assert "equipment" in data.reason
        assert len(data.suggestions) == 2
        assert len(data.alternative_dates) == 2

    def test_default_lists(self) -> None:
        """Test default empty lists."""
        data = UnassignedJobExplanationResponse(
            reason="Staff fully booked",
        )
        assert data.suggestions == []
        assert data.alternative_dates == []


@pytest.mark.unit
class TestParsedConstraint:
    """Test ParsedConstraint schema."""

    def test_staff_time_constraint(self) -> None:
        """Test staff time constraint."""
        data = ParsedConstraint(
            constraint_type="staff_time",
            description="Viktor not before 10am",
            parameters={"staff_name": "Viktor", "earliest_start": "10:00"},
        )
        assert data.constraint_type == "staff_time"
        assert data.parameters["staff_name"] == "Viktor"

    def test_job_grouping_constraint(self) -> None:
        """Test job grouping constraint."""
        data = ParsedConstraint(
            constraint_type="job_grouping",
            description="Group all Eden Prairie jobs",
            parameters={"city": "Eden Prairie", "group_by": "city"},
        )
        assert data.constraint_type == "job_grouping"

    def test_with_validation_errors(self) -> None:
        """Test constraint with validation errors."""
        data = ParsedConstraint(
            constraint_type="staff_restriction",
            description="Unknown staff member",
            parameters={"staff_name": "Unknown"},
            validation_errors=["Staff 'Unknown' not found"],
        )
        assert len(data.validation_errors) == 1

    def test_default_validation_errors(self) -> None:
        """Test default empty validation errors."""
        data = ParsedConstraint(
            constraint_type="geographic",
            description="Minimize travel",
            parameters={"strategy": "minimize_distance"},
        )
        assert data.validation_errors == []


@pytest.mark.unit
class TestParseConstraintsRequest:
    """Test ParseConstraintsRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid constraint parsing request."""
        data = ParseConstraintsRequest(
            constraint_text="Don't schedule Viktor before 10am",
        )
        assert "Viktor" in data.constraint_text

    def test_min_length_validation(self) -> None:
        """Test minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ParseConstraintsRequest(constraint_text="")
        assert "at least 1 character" in str(exc_info.value)

    def test_max_length_validation(self) -> None:
        """Test maximum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ParseConstraintsRequest(constraint_text="x" * 1001)
        assert "at most 1000 characters" in str(exc_info.value)


@pytest.mark.unit
class TestParseConstraintsResponse:
    """Test ParseConstraintsResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid constraint parsing response."""
        data = ParseConstraintsResponse(
            constraints=[
                ParsedConstraint(
                    constraint_type="staff_time",
                    description="Viktor not before 10am",
                    parameters={"staff_name": "Viktor", "earliest_start": "10:00"},
                ),
            ],
            unparseable_text=None,
        )
        assert len(data.constraints) == 1
        assert data.unparseable_text is None

    def test_with_unparseable_text(self) -> None:
        """Test response with unparseable text."""
        data = ParseConstraintsResponse(
            constraints=[],
            unparseable_text="Some gibberish that couldn't be parsed",
        )
        assert data.constraints == []
        assert data.unparseable_text is not None


@pytest.mark.unit
class TestJobReadyToSchedule:
    """Test JobReadyToSchedule schema."""

    def test_valid_job(self) -> None:
        """Test valid job ready to schedule."""
        data = JobReadyToSchedule(
            job_id=uuid4(),
            customer_id=uuid4(),
            customer_name="John Doe",
            job_type="startup",
            city="Eden Prairie",
            priority="high",
            estimated_duration_minutes=60,
            requires_equipment=["compressor"],
            status="approved",
        )
        assert data.job_type == "startup"
        assert data.priority == "high"
        assert len(data.requires_equipment) == 1

    def test_default_equipment(self) -> None:
        """Test default empty equipment list."""
        data = JobReadyToSchedule(
            job_id=uuid4(),
            customer_id=uuid4(),
            customer_name="Jane Smith",
            job_type="repair",
            city="Plymouth",
            priority="medium",
            estimated_duration_minutes=30,
            status="requested",
        )
        assert data.requires_equipment == []


@pytest.mark.unit
class TestJobsReadyToScheduleResponse:
    """Test JobsReadyToScheduleResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid jobs ready to schedule response."""
        job1 = JobReadyToSchedule(
            job_id=uuid4(),
            customer_id=uuid4(),
            customer_name="John Doe",
            job_type="startup",
            city="Eden Prairie",
            priority="high",
            estimated_duration_minutes=60,
            status="approved",
        )
        job2 = JobReadyToSchedule(
            job_id=uuid4(),
            customer_id=uuid4(),
            customer_name="Jane Smith",
            job_type="repair",
            city="Plymouth",
            priority="medium",
            estimated_duration_minutes=30,
            status="requested",
        )
        data = JobsReadyToScheduleResponse(
            jobs=[job1, job2],
            total_count=2,
            by_city={"Eden Prairie": 1, "Plymouth": 1},
            by_job_type={"startup": 1, "repair": 1},
        )
        assert len(data.jobs) == 2
        assert data.total_count == 2
        assert data.by_city["Eden Prairie"] == 1

    def test_default_dicts(self) -> None:
        """Test default empty dictionaries."""
        data = JobsReadyToScheduleResponse(
            jobs=[],
            total_count=0,
        )
        assert data.by_city == {}
        assert data.by_job_type == {}

    def test_empty_jobs(self) -> None:
        """Test response with no jobs."""
        data = JobsReadyToScheduleResponse(
            jobs=[],
            total_count=0,
            by_city={},
            by_job_type={},
        )
        assert data.jobs == []
        assert data.total_count == 0
