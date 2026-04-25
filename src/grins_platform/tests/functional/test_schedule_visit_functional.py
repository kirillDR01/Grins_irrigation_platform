"""Functional tests for the Schedule Visit calendar event workflow.

This codebase's "functional" tier is mocked-service-layer (mirrors
``test_sales_pipeline_functional.py``). Real-DB tests live under
``tests/integration/``.

Validates: Auto-advance from schedule_estimate → estimate_scheduled on
event creation; reschedule (PUT) does not re-advance; assignee survives
the create round-trip.
"""

from __future__ import annotations

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
from grins_platform.models.sales import SalesEntry
from grins_platform.schemas.sales_pipeline import (
    SalesCalendarEventCreate,
    SalesCalendarEventUpdate,
)


def _make_sales_entry(
    *,
    status: str = SalesEntryStatus.SCHEDULE_ESTIMATE.value,
) -> MagicMock:
    entry = MagicMock(spec=SalesEntry)
    entry.id = uuid4()
    entry.customer_id = uuid4()
    entry.status = status
    return entry


def _make_session(
    sales_entry: MagicMock | None,
    existing_event: MagicMock | None = None,
) -> AsyncMock:
    """Build a session mock that returns the given sales_entry on the first
    execute() call (used by create_calendar_event) or returns the
    existing_event for update_calendar_event."""
    session = AsyncMock()
    session.add = MagicMock()

    if existing_event is not None:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=existing_event)
        session.execute = AsyncMock(return_value=result)
    else:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sales_entry)
        session.execute = AsyncMock(return_value=result)

    session.commit = AsyncMock()

    async def _refresh(obj: Any) -> None:
        if not getattr(obj, "id", None):
            obj.id = uuid4()
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime.now(timezone.utc)

    session.refresh = AsyncMock(side_effect=_refresh)
    return session


@pytest.mark.functional
@pytest.mark.asyncio
async def test_workflow_create_event_advances_status() -> None:
    sales_entry = _make_sales_entry(
        status=SalesEntryStatus.SCHEDULE_ESTIMATE.value,
    )
    session = _make_session(sales_entry)
    user = MagicMock()

    body = SalesCalendarEventCreate(
        sales_entry_id=sales_entry.id,
        customer_id=sales_entry.customer_id,
        title="Estimate - Workflow Customer",
        scheduled_date=date(2026, 5, 5),
        start_time=time(13, 0),
        end_time=time(14, 0),
    )

    await create_calendar_event(body=body, _user=user, session=session)

    # Status advanced.
    assert sales_entry.status == SalesEntryStatus.ESTIMATE_SCHEDULED.value
    # Event row was added to the session.
    assert session.add.call_count == 1
    # Commit awaited.
    session.commit.assert_awaited()


@pytest.mark.functional
@pytest.mark.asyncio
async def test_workflow_reschedule_does_not_re_advance() -> None:
    # Existing event for an entry already at estimate_scheduled.
    existing = MagicMock()
    existing.id = uuid4()
    existing.sales_entry_id = uuid4()
    existing.customer_id = uuid4()
    existing.title = "Estimate - Original"
    existing.scheduled_date = date(2026, 5, 1)
    existing.start_time = time(14, 0)
    existing.end_time = time(15, 0)
    existing.notes = None
    existing.assigned_to_user_id = None
    existing.created_at = datetime.now(timezone.utc)
    existing.updated_at = datetime.now(timezone.utc)

    sales_entry = _make_sales_entry(
        status=SalesEntryStatus.ESTIMATE_SCHEDULED.value,
    )
    session = _make_session(sales_entry, existing_event=existing)
    user = MagicMock()

    body = SalesCalendarEventUpdate(
        scheduled_date=date(2026, 5, 8),
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    await update_calendar_event(
        event_id=existing.id,
        body=body,
        _user=user,
        session=session,
    )

    # The existing event was mutated.
    assert existing.scheduled_date == date(2026, 5, 8)
    # The sales entry status is unchanged (the update handler does not
    # re-advance the pipeline; the create handler is the only auto-advance
    # path).
    assert sales_entry.status == SalesEntryStatus.ESTIMATE_SCHEDULED.value


@pytest.mark.functional
@pytest.mark.asyncio
async def test_workflow_create_event_with_assignee_round_trips() -> None:
    sales_entry = _make_sales_entry()
    session = _make_session(sales_entry)
    user = MagicMock()
    assignee_id = uuid4()

    body = SalesCalendarEventCreate(
        sales_entry_id=sales_entry.id,
        customer_id=sales_entry.customer_id,
        title="Estimate - Assignee Round Trip",
        scheduled_date=date(2026, 5, 5),
        start_time=time(13, 0),
        end_time=time(14, 0),
        assigned_to_user_id=assignee_id,
    )

    await create_calendar_event(body=body, _user=user, session=session)

    added = session.add.call_args.args[0]
    assert added.assigned_to_user_id == assignee_id
