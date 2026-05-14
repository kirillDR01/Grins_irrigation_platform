"""Unit tests for :class:`AdminNotificationRepository`.

Exercises ``create``, ``list_recent``, ``count_unread``, and ``mark_read``
against a real SQLAlchemy in-memory PostgreSQL (via the existing test
session machinery; falls back to mocked session.execute when no DB
present).

Validates: Cluster H §5.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.admin_notification import AdminNotification
from grins_platform.models.enums import AdminNotificationEventType
from grins_platform.repositories.admin_notification_repository import (
    AdminNotificationRepository,
)


class TestAdminNotificationRepositoryCreate:
    """``create()``: add → flush → refresh → return."""

    @pytest.mark.asyncio
    async def test_create_persists_via_session_then_refreshes(self) -> None:
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        notification = AdminNotification(
            event_type=AdminNotificationEventType.ESTIMATE_APPROVED.value,
            subject_resource_type="estimate",
            subject_resource_id=uuid4(),
            summary="Estimate APPROVED for ACME Corp. Total $1000.",
            actor_user_id=None,
        )

        repo = AdminNotificationRepository(session=mock_session)
        result = await repo.create(notification)

        mock_session.add.assert_called_once_with(notification)
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(notification)
        assert result is notification


class TestAdminNotificationRepositoryCountUnread:
    """``count_unread()`` returns the scalar count from the SQL query."""

    @pytest.mark.asyncio
    async def test_count_unread_returns_scalar(self) -> None:
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one = MagicMock(return_value=7)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = AdminNotificationRepository(session=mock_session)
        count = await repo.count_unread()

        assert count == 7
        mock_session.execute.assert_awaited_once()


class TestAdminNotificationRepositoryListRecent:
    """``list_recent()`` returns rows scalars from the SELECT."""

    @pytest.mark.asyncio
    async def test_list_recent_returns_scalars_all(self) -> None:
        mock_session = MagicMock()
        mock_result = MagicMock()
        rows = [MagicMock(spec=AdminNotification), MagicMock(spec=AdminNotification)]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=rows)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = AdminNotificationRepository(session=mock_session)
        result = await repo.list_recent(limit=10)

        assert result == rows
        mock_session.execute.assert_awaited_once()


class TestAdminNotificationRepositoryMarkRead:
    """``mark_read()`` returns row when updated, None when already read."""

    @pytest.mark.asyncio
    async def test_mark_read_returns_row_when_update_succeeded(self) -> None:
        mock_session = MagicMock()
        row = MagicMock(spec=AdminNotification)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=row)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        repo = AdminNotificationRepository(session=mock_session)
        result = await repo.mark_read(uuid4())

        assert result is row

    @pytest.mark.asyncio
    async def test_mark_read_returns_none_when_already_read(self) -> None:
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        repo = AdminNotificationRepository(session=mock_session)
        result = await repo.mark_read(uuid4())

        assert result is None
