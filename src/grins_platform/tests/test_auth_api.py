"""
Authentication API endpoint tests.

Tests for login, logout, token refresh, and password change endpoints.

Validates: Requirements 14.1-14.8, 18.1-18.8
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import get_auth_service
from grins_platform.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
)
from grins_platform.main import app
from grins_platform.models.enums import UserRole

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_staff() -> MagicMock:
    """Create a mock staff member for testing."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.username = "testuser"
    staff.name = "Test User"
    staff.email = "test@example.com"
    staff.role = UserRole.MANAGER.value
    staff.is_active = True
    staff.is_login_enabled = True
    staff.password_hash = "$2b$12$test_hash"
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.last_login = None
    return staff


@pytest.fixture
def mock_admin_staff() -> MagicMock:
    """Create a mock admin staff member for testing."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.username = "admin"
    staff.name = "Admin User"
    staff.email = "admin@example.com"
    staff.role = UserRole.ADMIN.value
    staff.is_active = True
    staff.is_login_enabled = True
    staff.password_hash = "$2b$12$admin_hash"
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.last_login = None
    return staff


@pytest.fixture
def mock_locked_staff() -> MagicMock:
    """Create a mock locked staff member for testing."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.username = "lockeduser"
    staff.name = "Locked User"
    staff.email = "locked@example.com"
    staff.role = UserRole.TECH.value
    staff.is_active = True
    staff.is_login_enabled = True
    staff.password_hash = "$2b$12$locked_hash"
    staff.failed_login_attempts = 5
    staff.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    staff.last_login = None
    return staff


@pytest.fixture
def valid_access_token() -> str:
    """Return a valid access token for testing."""
    return "valid_access_token_123"


@pytest.fixture
def valid_refresh_token() -> str:
    """Return a valid refresh token for testing."""
    return "valid_refresh_token_456"


@pytest.fixture
def valid_csrf_token() -> str:
    """Return a valid CSRF token for testing."""
    return "valid_csrf_token_789"


@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Create a mock AuthService with async methods properly mocked."""
    service = MagicMock()
    # authenticate is async, so use AsyncMock for it
    service.authenticate = AsyncMock()
    service.refresh_access_token = AsyncMock()
    service.change_password = AsyncMock()
    # get_user_role is sync, so it stays as MagicMock
    return service


@pytest.fixture
def override_auth_service(
    mock_auth_service: MagicMock,
) -> Callable[[], MagicMock]:
    """Create an async override function for auth service."""

    async def _override() -> MagicMock:
        return mock_auth_service

    return _override  # type: ignore[return-value]


# =============================================================================
# Login Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        mock_staff: MagicMock,
        valid_access_token: str,
        valid_refresh_token: str,
        valid_csrf_token: str,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test successful login returns tokens and user info."""
        mock_auth_service.authenticate.return_value = (
            mock_staff,
            valid_access_token,
            valid_refresh_token,
            valid_csrf_token,
        )
        mock_auth_service.get_user_role.return_value = "manager"

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == valid_access_token
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 900  # 15 minutes
            assert data["csrf_token"] == valid_csrf_token
            assert data["user"]["username"] == "testuser"
            assert data["user"]["role"] == "manager"

            # Verify cookies are set
            cookies = response.cookies
            assert "refresh_token" in cookies
            assert "csrf_token" in cookies
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(
        self,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test login with invalid credentials returns 401."""
        mock_auth_service.authenticate.side_effect = InvalidCredentialsError(
            "Invalid credentials",
        )

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "wronguser", "password": "wrongpass"},
                )

            assert response.status_code == 401
            assert "Invalid username or password" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_account_locked(
        self,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test login with locked account returns 401."""
        mock_auth_service.authenticate.side_effect = AccountLockedError(
            "Account locked",
        )

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "lockeduser", "password": "password123"},
                )

            assert response.status_code == 401
            assert "Account is locked" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_missing_username(self) -> None:
        """Test login without username returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"password": "password123"},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_password(self) -> None:
        """Test login without password returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "testuser"},
            )

        assert response.status_code == 422


# =============================================================================
# Logout Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self) -> None:
        """Test successful logout clears cookies and returns 204."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            # Set cookies first
            client.cookies.set("refresh_token", "some_token")
            client.cookies.set("csrf_token", "some_csrf")

            response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_logout_without_cookies(self) -> None:
        """Test logout without existing cookies still returns 204."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 204


