"""Unit tests for :class:`AdminNotificationService`.

Verifies the fire-and-forget contract: the service swallows all
exceptions from the repository so admin-notification writes never block
the originating customer action.

Validates: Cluster H §5.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AdminNotificationEventType
from grins_platform.services.admin_notification_service import (
    AdminNotificationService,
)


class TestAdminNotificationServiceRecord:
    """``record()`` happy path + swallow-on-failure semantics."""

    @pytest.mark.asyncio
    async def test_record_calls_repository_create_with_correct_row(
        self,
    ) -> None:
        """Happy path: a single repo.create() call with the row shape."""
        mock_db = MagicMock()
        subject_id = uuid4()
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock()

        with patch(
            "grins_platform.services.admin_notification_service."
            "AdminNotificationRepository",
            return_value=mock_repo,
        ) as mock_repo_cls:
            service = AdminNotificationService()
            await service.record(
                event_type=AdminNotificationEventType.ESTIMATE_APPROVED,
                subject_resource_type="estimate",
                subject_resource_id=subject_id,
                summary="Estimate APPROVED for John Smith. Total $500.00.",
                actor_user_id=None,
                db=mock_db,
            )

        mock_repo_cls.assert_called_once_with(mock_db)
        mock_repo.create.assert_awaited_once()
        created = mock_repo.create.await_args.args[0]
        assert created.event_type == "estimate_approved"
        assert created.subject_resource_type == "estimate"
        assert created.subject_resource_id == subject_id
        assert created.actor_user_id is None
        assert "APPROVED" in created.summary

    @pytest.mark.asyncio
    async def test_record_swallows_repository_exception(self) -> None:
        """If repo.create raises, record returns None without re-raising."""
        mock_db = MagicMock()
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(side_effect=RuntimeError("DB exploded"))

        with patch(
            "grins_platform.services.admin_notification_service."
            "AdminNotificationRepository",
            return_value=mock_repo,
        ):
            service = AdminNotificationService()
            # Should NOT raise.
            result = await service.record(
                event_type=AdminNotificationEventType.APPOINTMENT_CANCELLED,
                subject_resource_type="appointment",
                subject_resource_id=uuid4(),
                summary="Appointment cancelled",
                actor_user_id=None,
                db=mock_db,
            )
        assert result is None
        mock_repo.create.assert_awaited_once()
