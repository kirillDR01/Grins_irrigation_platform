"""
Authentication integration tests.

Tests for end-to-end authentication flows including login, token refresh,
protected route access, and role-based access control.

Validates: Requirements 14.1-14.8, 17.1-17.12, 20.1-20.6
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import get_auth_service, get_current_user
from grins_platform.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from grins_platform.main import app
from grins_platform.models.enums import StaffRole, UserRole
from grins_platform.services.auth_service import AuthService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_admin_user() -> MagicMock:
    """Create a mock admin user with authentication enabled."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Admin User"
    staff.phone = "6125550001"
    staff.email = "admin@grins.com"
    staff.role = StaffRole.ADMIN.value
    staff.username = "admin"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_manager_user() -> MagicMock:
    """Create a mock manager user with authentication enabled."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Manager User"
    staff.phone = "6125550002"
    staff.email = "manager@grins.com"
    staff.role = UserRole.MANAGER.value
    staff.username = "manager"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_tech_user() -> MagicMock:
    """Create a mock tech user with authentication enabled."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Tech User"
    staff.phone = "6125550003"
    staff.email = "tech@grins.com"
    staff.role = StaffRole.TECH.value
    staff.username = "tech"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_locked_user() -> MagicMock:
    """Create a mock user with locked account."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Locked User"
    staff.phone = "6125550004"
    staff.email = "locked@grins.com"
    staff.role = StaffRole.TECH.value
    staff.username = "locked"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 5
    staff.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Create a mock auth service for testing."""
    service = MagicMock(spec=AuthService)
    service.authenticate = AsyncMock()
    service.verify_access_token = MagicMock()
    service.verify_refresh_token = MagicMock()
    service.refresh_access_token = AsyncMock()
    service.change_password = AsyncMock()
    service.get_current_user = AsyncMock()
    service.get_user_role = MagicMock(return_value=UserRole.ADMIN)
    return service


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# Test Login Flow End-to-End
# =============================================================================


@pytest.mark.integration
class TestLoginFlowIntegration:
    """Integration tests for the complete login flow."""

    @pytest.mark.asyncio
    async def test_login_success_returns_tokens_and_user(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test successful login returns access token, sets cookies, and user info.

        Validates: Requirements 14.1-14.2, 18.1, 18.6-18.8
        """
        # Setup mock to return successful authentication
        mock_auth_service.authenticate.return_value = (
            sample_admin_user,
            "access_token_123",
            "refresh_token_456",
            "csrf_token_789",
        )

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

        try:
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "password123"},
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response body
            assert "access_token" in data
            assert data["access_token"] == "access_token_123"
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 15 * 60
            assert "csrf_token" in data
            assert data["csrf_token"] == "csrf_token_789"

            # Verify user info
            assert "user" in data
            assert data["user"]["username"] == "admin"
            assert data["user"]["name"] == "Admin User"
            assert data["user"]["role"] == "admin"
            assert data["user"]["is_active"] is True

            # Verify cookies are set
            cookies = response.cookies
            assert "refresh_token" in cookies
            assert "csrf_token" in cookies

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_returns_401(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
    ) -> None:
        """Test login with invalid credentials returns 401.

        Validates: Requirement 14.2
        """
        mock_auth_service.authenticate.side_effect = InvalidCredentialsError(
            "Invalid credentials",
        )

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

        try:
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "invalid", "password": "wrong"},
            )

            assert response.status_code == 401
            data = response.json()
            assert "detail" in data
            assert "Invalid username or password" in data["detail"]

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_locked_account_returns_401(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
    ) -> None:
        """Test login with locked account returns 401.

        Validates: Requirements 16.5-16.7
        """
        mock_auth_service.authenticate.side_effect = AccountLockedError(
            "Account locked",
        )

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

        try:
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "locked", "password": "password123"},
            )

            assert response.status_code == 401
            data = response.json()
            assert "detail" in data
            assert "locked" in data["detail"].lower()

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Token Refresh Flow
# =============================================================================


@pytest.mark.integration
class TestTokenRefreshFlowIntegration:
    """Integration tests for token refresh flow."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
    ) -> None:
        """Test successful token refresh returns new access token.

        Validates: Requirements 18.3, 18.8
        """
        mock_auth_service.verify_refresh_token.return_value = {
            "sub": str(uuid.uuid4()),
            "type": "refresh",
        }
        # Return tuple of (access_token, expires_in)
        mock_auth_service.refresh_access_token.return_value = (
            "new_access_token_123",
            15 * 60,  # 15 minutes in seconds
        )

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

        try:
            response = await async_client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": "valid_refresh_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["access_token"] == "new_access_token_123"
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 15 * 60

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_refresh_token_missing_returns_401(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
    ) -> None:
        """Test refresh without token returns 401.

        Validates: Requirement 18.8
        """
        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

        try:
            response = await async_client.post("/api/v1/auth/refresh")

            assert response.status_code == 401
            data = response.json()
            assert "detail" in data

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_returns_401(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
    ) -> None:
        """Test refresh with invalid token returns 401.

        Validates: Requirement 18.8
        """
        mock_auth_service.refresh_access_token.side_effect = InvalidTokenError(
            "Invalid token",
        )

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

        try:
            response = await async_client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": "invalid_token"},
            )

            assert response.status_code == 401

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Protected Route Access
# =============================================================================


