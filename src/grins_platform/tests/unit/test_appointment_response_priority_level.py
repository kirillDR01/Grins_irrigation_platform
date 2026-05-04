"""Unit tests for ``_enrich_appointment_response`` priority_level fan-out.

Verifies that the new ``priority_level`` field on ``AppointmentResponse``
is populated from the joined ``Job`` model, and falls back to ``None``
when no job is loaded. Surfaced to the FE for the resource-timeline
view's priority-star icon.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from grins_platform.api.v1.appointments import _enrich_appointment_response
from grins_platform.models.enums import AppointmentStatus


def _make_appointment(
    *,
    job: MagicMock | None = None,
) -> MagicMock:
    """Build a mock Appointment with the minimum fields AppointmentResponse needs."""
    apt = MagicMock()
    apt.id = uuid4()
    apt.job_id = uuid4()
    apt.staff_id = uuid4()
    apt.scheduled_date = date(2026, 4, 30)
    apt.time_window_start = time(9, 0)
    apt.time_window_end = time(10, 30)
    apt.status = AppointmentStatus.CONFIRMED.value
    apt.arrived_at = None
    apt.completed_at = None
    apt.en_route_at = None
    apt.materials_needed = None
    apt.estimated_duration_minutes = None
    apt.notes = None
    apt.route_order = None
    apt.estimated_arrival = None
    apt.created_at = datetime.now(tz=timezone.utc)
    apt.updated_at = datetime.now(tz=timezone.utc)
    # Extended display fields default to None on the model side; the
    # enrichment helper post-fills them from relationships. Pydantic's
    # ``from_attributes=True`` would otherwise pick up MagicMock auto-attrs.
    apt.job_type = None
    apt.customer_name = None
    apt.customer_internal_notes = None
    apt.staff_name = None
    apt.service_agreement_id = None
    apt.priority_level = None
    apt.reply_state = None
    apt.property_summary = None
    apt.job = job
    apt.staff = None
    return apt


def _make_job(*, priority_level: int = 0) -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.job_type = "Spring opening"
    job.priority_level = priority_level
    job.service_agreement_id = None
    job.customer = None
    job.job_property = None
    return job


@pytest.mark.unit
class TestEnrichAppointmentResponsePriorityLevel:
    """Property: _enrich_appointment_response surfaces Job.priority_level."""

    def test_priority_level_populated_from_joined_job(self) -> None:
        """priority_level=3 on the joined Job round-trips to the response."""
        appointment = _make_appointment(job=_make_job(priority_level=3))

        response = _enrich_appointment_response(appointment)

        assert response.priority_level == 3

    def test_priority_level_zero_passes_through(self) -> None:
        """priority_level=0 (the default value) is not coerced to None."""
        appointment = _make_appointment(job=_make_job(priority_level=0))

        response = _enrich_appointment_response(appointment)

        assert response.priority_level == 0

    def test_priority_level_high_passes_through(self) -> None:
        """priority_level=5 (highest) round-trips."""
        appointment = _make_appointment(job=_make_job(priority_level=5))

        response = _enrich_appointment_response(appointment)

        assert response.priority_level == 5

    def test_priority_level_none_when_job_not_loaded(self) -> None:
        """Without a loaded Job relationship, priority_level defaults to None."""
        appointment = _make_appointment(job=None)

        response = _enrich_appointment_response(appointment)

        assert response.priority_level is None
