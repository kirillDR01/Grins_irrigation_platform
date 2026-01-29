"""
Schedule Clear API endpoint tests.

Tests for clear schedule, recent clears, and audit details endpoints.

Validates: Requirements 3.1-3.7, 5.1-5.6, 6.1-6.5, 17.5-17.6
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import require_manager_or_admin
from grins_platform.api.v1.schedule_clear import get_schedule_clear_service
from grins_platform.exceptions import ScheduleClearAuditNotFoundError
from grins_platform.main import app
from grins_platform.models.enums import UserRole
from grins_platform.schemas.schedule_clear import (
    ScheduleClearAuditDetailResponse,
    ScheduleClearAuditResponse,
    ScheduleClearResponse,
)

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_manager_user() -> MagicMock:
    """Create a mock manager user for testing."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "manager"
    user.name = "Manager User"
    user.email = "manager@example.com"
    user.role = UserRole.MANAGER.value
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user() -> MagicMock:
    """Create a mock admin user for testing."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "admin"
    user.name = "Admin User"
    user.email = "admin@example.com"
    user.role = UserRole.ADMIN.value
    user.is_active = True
    return user


@pytest.fixture
def mock_schedule_clear_service() -> MagicMock:
    """Create a mock ScheduleClearService."""
    service = MagicMock()
    service.clear_schedule = AsyncMock()
    service.get_recent_clears = AsyncMock()
    service.get_clear_details = AsyncMock()
    return service


@pytest.fixture
def override_schedule_clear_service(
    mock_schedule_clear_service: MagicMock,
) -> Callable[[], MagicMock]:
    """Create an async override function for schedule clear service."""

    async def _override() -> MagicMock:
        return mock_schedule_clear_service

    return _override  # type: ignore[return-value]


@pytest.fixture
def override_manager_or_admin(
    mock_manager_user: MagicMock,
) -> Callable[[], MagicMock]:
    """Create an async override function for require_manager_or_admin."""

    async def _override() -> MagicMock:
        return mock_manager_user

    return _override  # type: ignore[return-value]


@pytest.fixture
def override_admin_user(
    mock_admin_user: MagicMock,
) -> Callable[[], MagicMock]:
    """Create an async override function for require_manager_or_admin (admin)."""

    async def _override() -> MagicMock:
        return mock_admin_user

    return _override  # type: ignore[return-value]


# =============================================================================
# Clear Schedule Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestClearScheduleEndpoint:
    """Tests for POST /api/v1/schedule/clear endpoint."""

    @pytest.mark.asyncio
    async def test_clear_schedule_success_as_manager(
        self,
        mock_schedule_clear_service: MagicMock,
        override_schedule_clear_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test successful schedule clear as manager."""
        audit_id = uuid.uuid4()
        schedule_date = date.today()
        cleared_at = datetime.now(timezone.utc)

        mock_response = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=schedule_date,
            appointments_deleted=5,
            jobs_reset=3,
            cleared_at=cleared_at,
        )
        mock_schedule_clear_service.clear_schedule.return_value = mock_response

        app.dependency_overrides[get_schedule_clear_service] = (
            override_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/schedule/clear",
                    json={
                        "schedule_date": str(schedule_date),
                        "notes": "Test clear",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert data["audit_id"] == str(audit_id)
            assert data["appointments_deleted"] == 5
            assert data["jobs_reset"] == 3
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clear_schedule_success_as_admin(
        self,
        mock_schedule_clear_service: MagicMock,
        override_schedule_clear_service: Callable[[], MagicMock],
        override_admin_user: Callable[[], MagicMock],
    ) -> None:
        """Test successful schedule clear as admin."""
        audit_id = uuid.uuid4()
        schedule_date = date.today()
        cleared_at = datetime.now(timezone.utc)

        mock_response = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=schedule_date,
            appointments_deleted=2,
            jobs_reset=1,
            cleared_at=cleared_at,
        )
        mock_schedule_clear_service.clear_schedule.return_value = mock_response

        app.dependency_overrides[get_schedule_clear_service] = (
            override_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = override_admin_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/schedule/clear",
                    json={"schedule_date": str(schedule_date)},
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clear_schedule_unauthorized_no_auth(self) -> None:
        """Test schedule clear denied without authentication."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": str(date.today())},
            )

        # Without auth, should get 401 or 403
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_clear_schedule_invalid_date(
        self,
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test schedule clear with invalid date format."""
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/schedule/clear",
                    json={"schedule_date": "invalid-date"},
                )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clear_schedule_with_notes(
        self,
        mock_schedule_clear_service: MagicMock,
        override_schedule_clear_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test schedule clear with notes."""
        audit_id = uuid.uuid4()
        schedule_date = date.today()
        cleared_at = datetime.now(timezone.utc)

        mock_response = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=schedule_date,
            appointments_deleted=3,
            jobs_reset=2,
            cleared_at=cleared_at,
        )
        mock_schedule_clear_service.clear_schedule.return_value = mock_response

        app.dependency_overrides[get_schedule_clear_service] = (
            override_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/schedule/clear",
                    json={
                        "schedule_date": str(schedule_date),
                        "notes": "Weather cancellation",
                    },
                )

            assert response.status_code == 200
            # Verify service was called with notes
            mock_schedule_clear_service.clear_schedule.assert_called_once()
            call_kwargs = mock_schedule_clear_service.clear_schedule.call_args.kwargs
            assert call_kwargs["notes"] == "Weather cancellation"
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Recent Clears Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestRecentClearsEndpoint:
    """Tests for GET /api/v1/schedule/clear/recent endpoint."""

    @pytest.mark.asyncio
    async def test_get_recent_clears_success(
        self,
        mock_schedule_clear_service: MagicMock,
        override_schedule_clear_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test successful retrieval of recent clears."""
        audit_id = uuid.uuid4()
        cleared_by = uuid.uuid4()
        schedule_date = date.today()
        cleared_at = datetime.now(timezone.utc)

        mock_audit = ScheduleClearAuditResponse(
            id=audit_id,
            schedule_date=schedule_date,
            appointment_count=5,
            cleared_at=cleared_at,
            cleared_by=cleared_by,
            notes="Test clear",
        )
        mock_schedule_clear_service.get_recent_clears.return_value = [mock_audit]

        app.dependency_overrides[get_schedule_clear_service] = (
            override_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/schedule/clear/recent")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["appointment_count"] == 5
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_recent_clears_empty(
        self,
        mock_schedule_clear_service: MagicMock,
        override_schedule_clear_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test retrieval of recent clears when none exist."""
        mock_schedule_clear_service.get_recent_clears.return_value = []

        app.dependency_overrides[get_schedule_clear_service] = (
            override_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/schedule/clear/recent")

            assert response.status_code == 200
            data = response.json()
            assert data == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_recent_clears_custom_hours(
        self,
        mock_schedule_clear_service: MagicMock,
        override_schedule_clear_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test retrieval of recent clears with custom hours parameter."""
        mock_schedule_clear_service.get_recent_clears.return_value = []

        app.dependency_overrides[get_schedule_clear_service] = (
            override_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/schedule/clear/recent",
                    params={"hours": 48},
                )

            assert response.status_code == 200
            mock_schedule_clear_service.get_recent_clears.assert_called_once_with(
                hours=48,
            )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_recent_clears_unauthorized_no_auth(self) -> None:
        """Test recent clears denied without authentication."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/schedule/clear/recent")

        # Without auth, should get 401 or 403
        assert response.status_code in (401, 403)


# =============================================================================
# Clear Details Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestClearDetailsEndpoint:
    """Tests for GET /api/v1/schedule/clear/{audit_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_clear_details_success(
        self,
        mock_schedule_clear_service: MagicMock,
        override_schedule_clear_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test successful retrieval of clear details."""
        audit_id = uuid.uuid4()
        cleared_by = uuid.uuid4()
        schedule_date = date.today()
        cleared_at = datetime.now(timezone.utc)
        job_id_1 = uuid.uuid4()
        job_id_2 = uuid.uuid4()

        mock_audit = ScheduleClearAuditDetailResponse(
            id=audit_id,
            schedule_date=schedule_date,
            appointment_count=5,
            cleared_at=cleared_at,
            cleared_by=cleared_by,
            notes="Test clear",
            appointments_data=[
                {
                    "id": str(uuid.uuid4()),
                    "job_id": str(uuid.uuid4()),
                    "staff_id": str(uuid.uuid4()),
                    "scheduled_date": str(schedule_date),
                    "time_window_start": "08:00:00",
                    "time_window_end": "10:00:00",
                    "status": "scheduled",
                    "notes": None,
                    "route_order": 1,
                    "estimated_arrival": None,
                },
            ],
            jobs_reset=[job_id_1, job_id_2],
        )
        mock_schedule_clear_service.get_clear_details.return_value = mock_audit

        app.dependency_overrides[get_schedule_clear_service] = (
            override_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get(f"/api/v1/schedule/clear/{audit_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(audit_id)
            assert "appointments_data" in data
            assert "jobs_reset" in data
            assert len(data["jobs_reset"]) == 2
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_clear_details_not_found(
        self,
        mock_schedule_clear_service: MagicMock,
        override_schedule_clear_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test retrieval of non-existent clear details returns 404."""
        audit_id = uuid.uuid4()
        mock_schedule_clear_service.get_clear_details.side_effect = (
            ScheduleClearAuditNotFoundError(audit_id)
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            override_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get(f"/api/v1/schedule/clear/{audit_id}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_clear_details_invalid_uuid(
        self,
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test retrieval with invalid UUID returns 422."""
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/schedule/clear/invalid-uuid")

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_clear_details_unauthorized_no_auth(self) -> None:
        """Test clear details denied without authentication."""
        audit_id = uuid.uuid4()
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(f"/api/v1/schedule/clear/{audit_id}")

        # Without auth, should get 401 or 403
        assert response.status_code in (401, 403)


__all__ = [
    "TestClearDetailsEndpoint",
    "TestClearScheduleEndpoint",
    "TestRecentClearsEndpoint",
]
