"""Integration tests for the admin notifications API.

Covers:

- ``GET /api/v1/admin/notifications`` — admin-only list.
- ``GET /api/v1/admin/notifications/unread-count`` — admin-only count.
- ``POST /api/v1/admin/notifications/{id}/read`` — admin-only mark-read.

Auth dependencies (``get_current_active_user`` and ``require_admin``) are
overridden via :data:`app.dependency_overrides`; the database session
dependency is overridden to inject a mocked :class:`AsyncSession`.

Validates: Cluster H §5.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
    require_admin,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.main import app
from grins_platform.models.enums import StaffRole


@pytest.fixture
def admin_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "admin"
    user.email = "admin@grins.com"
    user.role = StaffRole.ADMIN.value
    user.is_active = True
    return user


@pytest.fixture
def manager_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "mgr"
    user.email = "mgr@grins.com"
    user.role = StaffRole.SALES.value  # "sales" maps to UserRole.MANAGER
    user.is_active = True
    return user


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _build_notification_mock(*, read_at: datetime | None = None) -> MagicMock:
    n = MagicMock()
    n.id = uuid.uuid4()
    n.event_type = "estimate_approved"
    n.subject_resource_type = "estimate"
    n.subject_resource_id = uuid.uuid4()
    n.summary = "Estimate APPROVED for ACME. Total $100."
    n.actor_user_id = None
    n.created_at = datetime.now(timezone.utc)
    n.read_at = read_at
    return n


@pytest.mark.integration
class TestAdminNotificationsList:
    @pytest.mark.asyncio
    async def test_admin_can_list(
        self,
        async_client: AsyncClient,
        admin_user: MagicMock,
    ) -> None:
        mock_db = MagicMock()
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user
        app.dependency_overrides[get_db_session] = lambda: mock_db

        rows = [_build_notification_mock(), _build_notification_mock()]
        fake_repo = MagicMock()
        fake_repo.list_recent = AsyncMock(return_value=rows)

        try:
            with patch(
                "grins_platform.api.v1.admin_notifications.AdminNotificationRepository",
                return_value=fake_repo,
            ):
                response = await async_client.get(
                    "/api/v1/admin/notifications",
                    headers={"Authorization": "Bearer test"},
                )
            assert response.status_code == 200
            body = response.json()
            assert body["total"] == 2
            assert len(body["items"]) == 2
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_manager_is_forbidden(
        self,
        async_client: AsyncClient,
        manager_user: MagicMock,
    ) -> None:
        """Manager role → 403; admin-only endpoint."""
        app.dependency_overrides[get_current_user] = lambda: manager_user
        app.dependency_overrides[get_current_active_user] = lambda: manager_user
        try:
            response = await async_client.get(
                "/api/v1/admin/notifications",
                headers={"Authorization": "Bearer test"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()


@pytest.mark.integration
class TestAdminNotificationsUnreadCount:
    @pytest.mark.asyncio
    async def test_admin_unread_count(
        self,
        async_client: AsyncClient,
        admin_user: MagicMock,
    ) -> None:
        mock_db = MagicMock()
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user
        app.dependency_overrides[get_db_session] = lambda: mock_db

        fake_repo = MagicMock()
        fake_repo.count_unread = AsyncMock(return_value=5)

        try:
            with patch(
                "grins_platform.api.v1.admin_notifications.AdminNotificationRepository",
                return_value=fake_repo,
            ):
                response = await async_client.get(
                    "/api/v1/admin/notifications/unread-count",
                    headers={"Authorization": "Bearer test"},
                )
            assert response.status_code == 200
            assert response.json() == {"unread": 5}
        finally:
            app.dependency_overrides.clear()


@pytest.mark.integration
class TestAdminNotificationsMarkRead:
    @pytest.mark.asyncio
    async def test_mark_read_success(
        self,
        async_client: AsyncClient,
        admin_user: MagicMock,
    ) -> None:
        mock_db = MagicMock()
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user
        app.dependency_overrides[get_db_session] = lambda: mock_db

        row = _build_notification_mock(read_at=datetime.now(timezone.utc))
        fake_repo = MagicMock()
        fake_repo.mark_read = AsyncMock(return_value=row)

        try:
            with patch(
                "grins_platform.api.v1.admin_notifications.AdminNotificationRepository",
                return_value=fake_repo,
            ):
                response = await async_client.post(
                    f"/api/v1/admin/notifications/{row.id}/read",
                    headers={"Authorization": "Bearer test"},
                )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mark_read_404_when_already_read_or_missing(
        self,
        async_client: AsyncClient,
        admin_user: MagicMock,
    ) -> None:
        mock_db = MagicMock()
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user
        app.dependency_overrides[get_db_session] = lambda: mock_db

        fake_repo = MagicMock()
        fake_repo.mark_read = AsyncMock(return_value=None)

        try:
            with patch(
                "grins_platform.api.v1.admin_notifications.AdminNotificationRepository",
                return_value=fake_repo,
            ):
                response = await async_client.post(
                    f"/api/v1/admin/notifications/{uuid.uuid4()}/read",
                    headers={"Authorization": "Bearer test"},
                )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
