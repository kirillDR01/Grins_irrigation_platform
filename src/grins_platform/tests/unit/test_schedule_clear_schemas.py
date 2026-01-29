"""Unit tests for schedule clear schemas.

Tests all schemas in schedule_clear.py for:
- Date validation
- Response serialization
- Required field validation
- Field constraints

Validates: Requirements 3.1-3.7, 5.1-5.6
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.schemas.schedule_clear import (
    ScheduleClearAuditDetailResponse,
    ScheduleClearAuditResponse,
    ScheduleClearRequest,
    ScheduleClearResponse,
)


@pytest.mark.unit
class TestScheduleClearRequest:
    """Test ScheduleClearRequest schema validation.

    Validates: Requirements 3.1-3.7
    """

    def test_valid_request_with_date_only(self) -> None:
        """Test valid request with only schedule_date."""
        data = ScheduleClearRequest(schedule_date=date(2025, 1, 15))
        assert data.schedule_date == date(2025, 1, 15)
        assert data.notes is None

    def test_valid_request_with_notes(self) -> None:
        """Test valid request with schedule_date and notes."""
        data = ScheduleClearRequest(
            schedule_date=date(2025, 1, 15),
            notes="Clearing due to weather cancellation",
        )
        assert data.schedule_date == date(2025, 1, 15)
        assert data.notes == "Clearing due to weather cancellation"

    def test_missing_schedule_date_rejected(self) -> None:
        """Test that missing schedule_date is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleClearRequest()  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("schedule_date",) for e in errors)

    def test_invalid_date_format_rejected(self) -> None:
        """Test that invalid date format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleClearRequest(schedule_date="not-a-date")  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("schedule_date",) for e in errors)

    def test_date_from_string_iso_format(self) -> None:
        """Test date can be parsed from ISO format string."""
        data = ScheduleClearRequest(schedule_date="2025-01-15")  # type: ignore[arg-type]
        assert data.schedule_date == date(2025, 1, 15)

    def test_notes_can_be_empty_string(self) -> None:
        """Test notes can be an empty string."""
        data = ScheduleClearRequest(schedule_date=date(2025, 1, 15), notes="")
        assert data.notes == ""

    def test_notes_with_special_characters(self) -> None:
        """Test notes can contain special characters."""
        notes = "Customer's request: \"Cancel all\" & reschedule\nNew line"
        data = ScheduleClearRequest(schedule_date=date(2025, 1, 15), notes=notes)
        assert data.notes == notes


@pytest.mark.unit
class TestScheduleClearResponse:
    """Test ScheduleClearResponse schema serialization.

    Validates: Requirements 3.1-3.7
    """

    def test_valid_response_serialization(self) -> None:
        """Test valid response with all fields."""
        audit_id = uuid4()
        cleared_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        data = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=date(2025, 1, 15),
            appointments_deleted=5,
            jobs_reset=3,
            cleared_at=cleared_at,
        )
        assert data.audit_id == audit_id
        assert data.schedule_date == date(2025, 1, 15)
        assert data.appointments_deleted == 5
        assert data.jobs_reset == 3
        assert data.cleared_at == cleared_at

    def test_response_to_dict(self) -> None:
        """Test response can be serialized to dict."""
        audit_id = uuid4()
        cleared_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        data = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=date(2025, 1, 15),
            appointments_deleted=5,
            jobs_reset=3,
            cleared_at=cleared_at,
        )
        result = data.model_dump()
        assert result["audit_id"] == audit_id
        assert result["schedule_date"] == date(2025, 1, 15)
        assert result["appointments_deleted"] == 5
        assert result["jobs_reset"] == 3

    def test_response_to_json(self) -> None:
        """Test response can be serialized to JSON."""
        audit_id = uuid4()
        cleared_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        data = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=date(2025, 1, 15),
            appointments_deleted=5,
            jobs_reset=3,
            cleared_at=cleared_at,
        )
        json_str = data.model_dump_json()
        assert str(audit_id) in json_str
        assert "2025-01-15" in json_str
        assert "5" in json_str

    def test_missing_required_fields_rejected(self) -> None:
        """Test that missing required fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleClearResponse(
                audit_id=uuid4(),
                schedule_date=date(2025, 1, 15),
                # Missing appointments_deleted, jobs_reset, cleared_at
            )  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert len(errors) >= 1

    def test_zero_appointments_deleted_valid(self) -> None:
        """Test zero appointments_deleted is valid."""
        data = ScheduleClearResponse(
            audit_id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_deleted=0,
            jobs_reset=0,
            cleared_at=datetime.now(timezone.utc),
        )
        assert data.appointments_deleted == 0
        assert data.jobs_reset == 0


