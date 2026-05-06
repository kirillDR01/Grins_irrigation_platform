"""Unit tests for the Schedule Visit calendar event handlers.

Validates: assigned_to_user_id round-trips through the create/update
handlers, and the create_calendar_event handler emits the new field
in its log_completed event.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.api.v1.sales_pipeline import (
    create_calendar_event,
    update_calendar_event,
)
from grins_platform.models.enums import SalesEntryStatus
from grins_platform.schemas.sales_pipeline import (
    SalesCalendarEventCreate,
    SalesCalendarEventUpdate,
)


def _make_session_with_entry(entry_status: str | None) -> AsyncMock:
    """Build an AsyncSession mock that returns a SalesEntry on execute()."""
    session = AsyncMock()
    session.add = MagicMock()

    if entry_status is None:
        scalar_value: Any = None
    else:
        sales_entry = MagicMock()
        sales_entry.id = uuid4()
        sales_entry.status = entry_status
        scalar_value = sales_entry

    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_value)
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    async def _refresh(obj: Any) -> None:
        # Mimic the DB assigning created_at/updated_at on refresh.
        if not hasattr(obj, "created_at") or obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)
        if not hasattr(obj, "updated_at") or obj.updated_at is None:
            obj.updated_at = datetime.now(timezone.utc)
        if not getattr(obj, "id", None):
            obj.id = uuid4()
        # Polymorphic FK confirmation lifecycle (migration
        # 20260509_120000): a real DB applies the server_default; the
        # mock fakes that here so the response schema validates.
        if not getattr(obj, "confirmation_status", None):
            obj.confirmation_status = "pending"

    session.refresh = AsyncMock(side_effect=_refresh)
    return session


def _make_session_for_update(existing_event: MagicMock) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=existing_event)
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    async def _refresh(_obj: Any) -> None:
        return None

    session.refresh = AsyncMock(side_effect=_refresh)
    return session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_calendar_event_with_assignee_returns_201() -> None:
    entry_id = uuid4()
    customer_id = uuid4()
    assignee_id = uuid4()
    body = SalesCalendarEventCreate(
        sales_entry_id=entry_id,
        customer_id=customer_id,
        title="Estimate - Viktor Petrov",
        scheduled_date=date(2026, 5, 1),
        start_time=time(14, 0),
        end_time=time(15, 0),
        notes="Gate code 4412",
        assigned_to_user_id=assignee_id,
    )
    session = _make_session_with_entry(SalesEntryStatus.SCHEDULE_ESTIMATE.value)
    user = MagicMock()

    response = await create_calendar_event(
        body=body,
        user=user,
        session=session,
        pipeline_service=MagicMock(),
    )

    # The SalesCalendarEvent passed to session.add carries the new field.
    assert session.add.call_count == 1
    added_event = session.add.call_args.args[0]
    assert added_event.assigned_to_user_id == assignee_id
    assert added_event.notes == "Gate code 4412"

    # Response surfaces the assigned_to_user_id.
    assert response.assigned_to_user_id == assignee_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_calendar_event_without_assignee_defaults_none() -> None:
    body = SalesCalendarEventCreate(
        sales_entry_id=uuid4(),
        customer_id=uuid4(),
        title="Estimate - No Assignee",
        scheduled_date=date(2026, 5, 1),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    session = _make_session_with_entry(SalesEntryStatus.SCHEDULE_ESTIMATE.value)
    user = MagicMock()

    response = await create_calendar_event(
        body=body,
        user=user,
        session=session,
        pipeline_service=MagicMock(),
    )

    added_event = session.add.call_args.args[0]
    assert added_event.assigned_to_user_id is None
    assert response.assigned_to_user_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_calendar_event_changes_assignee() -> None:
    event_id = uuid4()
    new_assignee = uuid4()

    existing_event = MagicMock()
    existing_event.id = event_id
    existing_event.sales_entry_id = uuid4()
    existing_event.customer_id = uuid4()
    existing_event.title = "Estimate - Original"
    existing_event.scheduled_date = date(2026, 5, 1)
    existing_event.start_time = time(14, 0)
    existing_event.end_time = time(15, 0)
    existing_event.notes = None
    existing_event.assigned_to_user_id = None
    # Polymorphic FK confirmation lifecycle (migration 20260509_120000):
    # the response schema now requires these to be string-shaped.
    existing_event.confirmation_status = "pending"
    existing_event.confirmation_status_at = None
    existing_event.created_at = datetime.now(timezone.utc)
    existing_event.updated_at = datetime.now(timezone.utc)

    session = _make_session_for_update(existing_event)
    user = MagicMock()

    body = SalesCalendarEventUpdate(assigned_to_user_id=new_assignee)
    response = await update_calendar_event(
        event_id=event_id,
        body=body,
        _user=user,
        session=session,
    )

    # The setattr loop should have applied the new assignee.
    assert existing_event.assigned_to_user_id == new_assignee
    assert response.assigned_to_user_id == new_assignee


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_calendar_event_logs_assignee_in_completed_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assignee_id = uuid4()
    body = SalesCalendarEventCreate(
        sales_entry_id=uuid4(),
        customer_id=uuid4(),
        title="Estimate - Logging Test",
        scheduled_date=date(2026, 5, 1),
        start_time=time(11, 0),
        end_time=time(12, 0),
        assigned_to_user_id=assignee_id,
    )
    session = _make_session_with_entry(SalesEntryStatus.SCHEDULE_ESTIMATE.value)
    user = MagicMock()

    with caplog.at_level(logging.INFO):
        await create_calendar_event(
            body=body,
            user=user,
            session=session,
            pipeline_service=MagicMock(),
        )

    # Find the create_calendar_event_completed log record.
    matching = [
        r
        for r in caplog.records
        if "create_calendar_event_completed" in (r.getMessage() or "")
        or getattr(r, "event", "") == "create_calendar_event_completed"
    ]
    assert matching, "Expected a log record for create_calendar_event_completed"
    # The assignee should appear somewhere in the log payload — check both
    # structured-log attribute access and the rendered message.
    found_assignee = False
    for record in matching:
        if getattr(record, "assigned_to_user_id", None) == str(assignee_id):
            found_assignee = True
            break
        if str(assignee_id) in (record.getMessage() or ""):
            found_assignee = True
            break
    assert found_assignee, (
        "Expected assigned_to_user_id to be present in the completed log"
    )
