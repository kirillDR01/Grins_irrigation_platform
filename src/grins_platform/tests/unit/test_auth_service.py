"""
Unit tests for AuthService.

Tests authentication service methods including login, token management,
password handling, and account lockout.

Validates: Requirements 14.1-14.8, 16.1-16.8
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
)
from grins_platform.models.enums import UserRole
from grins_platform.schemas.auth import ChangePasswordRequest
from grins_platform.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AuthService,
)

# Pre-computed bcrypt hash for "ValidPass123" (cost 12)
# Generated with: bcrypt.hashpw(b'ValidPass123', bcrypt.gensalt(rounds=12))
VALID_PASSWORD = "ValidPass123"
VALID_PASSWORD_HASH = "$2b$12$rHSdAjcZ2in87rbcVyEf0.YAMxKlq77JqvW5urCZVqMBT6eJmwk2G"


@pytest.fixture
def mock_staff_repository() -> AsyncMock:
    """Create a mock StaffRepository."""
    return AsyncMock()


@pytest.fixture
def auth_service(mock_staff_repository: AsyncMock) -> AuthService:
    """Create AuthService with mocked repository."""
    return AuthService(repository=mock_staff_repository)


@pytest.fixture
def mock_staff() -> MagicMock:
    """Create a mock Staff model with auth fields."""
    staff = MagicMock()
    staff.id = uuid4()
    staff.username = "testuser"
    # Use pre-computed hash to avoid bcrypt issues in tests
    staff.password_hash = VALID_PASSWORD_HASH
    staff.is_login_enabled = True
    staff.role = "admin"
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.last_login = None
    staff.name = "Test User"
    staff.email = "test@example.com"
    return staff


@pytest.mark.unit
class TestAuthServicePasswordHashing:
    """Test password hashing methods.

    Validates: Requirements 15.8, 16.1

    Note: These tests mock the passlib pwd_context to avoid compatibility
    issues between passlib and newer bcrypt versions in the test environment.
    """

    def test_hash_password_produces_bcrypt_hash(
        self, auth_service: AuthService,
    ) -> None:
        """Test _hash_password produces valid bcrypt hash."""
        with patch(
            "grins_platform.services.auth_service.pwd_context.hash",
            return_value=VALID_PASSWORD_HASH,
        ):
            hashed = auth_service._hash_password("TestPassword123")

            assert hashed.startswith("$2b$")
            assert len(hashed) == 60

    def test_hash_password_calls_pwd_context(
        self, auth_service: AuthService,
    ) -> None:
        """Test _hash_password calls pwd_context.hash."""
        with patch(
            "grins_platform.services.auth_service.pwd_context.hash",
            return_value=VALID_PASSWORD_HASH,
        ) as mock_hash:
            auth_service._hash_password("TestPassword123")
            mock_hash.assert_called_once_with("TestPassword123")

    def test_verify_password_correct(self, auth_service: AuthService) -> None:
        """Test _verify_password returns True for correct password."""
        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=True,
        ):
            result = auth_service._verify_password(VALID_PASSWORD, VALID_PASSWORD_HASH)
            assert result is True

    def test_verify_password_incorrect(self, auth_service: AuthService) -> None:
        """Test _verify_password returns False for incorrect password."""
        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=False,
        ):
            result = auth_service._verify_password("WrongPassword", VALID_PASSWORD_HASH)
            assert result is False

    def test_verify_password_empty_password(self, auth_service: AuthService) -> None:
        """Test _verify_password with empty password."""
        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=False,
        ):
            assert auth_service._verify_password("", VALID_PASSWORD_HASH) is False


@pytest.mark.unit
class TestAuthServiceTokenGeneration:
    """Test token generation methods.

    Validates: Requirements 14.3-14.4
    """

    def test_create_access_token_valid(self, auth_service: AuthService) -> None:
        """Test _create_access_token generates valid JWT."""
        user_id = uuid4()
        role = UserRole.ADMIN

        token = auth_service._create_access_token(user_id, role)

        assert isinstance(token, str)
        assert len(token) > 0
        # Verify token can be decoded
        payload = auth_service.verify_access_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["role"] == role.value
        assert payload["type"] == "access"

    def test_create_access_token_custom_expiration(
        self, auth_service: AuthService,
    ) -> None:
        """Test _create_access_token with custom expiration."""
        user_id = uuid4()
        role = UserRole.TECH
        expires_delta = timedelta(hours=1)

        token = auth_service._create_access_token(user_id, role, expires_delta)

        payload = auth_service.verify_access_token(token)
        assert payload["sub"] == str(user_id)

    def test_create_refresh_token_valid(self, auth_service: AuthService) -> None:
        """Test _create_refresh_token generates valid JWT."""
        user_id = uuid4()

        token = auth_service._create_refresh_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0
        # Verify token can be decoded
        payload = auth_service.verify_refresh_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_create_refresh_token_custom_expiration(
        self, auth_service: AuthService,
    ) -> None:
        """Test _create_refresh_token with custom expiration."""
        user_id = uuid4()
        expires_delta = timedelta(days=14)

        token = auth_service._create_refresh_token(user_id, expires_delta)

        payload = auth_service.verify_refresh_token(token)
        assert payload["sub"] == str(user_id)


@pytest.mark.unit
class TestAuthServiceTokenVerification:
    """Test token verification methods.

    Validates: Requirements 14.5-14.6
    """

    def test_verify_access_token_valid(self, auth_service: AuthService) -> None:
        """Test verify_access_token with valid token."""
        user_id = uuid4()
        token = auth_service._create_access_token(user_id, UserRole.ADMIN)

        payload = auth_service.verify_access_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_verify_access_token_expired(self, auth_service: AuthService) -> None:
        """Test verify_access_token with expired token."""
        user_id = uuid4()
        # Create token that expired 1 hour ago
        token = auth_service._create_access_token(
            user_id, UserRole.ADMIN, timedelta(hours=-1),
        )

        with pytest.raises(TokenExpiredError):
            auth_service.verify_access_token(token)

    def test_verify_access_token_invalid(self, auth_service: AuthService) -> None:
        """Test verify_access_token with invalid token."""
        with pytest.raises(InvalidTokenError):
            auth_service.verify_access_token("invalid.token.here")

    def test_verify_access_token_wrong_type(self, auth_service: AuthService) -> None:
        """Test verify_access_token rejects refresh token."""
        user_id = uuid4()
        refresh_token = auth_service._create_refresh_token(user_id)

        with pytest.raises(InvalidTokenError):
            auth_service.verify_access_token(refresh_token)

    def test_verify_refresh_token_valid(self, auth_service: AuthService) -> None:
        """Test verify_refresh_token with valid token."""
        user_id = uuid4()
        token = auth_service._create_refresh_token(user_id)

        payload = auth_service.verify_refresh_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_verify_refresh_token_expired(self, auth_service: AuthService) -> None:
        """Test verify_refresh_token with expired token."""
        user_id = uuid4()
        # Create token that expired 1 day ago
        token = auth_service._create_refresh_token(user_id, timedelta(days=-1))

        with pytest.raises(TokenExpiredError):
            auth_service.verify_refresh_token(token)

    def test_verify_refresh_token_invalid(self, auth_service: AuthService) -> None:
        """Test verify_refresh_token with invalid token."""
        with pytest.raises(InvalidTokenError):
            auth_service.verify_refresh_token("invalid.token.here")

    def test_verify_refresh_token_wrong_type(self, auth_service: AuthService) -> None:
        """Test verify_refresh_token rejects access token."""
        user_id = uuid4()
        access_token = auth_service._create_access_token(user_id, UserRole.ADMIN)

        with pytest.raises(InvalidTokenError):
            auth_service.verify_refresh_token(access_token)


@pytest.mark.unit
class TestAuthServiceAuthenticate:
    """Test authenticate method.

    Validates: Requirements 14.1-14.2, 16.5-16.7
    """

    @pytest.mark.asyncio
    async def test_authenticate_success(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test successful authentication."""
        mock_staff_repository.find_by_username.return_value = mock_staff
        mock_staff_repository.update_auth_fields.return_value = None

        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=True,
        ):
            result = await auth_service.authenticate("testuser", VALID_PASSWORD)
            staff, access_token, refresh_token, csrf_token = result

        assert staff == mock_staff
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert isinstance(csrf_token, str)
        mock_staff_repository.update_auth_fields.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
    ) -> None:
        """Test authentication with non-existent user."""
        mock_staff_repository.find_by_username.return_value = None

        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate("nonexistent", "password")

    @pytest.mark.asyncio
    async def test_authenticate_login_disabled(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test authentication with login disabled."""
        mock_staff.is_login_enabled = False
        mock_staff_repository.find_by_username.return_value = mock_staff

        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate("testuser", VALID_PASSWORD)

    @pytest.mark.asyncio
    async def test_authenticate_invalid_password(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test authentication with wrong password."""
        mock_staff_repository.find_by_username.return_value = mock_staff
        mock_staff_repository.update_auth_fields.return_value = None

        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=False,
        ), pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate("testuser", "WrongPassword")

        # Verify failed login was recorded
        mock_staff_repository.update_auth_fields.assert_called()

    @pytest.mark.asyncio
    async def test_authenticate_account_locked(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test authentication with locked account."""
        mock_staff.locked_until = datetime.now(UTC) + timedelta(minutes=10)
        mock_staff_repository.find_by_username.return_value = mock_staff

        with pytest.raises(AccountLockedError):
            await auth_service.authenticate("testuser", VALID_PASSWORD)

    @pytest.mark.asyncio
    async def test_authenticate_lockout_expired(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test authentication after lockout expires."""
        # Lockout expired 5 minutes ago
        mock_staff.locked_until = datetime.now(UTC) - timedelta(minutes=5)
        mock_staff_repository.find_by_username.return_value = mock_staff
        mock_staff_repository.update_auth_fields.return_value = None

        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=True,
        ):
            staff, access_token, _, _ = await auth_service.authenticate(
                "testuser", VALID_PASSWORD,
            )

        assert staff == mock_staff
        assert isinstance(access_token, str)