# =============================================================================
# Token Refresh Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestRefreshEndpoint:
    """Tests for POST /api/v1/auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(
        self,
        valid_refresh_token: str,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test successful token refresh returns new access token."""
        mock_auth_service.refresh_access_token.return_value = (
            "new_access_token",
            900,
        )

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                client.cookies.set("refresh_token", valid_refresh_token)
                response = await client.post("/api/v1/auth/refresh")

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_access_token"
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 900
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_refresh_missing_token(
        self,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test refresh without token returns 401."""
        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post("/api/v1/auth/refresh")

            assert response.status_code == 401
            assert "Refresh token not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_refresh_expired_token(
        self,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test refresh with expired token returns 401."""
        mock_auth_service.refresh_access_token.side_effect = TokenExpiredError(
            "Token expired",
        )

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                client.cookies.set("refresh_token", "expired_token")
                response = await client.post("/api/v1/auth/refresh")

            assert response.status_code == 401
            assert "expired" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(
        self,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test refresh with invalid token returns 401."""
        mock_auth_service.refresh_access_token.side_effect = InvalidTokenError(
            "Invalid token",
        )

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                client.cookies.set("refresh_token", "invalid_token")
                response = await client.post("/api/v1/auth/refresh")

            assert response.status_code == 401
            assert "Invalid refresh token" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Get Current User Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestGetMeEndpoint:
    """Tests for GET /api/v1/auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(
        self,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test getting current user without auth returns 401/403."""
        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/auth/me")

            # Should return 401 or 403 without valid token
            assert response.status_code in [401, 403]
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Change Password Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestChangePasswordEndpoint:
    """Tests for POST /api/v1/auth/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_unauthorized(
        self,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test changing password without auth returns 401/403."""
        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/change-password",
                    json={
                        "current_password": "oldpass",
                        "new_password": "NewPass123!",
                        "confirm_password": "NewPass123!",
                    },
                )

            assert response.status_code in [401, 403]
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Cookie Security Tests
# =============================================================================


@pytest.mark.unit
class TestCookieSecurity:
    """Tests for cookie security settings."""

    @pytest.mark.asyncio
    async def test_refresh_token_cookie_httponly(
        self,
        mock_staff: MagicMock,
        valid_access_token: str,
        valid_refresh_token: str,
        valid_csrf_token: str,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test refresh token cookie is HttpOnly."""
        mock_auth_service.authenticate.return_value = (
            mock_staff,
            valid_access_token,
            valid_refresh_token,
            valid_csrf_token,
        )
        mock_auth_service.get_user_role.return_value = "manager"

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )

            assert response.status_code == 200
            # Check Set-Cookie headers for httponly flag
            set_cookie_headers = response.headers.get_list("set-cookie")
            refresh_cookie = next(
                (h for h in set_cookie_headers if "refresh_token" in h),
                None,
            )
            if refresh_cookie:
                assert "httponly" in refresh_cookie.lower()
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Response Format Tests
# =============================================================================


@pytest.mark.unit
class TestResponseFormats:
    """Tests for API response formats."""

    @pytest.mark.asyncio
    async def test_login_response_format(
        self,
        mock_staff: MagicMock,
        valid_access_token: str,
        valid_refresh_token: str,
        valid_csrf_token: str,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test login response has correct format."""
        mock_auth_service.authenticate.return_value = (
            mock_staff,
            valid_access_token,
            valid_refresh_token,
            valid_csrf_token,
        )
        mock_auth_service.get_user_role.return_value = "manager"

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )

            assert response.status_code == 200
            data = response.json()

            # Verify required fields
            assert "access_token" in data
            assert "token_type" in data
            assert "expires_in" in data
            assert "user" in data
            assert "csrf_token" in data

            # Verify user object fields
            user = data["user"]
            assert "id" in user
            assert "username" in user
            assert "name" in user
            assert "role" in user
            assert "is_active" in user
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_token_response_format(
        self,
        valid_refresh_token: str,
        mock_auth_service: MagicMock,
        override_auth_service: Callable[[], MagicMock],
    ) -> None:
        """Test token refresh response has correct format."""
        mock_auth_service.refresh_access_token.return_value = (
            "new_access_token",
            900,
        )

        app.dependency_overrides[get_auth_service] = override_auth_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                client.cookies.set("refresh_token", valid_refresh_token)
                response = await client.post("/api/v1/auth/refresh")

            assert response.status_code == 200
            data = response.json()

            # Verify required fields
            assert "access_token" in data
            assert "token_type" in data
            assert "expires_in" in data
            assert data["token_type"] == "bearer"
        finally:
            app.dependency_overrides.clear()


__all__ = [
    "TestChangePasswordEndpoint",
    "TestCookieSecurity",
    "TestGetMeEndpoint",
    "TestLoginEndpoint",
    "TestLogoutEndpoint",
    "TestRefreshEndpoint",
    "TestResponseFormats",
]
