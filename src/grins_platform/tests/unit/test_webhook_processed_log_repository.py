"""Unit tests for :class:`WebhookProcessedLogRepository`.

Exercises the happy paths against a fully-mocked :class:`AsyncSession`.
Race-safety and prune-under-real-data are covered in the sibling
integration suite because they require a real Postgres backend.

Validates: Gap 07 — Webhook Security & Dedup (7.B)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.repositories.webhook_processed_log_repository import (
    WebhookProcessedLogRepository,
)


@pytest.mark.unit
class TestWebhookProcessedLogRepository:
    """Tests for :class:`WebhookProcessedLogRepository`."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock()
        return session

    @pytest.fixture
    def repository(
        self,
        mock_session: AsyncMock,
    ) -> WebhookProcessedLogRepository:
        """Create a repository bound to the mock session."""
        return WebhookProcessedLogRepository(mock_session)

    @pytest.mark.asyncio
    async def test_exists_with_no_row_returns_false(
        self,
        repository: WebhookProcessedLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``exists`` returns False when no matching row is found."""
        mock_session.scalar = AsyncMock(return_value=None)

        result = await repository.exists("callrail", "res_abc")

        assert result is False
        mock_session.scalar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exists_with_matching_row_returns_true(
        self,
        repository: WebhookProcessedLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``exists`` returns True when a row matches (provider, msg_id)."""
        mock_session.scalar = AsyncMock(return_value=uuid.uuid4())

        result = await repository.exists("callrail", "res_abc")

        assert result is True

    @pytest.mark.asyncio
    async def test_mark_processed_with_new_row_flushes_session(
        self,
        repository: WebhookProcessedLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``mark_processed`` executes the INSERT and flushes the session."""
        await repository.mark_processed("callrail", "res_new")

        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_prune_older_than_with_recent_cutoff_returns_rowcount(
        self,
        repository: WebhookProcessedLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``prune_older_than`` returns the DELETE rowcount (non-negative)."""
        exec_result = MagicMock()
        exec_result.rowcount = 5
        mock_session.execute = AsyncMock(return_value=exec_result)

        deleted = await repository.prune_older_than(days=30)

        assert deleted == 5
        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_prune_older_than_with_no_matching_rows_returns_zero(
        self,
        repository: WebhookProcessedLogRepository,
        mock_session: AsyncMock,
    ) -> None:
        """``prune_older_than`` coerces None rowcount to 0."""
        exec_result = MagicMock()
        exec_result.rowcount = None
        mock_session.execute = AsyncMock(return_value=exec_result)

        deleted = await repository.prune_older_than(days=30)

        assert deleted == 0
