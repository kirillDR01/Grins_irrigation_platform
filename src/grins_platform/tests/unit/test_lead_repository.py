"""Unit tests for LeadRepository.

This module tests all LeadRepository methods using mocked AsyncSession,
following the same patterns as test_invoice_repository.py.

Validates: Requirement 4, 5, 8
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.models.lead import Lead
from grins_platform.repositories.lead_repository import LeadRepository
from grins_platform.schemas.lead import LeadListParams

# =============================================================================
# Create method tests
# =============================================================================


@pytest.mark.unit
class TestLeadRepositoryCreate:
    """Tests for LeadRepository.create method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create repository with mock session."""
        return LeadRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_calls_session_add_flush_refresh(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that create calls session.add, flush, and refresh."""
        result = await repository.create(
            name="John Doe",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM.value,
            source_site="residential",
            status=LeadStatus.NEW.value,
        )

        mock_session.add.assert_called_once()
        added_lead = mock_session.add.call_args[0][0]
        assert isinstance(added_lead, Lead)
        assert added_lead.name == "John Doe"
        assert added_lead.phone == "6125550123"
        assert added_lead.zip_code == "55424"
        assert added_lead.situation == LeadSituation.NEW_SYSTEM.value
        assert added_lead.source_site == "residential"
        assert added_lead.status == LeadStatus.NEW.value

        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()
        assert result == added_lead

    @pytest.mark.asyncio
    async def test_create_with_optional_fields(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating a lead with optional email and notes."""
        await repository.create(
            name="Jane Smith",
            phone="6125559999",
            zip_code="55401",
            situation=LeadSituation.REPAIR.value,
            email="jane@example.com",
            notes="Large backyard system",
            source_site="commercial",
            status=LeadStatus.NEW.value,
        )

        added_lead = mock_session.add.call_args[0][0]
        assert added_lead.email == "jane@example.com"
        assert added_lead.notes == "Large backyard system"
        assert added_lead.source_site == "commercial"


# =============================================================================
# Get by ID tests
# =============================================================================


@pytest.mark.unit
class TestLeadRepositoryGetById:
    """Tests for LeadRepository.get_by_id method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create repository with mock session."""
        return LeadRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a lead by ID when it exists."""
        lead_id = uuid4()
        mock_lead = MagicMock(spec=Lead)
        mock_lead.id = lead_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(lead_id)

        assert result == mock_lead
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a lead by ID when it doesn't exist."""
        lead_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(lead_id)

        assert result is None


# =============================================================================
# Get by phone and active status tests
# =============================================================================


@pytest.mark.unit
class TestLeadRepositoryGetByPhoneAndActiveStatus:
    """Tests for LeadRepository.get_by_phone_and_active_status method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create repository with mock session."""
        return LeadRepository(mock_session)

    @pytest.mark.asyncio
    async def test_matching_active_lead_found(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding an active lead by phone number."""
        mock_lead = MagicMock(spec=Lead)
        mock_lead.phone = "6125550123"
        mock_lead.status = LeadStatus.NEW.value

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_phone_and_active_status("6125550123")

        assert result == mock_lead
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_matching_lead_returns_none(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that no matching lead returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_phone_and_active_status("6125559999")

        assert result is None


# =============================================================================
# List with filters tests
# =============================================================================


@pytest.mark.unit
class TestLeadRepositoryListWithFilters:
    """Tests for LeadRepository.list_with_filters method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create repository with mock session."""
        return LeadRepository(mock_session)

    @pytest.mark.asyncio
    async def test_list_with_no_filters(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing leads with no filters returns items and count."""
        mock_lead1 = MagicMock(spec=Lead)
        mock_lead2 = MagicMock(spec=Lead)

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Mock list query
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_lead1, mock_lead2]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = LeadListParams()
        leads, total = await repository.list_with_filters(params)

        assert len(leads) == 2
        assert total == 2
        assert mock_session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_list_with_status_filter(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing leads filtered by status."""
        mock_lead = MagicMock(spec=Lead)
        mock_lead.status = LeadStatus.NEW.value

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_lead]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = LeadListParams(status=LeadStatus.NEW)
        leads, total = await repository.list_with_filters(params)

        assert len(leads) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_with_situation_filter(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing leads filtered by situation."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = LeadListParams(situation=LeadSituation.REPAIR)
        leads, total = await repository.list_with_filters(params)

        assert len(leads) == 0
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_search_filter(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing leads with search on name/phone."""
        mock_lead = MagicMock(spec=Lead)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_lead]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = LeadListParams(search="John")
        leads, total = await repository.list_with_filters(params)

        assert len(leads) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_pagination(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing leads with pagination."""
        mock_lead = MagicMock(spec=Lead)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_lead]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = LeadListParams(page=3, page_size=10)
        _leads, total = await repository.list_with_filters(params)

        assert total == 50
        assert mock_session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_list_sorting_desc(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing leads with descending sort (default)."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = LeadListParams(sort_by="created_at", sort_order="desc")
        await repository.list_with_filters(params)

        mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_list_sorting_asc(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing leads with ascending sort."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = LeadListParams(sort_by="name", sort_order="asc")
        await repository.list_with_filters(params)

        mock_session.execute.assert_awaited()


# =============================================================================
# Update method tests
# =============================================================================


@pytest.mark.unit
class TestLeadRepositoryUpdate:
    """Tests for LeadRepository.update method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create repository with mock session."""
        return LeadRepository(mock_session)

    @pytest.mark.asyncio
    async def test_update_lead_found(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating a lead when it exists."""
        lead_id = uuid4()
        mock_lead = MagicMock(spec=Lead)
        mock_lead.id = lead_id
        mock_lead.status = LeadStatus.CONTACTED.value

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        result = await repository.update(
            lead_id,
            {"status": LeadStatus.CONTACTED.value},
        )

        assert result == mock_lead
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_lead_not_found(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating a lead when it doesn't exist."""
        lead_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.update(
            lead_id,
            {"status": LeadStatus.CONTACTED.value},
        )

        assert result is None
        mock_session.flush.assert_awaited_once()


# =============================================================================
# Delete method tests
# =============================================================================


@pytest.mark.unit
class TestLeadRepositoryDelete:
    """Tests for LeadRepository.delete method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create repository with mock session."""
        return LeadRepository(mock_session)

    @pytest.mark.asyncio
    async def test_delete_executes_query(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that delete executes a delete query and flushes."""
        lead_id = uuid4()

        await repository.delete(lead_id)

        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once()


# =============================================================================
# Count new today tests
# =============================================================================


@pytest.mark.unit
class TestLeadRepositoryCountNewToday:
    """Tests for LeadRepository.count_new_today method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create repository with mock session."""
        return LeadRepository(mock_session)

    @pytest.mark.asyncio
    async def test_count_new_today_returns_count(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that count_new_today returns the correct count."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await repository.count_new_today()

        assert result == 5
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_count_new_today_returns_zero_when_none(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that count_new_today returns 0 when scalar is None."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.count_new_today()

        assert result == 0


# =============================================================================
# Count uncontacted tests
# =============================================================================


@pytest.mark.unit
class TestLeadRepositoryCountUncontacted:
    """Tests for LeadRepository.count_uncontacted method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create repository with mock session."""
        return LeadRepository(mock_session)

    @pytest.mark.asyncio
    async def test_count_uncontacted_returns_count(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that count_uncontacted returns the correct count."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 12
        mock_session.execute.return_value = mock_result

        result = await repository.count_uncontacted()

        assert result == 12
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_count_uncontacted_returns_zero_when_none(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that count_uncontacted returns 0 when scalar is None."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.count_uncontacted()

        assert result == 0