@pytest.mark.integration
class TestProtectedRouteAccessIntegration:
    """Integration tests for protected route access."""

    @pytest.mark.asyncio
    async def test_protected_route_without_token_returns_401(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test accessing protected route without token returns 401.

        Validates: Requirements 20.1-20.2
        """
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_with_valid_token_succeeds(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test accessing protected route with valid token succeeds.

        Validates: Requirements 20.1-20.2, 18.4
        """
        mock_auth_service.verify_access_token.return_value = {
            "sub": str(sample_admin_user.id),
            "role": "admin",
            "type": "access",
        }
        mock_auth_service.get_current_user.return_value = sample_admin_user
        mock_auth_service.get_user_role.return_value = UserRole.ADMIN

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_current_user] = lambda: sample_admin_user

        try:
            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer valid_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "admin"
            assert data["name"] == "Admin User"

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Role-Based Access Control
# =============================================================================


@pytest.mark.integration
class TestRoleBasedAccessControlIntegration:
    """Integration tests for role-based access control."""

    @pytest.mark.asyncio
    async def test_admin_can_access_admin_only_endpoints(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test admin user can access admin-only endpoints.

        Validates: Requirements 17.1-17.4
        """
        mock_auth_service.verify_access_token.return_value = {
            "sub": str(sample_admin_user.id),
            "role": "admin",
            "type": "access",
        }
        mock_auth_service.get_current_user.return_value = sample_admin_user
        mock_auth_service.get_user_role.return_value = UserRole.ADMIN

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_current_user] = lambda: sample_admin_user

        try:
            # Admin should be able to access /me endpoint
            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 200

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_manager_can_access_manager_endpoints(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test manager user can access manager-level endpoints.

        Validates: Requirements 17.5-17.6
        """
        mock_auth_service.verify_access_token.return_value = {
            "sub": str(sample_manager_user.id),
            "role": "manager",
            "type": "access",
        }
        mock_auth_service.get_current_user.return_value = sample_manager_user
        mock_auth_service.get_user_role.return_value = UserRole.MANAGER

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_current_user] = lambda: sample_manager_user

        try:
            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer manager_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "manager"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_tech_can_access_tech_endpoints(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_tech_user: MagicMock,
    ) -> None:
        """Test tech user can access tech-level endpoints.

        Validates: Requirements 17.9-17.12
        """
        mock_auth_service.verify_access_token.return_value = {
            "sub": str(sample_tech_user.id),
            "role": "tech",
            "type": "access",
        }
        mock_auth_service.get_current_user.return_value = sample_tech_user
        mock_auth_service.get_user_role.return_value = UserRole.TECH

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user

        try:
            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer tech_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "tech"

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Logout Flow
# =============================================================================


