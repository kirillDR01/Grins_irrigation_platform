"""
Authentication Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for authentication-related API operations,
including login, token management, and password changes.

Validates: Requirements 14.1-14.8, 16.1-16.4, 18.1-18.8
"""

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from grins_platform.models.enums import UserRole

# Password validation error messages
_ERR_PASSWORD_LENGTH = "Password must be at least 8 characters long"
_ERR_PASSWORD_UPPERCASE = "Password must contain at least one uppercase letter"
_ERR_PASSWORD_LOWERCASE = "Password must contain at least one lowercase letter"
_ERR_PASSWORD_NUMBER = "Password must contain at least one number"


class LoginRequest(BaseModel):
    """Schema for login request.

    Validates: Requirements 14.1, 18.1
    """

    username: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Username for authentication",
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Password for authentication",
    )
    remember_me: bool = Field(
        default=False,
        description="Whether to extend session duration",
    )


class UserResponse(BaseModel):
    """Schema for user information in responses.

    Validates: Requirements 18.4
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    name: str = Field(..., description="Full name")
    email: EmailStr | None = Field(default=None, description="Email address")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")


class LoginResponse(BaseModel):
    """Schema for login response.

    Validates: Requirements 14.1-14.2, 18.1, 18.6-18.8
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="Authenticated user information")
    csrf_token: str = Field(..., description="CSRF token for state-changing requests")


class TokenResponse(BaseModel):
    """Schema for token refresh response.

    Validates: Requirements 18.3, 18.8
    """

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class ChangePasswordRequest(BaseModel):
    """Schema for password change request.

    Validates: Requirements 16.1-16.4, 18.5
    """

    current_password: str = Field(
        ...,
        min_length=1,
        description="Current password for verification",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 chars, uppercase, lowercase, number)",
    )

    @field_validator("new_password")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets strength requirements.

        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number

        Validates: Requirements 16.1-16.4
        """
        if len(v) < 8:
            raise ValueError(_ERR_PASSWORD_LENGTH)

        if not re.search(r"[A-Z]", v):
            raise ValueError(_ERR_PASSWORD_UPPERCASE)

        if not re.search(r"[a-z]", v):
            raise ValueError(_ERR_PASSWORD_LOWERCASE)

        if not re.search(r"\d", v):
            raise ValueError(_ERR_PASSWORD_NUMBER)

        return v
