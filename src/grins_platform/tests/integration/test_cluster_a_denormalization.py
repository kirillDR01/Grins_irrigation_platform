"""Cluster A denormalization tests — customer_tags surfaced on Job /
Appointment / Sales responses.

These tests exercise the response builders in isolation (no DB) — the
``_populate_customer_tags`` (jobs), ``_populate_appointment_extended_fields``
(appointments), and ``_entry_to_response`` (sales) helpers are the
single-source-of-truth attachment points. Verifying them at the pure-
function level is sufficient + far cheaper than spinning a Postgres
fixture.

Validates:
- Job with two customer tags → ``customer_tags`` array, length 2.
- Appointment with two customer tags → same.
- Customer with zero tags → ``customer_tags == []`` (NOT ``None``); empty
  vs unloaded is preserved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from grins_platform.api.v1.appointments import _populate_appointment_extended_fields
from grins_platform.api.v1.jobs import _populate_customer_tags
from grins_platform.models.enums import (
    AppointmentStatus,
    JobCategory,
    JobStatus,
)
from grins_platform.schemas.appointment import AppointmentResponse
from grins_platform.schemas.job import JobResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tag(label: str) -> MagicMock:
    t = MagicMock()
    t.id = uuid4()
    t.customer_id = uuid4()
    t.label = label
    t.tone = "neutral"
    t.source = "manual"
    t.created_at = datetime.now(tz=timezone.utc)
    return t


def _customer_with_tags(tags: list | None) -> MagicMock:
    customer = MagicMock()
    customer.id = uuid4()
    customer.first_name = "Test"
    customer.last_name = "Customer"
    customer.internal_notes = "shared blob"
    customer.tags = tags
    return customer


def _job_response_skeleton(customer_id) -> JobResponse:
    now = datetime.now(tz=timezone.utc)
    return JobResponse(
        id=uuid4(),
        customer_id=customer_id,
        job_type="repair",
        category=JobCategory.READY_TO_SCHEDULE,
        status=JobStatus.TO_BE_SCHEDULED,
        priority_level=3,
        weather_sensitive=False,
        staffing_required=1,
        payment_collected_on_site=False,
        notes=None,
        summary=None,
        description=None,
        estimated_duration_minutes=None,
        quoted_amount=Decimal("0"),
        final_amount=None,
        created_at=now,
        updated_at=now,
    )


def _appointment_response_skeleton() -> AppointmentResponse:
    now = datetime.now(tz=timezone.utc)
    return AppointmentResponse(
        id=uuid4(),
        job_id=uuid4(),
        staff_id=uuid4(),
        scheduled_date=now.date(),
        time_window_start=now.time(),
        time_window_end=now.time(),
        status=AppointmentStatus.SCHEDULED,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_job_response_includes_customer_tags() -> None:
    customer = _customer_with_tags([_tag("Priority"), _tag("VIP")])
    job = MagicMock()
    job.customer = customer
    resp = _job_response_skeleton(customer.id)

    _populate_customer_tags(job, resp)

    assert resp.customer_tags is not None
    assert len(resp.customer_tags) == 2
    labels = {t.label for t in resp.customer_tags}
    assert labels == {"Priority", "VIP"}


@pytest.mark.unit
def test_empty_customer_tags_returns_empty_array_not_null() -> None:
    """A customer with `tags = []` should render as an empty list, not None.

    Distinguishes 'no tags' from 'relationship not loaded'.
    """
    customer = _customer_with_tags([])
    job = MagicMock()
    job.customer = customer
    resp = _job_response_skeleton(customer.id)

    _populate_customer_tags(job, resp)

    assert resp.customer_tags == []


@pytest.mark.unit
def test_job_response_customer_tags_remains_none_when_customer_unloaded() -> None:
    job = MagicMock()
    job.customer = None
    resp = _job_response_skeleton(uuid4())

    _populate_customer_tags(job, resp)

    # The helper short-circuits → field stays at its default (None).
    assert resp.customer_tags is None


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_appointment_response_includes_customer_tags() -> None:
    customer = _customer_with_tags([_tag("Priority"), _tag("VIP")])
    customer.first_name = "Jane"
    customer.last_name = "Doe"

    job = MagicMock()
    job.job_type = "repair"
    job.service_agreement_id = None
    job.priority_level = 3
    job.customer = customer
    job.job_property = None

    appointment = MagicMock()
    appointment.job = job
    appointment.staff = None

    resp = _appointment_response_skeleton()

    _populate_appointment_extended_fields(resp, appointment)

    assert resp.customer_tags is not None
    assert len(resp.customer_tags) == 2
    assert resp.customer_name == "Jane Doe"
    assert resp.customer_internal_notes == "shared blob"


@pytest.mark.unit
def test_appointment_customer_tags_empty_array_when_zero_tags() -> None:
    customer = _customer_with_tags([])
    customer.first_name = "Jane"
    customer.last_name = "Doe"

    job = MagicMock()
    job.job_type = "repair"
    job.service_agreement_id = None
    job.priority_level = 3
    job.customer = customer
    job.job_property = None

    appointment = MagicMock()
    appointment.job = job
    appointment.staff = None

    resp = _appointment_response_skeleton()
    _populate_appointment_extended_fields(resp, appointment)

    assert resp.customer_tags == []
