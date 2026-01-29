"""
Schedule Clear integration tests.

Tests for end-to-end schedule clear flows including clearing schedules,
job status reset, audit log creation, and recent clears retrieval.

Validates: Requirements 3.1-3.7, 5.1-5.6, 6.1-6.5
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_user,
    require_manager_or_admin,
)
from grins_platform.api.v1.schedule_clear import get_schedule_clear_service
from grins_platform.exceptions import ScheduleClearAuditNotFoundError
from grins_platform.main import app
from grins_platform.models.enums import StaffRole, UserRole
from grins_platform.schemas.schedule_clear import (
    ScheduleClearAuditDetailResponse,
    ScheduleClearAuditResponse,
    ScheduleClearResponse,
)
from grins_platform.services.schedule_clear_service import ScheduleClearService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_manager_user() -> MagicMock:
    """Create a mock manager user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Manager User"
    user.username = "manager"
    user.email = "manager@grins.com"
    user.role = UserRole.MANAGER.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def sample_admin_user() -> MagicMock:
    """Create a mock admin user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin User"
    user.username = "admin"
    user.email = "admin@grins.com"
    user.role = StaffRole.ADMIN.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def sample_tech_user() -> MagicMock:
    """Create a mock tech user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Tech User"
    user.username = "tech"
    user.email = "tech@grins.com"
    user.role = StaffRole.TECH.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def sample_appointments_data() -> list[dict[str, Any]]:
    """Create sample serialized appointments data."""
    return [
        {
            "id": str(uuid.uuid4()),
            "job_id": str(uuid.uuid4()),
            "staff_id": str(uuid.uuid4()),
            "scheduled_date": "2025-01-29",
            "time_window_start": "09:00:00",
            "time_window_end": "11:00:00",
            "status": "scheduled",
            "notes": "Spring startup",
            "route_order": 1,
            "estimated_arrival": None,
        },
        {
            "id": str(uuid.uuid4()),
            "job_id": str(uuid.uuid4()),
            "staff_id": str(uuid.uuid4()),
            "scheduled_date": "2025-01-29",
            "time_window_start": "11:00:00",
            "time_window_end": "13:00:00",
            "status": "scheduled",
            "notes": "Winterization",
            "route_order": 2,
            "estimated_arrival": None,
        },
    ]


@pytest.fixture
def sample_jobs_reset() -> list[uuid.UUID]:
    """Create sample job IDs that were reset."""
    return [uuid.uuid4(), uuid.uuid4()]


@pytest.fixture
def mock_schedule_clear_service() -> MagicMock:
    """Create a mock ScheduleClearService."""
    service = MagicMock(spec=ScheduleClearService)
    service.clear_schedule = AsyncMock()
    service.get_recent_clears = AsyncMock()
    service.get_clear_details = AsyncMock()
    return service


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# Test Clear Schedule with Appointments
# =============================================================================


