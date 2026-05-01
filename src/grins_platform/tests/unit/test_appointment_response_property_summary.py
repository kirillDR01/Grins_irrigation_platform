"""Unit tests for ``_enrich_appointment_response`` property_summary fan-out.

Verifies that the new ``property_summary`` field on ``AppointmentResponse``
is populated from the joined ``Job.job_property`` relationship, and falls
back to ``None`` when no job/property is loaded. Powers the tech-mobile
schedule cards (street, city, state, zip, zone count, system type).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from grins_platform.api.v1.appointments import _enrich_appointment_response
from grins_platform.models.enums import AppointmentStatus


def _make_appointment(*, job: MagicMock | None = None) -> MagicMock:
    """Build a mock Appointment with the minimum fields AppointmentResponse needs."""
    apt = MagicMock()
    apt.id = uuid4()
    apt.job_id = uuid4()
    apt.staff_id = uuid4()
    apt.scheduled_date = date(2026, 5, 1)
    apt.time_window_start = time(9, 0)
    apt.time_window_end = time(10, 30)
    apt.status = AppointmentStatus.SCHEDULED.value
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


def _make_job(*, job_property: MagicMock | None = None) -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.job_type = "Spring opening"
    job.priority_level = 0
    job.service_agreement_id = None
    job.customer = None
    job.job_property = job_property
    return job


def _make_property(
    *,
    address: str = "12345 Eden Way",
    city: str = "Eden Prairie",
    state: str = "MN",
    zip_code: str | None = "55344",
    zone_count: int | None = 8,
    system_type: str | None = "city_water",
) -> MagicMock:
    prop = MagicMock()
    prop.address = address
    prop.city = city
    prop.state = state
    prop.zip_code = zip_code
    prop.zone_count = zone_count
    prop.system_type = system_type
    return prop


@pytest.mark.unit
class TestEnrichAppointmentResponsePropertySummary:
    """Property: _enrich_appointment_response surfaces Job.job_property."""

    def test_property_summary_populated_when_job_property_loaded(self) -> None:
        appointment = _make_appointment(job=_make_job(job_property=_make_property()))

        response = _enrich_appointment_response(appointment)

        assert response.property_summary is not None
        assert response.property_summary.address == "12345 Eden Way"
        assert response.property_summary.city == "Eden Prairie"
        assert response.property_summary.state == "MN"
        assert response.property_summary.zip_code == "55344"
        assert response.property_summary.zone_count == 8
        assert response.property_summary.system_type == "city_water"

    def test_property_summary_none_when_job_property_missing(self) -> None:
        appointment = _make_appointment(job=_make_job(job_property=None))

        response = _enrich_appointment_response(appointment)

        assert response.property_summary is None

    def test_property_summary_none_when_job_not_loaded(self) -> None:
        appointment = _make_appointment(job=None)

        response = _enrich_appointment_response(appointment)

        assert response.property_summary is None

    def test_property_summary_optional_fields_pass_through_as_none(self) -> None:
        appointment = _make_appointment(
            job=_make_job(
                job_property=_make_property(
                    zip_code=None, zone_count=None, system_type=None
                )
            )
        )

        response = _enrich_appointment_response(appointment)

        assert response.property_summary is not None
        assert response.property_summary.zip_code is None
        assert response.property_summary.zone_count is None
        assert response.property_summary.system_type is None