@pytest.mark.unit
class TestScheduleClearAuditResponse:
    """Test ScheduleClearAuditResponse schema serialization.

    Validates: Requirements 5.1-5.6, 6.1-6.2
    """

    def test_valid_audit_response(self) -> None:
        """Test valid audit response with all fields."""
        audit_id = uuid4()
        staff_id = uuid4()
        cleared_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        data = ScheduleClearAuditResponse(
            id=audit_id,
            schedule_date=date(2025, 1, 15),
            appointment_count=5,
            cleared_at=cleared_at,
            cleared_by=staff_id,
            notes="Weather cancellation",
        )
        assert data.id == audit_id
        assert data.schedule_date == date(2025, 1, 15)
        assert data.appointment_count == 5
        assert data.cleared_at == cleared_at
        assert data.cleared_by == staff_id
        assert data.notes == "Weather cancellation"

    def test_audit_response_optional_fields(self) -> None:
        """Test audit response with optional fields as None."""
        data = ScheduleClearAuditResponse(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointment_count=3,
            cleared_at=datetime.now(timezone.utc),
            cleared_by=None,
            notes=None,
        )
        assert data.cleared_by is None
        assert data.notes is None

    def test_audit_response_from_attributes(self) -> None:
        """Test audit response can be created from ORM model attributes."""
        # Simulate ORM model with attributes
        class MockAudit:
            id = uuid4()
            schedule_date = date(2025, 1, 15)
            appointment_count = 5
            cleared_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            cleared_by = uuid4()
            notes = "Test notes"

        mock = MockAudit()
        data = ScheduleClearAuditResponse.model_validate(mock)
        assert data.id == mock.id
        assert data.schedule_date == mock.schedule_date
        assert data.appointment_count == mock.appointment_count

    def test_audit_response_to_dict(self) -> None:
        """Test audit response serialization to dict."""
        audit_id = uuid4()
        data = ScheduleClearAuditResponse(
            id=audit_id,
            schedule_date=date(2025, 1, 15),
            appointment_count=5,
            cleared_at=datetime.now(timezone.utc),
            cleared_by=None,
            notes=None,
        )
        result = data.model_dump()
        assert result["id"] == audit_id
        assert result["schedule_date"] == date(2025, 1, 15)
        assert result["appointment_count"] == 5


@pytest.mark.unit
class TestScheduleClearAuditDetailResponse:
    """Test ScheduleClearAuditDetailResponse schema serialization.

    Validates: Requirements 6.3
    """

    def test_valid_detail_response(self) -> None:
        """Test valid detail response with all fields."""
        audit_id = uuid4()
        job_ids = [uuid4(), uuid4(), uuid4()]
        appointments_data = [
            {
                "id": str(uuid4()),
                "job_id": str(job_ids[0]),
                "customer_name": "John Doe",
                "time_window_start": "09:00",
            },
            {
                "id": str(uuid4()),
                "job_id": str(job_ids[1]),
                "customer_name": "Jane Smith",
                "time_window_start": "11:00",
            },
        ]
        data = ScheduleClearAuditDetailResponse(
            id=audit_id,
            schedule_date=date(2025, 1, 15),
            appointment_count=2,
            cleared_at=datetime.now(timezone.utc),
            cleared_by=None,
            notes=None,
            appointments_data=appointments_data,
            jobs_reset=job_ids,
        )
        assert data.id == audit_id
        assert len(data.appointments_data) == 2
        assert len(data.jobs_reset) == 3
        assert data.appointments_data[0]["customer_name"] == "John Doe"

    def test_detail_response_inherits_base_fields(self) -> None:
        """Test detail response inherits all base fields."""
        staff_id = uuid4()
        data = ScheduleClearAuditDetailResponse(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointment_count=1,
            cleared_at=datetime.now(timezone.utc),
            cleared_by=staff_id,
            notes="Inherited notes",
            appointments_data=[],
            jobs_reset=[],
        )
        # Inherited fields from ScheduleClearAuditResponse
        assert data.cleared_by == staff_id
        assert data.notes == "Inherited notes"

    def test_detail_response_empty_lists(self) -> None:
        """Test detail response with empty appointments and jobs."""
        data = ScheduleClearAuditDetailResponse(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointment_count=0,
            cleared_at=datetime.now(timezone.utc),
            cleared_by=None,
            notes=None,
            appointments_data=[],
            jobs_reset=[],
        )
        assert data.appointments_data == []
        assert data.jobs_reset == []

    def test_detail_response_to_json(self) -> None:
        """Test detail response can be serialized to JSON."""
        job_id = uuid4()
        data = ScheduleClearAuditDetailResponse(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointment_count=1,
            cleared_at=datetime.now(timezone.utc),
            cleared_by=None,
            notes=None,
            appointments_data=[{"job_id": str(job_id), "name": "Test"}],
            jobs_reset=[job_id],
        )
        json_str = data.model_dump_json()
        assert str(job_id) in json_str
        assert "Test" in json_str

    def test_detail_response_appointments_data_nested(self) -> None:
        """Test detail response with nested appointment data."""
        appointments_data = [
            {
                "id": str(uuid4()),
                "job": {
                    "type": "spring_startup",
                    "customer": {"name": "John Doe", "phone": "6125551234"},
                },
                "staff": {"name": "Tech One"},
            },
        ]
        data = ScheduleClearAuditDetailResponse(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointment_count=1,
            cleared_at=datetime.now(timezone.utc),
            cleared_by=None,
            notes=None,
            appointments_data=appointments_data,
            jobs_reset=[],
        )
        assert data.appointments_data[0]["job"]["customer"]["name"] == "John Doe"

    def test_detail_response_from_orm_model(self) -> None:
        """Test detail response can be created from ORM model."""
        mock_id = uuid4()
        mock_job_id = uuid4()
        mock_appointments = [{"id": "test"}]
        mock_jobs = [mock_job_id]

        class MockDetailAudit:
            id = mock_id
            schedule_date = date(2025, 1, 15)
            appointment_count = 2
            cleared_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            cleared_by = None
            notes = None
            appointments_data = mock_appointments
            jobs_reset = mock_jobs

        mock = MockDetailAudit()
        data = ScheduleClearAuditDetailResponse.model_validate(mock)
        assert data.id == mock_id
        assert data.appointments_data == mock_appointments
        assert data.jobs_reset == mock_jobs
