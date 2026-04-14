"""Unit tests for inline target-week editing on jobs.

Covers:
  - JobUpdate Pydantic schema accepts target_start_date / target_end_date,
    with the validator enforcing the Mon-Sun pair and sane range.
  - JobService.update_job blocks target-date edits when the job is
    already past 'to_be_scheduled'.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.exceptions import JobTargetDateEditNotAllowedError
from grins_platform.models.enums import JobStatus
from grins_platform.schemas.job import JobUpdate
from grins_platform.services.job_service import JobService


def _next_monday(weeks_ahead: int = 1) -> date:
    """Return a Monday that is at least ``weeks_ahead`` weeks in the future."""
    today = date.today()
    # Move to next Monday, then add whole weeks from there.
    days_to_monday = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_to_monday + 7 * (weeks_ahead - 1))


# ---------------------------------------------------------------------------
# Schema: target-date validator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJobUpdateTargetDateValidator:
    def test_accepts_valid_mon_sun_pair(self) -> None:
        monday = _next_monday()
        sunday = monday + timedelta(days=6)
        upd = JobUpdate(target_start_date=monday, target_end_date=sunday)
        assert upd.target_start_date == monday
        assert upd.target_end_date == sunday

    def test_allows_both_fields_omitted(self) -> None:
        # Existing update paths that don't touch target dates must keep working.
        upd = JobUpdate(notes="admin note")
        assert upd.target_start_date is None
        assert upd.target_end_date is None
        assert upd.notes == "admin note"

    def test_rejects_start_without_end(self) -> None:
        with pytest.raises(ValidationError, match="must be provided together"):
            JobUpdate(target_start_date=_next_monday())

    def test_rejects_end_without_start(self) -> None:
        monday = _next_monday()
        with pytest.raises(ValidationError, match="must be provided together"):
            JobUpdate(target_end_date=monday + timedelta(days=6))

    def test_rejects_non_monday_start(self) -> None:
        tuesday = _next_monday() + timedelta(days=1)
        with pytest.raises(ValidationError, match="must be a Monday"):
            JobUpdate(
                target_start_date=tuesday,
                target_end_date=tuesday + timedelta(days=6),
            )

    def test_rejects_mismatched_window_length(self) -> None:
        monday = _next_monday()
        saturday = monday + timedelta(days=5)
        with pytest.raises(
            ValidationError, match="must equal target_start_date \\+ 6 days",
        ):
            JobUpdate(target_start_date=monday, target_end_date=saturday)

    def test_rejects_ancient_start(self) -> None:
        # A Monday way in the past.
        ancient_monday = date(2020, 1, 6)
        with pytest.raises(ValidationError, match="out of the allowed range"):
            JobUpdate(
                target_start_date=ancient_monday,
                target_end_date=ancient_monday + timedelta(days=6),
            )

    def test_rejects_far_future_start(self) -> None:
        far_monday = _next_monday() + timedelta(days=365 * 3)
        # Normalize to Monday.
        while far_monday.weekday() != 0:
            far_monday += timedelta(days=1)
        with pytest.raises(ValidationError, match="out of the allowed range"):
            JobUpdate(
                target_start_date=far_monday,
                target_end_date=far_monday + timedelta(days=6),
            )


# ---------------------------------------------------------------------------
# Service: status guard
# ---------------------------------------------------------------------------


def _make_job_repo(job: MagicMock) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=job)
    repo.update = AsyncMock(return_value=job)
    return repo


def _make_service(job: MagicMock) -> JobService:
    svc = JobService.__new__(JobService)
    # Minimal ancestor init — we only exercise update_job here.
    svc.job_repository = _make_job_repo(job)  # type: ignore[attr-defined]
    # Logger stubs so LoggerMixin doesn't try to inspect a missing domain.
    svc.log_started = lambda *a, **kw: None  # type: ignore[attr-defined,method-assign]
    svc.log_completed = lambda *a, **kw: None  # type: ignore[attr-defined,method-assign]
    svc.log_rejected = lambda *a, **kw: None  # type: ignore[attr-defined,method-assign]
    return svc


@pytest.mark.unit
class TestJobServiceUpdateTargetDateGuard:
    @pytest.mark.asyncio
    async def test_allows_edit_when_status_is_to_be_scheduled(self) -> None:
        job = MagicMock()
        job.id = uuid4()
        job.status = JobStatus.TO_BE_SCHEDULED.value
        job.category = "ready_to_schedule"
        svc = _make_service(job)

        monday = _next_monday()
        upd = JobUpdate(
            target_start_date=monday,
            target_end_date=monday + timedelta(days=6),
        )
        await svc.update_job(job.id, upd)

        # Repo.update was called with the new date range
        call_kwargs = svc.job_repository.update.call_args[0][1]
        assert call_kwargs["target_start_date"] == monday
        assert call_kwargs["target_end_date"] == monday + timedelta(days=6)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "blocked_status",
        [
            JobStatus.SCHEDULED.value,
            JobStatus.IN_PROGRESS.value,
            JobStatus.COMPLETED.value,
            JobStatus.CANCELLED.value,
        ],
    )
    async def test_rejects_edit_when_status_is_not_to_be_scheduled(
        self, blocked_status: str,
    ) -> None:
        job = MagicMock()
        job.id = uuid4()
        job.status = blocked_status
        job.category = "ready_to_schedule"
        svc = _make_service(job)

        monday = _next_monday()
        upd = JobUpdate(
            target_start_date=monday,
            target_end_date=monday + timedelta(days=6),
        )
        with pytest.raises(JobTargetDateEditNotAllowedError) as exc_info:
            await svc.update_job(job.id, upd)
        assert exc_info.value.current_status == blocked_status
        # Repo.update must NOT have been called
        svc.job_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_date_updates_still_work_on_scheduled_job(self) -> None:
        """A notes-only update on a scheduled job is unaffected by the guard."""
        job = MagicMock()
        job.id = uuid4()
        job.status = JobStatus.SCHEDULED.value
        job.category = "ready_to_schedule"
        svc = _make_service(job)

        upd = JobUpdate(notes="admin note after scheduling")
        await svc.update_job(job.id, upd)

        call_kwargs = svc.job_repository.update.call_args[0][1]
        assert call_kwargs == {"notes": "admin note after scheduling"}
