"""
Authentication API endpoints.

This module provides FastAPI endpoints for authentication operations
including login, logout, token refresh, and password management.

Validates: Requirements 14.1-14.8, 16.8, 18.1-18.8
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,
    get_auth_service,
)
from grins_platform.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
)
from grins_platform.models.staff import Staff
from grins_platform.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserResponse,
)
from grins_platform.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie settings
REFRESH_TOKEN_COOKIE = "refresh_token"
CSRF_TOKEN_COOKIE = "csrf_token"
COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def _create_user_response(staff: Staff, auth_service: AuthService) -> UserResponse:
    """Create UserResponse from Staff model.

    Args:
        staff: Staff member
        auth_service: AuthService for role mapping

    Returns:
        UserResponse with user information
    """
    return UserResponse(
        id=staff.id,
        username=staff.username or "",
        name=staff.name,
        email=staff.email,
        role=auth_service.get_user_role(staff),
        is_active=staff.is_active,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user",
    description="Authenticate with username/password. Returns access token.",
)
async def login(
    request: LoginRequest,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    """Authenticate user with username and password.

    Returns access token in response body and sets refresh token as HttpOnly cookie.
    Also sets CSRF token cookie (not HttpOnly) for state-changing requests.

    Validates: Requirements 14.1-14.2, 16.8, 18.1, 18.6-18.8
    """
    try:
        result = await auth_service.authenticate(
            request.username,
            request.password,
        )
        staff, access_token, refresh_token, csrf_token = result
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from e
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is locked. Please try again later.",
        ) from e

    # Set refresh token as HttpOnly cookie
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )

    # Set CSRF token cookie (not HttpOnly so JS can read it)
    response.set_cookie(
        key=CSRF_TOKEN_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )

    user_response = _create_user_response(staff, auth_service)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=15 * 60,  # 15 minutes in seconds
        user=user_response,
        csrf_token=csrf_token,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="Clear authentication cookies to logout user.",
)
async def logout(response: Response) -> None:
    """Logout user by clearing authentication cookies.

    Validates: Requirements 14.8, 16.8, 18.2
    """
    # Clear refresh token cookie
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path="/",
        secure=True,
        samesite="lax",
    )

    # Clear CSRF token cookie
    response.delete_cookie(
        key=CSRF_TOKEN_COOKIE,
        path="/",
        secure=True,
        samesite="lax",
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate new access token using refresh token from cookie.",
)
async def refresh(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_TOKEN_COOKIE)] = None,
) -> TokenResponse:
    """Refresh access token using refresh token from cookie.

    Validates: Requirements 18.3, 18.8
    """
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    try:
        result = await auth_service.refresh_access_token(refresh_token)
        access_token, expires_in = result
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please login again.",
        ) from e
    except (InvalidTokenError, UserNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from e

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_me(
    current_user: CurrentActiveUser,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Get current authenticated user information.

    Validates: Requirement 18.4
    """
    return _create_user_response(current_user, auth_service)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Change the current user's password.",
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentActiveUser,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """Change current user's password.

    Validates: Requirement 18.5
    """
    try:
        await auth_service.change_password(current_user.id, request)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        ) from e


__all__ = ["router"]
