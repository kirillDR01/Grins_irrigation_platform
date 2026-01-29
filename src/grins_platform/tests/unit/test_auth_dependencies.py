"""
Unit tests for authentication dependencies and RBAC.

This module tests the permission decorator and FastAPI dependencies
for role-based access control.

Validates: Requirements 17.1-17.12
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from grins_platform.api.v1.auth_dependencies import (
    _get_user_role,
    get_current_active_user,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    require_roles,
)
from grins_platform.exceptions.auth import (
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
)
from grins_platform.models.enums import UserRole

if TYPE_CHECKING:
    from grins_platform.models.staff import Staff


@pytest.fixture
def mock_staff() -> MagicMock:
    """Create a mock staff member."""
    staff = MagicMock()
    staff.id = uuid4()
    staff.username = "testuser"
    staff.first_name = "Test"
    staff.last_name = "User"
    staff.email = "test@example.com"
    staff.role = "tech"
    staff.is_active = True
    staff.is_login_enabled = True
    return staff


@pytest.fixture
def mock_admin_staff() -> MagicMock:
    """Create a mock admin staff member."""
    staff = MagicMock()
    staff.id = uuid4()
    staff.username = "admin"
    staff.first_name = "Admin"
    staff.last_name = "User"
    staff.email = "admin@example.com"
    staff.role = "admin"
    staff.is_active = True
    staff.is_login_enabled = True
    return staff


@pytest.fixture
def mock_manager_staff() -> MagicMock:
    """Create a mock manager staff member."""
    staff = MagicMock()
    staff.id = uuid4()
    staff.username = "manager"
    staff.first_name = "Manager"
    staff.last_name = "User"
    staff.email = "manager@example.com"
    staff.role = "sales"  # Sales maps to MANAGER
    staff.is_active = True
    staff.is_login_enabled = True
    return staff


@pytest.fixture
def mock_inactive_staff() -> MagicMock:
    """Create a mock inactive staff member."""
    staff = MagicMock()
    staff.id = uuid4()
    staff.username = "inactive"
    staff.first_name = "Inactive"
    staff.last_name = "User"
    staff.email = "inactive@example.com"
    staff.role = "tech"
    staff.is_active = False
    staff.is_login_enabled = True
    return staff


class TestGetUserRole:
    """Tests for _get_user_role helper function."""

    def test_admin_role_mapping(self, mock_admin_staff: MagicMock) -> None:
        """Test admin role maps to UserRole.ADMIN."""
        result = _get_user_role(mock_admin_staff)
        assert result == UserRole.ADMIN

    def test_sales_role_maps_to_manager(self, mock_manager_staff: MagicMock) -> None:
        """Test sales role maps to UserRole.MANAGER."""
        result = _get_user_role(mock_manager_staff)
        assert result == UserRole.MANAGER

    def test_tech_role_mapping(self, mock_staff: MagicMock) -> None:
        """Test tech role maps to UserRole.TECH."""
        result = _get_user_role(mock_staff)
        assert result == UserRole.TECH

    def test_unknown_role_defaults_to_tech(self) -> None:
        """Test unknown role defaults to UserRole.TECH."""
        staff = MagicMock()
        staff.role = "unknown_role"
        result = _get_user_role(staff)
        assert result == UserRole.TECH


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_with_valid_token(
        self, mock_staff: MagicMock,
    ) -> None:
        """Test get_current_user returns user with valid token."""
        mock_request = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        mock_auth_service = AsyncMock()
        mock_auth_service.get_current_user.return_value = mock_staff

        result = await get_current_user(
            mock_request, mock_credentials, mock_auth_service,
        )

        assert result == mock_staff
        mock_auth_service.get_current_user.assert_called_once_with("valid_token")
        assert mock_request.state.current_user == mock_staff

    @pytest.mark.asyncio
    async def test_raises_401_when_no_credentials(self) -> None:
        """Test get_current_user raises 401 when no credentials provided."""
        mock_request = MagicMock()
        mock_auth_service = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, None, mock_auth_service)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"

    @pytest.mark.asyncio
    async def test_raises_401_on_expired_token(self) -> None:
        """Test get_current_user raises 401 on expired token."""
        mock_request = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "expired_token"
        mock_auth_service = AsyncMock()
        mock_auth_service.get_current_user.side_effect = TokenExpiredError()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_credentials, mock_auth_service)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token has expired"

    @pytest.mark.asyncio
    async def test_raises_401_on_invalid_token(self) -> None:
        """Test get_current_user raises 401 on invalid token."""
        mock_request = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"
        mock_auth_service = AsyncMock()
        mock_auth_service.get_current_user.side_effect = InvalidTokenError()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_credentials, mock_auth_service)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid authentication credentials"

    @pytest.mark.asyncio
    async def test_raises_401_on_user_not_found(self) -> None:
        """Test get_current_user raises 401 when user not found."""
        mock_request = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        mock_auth_service = AsyncMock()
        mock_auth_service.get_current_user.side_effect = UserNotFoundError()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_credentials, mock_auth_service)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid authentication credentials"


class TestGetCurrentActiveUser:
    """Tests for get_current_active_user dependency."""

    @pytest.mark.asyncio
    async def test_returns_active_user(self, mock_staff: MagicMock) -> None:
        """Test get_current_active_user returns active user."""
        result = await get_current_active_user(mock_staff)
        assert result == mock_staff

    @pytest.mark.asyncio
    async def test_raises_403_for_inactive_user(
        self, mock_inactive_staff: MagicMock,
    ) -> None:
        """Test get_current_active_user raises 403 for inactive user."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(mock_inactive_staff)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "User account is inactive"