@pytest.mark.unit
class TestAuthServiceAccountLockout:
    """Test account lockout functionality.

    Validates: Requirements 16.5-16.7
    """

    @pytest.mark.asyncio
    async def test_failed_login_increments_counter(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test failed login increments failed_login_attempts."""
        mock_staff.failed_login_attempts = 2
        mock_staff_repository.find_by_username.return_value = mock_staff
        mock_staff_repository.update_auth_fields.return_value = None

        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=False,
        ), pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate("testuser", "WrongPassword")

        # Verify counter was incremented
        call_args = mock_staff_repository.update_auth_fields.call_args
        assert call_args[1]["failed_login_attempts"] == 3

    @pytest.mark.asyncio
    async def test_account_locks_after_5_failures(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test account locks after 5 failed attempts."""
        mock_staff.failed_login_attempts = 4  # Next failure will be 5th
        mock_staff_repository.find_by_username.return_value = mock_staff
        mock_staff_repository.update_auth_fields.return_value = None

        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=False,
        ), pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate("testuser", "WrongPassword")

        # Verify account was locked
        call_args = mock_staff_repository.update_auth_fields.call_args
        assert call_args[1]["failed_login_attempts"] == 5
        assert call_args[1]["locked_until"] is not None

    @pytest.mark.asyncio
    async def test_successful_login_resets_counter(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test successful login resets failed_login_attempts."""
        mock_staff.failed_login_attempts = 3
        mock_staff_repository.find_by_username.return_value = mock_staff
        mock_staff_repository.update_auth_fields.return_value = None

        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=True,
        ):
            await auth_service.authenticate("testuser", VALID_PASSWORD)

        # Verify counter was reset
        call_args = mock_staff_repository.update_auth_fields.call_args
        assert call_args[1]["failed_login_attempts"] == 0
        assert call_args[1]["locked_until"] is None

    def test_is_account_locked_true(
        self,
        auth_service: AuthService,
        mock_staff: MagicMock,
    ) -> None:
        """Test _is_account_locked returns True when locked."""
        mock_staff.locked_until = datetime.now(UTC) + timedelta(minutes=10)

        assert auth_service._is_account_locked(mock_staff) is True

    def test_is_account_locked_false_no_lockout(
        self,
        auth_service: AuthService,
        mock_staff: MagicMock,
    ) -> None:
        """Test _is_account_locked returns False when not locked."""
        mock_staff.locked_until = None

        assert auth_service._is_account_locked(mock_staff) is False

    def test_is_account_locked_false_expired(
        self,
        auth_service: AuthService,
        mock_staff: MagicMock,
    ) -> None:
        """Test _is_account_locked returns False when lockout expired."""
        mock_staff.locked_until = datetime.now(UTC) - timedelta(minutes=5)

        assert auth_service._is_account_locked(mock_staff) is False


@pytest.mark.unit
class TestAuthServiceRefreshToken:
    """Test refresh_access_token method.

    Validates: Requirement 14.7
    """

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test successful token refresh."""
        refresh_token = auth_service._create_refresh_token(mock_staff.id)
        mock_staff_repository.get_by_id.return_value = mock_staff

        new_token, expires_in = await auth_service.refresh_access_token(refresh_token)

        assert isinstance(new_token, str)
        assert expires_in == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @pytest.mark.asyncio
    async def test_refresh_access_token_expired(
        self,
        auth_service: AuthService,
    ) -> None:
        """Test token refresh with expired refresh token."""
        user_id = uuid4()
        expired_token = auth_service._create_refresh_token(user_id, timedelta(days=-1))

        with pytest.raises(TokenExpiredError):
            await auth_service.refresh_access_token(expired_token)

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid(
        self,
        auth_service: AuthService,
    ) -> None:
        """Test token refresh with invalid token."""
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_access_token("invalid.token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_user_not_found(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
    ) -> None:
        """Test token refresh when user no longer exists."""
        user_id = uuid4()
        refresh_token = auth_service._create_refresh_token(user_id)
        mock_staff_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFoundError):
            await auth_service.refresh_access_token(refresh_token)

    @pytest.mark.asyncio
    async def test_refresh_access_token_login_disabled(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test token refresh when login is disabled."""
        mock_staff.is_login_enabled = False
        refresh_token = auth_service._create_refresh_token(mock_staff.id)
        mock_staff_repository.get_by_id.return_value = mock_staff

        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_access_token(refresh_token)


@pytest.mark.unit
class TestAuthServiceChangePassword:
    """Test change_password method.

    Validates: Requirements 16.1-16.4, 18.5
    """

    @pytest.mark.asyncio
    async def test_change_password_success(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test successful password change."""
        mock_staff_repository.get_by_id.return_value = mock_staff
        mock_staff_repository.update_auth_fields.return_value = None

        request = ChangePasswordRequest(
            current_password=VALID_PASSWORD,
            new_password="NewValidPass456",
        )

        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=True,
        ), patch(
            "grins_platform.services.auth_service.pwd_context.hash",
            return_value="$2b$12$newhash",
        ):
            await auth_service.change_password(mock_staff.id, request)

        # Verify new password was hashed and saved
        call_args = mock_staff_repository.update_auth_fields.call_args
        assert "password_hash" in call_args[1]

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
    ) -> None:
        """Test password change with non-existent user."""
        mock_staff_repository.get_by_id.return_value = None

        request = ChangePasswordRequest(
            current_password="OldPass123",
            new_password="NewPass456",
        )

        with pytest.raises(UserNotFoundError):
            await auth_service.change_password(uuid4(), request)

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test password change with incorrect current password."""
        mock_staff_repository.get_by_id.return_value = mock_staff

        request = ChangePasswordRequest(
            current_password="WrongPassword",
            new_password="NewPass456",
        )

        with patch(
            "grins_platform.services.auth_service.pwd_context.verify",
            return_value=False,
        ), pytest.raises(InvalidCredentialsError):
            await auth_service.change_password(mock_staff.id, request)

    @pytest.mark.asyncio
    async def test_change_password_no_existing_hash(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test password change when user has no password set."""
        mock_staff.password_hash = None
        mock_staff_repository.get_by_id.return_value = mock_staff

        request = ChangePasswordRequest(
            current_password="AnyPassword",
            new_password="NewPass456",
        )

        with pytest.raises(InvalidCredentialsError):
            await auth_service.change_password(mock_staff.id, request)


