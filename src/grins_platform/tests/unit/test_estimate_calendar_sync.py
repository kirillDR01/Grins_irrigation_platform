"""Unit tests for estimate calendar event creation.

Auto-advance from ``schedule_estimate`` → ``estimate_scheduled`` moved
out of bare event creation and into
:meth:`SalesPipelineService.send_estimate_visit_confirmation` (per
sales-pipeline-estimate-visit-confirmation-lifecycle OQ-6). Bare
``POST /sales/calendar/events`` (without ``send_confirmation=true``)
**no longer** advances the entry — staff must intentionally send the
Y/R/C SMS to claim the customer has been told. These tests lock in
the new contract.

Validates: sales-pipeline-estimate-visit-confirmation-lifecycle (OQ-6).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, Mock
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
    # Polymorphic FK confirmation lifecycle (migration 20260509_120000).
    if not getattr(event, "confirmation_status", None):
        event.confirmation_status = "pending"  # type: ignore[attr-defined]


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
    """Bare ``POST /sales/calendar/events`` no longer auto-advances.

    Per OQ-6, the auto-advance lives inside
    :meth:`SalesPipelineService.send_estimate_visit_confirmation` so an
    event without an SMS dispatch (e.g. a 3rd-party calendar import)
    doesn't claim the customer has been told. These tests lock in the
    new contract.
    """

    @pytest.mark.asyncio()
    async def test_create_event_does_not_auto_advance(self) -> None:
        """Bare event creation leaves the entry at ``schedule_estimate``."""
        entry = _make_sales_entry(SalesEntryStatus.SCHEDULE_ESTIMATE.value)
        body = _make_body(sales_entry_id=entry.id)
        session = _build_mock_session(entry)

        await create_calendar_event(
            body=body,
            user=_mock_user(),
            session=session,
            pipeline_service=MagicMock(),
        )

        # The auto-advance is now gated on send_confirmation=True.
        assert entry.status == SalesEntryStatus.SCHEDULE_ESTIMATE.value

    @pytest.mark.asyncio()
    async def test_create_event_does_not_advance_estimate_scheduled(self) -> None:
        """Already-advanced entries stay put."""
        entry = _make_sales_entry(SalesEntryStatus.ESTIMATE_SCHEDULED.value)
        body = _make_body(sales_entry_id=entry.id)
        session = _build_mock_session(entry)

        await create_calendar_event(
            body=body,
            user=_mock_user(),
            session=session,
            pipeline_service=MagicMock(),
        )

        assert entry.status == SalesEntryStatus.ESTIMATE_SCHEDULED.value

    @pytest.mark.asyncio()
    async def test_create_event_does_not_advance_later_statuses(self) -> None:
        """Entries past ``estimate_scheduled`` are untouched."""
        entry = _make_sales_entry(SalesEntryStatus.SEND_ESTIMATE.value)
        body = _make_body(sales_entry_id=entry.id)
        session = _build_mock_session(entry)

        await create_calendar_event(
            body=body,
            user=_mock_user(),
            session=session,
            pipeline_service=MagicMock(),
        )

        assert entry.status == SalesEntryStatus.SEND_ESTIMATE.value

    @pytest.mark.asyncio()
    async def test_create_event_handles_missing_sales_entry(self) -> None:
        """Missing sales entry no longer gets queried at create time.

        The legacy auto-advance block looked up the entry and did
        nothing if missing. Now no lookup happens in the create path —
        the only execute call is from the (mocked) request lifecycle.
        """
        body = _make_body()
        session = _build_mock_session(None)

        await create_calendar_event(
            body=body,
            user=_mock_user(),
            session=session,
            pipeline_service=MagicMock(),
        )

        session.add.assert_called_once()
        session.commit.assert_called_once()
