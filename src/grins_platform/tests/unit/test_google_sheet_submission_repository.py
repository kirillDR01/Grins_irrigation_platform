"""Unit tests for GoogleSheetSubmissionRepository.

Tests all CRUD methods with mocked AsyncSession,
following the same patterns as test_lead_repository.py.

Validates: Requirements 2.1, 2.2, 5.1, 12.1, 12.4
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.google_sheet_submission import GoogleSheetSubmission
from grins_platform.repositories.google_sheet_submission_repository import (
    GoogleSheetSubmissionRepository,
)
from grins_platform.schemas.google_sheet_submission import SubmissionListParams

# =============================================================================
# Create method tests
# =============================================================================


@pytest.mark.unit
class TestGoogleSheetSubmissionRepositoryCreate:
    """Tests for GoogleSheetSubmissionRepository.create method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> GoogleSheetSubmissionRepository:
        return GoogleSheetSubmissionRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_calls_session_add_flush_refresh(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        result = await repository.create(
            sheet_row_number=2,
            name="Jane Smith",
            phone="6125559876",
            client_type="new",
        )

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert isinstance(added, GoogleSheetSubmission)
        assert added.sheet_row_number == 2
        assert added.name == "Jane Smith"
        assert added.phone == "6125559876"
        assert added.client_type == "new"
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()
        assert result == added


# =============================================================================
# Get by ID tests
# =============================================================================


@pytest.mark.unit
class TestGoogleSheetSubmissionRepositoryGetById:
    """Tests for GoogleSheetSubmissionRepository.get_by_id method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> GoogleSheetSubmissionRepository:
        return GoogleSheetSubmissionRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        sub_id = uuid4()
        mock_sub = MagicMock(spec=GoogleSheetSubmission)
        mock_sub.id = sub_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_sub
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(sub_id)

        assert result == mock_sub
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(uuid4())

        assert result is None


# =============================================================================
# Get max row number tests
# =============================================================================


@pytest.mark.unit
class TestGoogleSheetSubmissionRepositoryGetMaxRowNumber:
    """Tests for GoogleSheetSubmissionRepository.get_max_row_number method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> GoogleSheetSubmissionRepository:
        return GoogleSheetSubmissionRepository(mock_session)

    @pytest.mark.asyncio
    async def test_returns_max_row(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result

        result = await repository.get_max_row_number()

        assert result == 42

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_rows(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await repository.get_max_row_number()

        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_scalar_is_none(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_max_row_number()

        assert result == 0


# =============================================================================
# List with filters tests
# =============================================================================


@pytest.mark.unit
class TestGoogleSheetSubmissionRepositoryListWithFilters:
    """Tests for GoogleSheetSubmissionRepository.list_with_filters method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> GoogleSheetSubmissionRepository:
        return GoogleSheetSubmissionRepository(mock_session)

    def _setup_list_mocks(
        self,
        mock_session: AsyncMock,
        items: list[MagicMock],
        total: int,
    ) -> None:
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = total

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = items
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

    @pytest.mark.asyncio
    async def test_list_with_no_filters(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        sub1 = MagicMock(spec=GoogleSheetSubmission)
        sub2 = MagicMock(spec=GoogleSheetSubmission)
        self._setup_list_mocks(mock_session, [sub1, sub2], 2)

        items, total = await repository.list_with_filters(SubmissionListParams())

        assert len(items) == 2
        assert total == 2
        assert mock_session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_list_with_processing_status_filter(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        sub = MagicMock(spec=GoogleSheetSubmission)
        self._setup_list_mocks(mock_session, [sub], 1)

        params = SubmissionListParams(processing_status="imported")
        items, total = await repository.list_with_filters(params)

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_with_client_type_filter(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        self._setup_list_mocks(mock_session, [], 0)

        params = SubmissionListParams(client_type="new")
        items, total = await repository.list_with_filters(params)

        assert len(items) == 0
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_search_filter(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        sub = MagicMock(spec=GoogleSheetSubmission)
        self._setup_list_mocks(mock_session, [sub], 1)

        params = SubmissionListParams(search="Jane")
        items, total = await repository.list_with_filters(params)

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_pagination(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        sub = MagicMock(spec=GoogleSheetSubmission)
        self._setup_list_mocks(mock_session, [sub], 50)

        params = SubmissionListParams(page=3, page_size=10)
        _items, total = await repository.list_with_filters(params)

        assert total == 50
        assert mock_session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_list_sorting_asc(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        self._setup_list_mocks(mock_session, [], 0)

        params = SubmissionListParams(sort_by="name", sort_order="asc")
        await repository.list_with_filters(params)

        mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_list_sorting_desc(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        self._setup_list_mocks(mock_session, [], 0)

        params = SubmissionListParams(sort_by="imported_at", sort_order="desc")
        await repository.list_with_filters(params)

        mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_list_with_all_filters_combined(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        self._setup_list_mocks(mock_session, [], 0)

        params = SubmissionListParams(
            processing_status="lead_created",
            client_type="existing",
            search="Smith",
            page=2,
            page_size=5,
            sort_by="name",
            sort_order="asc",
        )
        items, total = await repository.list_with_filters(params)

        assert len(items) == 0
        assert total == 0


# =============================================================================
# Update method tests
# =============================================================================


@pytest.mark.unit
class TestGoogleSheetSubmissionRepositoryUpdate:
    """Tests for GoogleSheetSubmissionRepository.update method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> GoogleSheetSubmissionRepository:
        return GoogleSheetSubmissionRepository(mock_session)

    @pytest.mark.asyncio
    async def test_update_found(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        sub_id = uuid4()
        mock_sub = MagicMock(spec=GoogleSheetSubmission)
        mock_sub.id = sub_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_sub
        mock_session.execute.return_value = mock_result

        result = await repository.update(
            sub_id,
            {"processing_status": "lead_created"},
        )

        assert result == mock_sub
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repository: GoogleSheetSubmissionRepository,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.update(
            uuid4(),
            {"processing_status": "error"},
        )

        assert result is None
        mock_session.flush.assert_awaited_once()