@pytest.mark.unit
class TestAuthServiceGetCurrentUser:
    """Test get_current_user method.

    Validates: Requirement 18.4
    """

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
        mock_staff: MagicMock,
    ) -> None:
        """Test getting current user from valid token."""
        access_token = auth_service._create_access_token(mock_staff.id, UserRole.ADMIN)
        mock_staff_repository.get_by_id.return_value = mock_staff

        user = await auth_service.get_current_user(access_token)

        assert user == mock_staff

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(
        self,
        auth_service: AuthService,
    ) -> None:
        """Test getting current user with expired token."""
        user_id = uuid4()
        expired_token = auth_service._create_access_token(
            user_id, UserRole.ADMIN, timedelta(hours=-1),
        )

        with pytest.raises(TokenExpiredError):
            await auth_service.get_current_user(expired_token)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(
        self,
        auth_service: AuthService,
    ) -> None:
        """Test getting current user with invalid token."""
        with pytest.raises(InvalidTokenError):
            await auth_service.get_current_user("invalid.token")

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(
        self,
        auth_service: AuthService,
        mock_staff_repository: AsyncMock,
    ) -> None:
        """Test getting current user when user no longer exists."""
        user_id = uuid4()
        access_token = auth_service._create_access_token(user_id, UserRole.ADMIN)
        mock_staff_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFoundError):
            await auth_service.get_current_user(access_token)


