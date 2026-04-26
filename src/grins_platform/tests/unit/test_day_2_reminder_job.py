"""Unit tests for :class:`Day2ReminderJob` (gap-10 Phase 1).

Validates eligibility, dedup, opt-out, race protection, quiet-hours
deferral, and feature-flag gating for the Day-2 No-Reply Reminder.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus
from grins_platform.services.background_jobs import Day2ReminderJob


class _CannedExecute:
    """``session.execute`` double that returns canned results in order.

    Mirrors the helper used by NoReplyConfirmationFlagger tests so the
    job's staged queries can be prescribed without an in-memory DB.
    """

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.calls = 0

    async def __call__(self, *args: object, **kwargs: object) -> Any:
        _ = (args, kwargs)
        self.calls += 1
        if not self._results:
            empty = MagicMock()
            empty.scalars.return_value.all.return_value = []
            empty.scalar.return_value = 0
            empty.scalar_one_or_none.return_value = None
            return empty
        return self._results.pop(0)


def _canned_scalars(rows: list[Any]) -> MagicMock:
    """Wrap rows for ``.scalars().all()``."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = rows
    return r


def _canned_scalar(value: Any) -> MagicMock:
    """Wrap a scalar return value."""
    r = MagicMock()
    r.scalar.return_value = value
    return r


def _make_appt() -> MagicMock:
    appt = MagicMock()
    appt.id = uuid4()
    appt.status = AppointmentStatus.SCHEDULED.value
    appt.job_id = uuid4()
    appt.scheduled_date = datetime.now(timezone.utc).date() + timedelta(days=2)
    appt.time_window_start = None
    appt.time_window_end = None
    return appt


def _make_customer(phone: str = "+19527373312") -> MagicMock:
    c = MagicMock()
    c.id = uuid4()
    c.phone = phone
    c.first_name = "Test"
    c.last_name = "User"
    c.full_name = "Test User"
    return c


def _make_job() -> MagicMock:
    j = MagicMock()
    j.id = uuid4()
    j.customer_id = uuid4()
    j.job_type = None
    return j


def _setup_db(
    *,
    canned_results: list[Any],
    session_get_side_effect: list[Any] | None = None,
) -> tuple[MagicMock, MagicMock]:
    """Build a (mock_db, mock_session) pair with canned execute + get."""
    mock_session = MagicMock()
    mock_session.execute = _CannedExecute(canned_results)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    if session_get_side_effect is not None:
        mock_session.get = AsyncMock(side_effect=session_get_side_effect)
    else:
        mock_session.get = AsyncMock(return_value=None)

    mock_db = MagicMock()

    async def get_session() -> Any:
        yield mock_session

    mock_db.get_session = get_session
    return mock_db, mock_session


@pytest.mark.unit
class TestDay2ReminderJobGating:
    """Feature-flag + settings behavior."""

    @pytest.mark.asyncio
    async def test_run_with_flag_disabled_does_nothing(self) -> None:
        """When ``confirmation_day_2_reminder_enabled`` is False, no work happens."""
        job = Day2ReminderJob()
        mock_db, mock_session = _setup_db(canned_results=[])

        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=mock_db,
            ),
            patch.object(
                Day2ReminderJob,
                "_resolve_settings",
                AsyncMock(return_value=(False, 48)),
            ),
        ):
            await job.run()

        # No DB candidates queried, no rows added.
        assert mock_session.execute.calls == 0  # type: ignore[attr-defined]
        assert not mock_session.add.called


@pytest.mark.unit
class TestDay2ReminderJobEligibility:
    """Eligibility filter + dedup + send paths."""

    @pytest.mark.asyncio
    async def test_run_with_no_candidates_skips_send(self) -> None:
        """Empty candidate list returns 0 / 0 with no SMS sent."""
        job = Day2ReminderJob()
        # Eligibility query returns no appointments.
        mock_db, mock_session = _setup_db(
            canned_results=[_canned_scalars([])],
        )

        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=mock_db,
            ),
            patch.object(
                Day2ReminderJob,
                "_resolve_settings",
                AsyncMock(return_value=(True, 48)),
            ),
        ):
            await job.run()

        assert not mock_session.add.called

    @pytest.mark.asyncio
    async def test_run_skips_when_status_changed_after_query(self) -> None:
        """Race: appt confirmed between SELECT and send → skip + no row."""
        job = Day2ReminderJob()
        appt = _make_appt()

        # Eligibility query returns the candidate.
        canned = [_canned_scalars([appt])]

        # Race-protection re-read returns a CONFIRMED appointment.
        confirmed = _make_appt()
        confirmed.id = appt.id
        confirmed.status = AppointmentStatus.CONFIRMED.value

        mock_db, mock_session = _setup_db(
            canned_results=canned,
            session_get_side_effect=[confirmed],
        )

        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=mock_db,
            ),
            patch.object(
                Day2ReminderJob,
                "_resolve_settings",
                AsyncMock(return_value=(True, 48)),
            ),
        ):
            await job.run()

        # No reminder log row added because status changed.
        assert not mock_session.add.called

    @pytest.mark.asyncio
    async def test_run_skips_when_reply_landed_after_query(self) -> None:
        """Reply check returns >0 → skip the send + no log row."""
        job = Day2ReminderJob()
        appt = _make_appt()

        canned = [
            _canned_scalars([appt]),  # eligibility
            _canned_scalar(  # last confirmation sent_at
                datetime.now(timezone.utc) - timedelta(hours=49),
            ),
            _canned_scalar(1),  # reply count > 0
        ]

        mock_db, mock_session = _setup_db(
            canned_results=canned,
            session_get_side_effect=[appt],
        )

        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=mock_db,
            ),
            patch.object(
                Day2ReminderJob,
                "_resolve_settings",
                AsyncMock(return_value=(True, 48)),
            ),
        ):
            await job.run()

        assert not mock_session.add.called

    @pytest.mark.asyncio
    async def test_run_skips_opted_out_customer(self) -> None:
        """Latest SmsConsentRecord with consent_given=False → skip."""
        job = Day2ReminderJob()
        appt = _make_appt()
        customer = _make_customer()
        customer.phone = "+19527373312"
        cust_job = _make_job()

        canned = [
            _canned_scalars([appt]),  # eligibility
            _canned_scalar(  # last confirmation sent_at
                datetime.now(timezone.utc) - timedelta(hours=49),
            ),
            _canned_scalar(0),  # no reply yet
            _canned_scalar(False),  # opted out
        ]

        mock_db, mock_session = _setup_db(
            canned_results=canned,
            session_get_side_effect=[appt, cust_job, customer],
        )

        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=mock_db,
            ),
            patch.object(
                Day2ReminderJob,
                "_resolve_settings",
                AsyncMock(return_value=(True, 48)),
            ),
        ):
            await job.run()

        # No SMS row, no log row.
        assert not mock_session.add.called
