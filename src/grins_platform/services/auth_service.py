"""
Authentication service for user authentication and authorization.

This module provides the AuthService class for all authentication-related
business operations including login, token management, and password handling.

Validates: Requirements 14.1-14.8, 16.1-16.8
"""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from grins_platform.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import UserRole

if TYPE_CHECKING:
    from grins_platform.models.staff import Staff
    from grins_platform.repositories.staff_repository import StaffRepository
    from grins_platform.schemas.auth import ChangePasswordRequest, UpdateProfileRequest

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Account lockout configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Bcrypt cost factor
BCRYPT_ROUNDS = 12


class BcryptContext:
    """Simple bcrypt wrapper to replace passlib CryptContext."""

    def hash(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False


pwd_context = BcryptContext()


class AuthService(LoggerMixin):
    """Service for authentication operations.

    This class handles all authentication logic including user login,
    token generation/verification, password management, and account lockout.

    Attributes:
        repository: StaffRepository for database operations

    Validates: Requirements 14.1-14.8, 16.1-16.8
    """

    DOMAIN = "auth"

    def __init__(self, repository: StaffRepository) -> None:
        """Initialize service with repository.

        Args:
            repository: StaffRepository for database operations
        """
        super().__init__()
        self.repository = repository

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt with cost factor 12.

        Args:
            password: Plain text password to hash

        Returns:
            Bcrypt hashed password string

        Validates: Requirement 15.8
        """
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Bcrypt hashed password to compare against

        Returns:
            True if password matches, False otherwise

        Validates: Requirement 16.1
        """
        return pwd_context.verify(plain_password, hashed_password)

    def _create_access_token(
        self,
        user_id: UUID,
        role: UserRole,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT access token.

        Args:
            user_id: User's UUID
            role: User's role
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT access token

        Validates: Requirement 14.3
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        expire = datetime.now(UTC) + expires_delta
        to_encode: dict[str, Any] = {
            "sub": str(user_id),
            "role": role.value,
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def _create_refresh_token(
        self,
        user_id: UUID,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT refresh token.

        Args:
            user_id: User's UUID
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT refresh token

        Validates: Requirement 14.4
        """
        if expires_delta is None:
            expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        expire = datetime.now(UTC) + expires_delta
        to_encode: dict[str, Any] = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
        }
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify and decode an access token.

        Args:
            token: JWT access token to verify

        Returns:
            Decoded token payload

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid or not an access token

        Validates: Requirement 14.5
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except JWTError as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError from e
            raise InvalidTokenError from e
        else:
            if payload.get("type") != "access":
                raise InvalidTokenError
            return payload

    def verify_refresh_token(self, token: str) -> dict[str, Any]:
        """Verify and decode a refresh token.

        Args:
            token: JWT refresh token to verify

        Returns:
            Decoded token payload

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid or not a refresh token

        Validates: Requirement 14.6
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except JWTError as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError from e
            raise InvalidTokenError from e
        else:
            if payload.get("type") != "refresh":
                raise InvalidTokenError
            return payload

    def _is_account_locked(self, staff: Staff) -> bool:
        """Check if account is currently locked.

        Args:
            staff: Staff member to check

        Returns:
            True if account is locked, False otherwise

        Validates: Requirement 16.5
        """
        if staff.locked_until is None:
            return False
        # Use naive UTC datetime for comparison with database TIMESTAMP WITHOUT TIME ZONE
        now_utc = datetime.now(UTC).replace(tzinfo=None)
        return bool(now_utc < staff.locked_until)

    async def _handle_failed_login(self, staff: Staff) -> None:
        """Handle a failed login attempt.

        Increments failed attempt counter and locks account if threshold reached.

        Args:
            staff: Staff member who failed login

        Validates: Requirements 16.5-16.7
        """
        staff.failed_login_attempts += 1

        if staff.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            # Use naive UTC datetime for database TIMESTAMP WITHOUT TIME ZONE
            now_utc = datetime.now(UTC).replace(tzinfo=None)
            staff.locked_until = now_utc + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES,
            )
            self.log_rejected(
                "login",
                reason="account_locked",
                username=staff.username,
                failed_attempts=staff.failed_login_attempts,
            )

        _ = await self.repository.update_auth_fields(
            staff.id,
            failed_login_attempts=staff.failed_login_attempts,
            locked_until=staff.locked_until,
        )

    async def _handle_successful_login(self, staff: Staff) -> None:
        """Handle a successful login.

        Resets failed attempt counter and updates last login timestamp.

        Args:
            staff: Staff member who logged in successfully

        Validates: Requirement 16.7
        """
        # Use naive UTC datetime for database TIMESTAMP WITHOUT TIME ZONE
        now_utc = datetime.now(UTC).replace(tzinfo=None)
        _ = await self.repository.update_auth_fields(
            staff.id,
            failed_login_attempts=0,
            locked_until=None,
            last_login=now_utc,
        )

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> tuple[Staff, str, str, str]:
        """Authenticate a user with username and password.

        Args:
            username: User's username
            password: User's password

        Returns:
            Tuple of (staff, access_token, refresh_token, csrf_token)

        Raises:
            InvalidCredentialsError: If username or password is invalid
            AccountLockedError: If account is locked due to failed attempts

        Validates: Requirements 14.1-14.2, 16.5-16.7
        """
        self.log_started("authenticate", username=username)

        # Find user by username
        staff = await self.repository.find_by_username(username)
        if staff is None:
            self.log_rejected(
                "authenticate",
                reason="user_not_found",
                username=username,
            )
            raise InvalidCredentialsError

        # Check if login is enabled
        if not staff.is_login_enabled:
            self.log_rejected(
                "authenticate",
                reason="login_disabled",
                username=username,
            )
            raise InvalidCredentialsError

        # Check if account is locked
        if self._is_account_locked(staff):
            self.log_rejected(
                "authenticate",
                reason="account_locked",
                username=username,
            )
            raise AccountLockedError

        # Verify password
        if staff.password_hash is None or not self._verify_password(
            password,
            staff.password_hash,
        ):
            await self._handle_failed_login(staff)
            self.log_rejected(
                "authenticate",
                reason="invalid_password",
                username=username,
            )
            raise InvalidCredentialsError

        # Successful login
        await self._handle_successful_login(staff)

        # Get user role from staff role
        user_role = self.get_user_role(staff)

        # Generate tokens
        access_token = self._create_access_token(staff.id, user_role)
        refresh_token = self._create_refresh_token(staff.id)
        csrf_token = secrets.token_urlsafe(32)

        self.log_completed("authenticate", user_id=str(staff.id), username=username)
        return staff, access_token, refresh_token, csrf_token

    def get_user_role(self, staff: Staff) -> UserRole:
        """Map staff role to user role.

        Args:
            staff: Staff member

        Returns:
            Corresponding UserRole

        Validates: Requirement 17.1
        """
        role_mapping = {
            "admin": UserRole.ADMIN,
            "sales": UserRole.MANAGER,  # Sales staff get manager role
            "tech": UserRole.TECH,
        }
        return role_mapping.get(staff.role, UserRole.TECH)

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, int]:
        """Generate a new access token using a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Tuple of (new_access_token, expires_in_seconds)

        Raises:
            TokenExpiredError: If refresh token has expired
            InvalidTokenError: If refresh token is invalid
            UserNotFoundError: If user no longer exists

        Validates: Requirement 14.7
        """
        self.log_started("refresh_access_token")

        payload = self.verify_refresh_token(refresh_token)
        user_id = payload.get("sub")

        if user_id is None:
            raise InvalidTokenError

        # Get user to verify they still exist and get current role
        staff = await self.repository.get_by_id(UUID(user_id))
        if staff is None:
            raise UserNotFoundError

        if not staff.is_login_enabled:
            raise InvalidTokenError

        user_role = self.get_user_role(staff)
        access_token = self._create_access_token(staff.id, user_role)

        self.log_completed("refresh_access_token", user_id=user_id)
        return access_token, ACCESS_TOKEN_EXPIRE_MINUTES * 60

    async def change_password(
        self,
        user_id: UUID,
        request: ChangePasswordRequest,
    ) -> None:
        """Change a user's password.

        Args:
            user_id: ID of the user changing password
            request: Password change request with current and new password

        Raises:
            UserNotFoundError: If user not found
            InvalidCredentialsError: If current password is incorrect

        Validates: Requirements 16.1-16.4, 18.5
        """
        self.log_started("change_password", user_id=str(user_id))

        staff = await self.repository.get_by_id(user_id)
        if staff is None:
            raise UserNotFoundError

        # Verify current password
        if staff.password_hash is None or not self._verify_password(
            request.current_password,
            staff.password_hash,
        ):
            self.log_rejected(
                "change_password",
                reason="invalid_current_password",
                user_id=str(user_id),
            )
            raise InvalidCredentialsError

        # Hash and save new password
        new_hash = self._hash_password(request.new_password)
        _ = await self.repository.update_auth_fields(user_id, password_hash=new_hash)

        self.log_completed("change_password", user_id=str(user_id))

    async def update_profile(
        self,
        user_id: UUID,
        request: UpdateProfileRequest,
    ) -> Staff:
        """Update a user's profile information.

        Args:
            user_id: ID of the user to update
            request: Profile update request

        Returns:
            Updated staff member

        Raises:
            UserNotFoundError: If user not found
        """
        self.log_started("update_profile", user_id=str(user_id))

        staff = await self.repository.get_by_id(user_id)
        if staff is None:
            raise UserNotFoundError

        # Build update dict from non-None fields
        update_data: dict[str, Any] = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.email is not None:
            update_data["email"] = request.email
        if request.phone is not None:
            update_data["phone"] = request.phone

        if update_data:
            updated = await self.repository.update(user_id, update_data)
            if updated is None:
                raise UserNotFoundError
            self.log_completed("update_profile", user_id=str(user_id))
            return updated

        self.log_completed("update_profile", user_id=str(user_id), no_changes=True)
        return staff

    async def get_current_user(self, token: str) -> Staff:
        """Get the current user from an access token.

        Args:
            token: Valid access token

        Returns:
            Staff member associated with the token

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid
            UserNotFoundError: If user not found

        Validates: Requirement 18.4
        """
        payload = self.verify_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise InvalidTokenError

        staff = await self.repository.get_by_id(UUID(user_id))
        if staff is None:
            raise UserNotFoundError

        return staff
