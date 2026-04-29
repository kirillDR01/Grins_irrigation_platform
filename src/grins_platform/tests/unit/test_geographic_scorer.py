"""Unit tests for GeographicScorer (criteria 1-5).

Tests each criterion with mocked data inputs to verify scoring logic,
edge cases, and graceful handling of missing data.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal

import pytest

from grins_platform.schemas.ai_scheduling import SchedulingContext
from grins_platform.services.ai.scheduling.scorers.geographic import (
    GeographicScorer,
    _linear_score,
)
from grins_platform.services.schedule_domain import (
    ScheduleJob,
    ScheduleLocation,
    ScheduleStaff,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeCriterionConfig:
    """Minimal stand-in for _CriterionConfig."""

    __slots__ = (
        "config_json",
        "criterion_group",
        "criterion_name",
        "criterion_number",
        "is_enabled",
        "is_hard_constraint",
        "weight",
    )

    def __init__(
        self,
        criterion_number: int,
        weight: int = 50,
        is_hard_constraint: bool = False,
    ) -> None:
        self.criterion_number = criterion_number
        self.criterion_name = f"Criterion {criterion_number}"
        self.criterion_group = "geographic"
        self.weight = weight
        self.is_hard_constraint = is_hard_constraint
        self.is_enabled = True
        self.config_json: dict = {}


def _default_config() -> dict:
    """Build a default config dict for criteria 1-5."""
    return {
        1: _FakeCriterionConfig(1, weight=80),
        2: _FakeCriterionConfig(2, weight=70),
        3: _FakeCriterionConfig(3, weight=60),
        4: _FakeCriterionConfig(4, weight=50),
        5: _FakeCriterionConfig(5, weight=90, is_hard_constraint=True),
    }


def _make_location(
    lat: float,
    lon: float,
) -> ScheduleLocation:
    return ScheduleLocation(
        latitude=Decimal(str(lat)),
        longitude=Decimal(str(lon)),
    )


def _make_job(
    lat: float = 33.45,
    lon: float = -112.07,
    preferred_start: time | None = None,
) -> ScheduleJob:
    return ScheduleJob(
        id=uuid.uuid4(),
        customer_name="Test Customer",
        location=_make_location(lat, lon),
        service_type="maintenance",
        duration_minutes=60,
        preferred_time_start=preferred_start,
    )


def _make_staff(
    lat: float = 33.44,
    lon: float = -112.06,
) -> ScheduleStaff:
    return ScheduleStaff(
        id=uuid.uuid4(),
        name="Test Tech",
        start_location=_make_location(lat, lon),
    )


def _make_context(
    traffic: dict | None = None,
    backlog: dict | None = None,
) -> SchedulingContext:
    return SchedulingContext(
        schedule_date=date(2026, 5, 1),
        traffic=traffic,
        backlog=backlog,
    )


# ---------------------------------------------------------------------------
# _linear_score tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLinearScore:
    def test_at_best_returns_100(self) -> None:
        assert _linear_score(5.0, 5.0, 60.0) == 100.0

    def test_below_best_returns_100(self) -> None:
        assert _linear_score(2.0, 5.0, 60.0) == 100.0

    def test_at_worst_returns_0(self) -> None:
        assert _linear_score(60.0, 5.0, 60.0) == 0.0

    def test_above_worst_returns_0(self) -> None:
        assert _linear_score(100.0, 5.0, 60.0) == 0.0

    def test_midpoint(self) -> None:
        score = _linear_score(32.5, 5.0, 60.0)
        assert 49.0 <= score <= 51.0  # ~50


# ---------------------------------------------------------------------------
# Criterion 1 — Proximity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCriterion1Proximity:
    @pytest.mark.asyncio
    async def test_close_job_scores_high(self) -> None:
        scorer = GeographicScorer()
        # Same location -> ~1 min travel -> score ~100
        job = _make_job(33.44, -112.06)
        staff = _make_staff(33.44, -112.06)
        ctx = _make_context()

        result = await scorer._score_proximity(job, staff, ctx, _default_config())

        assert result.criterion_number == 1
        assert result.score >= 80.0
        assert result.is_satisfied is True
        assert "haversine" in result.explanation

    @pytest.mark.asyncio
    async def test_far_job_scores_low(self) -> None:
        scorer = GeographicScorer()
        # ~100 km apart -> well over 60 min
        job = _make_job(34.5, -112.07)
        staff = _make_staff(33.44, -112.06)
        ctx = _make_context()

        result = await scorer._score_proximity(job, staff, ctx, _default_config())

        assert result.score <= 20.0

    @pytest.mark.asyncio
    async def test_google_maps_fallback(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        # Provide Google Maps drive time in context
        ctx = _make_context(
            traffic={
                "drive_times": {
                    f"{staff.id}:{job.id}": 10,
                },
            },
        )

        result = await scorer._score_proximity(job, staff, ctx, _default_config())

        assert "google_maps" in result.explanation
        # 10 min -> score should be ~90.9
        assert result.score > 80.0


# ---------------------------------------------------------------------------
# Criterion 2 — Intra-route drive time
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCriterion2IntraRoute:
    @pytest.mark.asyncio
    async def test_no_existing_route(self) -> None:
        scorer = GeographicScorer()
        job = _make_job(33.45, -112.07)
        staff = _make_staff(33.44, -112.06)
        ctx = _make_context()

        result = await scorer._score_intra_route_drive_time(
            job, staff, ctx, _default_config()
        )

        assert result.criterion_number == 2
        assert result.score > 0.0
        assert "1 stops" in result.explanation

    @pytest.mark.asyncio
    async def test_with_existing_route_jobs(self) -> None:
        scorer = GeographicScorer()
        job = _make_job(33.50, -112.10)
        staff = _make_staff(33.44, -112.06)

        # Existing route with 2 jobs
        route_job1 = _make_job(33.45, -112.07)
        route_job2 = _make_job(33.47, -112.08)

        ctx = _make_context(
            traffic={
                "route_jobs": {
                    str(staff.id): [route_job1, route_job2],
                },
            },
        )

        result = await scorer._score_intra_route_drive_time(
            job, staff, ctx, _default_config()
        )

        assert result.criterion_number == 2
        assert "3 stops" in result.explanation


# ---------------------------------------------------------------------------
# Criterion 3 — Service zone boundaries
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCriterion3ServiceZone:
    @pytest.mark.asyncio
    async def test_no_zone_data_neutral(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()

        result = await scorer._score_service_zone(job, staff, ctx, _default_config())

        assert result.criterion_number == 3
        assert result.score == 50.0
        assert "unavailable" in result.explanation

    @pytest.mark.asyncio
    async def test_in_zone_scores_100(self) -> None:
        scorer = GeographicScorer()
        staff = _make_staff(33.44, -112.06)
        job = _make_job(33.45, -112.07)

        zone_id = "zone-north"
        ctx = _make_context(
            backlog={
                "service_zones": [
                    {
                        "id": zone_id,
                        "name": "North",
                        "boundary_data": {
                            "min_lat": 33.0,
                            "max_lat": 34.0,
                            "min_lon": -113.0,
                            "max_lon": -111.0,
                        },
                        "assigned_staff_ids": [str(staff.id)],
                    },
                ],
                "staff_zones": {str(staff.id): zone_id},
            },
        )

        result = await scorer._score_service_zone(job, staff, ctx, _default_config())

        assert result.score == 100.0
        assert "within" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_cross_zone_scores_50_to_80(self) -> None:
        scorer = GeographicScorer()
        staff = _make_staff(33.44, -112.06)
        job = _make_job(33.45, -112.07)

        ctx = _make_context(
            backlog={
                "service_zones": [
                    {
                        "id": "zone-south",
                        "name": "South",
                        "boundary_data": {
                            "min_lat": 32.0,
                            "max_lat": 33.0,
                            "min_lon": -113.0,
                            "max_lon": -111.0,
                        },
                        "assigned_staff_ids": [str(staff.id)],
                    },
                ],
                "staff_zones": {str(staff.id): "zone-south"},
            },
        )

        result = await scorer._score_service_zone(job, staff, ctx, _default_config())

        assert 50.0 <= result.score <= 80.0
        assert "cross-zone" in result.explanation.lower()


# ---------------------------------------------------------------------------
# Criterion 4 — Real-time traffic
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCriterion4Traffic:
    @pytest.mark.asyncio
    async def test_no_traffic_data_neutral(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()

        result = await scorer._score_realtime_traffic(
            job, staff, ctx, _default_config()
        )

        assert result.criterion_number == 4
        assert result.score == 50.0
        assert "unavailable" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_no_delay_scores_100(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            traffic={
                "traffic_multipliers": {
                    f"{staff.id}:{job.id}": 1.0,
                },
            },
        )

        result = await scorer._score_realtime_traffic(
            job, staff, ctx, _default_config()
        )

        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_severe_delay_scores_0(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            traffic={
                "traffic_multipliers": {
                    f"{staff.id}:{job.id}": 2.5,
                },
            },
        )

        result = await scorer._score_realtime_traffic(
            job, staff, ctx, _default_config()
        )

        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_moderate_delay_scores_mid(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context(
            traffic={
                "traffic_multipliers": {
                    f"{staff.id}:{job.id}": 1.5,
                },
            },
        )

        result = await scorer._score_realtime_traffic(
            job, staff, ctx, _default_config()
        )

        assert 40.0 <= result.score <= 60.0


# ---------------------------------------------------------------------------
# Criterion 5 — Job site access constraints (HARD)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCriterion5AccessConstraints:
    @pytest.mark.asyncio
    async def test_no_constraints_scores_100(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()

        result = await scorer._score_access_constraints(
            job, staff, ctx, _default_config()
        )

        assert result.criterion_number == 5
        assert result.score == 100.0
        assert result.is_satisfied is True
        assert result.is_hard is True

    @pytest.mark.asyncio
    async def test_within_access_window_satisfied(self) -> None:
        scorer = GeographicScorer()
        job = _make_job(preferred_start=time(10, 0))
        staff = _make_staff()
        ctx = _make_context(
            backlog={
                "access_constraints": {
                    str(job.id): {
                        "access_window_start": "08:00",
                        "access_window_end": "17:00",
                        "gate_code": "1234",
                    },
                },
            },
        )

        result = await scorer._score_access_constraints(
            job, staff, ctx, _default_config()
        )

        assert result.score == 100.0
        assert result.is_satisfied is True
        assert "1234" in result.explanation

    @pytest.mark.asyncio
    async def test_outside_access_window_fails(self) -> None:
        scorer = GeographicScorer()
        job = _make_job(preferred_start=time(6, 0))
        staff = _make_staff()
        ctx = _make_context(
            backlog={
                "access_constraints": {
                    str(job.id): {
                        "access_window_start": "08:00",
                        "access_window_end": "17:00",
                    },
                },
            },
        )

        result = await scorer._score_access_constraints(
            job, staff, ctx, _default_config()
        )

        assert result.score == 0.0
        assert result.is_satisfied is False
        assert result.is_hard is True
        assert "VIOLATION" in result.explanation

    @pytest.mark.asyncio
    async def test_gate_code_noted(self) -> None:
        scorer = GeographicScorer()
        job = _make_job(preferred_start=time(10, 0))
        staff = _make_staff()
        ctx = _make_context(
            backlog={
                "access_constraints": {
                    str(job.id): {
                        "gate_code": "5678",
                        "hoa_requirements": "Check in at front desk",
                    },
                },
            },
        )

        result = await scorer._score_access_constraints(
            job, staff, ctx, _default_config()
        )

        assert result.score == 100.0
        assert "5678" in result.explanation
        assert "HOA" in result.explanation


# ---------------------------------------------------------------------------
# Full score_assignment integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScoreAssignment:
    @pytest.mark.asyncio
    async def test_returns_5_results(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()

        results = await scorer.score_assignment(job, staff, ctx, _default_config())

        assert len(results) == 5
        numbers = [r.criterion_number for r in results]
        assert numbers == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_all_scores_in_range(self) -> None:
        scorer = GeographicScorer()
        job = _make_job()
        staff = _make_staff()
        ctx = _make_context()

        results = await scorer.score_assignment(job, staff, ctx, _default_config())

        for r in results:
            assert 0.0 <= r.score <= 100.0
            assert r.explanation
