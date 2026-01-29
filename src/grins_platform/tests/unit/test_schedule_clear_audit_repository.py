"""Unit tests for ScheduleClearAuditRepository.

Requirements: 5.1-5.6, 6.1-6.5
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from grins_platform.models.schedule_clear_audit import ScheduleClearAudit
from grins_platform.repositories.schedule_clear_audit_repository import (
    ScheduleClearAuditRepository,
)


@pytest.mark.unit
class TestScheduleClearAuditRepositoryCreate:
    """Tests for ScheduleClearAuditRepository.create method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> ScheduleClearAuditRepository:
        """Create repository with mock session."""
        return ScheduleClearAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_audit_record(
        self,
        repository: ScheduleClearAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating an audit record with all fields."""
        schedule_date = date(2025, 1, 28)
        appointments_data = [
            {"id": str(uuid4()), "job_id": str(uuid4()), "time_slot": "09:00-11:00"},
            {"id": str(uuid4()), "job_id": str(uuid4()), "time_slot": "11:00-13:00"},
        ]
        jobs_reset = [uuid4(), uuid4()]
        cleared_by = uuid4()
        notes = "Test clear operation"

        result = await repository.create(
            schedule_date=schedule_date,
            appointments_data=appointments_data,
            jobs_reset=jobs_reset,
            appointment_count=2,
            cleared_by=cleared_by,
            notes=notes,
        )

        # Verify session.add was called
        mock_session.add.assert_called_once()
        added_audit = mock_session.add.call_args[0][0]
        assert isinstance(added_audit, ScheduleClearAudit)
        assert added_audit.schedule_date == schedule_date
        assert added_audit.appointments_data == appointments_data
        assert added_audit.jobs_reset == jobs_reset
        assert added_audit.appointment_count == 2
        assert added_audit.cleared_by == cleared_by
        assert added_audit.notes == notes

        # Verify flush and refresh were called
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()

        # Verify result is the added audit
        assert result == added_audit

    @pytest.mark.asyncio
    async def test_create_audit_record_minimal(
        self,
        repository: ScheduleClearAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating an audit record with minimal fields."""
        schedule_date = date(2025, 1, 28)
        appointments_data: list[dict[str, str]] = []
        jobs_reset: list[UUID] = []

        await repository.create(
            schedule_date=schedule_date,
            appointments_data=appointments_data,
            jobs_reset=jobs_reset,
            appointment_count=0,
        )

        mock_session.add.assert_called_once()
        added_audit = mock_session.add.call_args[0][0]
        assert added_audit.cleared_by is None
        assert added_audit.notes is None


@pytest.mark.unit
class TestScheduleClearAuditRepositoryGetById:
    """Tests for ScheduleClearAuditRepository.get_by_id method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> ScheduleClearAuditRepository:
        """Create repository with mock session."""
        return ScheduleClearAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ScheduleClearAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting an audit record by ID when it exists."""
        audit_id = uuid4()
        mock_audit = MagicMock(spec=ScheduleClearAudit)
        mock_audit.id = audit_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_audit
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(audit_id)

        assert result == mock_audit
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ScheduleClearAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting an audit record by ID when it doesn't exist."""
        audit_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(audit_id)

        assert result is None


@pytest.mark.unit
class TestScheduleClearAuditRepositoryFindSince:
    """Tests for ScheduleClearAuditRepository.find_since method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> ScheduleClearAuditRepository:
        """Create repository with mock session."""
        return ScheduleClearAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_find_since_with_results(
        self,
        repository: ScheduleClearAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding audit records within time window."""
        mock_audit1 = MagicMock(spec=ScheduleClearAudit)
        mock_audit1.cleared_at = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_audit2 = MagicMock(spec=ScheduleClearAudit)
        mock_audit2.cleared_at = datetime.now(timezone.utc) - timedelta(hours=12)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_audit1, mock_audit2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.find_since(hours=24)

        assert len(result) == 2
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_since_no_results(
        self,
        repository: ScheduleClearAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding audit records when none exist in time window."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.find_since(hours=24)

        assert result == []

    @pytest.mark.asyncio
    async def test_find_since_custom_hours(
        self,
        repository: ScheduleClearAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding audit records with custom time window."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        await repository.find_since(hours=48)

        # Verify execute was called (query was built)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_since_default_hours(
        self,
        repository: ScheduleClearAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding audit records with default 24 hour window."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        await repository.find_since()

        mock_session.execute.assert_awaited_once()
