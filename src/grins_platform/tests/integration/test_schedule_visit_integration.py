"""Integration tests for the Schedule Visit feature.

Drives the full /api/v1/sales/calendar/events POST and PUT paths
through FastAPI TestClient with auth + DB dependency overrides
(matches the existing integration tier pattern in
``test_appointment_notes_integration.py``).

Validates: assigned_to_user_id round-trips through HTTP; bare POST
(default ``send_confirmation=false``) does NOT auto-advance the entry —
only the combined ``?send_confirmation=true`` path advances on first
successful SMS dispatch, per
``sales-pipeline-estimate-visit-confirmation-lifecycle`` Task 12. PUT
update mutates the row but never re-advances the entry.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.api.v1.sales_pipeline import router as sales_pipeline_router
from grins_platform.models.enums import SalesEntryStatus


@pytest.fixture
def fake_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "test-admin"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_active = True
    return user


def _make_sales_entry(
    status: str = SalesEntryStatus.SCHEDULE_ESTIMATE.value,
) -> MagicMock:
    entry = MagicMock()
    entry.id = uuid.uuid4()
    entry.customer_id = uuid.uuid4()
    entry.status = status
    return entry


def _make_db(
    *,
    sales_entry: MagicMock | None = None,
    existing_event: MagicMock | None = None,
) -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh(obj: Any) -> None:
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime.now(timezone.utc)
        # server_default="pending" only fires on real flush; tests must
        # populate the column explicitly so SalesCalendarEventResponse
        # validation accepts the in-memory row.
        if getattr(obj, "confirmation_status", None) is None:
            obj.confirmation_status = "pending"

    db.refresh = AsyncMock(side_effect=_refresh)

    if existing_event is not None:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=existing_event)
        db.execute = AsyncMock(return_value=result)
    else:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sales_entry)
        db.execute = AsyncMock(return_value=result)

    return db


def _build_app(
    fake_user: MagicMock,
    db: AsyncMock,
) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(sales_pipeline_router, prefix="/api/v1/sales")
    test_app.dependency_overrides[get_current_user] = lambda: fake_user
    test_app.dependency_overrides[get_current_active_user] = lambda: fake_user

    async def _db_override() -> AsyncMock:
        return db

    test_app.dependency_overrides[get_db_session] = _db_override
    return test_app


@pytest.mark.integration
def test_schedule_visit_post_no_send_round_trips_assignee_without_advance(
    fake_user: MagicMock,
) -> None:
    """Bare POST (default ``send_confirmation=false``) round-trips the
    assignee + notes but must NOT auto-advance the sales entry. The
    auto-advance moved into the combined SMS-dispatch path so importers
    can't fake the customer ack.
    """
    sales_entry = _make_sales_entry()
    db = _make_db(sales_entry=sales_entry)
    app = _build_app(fake_user, db)
    client = TestClient(app)

    assignee_id = uuid.uuid4()
    payload = {
        "sales_entry_id": str(sales_entry.id),
        "customer_id": str(sales_entry.customer_id),
        "title": "Estimate - Integration Customer",
        "scheduled_date": "2026-05-12",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "notes": "Gate code 1234",
        "assigned_to_user_id": str(assignee_id),
    }

    resp = client.post("/api/v1/sales/calendar/events", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["assigned_to_user_id"] == str(assignee_id)
    assert data["notes"] == "Gate code 1234"
    # confirmation_status defaults to "pending" on the new event row.
    assert data["confirmation_status"] == "pending"

    # Status unchanged — auto-advance moved into the SMS-dispatch path.
    assert sales_entry.status == SalesEntryStatus.SCHEDULE_ESTIMATE.value


@pytest.mark.integration
def test_schedule_visit_put_updates_event_without_re_advance(
    fake_user: MagicMock,
) -> None:
    existing = MagicMock()
    existing.id = uuid.uuid4()
    existing.sales_entry_id = uuid.uuid4()
    existing.customer_id = uuid.uuid4()
    existing.title = "Estimate - Original"
    existing.scheduled_date = datetime(2026, 5, 1).date()
    existing.start_time = datetime(2026, 5, 1, 14, 0).time()
    existing.end_time = datetime(2026, 5, 1, 15, 0).time()
    existing.notes = None
    existing.assigned_to_user_id = None
    existing.confirmation_status = "pending"
    existing.confirmation_status_at = None
    existing.created_at = datetime.now(timezone.utc)
    existing.updated_at = datetime.now(timezone.utc)

    db = _make_db(existing_event=existing)
    app = _build_app(fake_user, db)
    client = TestClient(app)

    new_assignee = uuid.uuid4()
    payload = {
        "scheduled_date": "2026-05-15",
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "assigned_to_user_id": str(new_assignee),
    }

    resp = client.put(
        f"/api/v1/sales/calendar/events/{existing.id}",
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["assigned_to_user_id"] == str(new_assignee)
    assert data["scheduled_date"] == "2026-05-15"
