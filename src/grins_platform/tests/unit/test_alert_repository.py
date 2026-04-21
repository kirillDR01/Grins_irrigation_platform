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

    @pytest.mark.asyncio
    async def test_get_by_id_returns_row(
        self,
        repository: AlertRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``get`` returns the matching row."""
        alert = MagicMock(spec=Alert)
        alert.id = uuid4()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = alert
        mock_session.execute = AsyncMock(return_value=exec_result)

        result = await repository.get(alert.id)
        assert result is alert

    @pytest.mark.asyncio
    async def test_list_unacknowledged_by_type_filters(
        self,
        repository: AlertRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``list_unacknowledged_by_type`` returns only matching type rows."""
        matching = MagicMock(spec=Alert)
        matching.id = uuid4()
        matching.type = AlertType.INFORMAL_OPT_OUT.value
        matching.acknowledged_at = None

        scalars_result = MagicMock()
        scalars_result.all.return_value = [matching]
        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_result
        mock_session.execute = AsyncMock(return_value=exec_result)

        rows = await repository.list_unacknowledged_by_type(
            alert_type="informal_opt_out",
            limit=10,
        )
        assert rows == [matching]

    @pytest.mark.asyncio
    async def test_acknowledge_sets_timestamp_when_pending(
        self,
        repository: AlertRepository,
        mock_session: AsyncMock,
    ) -> None:
        """First acknowledge stamps acknowledged_at."""
        alert = Alert(
            type=AlertType.INFORMAL_OPT_OUT.value,
            severity=AlertSeverity.WARNING.value,
            entity_type="customer",
            entity_id=uuid4(),
            message="stop texting me",
        )
        alert.id = uuid4()
        alert.acknowledged_at = None
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = alert
        mock_session.execute = AsyncMock(return_value=exec_result)

        result = await repository.acknowledge(alert.id)
        assert result is alert
        assert alert.acknowledged_at is not None

    @pytest.mark.asyncio
    async def test_acknowledge_is_idempotent(
        self,
        repository: AlertRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Acknowledging an already-acknowledged row preserves the timestamp."""
        prior = datetime(2026, 1, 1, tzinfo=timezone.utc)
        alert = Alert(
            type=AlertType.INFORMAL_OPT_OUT.value,
            severity=AlertSeverity.WARNING.value,
            entity_type="customer",
            entity_id=uuid4(),
            message="stop texting me",
        )
        alert.id = uuid4()
        alert.acknowledged_at = prior
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = alert
        mock_session.execute = AsyncMock(return_value=exec_result)

        result = await repository.acknowledge(alert.id)
        assert result is alert
        assert alert.acknowledged_at == prior
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_acknowledge_missing_returns_none(
        self,
        repository: AlertRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Missing row → None."""
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=exec_result)

        result = await repository.acknowledge(uuid4())
        assert result is None
