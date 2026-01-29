"""Unit tests for authentication schemas.

Tests all schemas in auth.py for:
- Password strength validation
- Required field validation
- Field constraints
- Default values

Validates: Requirements 14.1-14.8, 16.1-16.4, 18.1-18.8
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.models.enums import UserRole
from grins_platform.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserResponse,
)

# Rebuild models that use forward references
UserResponse.model_rebuild()
LoginResponse.model_rebuild()


@pytest.mark.unit
class TestLoginRequest:
    """Test LoginRequest schema validation."""

    def test_valid_login_request(self) -> None:
        """Test valid login request with all fields."""
        data = LoginRequest(
            username="admin",
            password="password123",
            remember_me=True,
        )
        assert data.username == "admin"
        assert data.password == "password123"
        assert data.remember_me is True

    def test_valid_login_request_defaults(self) -> None:
        """Test login request with default remember_me."""
        data = LoginRequest(
            username="user",
            password="secret",
        )
        assert data.remember_me is False

    def test_empty_username_rejected(self) -> None:
        """Test that empty username is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username="", password="password123")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("username",) for e in errors)

    def test_missing_username_rejected(self) -> None:
        """Test that missing username is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(password="password123")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("username",) for e in errors)

    def test_empty_password_rejected(self) -> None:
        """Test that empty password is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username="admin", password="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("password",) for e in errors)

    def test_missing_password_rejected(self) -> None:
        """Test that missing password is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username="admin")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("password",) for e in errors)

    def test_username_max_length(self) -> None:
        """Test username max length constraint (50 chars)."""
        # Valid: exactly 50 chars
        data = LoginRequest(username="a" * 50, password="password")
        assert len(data.username) == 50

        # Invalid: 51 chars
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username="a" * 51, password="password")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("username",) for e in errors)


@pytest.mark.unit
class TestChangePasswordRequest:
    """Test ChangePasswordRequest schema with password strength validation."""

    def test_valid_password_change(self) -> None:
        """Test valid password change request."""
        data = ChangePasswordRequest(
            current_password="oldPassword1",
            new_password="NewPassword1",
        )
        assert data.current_password == "oldPassword1"
        assert data.new_password == "NewPassword1"

    def test_password_too_short_rejected(self) -> None:
        """Test password under 8 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="old",
                new_password="Short1",  # Only 6 chars
            )
        errors = exc_info.value.errors()
        assert any(
            "at least 8 characters" in str(e.get("msg", "")).lower()
            for e in errors
        )

    def test_password_missing_uppercase_rejected(self) -> None:
        """Test password without uppercase letter is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="old",
                new_password="lowercase1",  # No uppercase
            )
        errors = exc_info.value.errors()
        assert any(
            "uppercase" in str(e.get("msg", "")).lower()
            for e in errors
        )

    def test_password_missing_lowercase_rejected(self) -> None:
        """Test password without lowercase letter is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="old",
                new_password="UPPERCASE1",  # No lowercase
            )
        errors = exc_info.value.errors()
        assert any(
            "lowercase" in str(e.get("msg", "")).lower()
            for e in errors
        )

    def test_password_missing_number_rejected(self) -> None:
        """Test password without number is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="old",
                new_password="NoNumberHere",  # No number
            )
        errors = exc_info.value.errors()
        assert any(
            "number" in str(e.get("msg", "")).lower()
            for e in errors
        )

    def test_password_exactly_8_chars_valid(self) -> None:
        """Test password with exactly 8 characters is valid."""
        data = ChangePasswordRequest(
            current_password="old",
            new_password="Abcdefg1",  # Exactly 8 chars
        )
        assert len(data.new_password) == 8

    def test_password_max_length(self) -> None:
        """Test password max length constraint (128 chars)."""
        # Valid: exactly 128 chars
        long_password = "A" + "a" * 125 + "1" + "b"  # 128 chars with requirements
        data = ChangePasswordRequest(
            current_password="old",
            new_password=long_password,
        )
        assert len(data.new_password) == 128

        # Invalid: 129 chars
        too_long = "A" + "a" * 126 + "1" + "b"  # 129 chars
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="old",
                new_password=too_long,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("new_password",) for e in errors)

    def test_empty_current_password_rejected(self) -> None:
        """Test empty current password is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="",
                new_password="ValidPass1",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("current_password",) for e in errors)

    def test_missing_current_password_rejected(self) -> None:
        """Test missing current password is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(new_password="ValidPass1")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("current_password",) for e in errors)


@pytest.mark.unit
class TestUserResponse:
    """Test UserResponse schema."""

    def test_valid_user_response(self) -> None:
        """Test valid user response with all fields."""
        user_id = uuid4()
        data = UserResponse(
            id=user_id,
            username="admin",
            name="Admin User",
            email="admin@example.com",
            role=UserRole.ADMIN,
            is_active=True,
        )
        assert data.id == user_id
        assert data.username == "admin"
        assert data.name == "Admin User"
        assert data.email == "admin@example.com"
        assert data.role == UserRole.ADMIN
        assert data.is_active is True

    def test_user_response_optional_email(self) -> None:
        """Test user response with optional email as None."""
        data = UserResponse(
            id=uuid4(),
            username="tech",
            name="Tech User",
            email=None,
            role=UserRole.TECH,
            is_active=True,
        )
        assert data.email is None

    def test_user_response_invalid_email_rejected(self) -> None:
        """Test invalid email format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserResponse(
                id=uuid4(),
                username="user",
                name="User",
                email="not-an-email",
                role=UserRole.TECH,
                is_active=True,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)


@pytest.mark.unit
class TestLoginResponse:
    """Test LoginResponse schema."""

    def test_valid_login_response(self) -> None:
        """Test valid login response with all fields."""
        user = UserResponse(
            id=uuid4(),
            username="admin",
            name="Admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
            is_active=True,
        )
        data = LoginResponse(
            access_token="jwt.token.here",
            token_type="bearer",
            expires_in=900,
            user=user,
            csrf_token="csrf-token-value",
        )
        assert data.access_token == "jwt.token.here"
        assert data.token_type == "bearer"
        assert data.expires_in == 900
        assert data.user.username == "admin"
        assert data.csrf_token == "csrf-token-value"

    def test_login_response_default_token_type(self) -> None:
        """Test login response uses default token type."""
        user = UserResponse(
            id=uuid4(),
            username="user",
            name="User",
            email=None,
            role=UserRole.TECH,
            is_active=True,
        )
        data = LoginResponse(
            access_token="token",
            expires_in=900,
            user=user,
            csrf_token="csrf",
        )
        assert data.token_type == "bearer"


@pytest.mark.unit
class TestTokenResponse:
    """Test TokenResponse schema."""

    def test_valid_token_response(self) -> None:
        """Test valid token response."""
        data = TokenResponse(
            access_token="new.jwt.token",
            token_type="bearer",
            expires_in=900,
        )
        assert data.access_token == "new.jwt.token"
        assert data.token_type == "bearer"
        assert data.expires_in == 900

    def test_token_response_default_token_type(self) -> None:
        """Test token response uses default token type."""
        data = TokenResponse(
            access_token="token",
            expires_in=900,
        )
        assert data.token_type == "bearer"

    def test_missing_access_token_rejected(self) -> None:
        """Test missing access token is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TokenResponse(expires_in=900)  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("access_token",) for e in errors)

    def test_missing_expires_in_rejected(self) -> None:
        """Test missing expires_in is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TokenResponse(access_token="token")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("expires_in",) for e in errors)
