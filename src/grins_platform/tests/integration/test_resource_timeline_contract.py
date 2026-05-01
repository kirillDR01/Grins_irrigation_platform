"""Bug fix: resource-timeline /capacity & /utilization contract.

Validates: bughunt/2026-04-30-resource-timeline-loading-and-capacity-bugs.md
"""

from __future__ import annotations

import uuid
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app


def _staff(name: str = "Tech A") -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.name = name
    m.is_active = True
    m.is_available = True
    return m


def _availability(
    staff_id: uuid.UUID,
    *,
    start: time = time(8, 0),
    end: time = time(17, 0),
    lunch: int = 60,
) -> MagicMock:
    m = MagicMock()
    m.staff_id = staff_id
    m.date = date(2026, 5, 4)
    m.start_time = start
    m.end_time = end
    m.lunch_duration_minutes = lunch
    m.is_available = True
    return m


@pytest.mark.integration
@pytest.mark.asyncio
async def test_capacity_response_includes_numeric_utilization_pct() -> None:
    """``utilization_pct`` is present and numeric on /capacity (Bug A surface)."""
    from grins_platform.api.v1.dependencies import get_db_session
    from grins_platform.api.v1.schedule import get_schedule_service
    from grins_platform.services.schedule_generation_service import (
        ScheduleGenerationService,
    )

    tech = _staff()
    avail = _availability(tech.id)
    sync_session = MagicMock()
    # _load_available_staff -> [tech] then per-tech .first() -> avail
    sync_session.query.return_value.filter.return_value.all.side_effect = [
        [tech],  # active staff
        [],  # appointments for date (_get_scheduled_minutes)
    ]
    sync_session.query.return_value.filter.return_value.first.return_value = avail

    service = ScheduleGenerationService(db=sync_session)

    async_session = AsyncMock()
    app.dependency_overrides[get_schedule_service] = lambda: service
    app.dependency_overrides[get_db_session] = lambda: async_session

    try:
        with patch(
            "grins_platform.api.v1.schedule.load_assignments_for_date",
            new_callable=AsyncMock,
            return_value=[],
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/schedule/capacity/2026-05-04")
        assert response.status_code == 200
        body = response.json()
        assert "utilization_pct" in body
        assert isinstance(body["utilization_pct"], (int, float))
        # No appointments scheduled → 0.0
        assert body["utilization_pct"] == 0.0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_utilization_falls_back_to_synthetic_shift_when_no_availability() -> None:
    """Empty ``staff_availability`` must NOT yield empty resources — dev parity."""
    from grins_platform.api.v1.schedule import get_schedule_service
    from grins_platform.services.schedule_generation_service import (
        ScheduleGenerationService,
    )

    tech = _staff()
    sync_session = MagicMock()
    # Order:
    # 1. Staff query (.all()) -> [tech]
    # 2. Appointment query (.all()) -> []
    sync_session.query.return_value.filter.return_value.all.side_effect = [
        [tech],
        [],
    ]
    # StaffAvailability lookup (.first()) -> None (table empty for date)
    sync_session.query.return_value.filter.return_value.first.return_value = None

    service = ScheduleGenerationService(db=sync_session)
    app.dependency_overrides[get_schedule_service] = lambda: service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/schedule/utilization?schedule_date=2026-05-04"
            )
        assert response.status_code == 200
        body = response.json()
        assert len(body["resources"]) == 1
        r0 = body["resources"][0]
        assert r0["total_minutes"] == ScheduleGenerationService.DEFAULT_SHIFT_MINUTES
        assert r0["assigned_minutes"] == 0
        assert r0["utilization_pct"] == 0.0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_utilization_report_uses_real_availability_when_present() -> None:
    """When availability rows exist, ``total_minutes`` reflects them."""
    from grins_platform.api.v1.schedule import get_schedule_service
    from grins_platform.services.schedule_generation_service import (
        ScheduleGenerationService,
    )

    tech = _staff()
    avail = _availability(
        tech.id,
        start=time(8, 0),
        end=time(17, 0),
        lunch=60,
    )
    sync_session = MagicMock()
    sync_session.query.return_value.filter.return_value.all.side_effect = [
        [tech],
        [],
    ]
    sync_session.query.return_value.filter.return_value.first.return_value = avail

    service = ScheduleGenerationService(db=sync_session)
    app.dependency_overrides[get_schedule_service] = lambda: service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/schedule/utilization?schedule_date=2026-05-04"
            )
        assert response.status_code == 200
        body = response.json()
        assert len(body["resources"]) == 1
        # 9h shift minus 60-min lunch == 8 * 60.
        assert body["resources"][0]["total_minutes"] == 8 * 60
    finally:
        app.dependency_overrides.clear()
