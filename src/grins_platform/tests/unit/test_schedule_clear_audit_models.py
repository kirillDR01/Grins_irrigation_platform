"""
Unit tests for ScheduleClearAudit model.

Tests model instantiation and JSON serialization of appointments_data.
Validates: Requirements 5.1-5.6
"""

import json
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from grins_platform.models.schedule_clear_audit import ScheduleClearAudit


@pytest.mark.unit
class TestScheduleClearAuditModel:
    """Test ScheduleClearAudit model instantiation.

    Validates: Requirements 5.1-5.6
    """

    def test_model_instantiation_with_required_fields(self) -> None:
        """Test model can be instantiated with required fields.

        Validates: Requirement 5.1 (schedule_clear_audit table)
        """
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=[],
            appointment_count=0,
        )
        assert audit.schedule_date == date(2025, 1, 15)
        assert audit.appointments_data == []
        assert audit.jobs_reset == []
        assert audit.appointment_count == 0

    def test_model_with_appointments_data(self) -> None:
        """Test model with appointments_data populated.

        Validates: Requirement 5.2 (appointments_data JSONB)
        """
        appointment_data = [
            {
                "id": str(uuid4()),
                "job_id": str(uuid4()),
                "staff_id": str(uuid4()),
                "scheduled_date": "2025-01-15",
                "time_window_start": "09:00",
                "time_window_end": "11:00",
                "status": "scheduled",
            },
            {
                "id": str(uuid4()),
                "job_id": str(uuid4()),
                "staff_id": str(uuid4()),
                "scheduled_date": "2025-01-15",
                "time_window_start": "11:00",
                "time_window_end": "13:00",
                "status": "scheduled",
            },
        ]
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=appointment_data,
            jobs_reset=[],
            appointment_count=2,
        )
        assert len(audit.appointments_data) == 2
        assert audit.appointments_data[0]["time_window_start"] == "09:00"
        assert audit.appointments_data[1]["time_window_start"] == "11:00"

    def test_model_with_jobs_reset(self) -> None:
        """Test model with jobs_reset array populated.

        Validates: Requirement 5.3 (jobs_reset UUID[])
        """
        job_ids = [uuid4(), uuid4(), uuid4()]
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=job_ids,
            appointment_count=0,
        )
        assert len(audit.jobs_reset) == 3
        assert audit.jobs_reset == job_ids

    def test_model_with_cleared_by(self) -> None:
        """Test model with cleared_by staff reference.

        Validates: Requirement 5.4 (cleared_by references staff)
        """
        staff_id = uuid4()
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=[],
            appointment_count=0,
            cleared_by=staff_id,
        )
        assert audit.cleared_by == staff_id

    def test_model_cleared_by_nullable(self) -> None:
        """Test model cleared_by can be None.

        Validates: Requirement 5.4 (nullable)
        """
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=[],
            appointment_count=0,
            cleared_by=None,
        )
        assert audit.cleared_by is None

    def test_model_with_notes(self) -> None:
        """Test model with notes field.

        Validates: Requirement 5.5 (notes TEXT)
        """
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=[],
            appointment_count=0,
            notes="Cleared due to weather cancellation",
        )
        assert audit.notes == "Cleared due to weather cancellation"

    def test_model_notes_nullable(self) -> None:
        """Test model notes can be None."""
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=[],
            appointment_count=0,
            notes=None,
        )
        assert audit.notes is None

    def test_model_with_cleared_at(self) -> None:
        """Test model with cleared_at timestamp.

        Validates: Requirement 5.6 (cleared_at timestamp)
        """
        cleared_time = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=[],
            appointment_count=0,
            cleared_at=cleared_time,
        )
        assert audit.cleared_at == cleared_time

    def test_model_repr(self) -> None:
        """Test model string representation."""
        audit_id = uuid4()
        audit = ScheduleClearAudit(
            id=audit_id,
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=[],
            appointment_count=5,
        )
        repr_str = repr(audit)
        assert "ScheduleClearAudit" in repr_str
        assert str(audit_id) in repr_str
        assert "2025-01-15" in repr_str
        assert "5" in repr_str