@pytest.mark.unit
class TestAuthServiceRoleMapping:
    """Test role mapping functionality.

    Validates: Requirement 17.1
    """

    def test_get_user_role_admin(
        self,
        auth_service: AuthService,
        mock_staff: MagicMock,
    ) -> None:
        """Test admin staff maps to ADMIN role."""
        mock_staff.role = "admin"

        role = auth_service.get_user_role(mock_staff)

        assert role == UserRole.ADMIN

    def test_get_user_role_sales(
        self,
        auth_service: AuthService,
        mock_staff: MagicMock,
    ) -> None:
        """Test sales staff maps to MANAGER role."""
        mock_staff.role = "sales"

        role = auth_service.get_user_role(mock_staff)

        assert role == UserRole.MANAGER

    def test_get_user_role_tech(
        self,
        auth_service: AuthService,
        mock_staff: MagicMock,
    ) -> None:
        """Test tech staff maps to TECH role."""
        mock_staff.role = "tech"

        role = auth_service.get_user_role(mock_staff)

        assert role == UserRole.TECH

    def test_get_user_role_unknown_defaults_to_tech(
        self,
        auth_service: AuthService,
        mock_staff: MagicMock,
    ) -> None:
        """Test unknown role defaults to TECH."""
        mock_staff.role = "unknown_role"

        role = auth_service.get_user_role(mock_staff)

        assert role == UserRole.TECH
