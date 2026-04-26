"""Unit tests for :class:`AppointmentReminderLogRepository`.

Validates: scheduling gaps gap-10 Phase 1 (Day-2 No-Reply Reminder)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.appointment_reminder_log import AppointmentReminderLog
from grins_platform.repositories.appointment_reminder_log_repository import (
    AppointmentReminderLogRepository,
)


@pytest.mark.unit
class TestAppointmentReminderLogRepository:
    """Tests for :class:`AppointmentReminderLogRepository`."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(
        self,
        mock_session: AsyncMock,
    ) -> AppointmentReminderLogRepository:
        """Create repository with mock session."""
        return AppointmentReminderLogRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_persists_row(
        self,
        repository: AppointmentReminderLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``create`` adds + flushes + refreshes the row."""
        log = AppointmentReminderLog(
            appointment_id=uuid4(),
            stage="day_2",
            sent_at=datetime.now(tz=timezone.utc),
            sent_message_id=uuid4(),
        )

        created = await repository.create(log)

        mock_session.add.assert_called_once_with(log)
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(log)
        assert created is log

    @pytest.mark.asyncio
    async def test_get_latest_for_returns_match(
        self,
        repository: AppointmentReminderLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``get_latest_for`` returns the most-recent row for the pair."""
        appointment_id = uuid4()
        existing = MagicMock(spec=AppointmentReminderLog)
        existing.id = uuid4()
        existing.appointment_id = appointment_id
        existing.stage = "day_2"
        existing.sent_at = datetime.now(tz=timezone.utc)

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=exec_result)

        row = await repository.get_latest_for(appointment_id, "day_2")

        assert row is existing
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_latest_for_returns_none_when_absent(
        self,
        repository: AppointmentReminderLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``get_latest_for`` returns ``None`` for unseen pair."""
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=exec_result)

        row = await repository.get_latest_for(uuid4(), "day_2")

        assert row is None

    @pytest.mark.asyncio
    async def test_count_for_appointment_returns_total(
        self,
        repository: AppointmentReminderLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``count_for_appointment`` returns the integer count."""
        exec_result = MagicMock()
        exec_result.scalar.return_value = 3
        mock_session.execute = AsyncMock(return_value=exec_result)

        count = await repository.count_for_appointment(uuid4())

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_for_appointment_handles_none(
        self,
        repository: AppointmentReminderLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``count_for_appointment`` coerces a NULL aggregate to ``0``."""
        exec_result = MagicMock()
        exec_result.scalar.return_value = None
        mock_session.execute = AsyncMock(return_value=exec_result)

        count = await repository.count_for_appointment(uuid4())

        assert count == 0
