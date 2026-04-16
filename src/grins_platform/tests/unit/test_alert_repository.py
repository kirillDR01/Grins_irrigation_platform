"""Unit tests for :class:`AlertRepository`.

Validates: bughunt 2026-04-16 finding H-5
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.alert import Alert
from grins_platform.models.enums import AlertSeverity, AlertType
from grins_platform.repositories.alert_repository import AlertRepository


@pytest.mark.unit
class TestAlertRepository:
    """Tests for :class:`AlertRepository`."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> AlertRepository:
        """Create repository with mock session."""
        return AlertRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_and_list_unacknowledged(
        self,
        repository: AlertRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Creating an alert persists it, and list_unacknowledged returns it.

        Exercises both methods end-to-end against the mock session:
          * ``create`` must ``add`` + ``flush`` + ``refresh`` the row.
          * ``list_unacknowledged`` must issue a SELECT filtered to
            ``acknowledged_at IS NULL`` and return the scalar rows.

        Validates: bughunt 2026-04-16 finding H-5
        """
        appointment_id = uuid4()
        alert = Alert(
            type=AlertType.CUSTOMER_CANCELLED_APPOINTMENT.value,
            severity=AlertSeverity.WARNING.value,
            entity_type="appointment",
            entity_id=appointment_id,
            message="Jane Doe cancelled via customer_sms for 2026-04-17 09:00",
        )

        # --- create -----------------------------------------------------
        created = await repository.create(alert)

        mock_session.add.assert_called_once_with(alert)
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(alert)
        assert created is alert

        # --- list_unacknowledged ---------------------------------------
        now = datetime.now(tz=timezone.utc)

        persisted_alert = MagicMock(spec=Alert)
        persisted_alert.id = uuid4()
        persisted_alert.type = AlertType.CUSTOMER_CANCELLED_APPOINTMENT.value
        persisted_alert.severity = AlertSeverity.WARNING.value
        persisted_alert.entity_type = "appointment"
        persisted_alert.entity_id = appointment_id
        persisted_alert.message = "Jane Doe cancelled via customer_sms"
        persisted_alert.created_at = now
        persisted_alert.acknowledged_at = None

        scalars_result = MagicMock()
        scalars_result.all.return_value = [persisted_alert]

        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_result
        mock_session.execute = AsyncMock(return_value=exec_result)

        listed = await repository.list_unacknowledged(limit=50)

        assert listed == [persisted_alert]
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_unacknowledged_empty(
        self,
        repository: AlertRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``list_unacknowledged`` returns ``[]`` when no rows match."""
        scalars_result = MagicMock()
        scalars_result.all.return_value = []

        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_result
        mock_session.execute = AsyncMock(return_value=exec_result)

        listed = await repository.list_unacknowledged()

        assert listed == []