@pytest.mark.integration
class TestLogoutFlowIntegration:
    """Integration tests for logout flow."""

    @pytest.mark.asyncio
    async def test_logout_clears_cookies(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test logout clears authentication cookies.

        Validates: Requirements 14.8, 18.2
        """
        response = await async_client.post("/api/v1/auth/logout")

        assert response.status_code == 204

        # Verify cookies are cleared (set to empty or deleted)
        # The response should have Set-Cookie headers that clear the cookies
        set_cookie_headers = response.headers.get_list("set-cookie")
        assert len(set_cookie_headers) >= 2  # refresh_token and csrf_token


# =============================================================================
# Test Password Change Flow
# =============================================================================


@pytest.mark.integration
class TestPasswordChangeFlowIntegration:
    """Integration tests for password change flow."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test successful password change.

        Validates: Requirement 18.5
        """
        mock_auth_service.verify_access_token.return_value = {
            "sub": str(sample_admin_user.id),
            "role": "admin",
            "type": "access",
        }
        mock_auth_service.get_current_user.return_value = sample_admin_user
        mock_auth_service.change_password.return_value = None
        mock_auth_service.get_user_role.return_value = UserRole.ADMIN

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_current_user] = lambda: sample_admin_user

        try:
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "oldpassword123",
                    "new_password": "NewPassword123!",
                },
                headers={"Authorization": "Bearer valid_token"},
            )

            assert response.status_code == 204
            mock_auth_service.change_password.assert_called_once()

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current_password(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test password change with wrong current password fails.

        Validates: Requirement 18.5
        """
        mock_auth_service.verify_access_token.return_value = {
            "sub": str(sample_admin_user.id),
            "role": "admin",
            "type": "access",
        }
        mock_auth_service.get_current_user.return_value = sample_admin_user
        mock_auth_service.change_password.side_effect = InvalidCredentialsError(
            "Invalid current password",
        )
        mock_auth_service.get_user_role.return_value = UserRole.ADMIN

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_current_user] = lambda: sample_admin_user

        try:
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "wrongpassword",
                    "new_password": "NewPassword123!",
                },
                headers={"Authorization": "Bearer valid_token"},
            )

            assert response.status_code == 400

        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Complete Authentication Workflow
# =============================================================================


@pytest.mark.integration
class TestCompleteAuthWorkflowIntegration:
    """Integration tests for complete authentication workflow."""

    @pytest.mark.asyncio
    async def test_full_auth_workflow_login_access_logout(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test complete workflow: login -> access protected -> logout.

        Validates: Requirements 14.1-14.8, 18.1-18.8, 20.1-20.6
        """
        # Step 1: Login
        mock_auth_service.authenticate.return_value = (
            sample_admin_user,
            "access_token_123",
            "refresh_token_456",
            "csrf_token_789",
        )
        mock_auth_service.verify_access_token.return_value = {
            "sub": str(sample_admin_user.id),
            "role": "admin",
            "type": "access",
        }
        mock_auth_service.get_current_user.return_value = sample_admin_user
        mock_auth_service.get_user_role.return_value = UserRole.ADMIN

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_current_user] = lambda: sample_admin_user

        try:
            # Login
            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "password123"},
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]

            # Step 2: Access protected route
            me_response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me_response.status_code == 200
            assert me_response.json()["username"] == "admin"

            # Step 3: Logout
            logout_response = await async_client.post("/api/v1/auth/logout")
            assert logout_response.status_code == 204

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_auth_workflow_with_token_refresh(
        self,
        async_client: AsyncClient,
        mock_auth_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test workflow with token refresh: login -> refresh -> access.

        Validates: Requirements 14.3-14.4, 18.3
        """
        # Setup mocks
        mock_auth_service.authenticate.return_value = (
            sample_admin_user,
            "access_token_123",
            "refresh_token_456",
            "csrf_token_789",
        )
        mock_auth_service.verify_refresh_token.return_value = {
            "sub": str(sample_admin_user.id),
            "type": "refresh",
        }
        mock_auth_service.refresh_access_token.return_value = (
            "new_access_token_789",
            15 * 60,  # 15 minutes in seconds
        )
        mock_auth_service.verify_access_token.return_value = {
            "sub": str(sample_admin_user.id),
            "role": "admin",
            "type": "access",
        }
        mock_auth_service.get_current_user.return_value = sample_admin_user
        mock_auth_service.get_user_role.return_value = UserRole.ADMIN

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_current_user] = lambda: sample_admin_user

        try:
            # Step 1: Login
            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "password123"},
            )
            assert login_response.status_code == 200

            # Step 2: Refresh token
            refresh_response = await async_client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": "refresh_token_456"},
            )
            assert refresh_response.status_code == 200
            new_token = refresh_response.json()["access_token"]
            assert new_token == "new_access_token_789"

            # Step 3: Access with new token
            me_response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {new_token}"},
            )
            assert me_response.status_code == 200

        finally:
            app.dependency_overrides.clear()