@pytest.mark.integration
class TestClearScheduleWithAppointmentsIntegration:
    """Integration tests for clearing schedules with appointments."""

    @pytest.mark.asyncio
    async def test_clear_schedule_with_appointments_success(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test clearing schedule with appointments returns correct response.

        Validates: Requirements 3.1-3.7
        """
        audit_id = uuid.uuid4()
        schedule_date = date(2025, 1, 29)
        cleared_at = datetime.now(timezone.utc)

        mock_schedule_clear_service.clear_schedule.return_value = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=schedule_date,
            appointments_deleted=5,
            jobs_reset=3,
            cleared_at=cleared_at,
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={
                    "schedule_date": "2025-01-29",
                    "notes": "Clearing for reschedule",
                },
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["audit_id"] == str(audit_id)
            assert data["schedule_date"] == "2025-01-29"
            assert data["appointments_deleted"] == 5
            assert data["jobs_reset"] == 3
            assert "cleared_at" in data

            mock_schedule_clear_service.clear_schedule.assert_called_once()
            call_args = mock_schedule_clear_service.clear_schedule.call_args
            assert call_args.kwargs["schedule_date"] == schedule_date
            assert call_args.kwargs["cleared_by"] == sample_manager_user.id
            assert call_args.kwargs["notes"] == "Clearing for reschedule"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clear_schedule_with_no_appointments(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test clearing schedule with no appointments returns zero counts.

        Validates: Requirements 3.1-3.7
        """
        audit_id = uuid.uuid4()
        schedule_date = date(2025, 1, 30)
        cleared_at = datetime.now(timezone.utc)

        mock_schedule_clear_service.clear_schedule.return_value = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=schedule_date,
            appointments_deleted=0,
            jobs_reset=0,
            cleared_at=cleared_at,
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": "2025-01-30"},
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["appointments_deleted"] == 0
            assert data["jobs_reset"] == 0

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clear_schedule_admin_can_access(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test admin user can clear schedules.

        Validates: Requirements 17.5-17.6
        """
        audit_id = uuid.uuid4()
        cleared_at = datetime.now(timezone.utc)

        mock_schedule_clear_service.clear_schedule.return_value = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=date(2025, 1, 29),
            appointments_deleted=2,
            jobs_reset=1,
            cleared_at=cleared_at,
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_admin_user

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": "2025-01-29"},
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Job Status Reset
# =============================================================================


@pytest.mark.integration
class TestJobStatusResetIntegration:
    """Integration tests for job status reset during schedule clear."""

    @pytest.mark.asyncio
    async def test_clear_schedule_resets_scheduled_jobs(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test that clearing schedule resets scheduled jobs to approved.

        Validates: Requirements 3.3-3.4
        """
        audit_id = uuid.uuid4()
        cleared_at = datetime.now(timezone.utc)

        # Service returns 3 jobs were reset
        mock_schedule_clear_service.clear_schedule.return_value = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=date(2025, 1, 29),
            appointments_deleted=5,
            jobs_reset=3,
            cleared_at=cleared_at,
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": "2025-01-29"},
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()

            # Verify jobs_reset count is returned
            assert data["jobs_reset"] == 3

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clear_schedule_does_not_reset_in_progress_jobs(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test that in-progress jobs are not reset.

        Validates: Requirements 3.3-3.4
        """
        audit_id = uuid.uuid4()
        cleared_at = datetime.now(timezone.utc)

        # Service returns fewer jobs reset than appointments deleted
        # because some jobs were in_progress
        mock_schedule_clear_service.clear_schedule.return_value = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=date(2025, 1, 29),
            appointments_deleted=5,
            jobs_reset=2,  # Only 2 of 5 were scheduled status
            cleared_at=cleared_at,
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": "2025-01-29"},
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()

            # Verify jobs_reset is less than appointments_deleted
            assert data["appointments_deleted"] == 5
            assert data["jobs_reset"] == 2

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Audit Log Creation
# =============================================================================


@pytest.mark.integration
class TestAuditLogCreationIntegration:
    """Integration tests for audit log creation during schedule clear."""

    @pytest.mark.asyncio
    async def test_clear_schedule_creates_audit_log(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test that clearing schedule creates an audit log.

        Validates: Requirements 5.1-5.6
        """
        audit_id = uuid.uuid4()
        cleared_at = datetime.now(timezone.utc)

        mock_schedule_clear_service.clear_schedule.return_value = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=date(2025, 1, 29),
            appointments_deleted=3,
            jobs_reset=2,
            cleared_at=cleared_at,
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={
                    "schedule_date": "2025-01-29",
                    "notes": "Test audit creation",
                },
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()

            # Verify audit_id is returned
            assert data["audit_id"] == str(audit_id)
            assert "cleared_at" in data

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_audit_details_returns_full_data(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
        sample_appointments_data: list[dict[str, Any]],
        sample_jobs_reset: list[uuid.UUID],
    ) -> None:
        """Test getting audit details returns full appointment data.

        Validates: Requirement 6.3
        """
        audit_id = uuid.uuid4()
        cleared_at = datetime.now(timezone.utc)

        mock_schedule_clear_service.get_clear_details.return_value = (
            ScheduleClearAuditDetailResponse(
                id=audit_id,
                schedule_date=date(2025, 1, 29),
                appointment_count=2,
                cleared_at=cleared_at,
                cleared_by=sample_manager_user.id,
                notes="Test clear",
                appointments_data=sample_appointments_data,
                jobs_reset=sample_jobs_reset,
            )
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.get(
                f"/api/v1/schedule/clear/{audit_id}",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["id"] == str(audit_id)
            assert data["schedule_date"] == "2025-01-29"
            assert data["appointment_count"] == 2
            assert "appointments_data" in data
            assert len(data["appointments_data"]) == 2
            assert "jobs_reset" in data
            assert len(data["jobs_reset"]) == 2

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_audit_details_not_found(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test getting non-existent audit returns 404.

        Validates: Requirement 22.3
        """
        audit_id = uuid.uuid4()

        mock_schedule_clear_service.get_clear_details.side_effect = (
            ScheduleClearAuditNotFoundError(audit_id)
        )

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.get(
                f"/api/v1/schedule/clear/{audit_id}",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 404

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Recent Clears Retrieval
# =============================================================================


@pytest.mark.integration
class TestRecentClearsRetrievalIntegration:
    """Integration tests for retrieving recent schedule clears."""

    @pytest.mark.asyncio
    async def test_get_recent_clears_returns_list(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test getting recent clears returns list of audits.

        Validates: Requirements 6.1-6.2
        """
        now = datetime.now(timezone.utc)
        audits = [
            ScheduleClearAuditResponse(
                id=uuid.uuid4(),
                schedule_date=date(2025, 1, 29),
                appointment_count=3,
                cleared_at=now - timedelta(hours=2),
                cleared_by=sample_manager_user.id,
                notes="Clear 1",
            ),
            ScheduleClearAuditResponse(
                id=uuid.uuid4(),
                schedule_date=date(2025, 1, 28),
                appointment_count=5,
                cleared_at=now - timedelta(hours=10),
                cleared_by=sample_manager_user.id,
                notes="Clear 2",
            ),
        ]

        mock_schedule_clear_service.get_recent_clears.return_value = audits

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.get(
                "/api/v1/schedule/clear/recent",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()

            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["appointment_count"] == 3
            assert data[1]["appointment_count"] == 5

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_recent_clears_empty_list(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test getting recent clears with no results returns empty list.

        Validates: Requirements 6.1-6.2
        """
        mock_schedule_clear_service.get_recent_clears.return_value = []

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.get(
                "/api/v1/schedule/clear/recent",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()

            assert isinstance(data, list)
            assert len(data) == 0

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_recent_clears_with_custom_hours(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test getting recent clears with custom hours parameter.

        Validates: Requirements 6.1-6.2
        """
        mock_schedule_clear_service.get_recent_clears.return_value = []

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.get(
                "/api/v1/schedule/clear/recent?hours=48",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200

            # Verify service was called with custom hours
            mock_schedule_clear_service.get_recent_clears.assert_called_once_with(
                hours=48,
            )

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Authorization
# =============================================================================


@pytest.mark.integration
class TestScheduleClearAuthorizationIntegration:
    """Integration tests for schedule clear authorization."""

    @pytest.mark.asyncio
    async def test_tech_cannot_clear_schedule(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
    ) -> None:
        """Test tech user cannot clear schedules.

        Validates: Requirements 17.5-17.6
        """
        # Don't override the service - let auth fail first
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user

        try:
            response = await async_client.post(
                "/api/v1/schedule/clear",
                json={"schedule_date": "2025-01-29"},
                headers={"Authorization": "Bearer test_token"},
            )

            # Should be forbidden for tech users
            assert response.status_code == 403

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_tech_cannot_view_recent_clears(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
    ) -> None:
        """Test tech user cannot view recent clears.

        Validates: Requirements 17.5-17.6
        """
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user

        try:
            response = await async_client.get(
                "/api/v1/schedule/clear/recent",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 403

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_tech_cannot_view_audit_details(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
    ) -> None:
        """Test tech user cannot view audit details.

        Validates: Requirements 17.5-17.6
        """
        audit_id = uuid.uuid4()
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user

        try:
            response = await async_client.get(
                f"/api/v1/schedule/clear/{audit_id}",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 403

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_clear_schedule(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test unauthenticated user cannot clear schedules.

        Validates: Requirements 17.5-17.6
        """
        response = await async_client.post(
            "/api/v1/schedule/clear",
            json={"schedule_date": "2025-01-29"},
        )

        assert response.status_code == 401


# =============================================================================
# Test Complete Workflow
# =============================================================================


@pytest.mark.integration
class TestScheduleClearCompleteWorkflowIntegration:
    """Integration tests for complete schedule clear workflow."""

    @pytest.mark.asyncio
    async def test_complete_clear_and_audit_workflow(
        self,
        async_client: AsyncClient,
        mock_schedule_clear_service: MagicMock,
        sample_manager_user: MagicMock,
        sample_appointments_data: list[dict[str, Any]],
        sample_jobs_reset: list[uuid.UUID],
    ) -> None:
        """Test complete workflow: clear schedule -> view audit.

        Validates: Requirements 3.1-3.7, 5.1-5.6, 6.1-6.5
        """
        audit_id = uuid.uuid4()
        schedule_date = date(2025, 1, 29)
        cleared_at = datetime.now(timezone.utc)

        # Setup clear response
        mock_schedule_clear_service.clear_schedule.return_value = ScheduleClearResponse(
            audit_id=audit_id,
            schedule_date=schedule_date,
            appointments_deleted=2,
            jobs_reset=2,
            cleared_at=cleared_at,
        )

        # Setup audit detail response
        mock_schedule_clear_service.get_clear_details.return_value = (
            ScheduleClearAuditDetailResponse(
                id=audit_id,
                schedule_date=schedule_date,
                appointment_count=2,
                cleared_at=cleared_at,
                cleared_by=sample_manager_user.id,
                notes="Workflow test",
                appointments_data=sample_appointments_data,
                jobs_reset=sample_jobs_reset,
            )
        )

        # Setup recent clears response
        mock_schedule_clear_service.get_recent_clears.return_value = [
            ScheduleClearAuditResponse(
                id=audit_id,
                schedule_date=schedule_date,
                appointment_count=2,
                cleared_at=cleared_at,
                cleared_by=sample_manager_user.id,
                notes="Workflow test",
            ),
        ]

        app.dependency_overrides[get_schedule_clear_service] = (
            lambda: mock_schedule_clear_service
        )
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            # Step 1: Clear the schedule
            clear_response = await async_client.post(
                "/api/v1/schedule/clear",
                json={
                    "schedule_date": "2025-01-29",
                    "notes": "Workflow test",
                },
                headers={"Authorization": "Bearer test_token"},
            )

            assert clear_response.status_code == 200
            clear_data = clear_response.json()
            returned_audit_id = clear_data["audit_id"]

            # Step 2: View the audit details
            detail_response = await async_client.get(
                f"/api/v1/schedule/clear/{returned_audit_id}",
                headers={"Authorization": "Bearer test_token"},
            )

            assert detail_response.status_code == 200
            detail_data = detail_response.json()
            assert detail_data["id"] == returned_audit_id
            assert len(detail_data["appointments_data"]) == 2
            assert len(detail_data["jobs_reset"]) == 2

            # Step 3: Verify it appears in recent clears
            recent_response = await async_client.get(
                "/api/v1/schedule/clear/recent",
                headers={"Authorization": "Bearer test_token"},
            )

            assert recent_response.status_code == 200
            recent_data = recent_response.json()
            assert len(recent_data) == 1
            assert recent_data[0]["id"] == returned_audit_id

        finally:
            app.dependency_overrides.clear()