@pytest.mark.unit
class TestScheduleClearAuditJsonSerialization:
    """Test JSON serialization of appointments_data.

    Validates: Requirements 5.1-5.6
    """

    def test_appointments_data_json_serializable(self) -> None:
        """Test appointments_data can be serialized to JSON."""
        appointment_data = [
            {
                "id": str(uuid4()),
                "job_id": str(uuid4()),
                "customer_name": "John Doe",
                "address": "123 Main St",
                "job_type": "spring_startup",
                "scheduled_date": "2025-01-15",
                "time_window_start": "09:00",
                "time_window_end": "11:00",
            },
        ]
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=appointment_data,
            jobs_reset=[],
            appointment_count=1,
        )
        # Should be JSON serializable
        json_str = json.dumps(audit.appointments_data)
        assert json_str is not None
        # Should be deserializable back
        deserialized = json.loads(json_str)
        assert deserialized == appointment_data

    def test_appointments_data_with_nested_objects(self) -> None:
        """Test appointments_data with nested objects."""
        appointment_data = [
            {
                "id": str(uuid4()),
                "job": {
                    "id": str(uuid4()),
                    "type": "spring_startup",
                    "customer": {
                        "name": "John Doe",
                        "phone": "6125551234",
                    },
                },
                "staff": {
                    "id": str(uuid4()),
                    "name": "Tech One",
                },
                "time_window": {
                    "start": "09:00",
                    "end": "11:00",
                },
            },
        ]
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=appointment_data,
            jobs_reset=[],
            appointment_count=1,
        )
        # Verify nested structure preserved
        assert audit.appointments_data[0]["job"]["customer"]["name"] == "John Doe"
        assert audit.appointments_data[0]["staff"]["name"] == "Tech One"
        # Should be JSON serializable
        json_str = json.dumps(audit.appointments_data)
        deserialized = json.loads(json_str)
        assert deserialized[0]["job"]["customer"]["name"] == "John Doe"

    def test_appointments_data_with_arrays(self) -> None:
        """Test appointments_data with array fields."""
        appointment_data = [
            {
                "id": str(uuid4()),
                "job_id": str(uuid4()),
                "materials": ["sprinkler_head", "pvc_pipe", "valve"],
                "notes": ["Customer has dog", "Gate code: 1234"],
            },
        ]
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=appointment_data,
            jobs_reset=[],
            appointment_count=1,
        )
        assert len(audit.appointments_data[0]["materials"]) == 3
        assert "sprinkler_head" in audit.appointments_data[0]["materials"]
        # Should be JSON serializable
        json_str = json.dumps(audit.appointments_data)
        deserialized = json.loads(json_str)
        assert deserialized[0]["materials"] == ["sprinkler_head", "pvc_pipe", "valve"]

    def test_appointments_data_empty_list(self) -> None:
        """Test appointments_data with empty list."""
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=[],
            jobs_reset=[],
            appointment_count=0,
        )
        json_str = json.dumps(audit.appointments_data)
        assert json_str == "[]"

    def test_appointments_data_with_special_characters(self) -> None:
        """Test appointments_data with special characters in strings."""
        appointment_data = [
            {
                "id": str(uuid4()),
                "notes": "Customer's address: 123 \"Main\" St & Oak Ave",
                "description": "Fix leak\nReplace valve\tCheck pressure",
            },
        ]
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=appointment_data,
            jobs_reset=[],
            appointment_count=1,
        )
        # Should handle special characters
        json_str = json.dumps(audit.appointments_data)
        deserialized = json.loads(json_str)
        assert "Customer's address" in deserialized[0]["notes"]
        assert '"Main"' in deserialized[0]["notes"]
        assert "\n" in deserialized[0]["description"]

    def test_appointments_data_with_numeric_values(self) -> None:
        """Test appointments_data with numeric values."""
        appointment_data = [
            {
                "id": str(uuid4()),
                "zone_count": 8,
                "quoted_amount": 150.50,
                "duration_minutes": 45,
                "is_priority": True,
            },
        ]
        audit = ScheduleClearAudit(
            id=uuid4(),
            schedule_date=date(2025, 1, 15),
            appointments_data=appointment_data,
            jobs_reset=[],
            appointment_count=1,
        )
        assert audit.appointments_data[0]["zone_count"] == 8
        assert audit.appointments_data[0]["quoted_amount"] == 150.50
        assert audit.appointments_data[0]["is_priority"] is True
        # Should be JSON serializable
        json_str = json.dumps(audit.appointments_data)
        deserialized = json.loads(json_str)
        assert deserialized[0]["zone_count"] == 8
        assert deserialized[0]["quoted_amount"] == 150.50