class TestRequireAdmin:
    """Tests for require_admin dependency."""

    @pytest.mark.asyncio
    async def test_allows_admin_user(self, mock_admin_staff: MagicMock) -> None:
        """Test require_admin allows admin user."""
        result = await require_admin(mock_admin_staff)
        assert result == mock_admin_staff

    @pytest.mark.asyncio
    async def test_denies_manager_user(self, mock_manager_staff: MagicMock) -> None:
        """Test require_admin denies manager user."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_manager_staff)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin access required"

    @pytest.mark.asyncio
    async def test_denies_tech_user(self, mock_staff: MagicMock) -> None:
        """Test require_admin denies tech user."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_staff)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin access required"


class TestRequireManagerOrAdmin:
    """Tests for require_manager_or_admin dependency."""

    @pytest.mark.asyncio
    async def test_allows_admin_user(self, mock_admin_staff: MagicMock) -> None:
        """Test require_manager_or_admin allows admin user."""
        result = await require_manager_or_admin(mock_admin_staff)
        assert result == mock_admin_staff

    @pytest.mark.asyncio
    async def test_allows_manager_user(self, mock_manager_staff: MagicMock) -> None:
        """Test require_manager_or_admin allows manager user."""
        result = await require_manager_or_admin(mock_manager_staff)
        assert result == mock_manager_staff

    @pytest.mark.asyncio
    async def test_denies_tech_user(self, mock_staff: MagicMock) -> None:
        """Test require_manager_or_admin denies tech user."""
        with pytest.raises(HTTPException) as exc_info:
            await require_manager_or_admin(mock_staff)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Manager or admin access required"


class TestRequireRolesDecorator:
    """Tests for require_roles decorator."""

    @pytest.mark.asyncio
    async def test_allows_user_with_required_role(
        self, mock_admin_staff: MagicMock,
    ) -> None:
        """Test decorator allows user with required role."""

        @require_roles(UserRole.ADMIN)
        async def protected_endpoint(
            current_user: Staff,  # noqa: ARG001
        ) -> dict[str, str]:
            return {"message": "success"}

        result = await protected_endpoint(current_user=mock_admin_staff)
        assert result == {"message": "success"}

    @pytest.mark.asyncio
    async def test_allows_user_with_one_of_multiple_roles(
        self, mock_manager_staff: MagicMock,
    ) -> None:
        """Test decorator allows user with one of multiple allowed roles."""

        @require_roles(UserRole.ADMIN, UserRole.MANAGER)
        async def protected_endpoint(
            current_user: Staff,  # noqa: ARG001
        ) -> dict[str, str]:
            return {"message": "success"}

        result = await protected_endpoint(current_user=mock_manager_staff)
        assert result == {"message": "success"}

    @pytest.mark.asyncio
    async def test_denies_user_without_required_role(
        self, mock_staff: MagicMock,
    ) -> None:
        """Test decorator denies user without required role."""

        @require_roles(UserRole.ADMIN)
        async def protected_endpoint(
            current_user: Staff,  # noqa: ARG001
        ) -> dict[str, str]:
            return {"message": "success"}

        with pytest.raises(HTTPException) as exc_info:
            await protected_endpoint(current_user=mock_staff)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_401_when_no_user(self) -> None:
        """Test decorator raises 401 when no user provided."""

        @require_roles(UserRole.ADMIN)
        async def protected_endpoint(
            current_user: Staff | None = None,  # noqa: ARG001
        ) -> dict[str, str]:
            return {"message": "success"}

        with pytest.raises(HTTPException) as exc_info:
            await protected_endpoint(current_user=None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self) -> None:
        """Test decorator preserves original function metadata."""

        @require_roles(UserRole.ADMIN)
        async def my_endpoint(
            current_user: Staff,  # noqa: ARG001
        ) -> dict[str, str]:
            """My endpoint docstring."""
            return {"message": "success"}

        assert my_endpoint.__name__ == "my_endpoint"
        assert my_endpoint.__doc__ == "My endpoint docstring."


class TestRolePermissionHierarchy:
    """Property-based tests for role permission hierarchy.

    Property 2: Role Permission Hierarchy
    - Admin has all permissions
    - Manager has subset of admin permissions
    - Tech has subset of manager permissions
    """

    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(
        self, mock_admin_staff: MagicMock,
    ) -> None:
        """Test admin can access all role-protected endpoints."""
        # Admin can access admin-only
        result = await require_admin(mock_admin_staff)
        assert result == mock_admin_staff

        # Admin can access manager-or-admin
        result = await require_manager_or_admin(mock_admin_staff)
        assert result == mock_admin_staff

    @pytest.mark.asyncio
    async def test_manager_has_subset_of_admin(
        self, mock_manager_staff: MagicMock,
    ) -> None:
        """Test manager has subset of admin permissions."""
        # Manager can access manager-or-admin
        result = await require_manager_or_admin(mock_manager_staff)
        assert result == mock_manager_staff

        # Manager cannot access admin-only
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_manager_staff)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_tech_has_subset_of_manager(self, mock_staff: MagicMock) -> None:
        """Test tech has subset of manager permissions."""
        # Tech cannot access manager-or-admin
        with pytest.raises(HTTPException) as exc_info:
            await require_manager_or_admin(mock_staff)
        assert exc_info.value.status_code == 403

        # Tech cannot access admin-only
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_staff)
        assert exc_info.value.status_code == 403
