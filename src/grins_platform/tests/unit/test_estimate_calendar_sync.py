"""Unit tests for estimate calendar → sales pipeline status sync.

Tests that creating a calendar event auto-advances a sales entry from
schedule_estimate to estimate_scheduled, and does NOT double-advance
entries already at estimate_scheduled or later.

Validates: Requirements 10.1, 10.4
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from grins_platform.api.v1.sales_pipeline import create_calendar_event
from grins_platform.models.enums import SalesEntryStatus
from grins_platform.schemas.sales_pipeline import SalesCalendarEventCreate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_body(
    *,
    sales_entry_id: object | None = None,
    customer_id: object | None = None,
) -> SalesCalendarEventCreate:
    return SalesCalendarEventCreate(
        sales_entry_id=sales_entry_id or uuid4(),
        customer_id=customer_id or uuid4(),
        title="Estimate visit",
        scheduled_date=date(2025, 7, 15),
        start_time=time(9, 0),
        end_time=time(10, 0),
        notes=None,
    )


def _make_sales_entry(status: str) -> Mock:
    entry = Mock()
    entry.id = uuid4()
    entry.status = status
    return entry


def _mock_user() -> Mock:
    user = Mock()
    user.id = uuid4()
    user.is_active = True
    user.role = "admin"
    return user


def _populate_event_fields(event: object) -> None:
    """Simulate DB-generated fields that session.refresh would populate."""
    if getattr(event, "id", None) is None:
        event.id = uuid4()  # type: ignore[attr-defined]
    now = datetime.now(tz=timezone.utc)
    if getattr(event, "created_at", None) is None:
        event.created_at = now  # type: ignore[attr-defined]
    if getattr(event, "updated_at", None) is None:
        event.updated_at = now  # type: ignore[attr-defined]


def _build_mock_session(sales_entry: Mock | None) -> AsyncMock:
    """Build a mock session that returns the given sales entry on execute."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.add = Mock()

    # session.refresh should populate DB-generated fields on the event
    async def _refresh(obj: object) -> None:
        _populate_event_fields(obj)

    session.refresh = AsyncMock(side_effect=_refresh)

    entry_result = Mock()
    entry_result.scalar_one_or_none.return_value = sales_entry
    session.execute.return_value = entry_result

    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestCalendarEventAutoAdvance:
    """Test auto-advance of sales entry on calendar event creation.

    Validates: Requirements 10.1, 10.4
    """

    @pytest.mark.asyncio()
    async def test_create_event_advances_schedule_estimate_to_estimate_scheduled(
        self,
    ) -> None:
        """Creating a calendar event for a schedule_estimate entry auto-advances it.

        Validates: Requirement 10.1
        """
        entry = _make_sales_entry(SalesEntryStatus.SCHEDULE_ESTIMATE.value)
        body = _make_body(sales_entry_id=entry.id)
        session = _build_mock_session(entry)

        await create_calendar_event(
            body=body,
            _user=_mock_user(),
            session=session,
        )

        assert entry.status == SalesEntryStatus.ESTIMATE_SCHEDULED.value

    @pytest.mark.asyncio()
    async def test_create_event_does_not_advance_estimate_scheduled(self) -> None:
        """Creating a calendar event for an already-advanced entry does NOT change status.

        Validates: Requirement 10.4
        """
        entry = _make_sales_entry(SalesEntryStatus.ESTIMATE_SCHEDULED.value)
        body = _make_body(sales_entry_id=entry.id)
        session = _build_mock_session(entry)

        await create_calendar_event(
            body=body,
            _user=_mock_user(),
            session=session,
        )

        assert entry.status == SalesEntryStatus.ESTIMATE_SCHEDULED.value

    @pytest.mark.asyncio()
    async def test_create_event_does_not_advance_later_statuses(self) -> None:
        """Creating a calendar event for a send_estimate entry does NOT change status.

        Validates: Requirement 10.4
        """
        entry = _make_sales_entry(SalesEntryStatus.SEND_ESTIMATE.value)
        body = _make_body(sales_entry_id=entry.id)
        session = _build_mock_session(entry)

        await create_calendar_event(
            body=body,
            _user=_mock_user(),
            session=session,
        )

        assert entry.status == SalesEntryStatus.SEND_ESTIMATE.value

    @pytest.mark.asyncio()
    async def test_create_event_handles_missing_sales_entry(self) -> None:
        """Creating a calendar event when sales entry is not found still creates the event.

        Edge case: the sales_entry_id might reference a deleted entry.
        """
        body = _make_body()
        session = _build_mock_session(None)  # No entry found

        # Should not raise — event is still created
        await create_calendar_event(
            body=body,
            _user=_mock_user(),
            session=session,
        )

        session.add.assert_called_once()
        session.commit.assert_called_once()
